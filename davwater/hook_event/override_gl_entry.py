import frappe
from frappe import _
import erpnext
from erpnext.accounts.party import validate_party_gle_currency
from erpnext.accounts.utils import get_account_currency
from erpnext.exceptions import InvalidAccountCurrency
from erpnext.accounts.doctype.gl_entry.gl_entry import GLEntry

exclude_from_linked_with = True


class OverrideGLEntry(GLEntry):
	def validate_currency(self):
		company_currency = erpnext.get_company_currency(self.company)
		account_currency = get_account_currency(self.account)

		if not self.account_currency:
			self.account_currency = account_currency or company_currency

		if account_currency != self.account_currency:
			frappe.throw(
				_("{0} {1}: Accounting Entry for {2} can only be made in currency: {3}").format(
					self.voucher_type, self.voucher_no, self.account, (account_currency or company_currency)
				),
				InvalidAccountCurrency,
			)

		if self.party_type and self.party and self.voucher_type not in ('Expense Claim', 'Journal Entry', 'Payment Entry', 'Purchase Invoice'):
			validate_party_gle_currency(self.party_type, self.party, self.company, self.account_currency)
