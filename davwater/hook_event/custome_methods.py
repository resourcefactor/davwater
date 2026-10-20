import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc, map_child_doc


@frappe.whitelist()
def make_service_schedule(source_name, target_doc=None):
    maint_schedule = frappe.db.sql("""select t1.name
		from `tabService Schedule` t1, `tabService Schedule Item` t2
		where t2.parent=t1.name and t2.sales_order=%s and t1.docstatus=1""", source_name)

    if not maint_schedule:
        doclist = get_mapped_doc("Sales Order", source_name, {
            "Sales Order": {
                "doctype": "Service Schedule",
                "validation": {
                    "docstatus": ["=", 1]
                }
            },
            "Sales Order Item": {
                "doctype": "Service Schedule Item",
                "field_map": {
                    "parent": "sales_order"
                },
                "add_if_empty": True
            }
        }, target_doc)

        return doclist


@frappe.whitelist()
def make_service_visit(source_name, target_doc=None):
    visit = frappe.db.sql("""select t1.name
		from `tabService Visit` t1, `tabService Visit Purpose` t2
		where t2.parent=t1.name and t2.prevdoc_docname=%s
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""", source_name)

    if not visit:
        doclist = get_mapped_doc("Sales Order", source_name, {
            "Sales Order": {
                "doctype": "Service Visit",
                "validation": {
                    "docstatus": ["=", 1]
                }
            },
            "Sales Order Item": {
                "doctype": "Service Visit Purpose",
                "field_map": {
                    "parent": "prevdoc_docname",
                    "parenttype": "prevdoc_doctype"
                },
                "add_if_empty": True
            }
        }, target_doc)

        return doclist


@frappe.whitelist()
def make_warnty_service_visit(source_name, target_doc=None):
    def _update_links(source_doc, target_doc, source_parent):
        target_doc.prevdoc_doctype = source_parent.doctype
        target_doc.prevdoc_docname = source_parent.name

    visit = frappe.db.sql("""select t1.name
		from `tabService Visit` t1, `tabService Visit Purpose` t2
		where t2.parent=t1.name and t2.prevdoc_docname=%s
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""", source_name)

    if not visit:
        target_doc = get_mapped_doc("Warranty Claim", source_name, {
            "Warranty Claim": {
                "doctype": "Service Visit",
                "field_map": {}
            }
        }, target_doc)

        source_doc = frappe.get_doc("Warranty Claim", source_name)
        if source_doc.get("item_code"):
            table_map = {
                "doctype": "Service Visit Purpose",
                "postprocess": _update_links
            }
            map_child_doc(source_doc, target_doc, table_map, source_doc)

        return target_doc


@frappe.whitelist()
def make_sales_inv_service_schedule(source_name, target_doc=None):
    doclist = get_mapped_doc("Sales Invoice", source_name, {
        "Sales Invoice": {
            "doctype": "Service Schedule",
            "field_map": {
                "parent": "sales_invoice",
            },
            "validation": {
                "docstatus": ["=", 1]
            }
        },
        "Sales Invoice Item": {
            "doctype": "Service Schedule Item",
        },
    }, target_doc)

    return doclist
