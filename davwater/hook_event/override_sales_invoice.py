import frappe
import erpnext

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

exclude_from_linked_with = True


class OverrideSalesInvoice(SalesInvoice):
	def validate_currency(self):
		pass
