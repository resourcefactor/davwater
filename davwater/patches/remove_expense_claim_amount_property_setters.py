import frappe


def execute():
	# v16 handles multi currency at claim level: amount / sanctioned_amount are entered in the claim
	# currency, so the v15 read-only + "(Company Currency)" label customizations must go
	for field in ("amount", "sanctioned_amount"):
		for prop in ("read_only", "label"):
			frappe.db.delete(
				"Property Setter",
				{"doc_type": "Expense Claim Detail", "field_name": field, "property": prop},
			)
	frappe.clear_cache(doctype="Expense Claim Detail")
