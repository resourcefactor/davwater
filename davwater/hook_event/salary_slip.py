# custom_app/custom_app/overrides.py
import frappe
from frappe import _
from frappe.utils import flt, rounded, getdate
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import (
    process_loan_interest_accrual_and_demand
)


class OverrideSalarySlip(SalarySlip):

    @frappe.whitelist()
    def get_emp_and_working_day_details(self) -> None:
        """First time, load all the components from salary structure"""
        if self.employee:
            self.set("earnings", [])
            self.set("deductions", [])
            self.set("employer_contributions", [])
            if hasattr(self, "loans"):
                self.set("loans", [])

            if self.payroll_frequency:
                self.get_date_details()

            self.validate_dates()

            # getin leave details
            self.get_working_days_details()
            struct = self.check_sal_struct()

            if struct:
                from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip

                self.pull_emp_expense_claim()
                timesheet_config = self._get_ssa_doc().get_timesheet_config()
                self.salary_slip_based_on_timesheet = timesheet_config.based_on_timesheet
                if self.salary_slip_based_on_timesheet:
                    self._timesheet_component = timesheet_config.timesheet_component
                    self.set_time_sheet()
                    self.add_timesheet_earning_component(timesheet_config)
                make_salary_slip(self.salary_structure, self)

            process_loan_interest_accrual_and_demand(self)

    @frappe.whitelist()
    def pull_emp_expense_claim(self):
        self.set("expense_claim", [])
        company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
        total_claim_amount = 0
        expense_lines = frappe.db.sql("""select * from `tabExpense Claim`
					where docstatus = 1 and status = 'Unpaid'
					and posting_date <= '{0}'
					and employee ='{1}'""".format(self.end_date, self.employee), as_dict=True)
        if expense_lines:
            for res in expense_lines:
                amount = flt(res.get('grand_total')) - flt(res.get('total_amount_reimbursed'))
                if company_currency != self.currency:
                    amount = amount / self.exchange_rate
                if amount > 0:
                    self.append("expense_claim", {
                        "expense_claim": res.get('name'),
                        "posting_date": res.get("posting_date"),
                        "amount": amount
                    })
                    total_claim_amount += amount
        else:
            self.set("expense_claim", [])
        self.total_claim_amount = total_claim_amount

    def set_net_pay(self):
        self.total_deduction = self.get_component_totals("deductions")
        self.base_total_deduction = flt(
            flt(self.total_deduction) * flt(self.exchange_rate), self.precision("base_total_deduction")
        )
        self.net_pay = flt(self.gross_pay) - (flt(self.total_deduction) + flt(self.total_loan_repayment)) + flt(
            self.total_claim_amount)
        self.rounded_total = rounded(self.net_pay)
        self.base_net_pay = flt(
            flt(self.net_pay) * flt(self.exchange_rate), self.precision("base_net_pay")
        )
        self.base_rounded_total = flt(rounded(self.base_net_pay), self.precision("base_net_pay"))
        self.hour_rate = flt(self._get_hourly_rate())
        if self.hour_rate:
            self.base_hour_rate = flt(
                flt(self.hour_rate) * flt(self.exchange_rate), self.precision("base_hour_rate")
            )
        self.set_net_total_in_words()

    def _get_hourly_rate(self):
        return frappe.db.get_value(
            "Salary Structure Assignment",
            {"employee": self.employee, "docstatus": 1},
            "hourly_rate",
            order_by="from_date desc",
        )

    def set_time_sheet(self):
        # overtime based: all submitted/billed timesheets up to the slip end date
        self.set("timesheets", [])
        timesheets = frappe.db.sql(
            """ select * from `tabTimesheet` where employee = %(employee)s
            and start_date <= %(end_date)s and (status = 'Submitted' or
            status = 'Billed')""",
            {"employee": self.employee, "end_date": self.end_date},
            as_dict=1,
        )

        for data in timesheets:
            self.append("timesheets", {"time_sheet": data.name, "working_hours": data.total_ot_hours})

    def add_timesheet_earning_component(self, timesheet_config):
        # hourly rate comes from the Salary Structure Assignment (custom field), not the Salary Structure
        self.hour_rate = flt(self._get_hourly_rate())
        self.base_hour_rate = flt(self.hour_rate) * flt(self.exchange_rate)
        self.total_working_hours = sum([d.working_hours or 0.0 for d in self.timesheets]) or 0.0
        wages_amount = self.hour_rate * self.total_working_hours

        self.add_earning_for_hourly_wages(self, timesheet_config.timesheet_component, wages_amount)

    # def on_submit(self):
    # 	super(OverrideSalarySlip, self).on_submit()
    # 	self.create_claim_entry()
    # self.update_claim_status()

    def create_claim_entry(self):
        if self.payroll_entry:
            if self.expense_claim and flt(self.total_claim_amount) > 0:
                jv = frappe.new_doc('Journal Entry')
                jv.voucher_type = 'Journal Entry'
                jv.posting_date = getdate()
                jv.company = self.company

                for res in self.expense_claim:
                    jv.append('accounts', {
                        'account': frappe.get_value("Expense Claim", res.expense_claim, "payable_account"),
                        'debit_in_account_currency': flt(res.amount),
                        'is_advance': 'No',
                        'party_type': "Employee",
                        'party': self.employee,
                        'reference_type': "Expense Claim",
                        'reference_name': res.expense_claim
                    })
                jv.append('accounts', {
                    'account': frappe.get_value("Payroll Entry", self.payroll_entry, "payroll_payable_account"),
                    'credit_in_account_currency': flt(self.total_claim_amount),
                    'is_advance': 'No',
                    'reference_type': "Payroll Entry",
                    'reference_name': self.payroll_entry
                })
                jv.save(ignore_permissions=True)
                jv.submit()

    def update_claim_status(self):
        if self.expense_claim:
            for res in self.expense_claim:
                doc = frappe.get_doc("Expense Claim", res.expense_claim)
                doc.total_amount_reimbursed += flt(res.amount)
                frappe.db.set_value(
                    "Expense Claim", doc.name, "total_amount_reimbursed", doc.total_amount_reimbursed
                )
                doc.set_status()
                frappe.db.set_value("Expense Claim", doc.name, "status", doc.status)

# Override the original method
# SalarySlip.set_time_sheet = set_time_sheet
# SalarySlip.pull_sal_struct = pull_sal_struct

# # Add a custom translation
# _['Salary Slip'].update({
# 	'set_time_sheet': 'Custom Set Time Sheet'
# })
