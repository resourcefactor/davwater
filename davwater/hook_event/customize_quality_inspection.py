
import frappe
from frappe import _
import json
from frappe.utils import flt, nowdate, getdate
from erpnext.stock.get_item_details import get_item_price, check_packing_list
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults


def make_stock_entry(doc, method):
    if doc:
        if doc.finish_item and doc.reference_type in ("Purchase Receipt", "Stock Entry"):
            p = frappe.get_doc( doc.reference_type, doc.reference_name)
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.quality_inspection = doc.name
            stock_entry.purpose = "Manufacture"
            stock_entry.stock_entry_type = "Manufacture"
            stock_entry.company = p.company
            stock_entry.posting_date = doc.report_date
            stock_entry.set_posting_time = 1
            s_warehouse = None
            rate = 0
            if doc.purchase_receipt_item:
                s_warehouse, rate = frappe.db.get_values("Purchase Receipt Item", doc.purchase_receipt_item, ["warehouse", "rate"])[0]

            if doc.stock_entry_item:
                s_warehouse, rate = frappe.db.get_values("Stock Entry Detail", doc.stock_entry_item, ["t_warehouse", "basic_rate"])[0]

            stock_uom = frappe.db.get_values("Item", doc.item_code, ["stock_uom"])[0]
            stock_entry.append("items", {
                "item_code": doc.item_code,
                "qty": doc.sample_size,
                "s_warehouse": s_warehouse,
                "basic_rate": rate,
                "uom ": stock_uom,
                "batch_no": doc.batch_no,
                "serial_no": doc.item_serial_no
            })
            for res in doc.raw_material_item:
                stock_entry.append("items", {
                    "item_code": res.item_code,
                    "qty": res.qty,
                    "s_warehouse": res.s_warehouse,
                    "basic_rate": res.rate,
                    "uom ": res.uom
                })
            for res in doc.finish_item:
                stock_entry.append("items", {
                    "item_code": res.item_code,
                    "qty": res.qty,
                    "t_warehouse": res.t_warehouse,
                    "basic_rate": res.rate,
                    "uom ": res.uom,
                    "serial_no": doc.item_serial_no,
                    "is_finished_item": 1
                })
            # stock_entry.insert()
            try:
                stock_entry.insert()
            except Exception:
                pass
            stock_entry.submit()

@frappe.whitelist()
def get_valuation_rate(item_code, company, warehouse=None):
    item = get_item_defaults(item_code, company)
    item_group = get_item_group_defaults(item_code, company)
    brand = get_brand_defaults(item_code, company)
    # item = frappe.get_doc("Item", item_code)
    rate = 0
    if item.get("is_stock_item"):
        if not warehouse:
            warehouse = item.get("default_warehouse") or item_group.get("default_warehouse") or brand.get(
                "default_warehouse")

        rate = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse},
                                   ["valuation_rate"], as_dict=True) or {"valuation_rate": 0}

    elif not item.get("is_stock_item"):
        valuation_rate = frappe.db.sql("""select sum(base_net_amount) / sum(qty*conversion_factor)
            from `tabPurchase Invoice Item`
            where item_code = %s and docstatus=1""", item_code)

        if valuation_rate:
            rate = {"valuation_rate": valuation_rate[0][0] or 0.0}
    else:
        rate = {"valuation_rate": 0.0}

    return rate.get('valuation_rate')

@frappe.whitelist()
def get_bom_material(bom):
    if bom:
        item_data = {'material': [], 'finish': []}
        bom_doc = frappe.get_doc("BOM", bom)
        for res in bom_doc.items:
            item_data['material'].append({
                'item_code': res.item_code,
                'item_name': res.item_name,
                'qty': res.qty,
                'uom': res.uom,
                'rate': res.rate,
                'amount': res.amount
            })
        item_data['finish'].append({
            'item_code': bom_doc.item,
            'item_name': bom_doc.item_name,
            'qty': bom_doc.quantity,
            'uom': bom_doc.uom,
        })
        return item_data
