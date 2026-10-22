import frappe

# Values that used to be hardcoded in the app: (field, doctype, name)
LEGACY_DEFAULTS = [
	("leasing_cost_center", "Cost Center", "Leasing - DW"),
	("customer_care_cost_center", "Cost Center", "Customer care - DW"),
	("trial_cogs_account", "Account", "51106 - COGS for Trial Machine - DW"),
	("machine_on_trial_account", "Account", "15150 - Machine on Trial (CGS) - DW"),
	("cogs_account", "Account", "51105 - Cost of Goods Sold - DW"),
	("lease_assets_cost_account", "Account", "17810 - Lease assets Cost - DW"),
	("vat_account", "Account", "23710 - VAT 5% - DW"),
	("iqc_warehouse", "Warehouse", "Stock under IQC UAE - DW"),
]


def execute():
	settings = frappe.get_single("Dav Water Settings")
	for fieldname, doctype, name in LEGACY_DEFAULTS:
		if not settings.get(fieldname) and frappe.db.exists(doctype, name):
			settings.set(fieldname, name)
	settings.flags.ignore_permissions = True
	settings.save()
