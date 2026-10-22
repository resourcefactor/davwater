from . import __version__ as app_version

app_name = "davwater"
app_title = "Dav Water"
app_publisher = "RF"
app_description = "Dav Water"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "hamza@rf.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/davwater/css/davwater.css"
app_include_js = [
	"/assets/davwater/js/dav_settings.js",
	"/assets/davwater/js/report_defaults.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/davwater/css/davwater.css"
# web_include_js = "/assets/davwater/js/davwater.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "davwater/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Attendance": "public/js/attendance.js",
	"Delivery Note": "public/js/delivery_note.js",
	"Sales Invoice": "public/js/sales_invoice.js",
	"Sales Order": "public/js/sales_order.js",
	"Shift Type": "public/js/shift_type.js",
	"Timesheet": "public/js/timesheet.js",
	"Salary Slip": "public/js/salary_slip.js",
	"Salary Structure": "public/js/salary_structure.js",
	"Salary Structure Assignment": "public/js/salary_structure_assignment.js",
	"Quality Inspection": "public/js/quality_inspection.js",
	"Purchase Receipt": "public/js/purchase_receipt.js",
	"Item": "public/js/item.js",
	"Expense Claim": "public/js/expense_claim.js",
	"Quotation": "public/js/quotation.js",
	"Item Tax Template": "public/js/item_tax_template.js",
	"Stock Entry": "public/js/stock_entry.js"
}
doctype_list_js = {"Asset": "public/js/asset_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "davwater.install.before_install"
# after_install = "davwater.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "davwater.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Purchase Receipt": "davwater.hook_event.Override_purchase_receipt.OverridePurchaseReceipt",
	"Item": "davwater.hook_event.override_item.OverrideItem",
	"Expense Claim": "davwater.hook_event.expense_claim.OverrideExpenseClaim",
	"GL Entry": "davwater.hook_event.override_gl_entry.OverrideGLEntry",
	"Sales Invoice": "davwater.hook_event.override_sales_invoice.OverrideSalesInvoice",
	"Auto Repeat": "davwater.hook_event.auto_repeat.OverrideAutoRepeat",
	# "Repost Item Valuation": "davwater.hook_event.repost_item_valuation.OverrideRepostItemValuation",
	"Salary Slip": "davwater.hook_event.salary_slip.OverrideSalarySlip",
	"Payroll Entry": "davwater.hook_event.payroll_entry.OverridePayrollEntry",
	# "Stock Ledger Entry": "davwater.hook_event.stock_ledger_entry.OvrStockLedgerEntry",
	"Stock Entry": "davwater.hook_event.stock_entry.OvrStockEntry",
	# "Landed Cost Voucher": "davwater.hook_event.landed_cost_voucher.OvrLandedCostVoucher",
	"Asset Depreciation Schedule": "davwater.hook_event.asset_depreciation_schedule.OverrideAssetDepreciationSchedule",
	"Serial and Batch Bundle": "davwater.hook_event.serial_and_batch_bundle.OvrSerialandBatchBundle"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Delivery Note": {
		"validate": "davwater.hook_event.delivery_note.validate_service_pack_item",
		"on_submit": ["davwater.hook_event.delivery_note.make_service_schedule",
					"davwater.hook_event.delivery_note.create_trial_type_jv",
					"davwater.hook_event.delivery_note.create_assets_item_and_asset_recode",
					"davwater.hook_event.delivery_note.create_device_list_entry"],
		"on_cancel": ["davwater.hook_event.delivery_note.check_service_schedule",
					  # "davwater.hook_event.util.remove_incoming_rate_ln_on_sr_no"
					  ],
		"before_save": ["davwater.hook_event.delivery_note.set_expense_account",
						"davwater.hook_event.delivery_note.set_item_level_lease_value"]
	},
	# "Employee Checkin": {
	# 	"before_save": "davwater.hook_event.custom_shift_type.fetch_shift"
	# },
	"Quality Inspection": {
		"on_submit": "davwater.hook_event.customize_quality_inspection.make_stock_entry"
	},
	"Stock Entry": {
		"on_submit": "davwater.hook_event.util.make_stock_entry_qc",
		"on_cancel": ["davwater.hook_event.util.remove_incoming_rate_ln_on_sr_no"]
	},
	"Purchase Invoice": {
		"validate": "davwater.hook_event.util.calculate_purchase_recoverable_std_exp",
		"on_cancel": ["davwater.hook_event.util.remove_incoming_rate_ln_on_sr_no"]
	},
	"Purchase Receipt": {
		"on_cancel": ["davwater.hook_event.util.remove_incoming_rate_ln_on_sr_no"],
		"on_submit": ["davwater.hook_event.Override_purchase_receipt.make_quality_inspection"]
	},
	"Sales Invoice": {
		"on_submit": ["davwater.hook_event.delivery_note.create_reverse_jv",
					  "davwater.hook_event.delivery_note.create_sales_invoice_auto_repeat"],
		# 'validate': 'davwater.hook_event.util.set_lease_income_acc_sinv'
	},
	"Sales Order": {
		"before_save": "davwater.hook_event.delivery_note.set_item_level_lease_value"
	},
	"Expense Claim": {
		"validate": "davwater.hook_event.util.validate_exchange_rate_expense_claim"
	},
	"*": {
		"on_cancel": "davwater.hook_event.util.disabled_auto_repeat"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	# "hourly": [
	# 	"davwater.hook_event.custom_shift_type.set_attendance_summary"
	# ],
	"daily": [
		# "davwater.dav_water.doctype.gratuity_settings.gratuity_settings.create_monthly_gratuity_jv",
		"davwater.hook_event.schedulars_methods.send_customer_notification",
		"davwater.hook_event.schedulars_methods.send_without_service_pack_notification",
		"davwater.dav_water.doctype.currency_exchange_settings_ew.currency_exchange_settings_ew.update_exchange_currency_rate"
	],
	"cron": {
		"0 10 * * *": [
			"davwater.dav_water.doctype.xe_currency_exchange_setting.xe_currency_exchange_setting.update_xe_exchange_currency_rate"
		],
		"1 0 * * *": "davwater.dav_water.doctype.gratuity_settings.gratuity_settings.create_monthly_gratuity_jv",
	}
}

# Testing
# -------

# before_tests = "davwater.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.controllers.stock_controller.make_quality_inspections": "davwater.hook_event.util.make_quality_inspections",
	# "erpnext.stock.utils.get_incoming_rate": "davwater.hook_event.util.get_incoming_rate",
	"erpnext.stock.doctype.stock_entry.stock_entry.get_warehouse_details": "davwater.hook_event.stock_entry.get_warehouse_details"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Delivery Note": "davwater.hook_event.delivery_note_dashboard.get_data",
	"Purchase Receipt": "davwater.hook_event.override_purchase_receipt_dashboard.get_data",
	"Quality Inspection": "davwater.hook_event.quality_inspection_dashboard.get_data",
	"Stock Entry": "davwater.hook_event.stock_entry_dashboard.get_data"
}
# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"davwater.auth.validate"
# ]

