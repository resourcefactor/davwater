import frappe
from frappe import _, msgprint
from frappe.utils import rounded, flt
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry
from hrms.hr.doctype.expense_claim.expense_claim import (
    get_outstanding_amount_for_claim,
)


def validate_expense_claim(self):
    pass
    for d in self.accounts:
        if d.reference_type == "Expense Claim":
            outstanding_amt = get_outstanding_amount_for_claim(d.reference_name)
            if rounded(d.debit) > rounded(outstanding_amt):
                frappe.throw(
                    _(
                        "Row No {0}: Amount cannot be greater than the Outstanding Amount against Expense Claim {1}. Outstanding Amount is {2}"
                    ).format(d.idx, d.reference_name, outstanding_amt)
                )


def validate_total_debit_and_credit(self):
    self.set_total_debit_credit()
    if -1 >= self.difference or self.difference >= 1:
        frappe.throw(
            _("Total Debit must be equal to Total Credit. The difference is {0}").format(self.difference)
        )

@frappe.whitelist()
def get_balance(self):
    if not self.get("accounts"):
        msgprint(_("'Entries' cannot be empty"), raise_exception=True)
    else:
        self.total_debit, self.total_credit = 0, 0
        diff = flt(self.difference, self.precision("difference"))

        # If any row without amount, set the diff on that row
        if diff:
            blank_row = None
            for d in self.get("accounts"):
                if not d.credit_in_account_currency and not d.debit_in_account_currency and diff != 0:
                    blank_row = d

            if not blank_row:
                blank_row = self.append("accounts", {})
            rounding_acc = frappe.get_value("Company", self.company, "round_off_account")
            cost_center = frappe.get_value("Company", self.company, "cost_center")
            blank_row.account = rounding_acc
            blank_row.cost_center = cost_center
            blank_row.exchange_rate = 1
            if diff > 0:
                blank_row.credit_in_account_currency = diff
                blank_row.credit = diff
            elif diff < 0:
                blank_row.debit_in_account_currency = abs(diff)
                blank_row.debit = abs(diff)

        self.validate_total_debit_and_credit()


JournalEntry.validate_expense_claim = validate_expense_claim
JournalEntry.validate_total_debit_and_credit = validate_total_debit_and_credit
JournalEntry.get_balance = get_balance
