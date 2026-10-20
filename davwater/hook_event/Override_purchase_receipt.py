import frappe
from frappe import _, throw
import frappe.defaults

from frappe.utils import flt, cint, nowdate
from frappe.utils import getdate
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt


class QualityInspectionRequiredError(frappe.ValidationError): pass


inspection_fieldname_map = {
    "Purchase Receipt": "inspection_required_before_purchase",
    "Purchase Invoice": "inspection_required_before_purchase",
    "Sales Invoice": "inspection_required_before_delivery",
    "Delivery Note": "inspection_required_before_delivery"
}


class OverridePurchaseReceipt(PurchaseReceipt):

    def validate_inspection(self):
        # Quality Inspection is created after the receipt is submitted (see make_quality_inspection),
        # so the standard "inspection must exist before save/submit" checks are skipped for Purchase Receipt.
        return


@frappe.whitelist()
def check_qc_is_created(doc_name):
    result = frappe.db.sql("""select * from `tabQuality Inspection` 
                where reference_name = '{0}'""".format(doc_name))
    if result:
        return True
    else:
        return False


@frappe.whitelist()
def make_qc(doc_name):
    if doc_name:
        doc = frappe.get_doc("Purchase Receipt", doc_name)
        count = 0
        for row in doc.get('items'):
            inspection_required_fieldname = inspection_fieldname_map.get(doc.doctype)
            if (inspection_required_fieldname and frappe.db.get_value("Item", row.item_code,
                                                                      inspection_required_fieldname)):
                doc.create_quality_inspection(row)
                count = 1
        if count == 0:
            frappe.throw("No item found required Quality Inspection")


def make_quality_inspection(doc1, method):
    doc = frappe.get_doc("Purchase Receipt", doc1.name)
    inspection_required_fieldname = inspection_fieldname_map.get(doc.doctype)
    if doc.generate_quality_inspection:
        for row in doc.get('items'):
            if (inspection_required_fieldname and frappe.db.get_value("Item", row.item_code,
                                                                      inspection_required_fieldname)):
                create_quality_inspection(doc, row)


def create_quality_inspection(self, row):
    if row:
        if frappe.db.get_value('Item', row.item_code, 'has_serial_no'):
            serial_nos = []
            if row.serial_and_batch_bundle:
                sb_doc = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
                for sr in sb_doc.entries:
                    serial_nos.append(sr.serial_no)
            else:
                serial_nos = row.serial_no.split("\n") if row.serial_no else None
            if serial_nos:
                for s in serial_nos:
                    if s and s != " ":
                        quality_inspection = frappe.get_doc({
                            "doctype": "Quality Inspection",
                            "inspection_type": "Incoming",
                            "inspected_by": frappe.session.user,
                            "reference_type": self.doctype,
                            "reference_name": self.name,
                            "item_code": row.get("item_code"),
                            "description": row.get("description"),
                            "sample_size": flt(1),
                            "item_serial_no": s if s else None,
                            "batch_no": row.get("batch_no"),
                            "purchase_receipt_item": row.name
                        }).insert()
                        quality_inspection.save()
            else:
                quality_inspection = frappe.get_doc({
                    "doctype": "Quality Inspection",
                    "inspection_type": "Incoming",
                    "inspected_by": frappe.session.user,
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                    "item_code": row.get("item_code"),
                    "description": row.get("description"),
                    "sample_size": flt(1),
                    "item_serial_no": None,
                    "batch_no": row.get("batch_no"),
                    "purchase_receipt_item": row.name
                }).insert()
                quality_inspection.save()