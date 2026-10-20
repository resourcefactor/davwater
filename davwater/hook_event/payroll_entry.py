import frappe
from frappe import _
from frappe.utils import flt, getdate, rounded
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
    submit_salary_slips_for_employees as hrms_submit_salary_slips_for_employees,
)


class OverridePayrollEntry(PayrollEntry):
    @frappe.whitelist(methods=["POST"])
    def submit_salary_slips(self) -> None:
        self.check_permission("write")
        salary_slips = self.get_sal_slip_list(ss_status=0)

        if len(salary_slips) > 30 or frappe.flags.enqueue_payroll_entry:
            self.db_set("status", "Queued")
            frappe.enqueue(
                submit_salary_slips_for_employees,
                timeout=3000,
                payroll_entry=self,
                salary_slips=salary_slips,
                publish_progress=False,
            )
            frappe.msgprint(
                _("Salary Slip submission is queued. It may take a few minutes"),
                alert=True,
                indicator="blue",
            )
        else:
            submit_salary_slips_for_employees(self, salary_slips, publish_progress=False)

    @frappe.whitelist()
    def make_expense_claim_jv(self):
        salary_slip_name_list = frappe.db.sql(
            """ select t1.name from `tabSalary Slip` t1
            where t1.docstatus = 1 and start_date >= %s and end_date <= %s and t1.payroll_entry = %s
            """,
            (self.start_date, self.end_date, self.name),
            as_list=True,
        )

        if salary_slip_name_list and len(salary_slip_name_list) > 0:
            salary_claim_total = 0
            company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
            jv = frappe.new_doc('Journal Entry')
            jv.voucher_type = 'Journal Entry'
            jv.posting_date = self.posting_date
            jv.company = self.company
            jv.multi_currency = 1
            for salary_slip_name in salary_slip_name_list:
                salary_slip = frappe.get_doc("Salary Slip", salary_slip_name[0])

                for res in salary_slip.expense_claim:
                    amount = flt(res.amount)
                    if company_currency != self.currency:
                        amount = flt(res.amount * salary_slip.exchange_rate)
                    jv.append('accounts', {
                        'account': frappe.get_value("Expense Claim", res.expense_claim, "payable_account"),
                        'debit_in_account_currency': amount,
                        'is_advance': 'No',
                        'party_type': "Employee",
                        'party': salary_slip.employee,
                        'reference_type': "Expense Claim",
                        'reference_name': res.expense_claim
                    })
                    salary_claim_total += amount
            if company_currency != self.currency:
                salary_claim_total = flt(salary_claim_total / salary_slip.exchange_rate)
            jv.append('accounts', {
                'account': self.payroll_payable_account,
                'credit_in_account_currency': flt(salary_claim_total),
                'is_advance': 'No',
                'reference_type': "Payroll Entry",
                'reference_name': self.name
            })
            if flt(salary_claim_total) > 0:
                jv.save(ignore_permissions=True)
                if jv.difference:
                    jv.get_balance()
                jv.submit()


def submit_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=True):
    # standard submission, followed by the Journal Entry that settles the expense claims on the slips
    hrms_submit_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=publish_progress)
    payroll_entry.make_expense_claim_jv()
