import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    make_custom_fields()
    add_permissions()

def make_custom_fields(update=True):
    is_zero_rated = dict(fieldname='is_zero_rated', label='Is Zero Rated',
                         fieldtype='Check', fetch_from='item_code.is_zero_rated',
                         insert_after='description', print_hide=1)
    custom_fields = {
        'Item': [
            dict(fieldname='is_zero_rated', label='Is Zero Rated',
                 fieldtype='Check', insert_after='item_group',
                 print_hide=1)
        ],
        'Sales Invoice Item': is_zero_rated,
        'Purchase Invoice Item': is_zero_rated,
        'Sales Taxes and Charges': is_zero_rated,
        'Purchase Taxes and Charges': is_zero_rated
    }

    create_custom_fields(custom_fields, update=update)

def add_permissions():
    if not frappe.db.get_value('Custom Role', dict(report="VAT Audit Report")):
        frappe.get_doc(dict(
            doctype='Custom Role',
            report="VAT Audit Report",
            roles=[
                dict(role='Accounts User'),
                dict(role='Accounts Manager'),
                dict(role='Auditor')
            ]
        )).insert()
