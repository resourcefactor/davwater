import frappe
from frappe.utils import getdate


@frappe.whitelist()
def validate_holidays(holiday, date):
	date = getdate(date)
	holidays = frappe.get_doc("Holiday List", holiday)
	holiday_list = [d.holiday_date for d in holidays.holidays]
	if date in holiday_list:
		return 1
	else:
		return 0
