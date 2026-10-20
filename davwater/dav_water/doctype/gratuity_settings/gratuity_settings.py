# Copyright (c) 2023, RF and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe.model.document import Document
from datetime import datetime
from frappe.utils import today, getdate, get_last_day, date_diff


class GratuitySettings(Document):
	pass


def create_monthly_gratuity_jv():
	if get_last_day(today()) == getdate(today()):
		try:
			grat_setting = frappe.get_doc("Gratuity Settings")
			# get month name from the current date i.e: current date = (08-12-2023) --> December
			month_name = datetime.strptime(today(), "%Y-%m-%d").strftime("%B")
			# get no. of days in a month
			num_days = get_last_day(today())

			user_remark = "Gratuity Approval For " + month_name
			total_amount = emp_amount = no_of_days_worked = 0

			if not grat_setting.disabled:  # check settings are not disabled
				for d in grat_setting.gratuity_settings_detail:  # for each company
					if frappe.db.get_list("Employee", {"status": "Active", "company": d.company}):
						if not frappe.db.exists("Journal Entry", {"company": d.company, "docstatus": 1, "user_remark": user_remark}):
							new_jv = frappe.new_doc("Journal Entry")
							new_jv.company = d.company
							new_jv.voucher_type = "Journal Entry"
							new_jv.posting_date = today()
							new_jv.user_remark = user_remark
							employees_list = frappe.db.get_list("Employee", {"status": "Active", "company": d.company})
							for row in employees_list:
								emp = frappe.get_doc("Employee", row.name)
								if frappe.db.exists("Salary Structure Assignment", {"docstatus": 1, "employee": row.name}):
									sa = frappe.get_doc("Salary Structure Assignment", {"docstatus": 1, "employee": row.name})
									if emp.date_of_joining.month == getdate(today()).month and emp.date_of_joining.year == getdate(today()).year:
										no_of_days_worked = date_diff(num_days, emp.date_of_joining)
										emp_amount = (sa.base / 365 * 21) / num_days.day * no_of_days_worked
									else:
										no_of_days_worked = num_days.day
										emp_amount = (sa.base / 365 * 21) / num_days.day * no_of_days_worked
									new_jv.append(
										"accounts",
										{
											"account": d.gratuity_accrual_account,
											"credit_in_account_currency": round(emp_amount, 2),
											"cost_center": erpnext.get_default_cost_center(d.company),
											"party_type": "Employee",
											"party": row.name
										},
									)
									total_amount += round(emp_amount, 2)

							new_jv.append(
								"accounts",
								{
									"account": d.gratuity_exp_account,
									"debit_in_account_currency": round(total_amount, 2),
									"cost_center": erpnext.get_default_cost_center(d.company)
								},
							)
							new_jv.insert(ignore_permissions=True)
							new_jv.flags.ignore_permissions = True
							new_jv.submit()
		except Exception as e:
			frappe.log_error(title="Gratuity JV Creation Issue", message=e)
