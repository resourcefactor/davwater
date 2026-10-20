import json

import frappe
from frappe import _
import json
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim
from frappe.utils import cstr, flt, get_link_to_form


class OverrideExpenseClaim(ExpenseClaim):
    @frappe.whitelist()
    def calculate_taxes(self):
        self.total_taxes_and_charges = 0
        tax_dict = {}
        for exp in self.expenses:
            if exp.item_tax_template:
                tax_template = frappe.get_doc("Item Tax Template", exp.item_tax_template)
                for res in tax_template.taxes:
                    if res.tax_type not in tax_dict:
                        tax_dict.setdefault(res.tax_type, [])
                    tax_dict[res.tax_type].append({res.tax_type: exp.sanctioned_amount})

        for tax in self.taxes:
            self.round_floats_in(tax)
            if tax.rate:
                if tax.account_head in tax_dict.keys():
                    for i, d in enumerate(tax_dict[tax.account_head]):
                        if tax.account_head in d.keys():
                            tax.taxable_amount = d[tax.account_head]
                            tax_dict[tax.account_head].pop(i)
                        else:
                            tax.taxable_amount = flt(self.total_sanctioned_amount)
                else:
                    tax.taxable_amount = flt(self.total_sanctioned_amount)

                tax.tax_amount = flt(
                    flt(tax.taxable_amount) * flt(tax.rate / 100), tax.precision("tax_amount")
                )

            tax.total = flt(tax.tax_amount) + flt(self.total_sanctioned_amount)
            self.total_taxes_and_charges += flt(tax.tax_amount)
            self.set_base_fields_amount(tax, ["tax_amount", "total"])

        self.round_floats_in(self, ["total_taxes_and_charges"])

        self.grand_total = flt(self.total_sanctioned_amount) + flt(self.total_taxes_and_charges) - flt(
            self.total_advance_amount)
        self.round_floats_in(self, ["grand_total"])
        self.set_base_fields_amount(self, ["grand_total"])

    def set_status(self, update=False):
        status = {"0": "Draft", "1": "Submitted", "2": "Cancelled"}[cstr(self.docstatus or 0)]

        precision = self.precision("grand_total")

        if (
                # set as paid
                self.is_paid
                or (
                        flt(self.total_sanctioned_amount > 0)
                        and (
                                # grand total is reimbursed
                                (
                                        self.docstatus == 1
                                        and flt(self.grand_total, precision) <= flt(self.total_amount_reimbursed,
                                                                                    precision)
                                )
                                # grand total (to be paid) is 0 since linked advances already cover the claimed amount
                                or (flt(self.grand_total, precision) == 0)
                        )
                )
        ) and self.approval_status == "Approved":
            status = "Paid"
        elif (
                flt(self.total_sanctioned_amount) > 0
                and self.docstatus == 1
                and self.approval_status == "Approved"
        ):
            if flt(self.total_amount_reimbursed, precision) > 0:
                status = "Partially Paid"
            else:
                status = "Unpaid"
        elif self.docstatus == 1 and self.approval_status == "Rejected":
            status = "Rejected"

        if update:
            self.db_set("status", status)
            self.publish_update()
            self.notify_update()
        else:
            self.status = status


@frappe.whitelist()
def get_tax_template_tax(item_tax_template, total_sanctioned_amount, data):
    lst = []
    if item_tax_template:
        data = json.loads(data)
        tax_template = frappe.get_doc("Item Tax Template", item_tax_template)
        for res in tax_template.taxes:
            tax_rate = res.tax_rate if res.tax_rate else 0
            sanctioned_amount = data.get('sanctioned_amount') if data.get('sanctioned_amount') else 0
            lst.append({'tax': res.tax_type,
                        'rate': res.tax_rate,
                        'taxable_amount': data.get('sanctioned_amount'),
                        'amount': sanctioned_amount * tax_rate / 100,
                        'total': float(total_sanctioned_amount) + (sanctioned_amount * tax_rate / 100)
                        })
    return lst
