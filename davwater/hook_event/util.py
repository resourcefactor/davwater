import frappe
import json
from frappe import _
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate, get_time
import erpnext
import datetime
from erpnext.stock.utils import get_valuation_method, get_fifo_rate, get_valid_serial_nos


@frappe.whitelist()
def make_quality_inspections(
    company=None, doctype=None, docname=None, items=None, inspection_type="Incoming"
):
    if doctype != 'Purchase Receipt':
        if isinstance(items, str):
            items = json.loads(items)

        inspections = []
        for item in items:
            if flt(item.get("sample_size")) > flt(item.get("qty")):
                frappe.throw(
                    _("{item_name}'s Sample Size ({sample_size}) cannot be greater than the Accepted Quantity ({accepted_quantity})").format(
                        item_name=item.get("item_name"),
                        sample_size=item.get("sample_size"),
                        accepted_quantity=item.get("qty")
                    ))

            quality_inspection = frappe.get_doc({
                "company": company,
                "doctype": "Quality Inspection",
                "inspection_type": inspection_type,
                "inspected_by": frappe.session.user,
                "reference_type": doctype,
                "reference_name": docname,
                "item_code": item.get("item_code"),
                "description": item.get("description"),
                "sample_size": flt(item.get("sample_size")),
                "item_serial_no": item.get("serial_no").split("\n")[0] if item.get("serial_no") else None,
                "batch_no": item.get("batch_no"),
                "child_row_reference": item.get("child_row_reference"),
            })
            quality_inspection.save()
            inspections.append(quality_inspection.name)

        return inspections


def make_stock_entry_qc(self, method):
    if self.generate_quality_inspection:
        for row in self.get('items'):
            create_quality_inspection(self, row)


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
                            "stock_entry_item": row.name
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
                    "stock_entry_item": row.name
                }).insert()
                quality_inspection.save()


# def set_lease_income_acc_sinv(doc, method):
#     for res in doc.items:
#         if res.sales_order:
#             sl = frappe.get_doc("Sales Order", res.sales_order)
#             if sl.type_of_sale == 'Lease with Service Pack':
#                 res.income_account = '40115 - Leasing Revenue - DW'


def disabled_auto_repeat(doc, method):
    auto_repeat = frappe.get_value("Auto Repeat", {'reference_doctype': doc.doctype, 'reference_document': doc.name},
                                   "name")
    if auto_repeat:
        ar = frappe.get_doc("Auto Repeat", auto_repeat)
        ar.disabled = True
        ar.db_update()


def calculate_purchase_recoverable_std_exp(doc, method):
    if doc.reverse_charge == "N":
        recoverable_standard_rated_expenses = 0
        for res in doc.taxes:
            if res.account_head == "23710 - VAT 5% - DW":
                recoverable_standard_rated_expenses += res.base_tax_amount

        doc.recoverable_standard_rated_expenses = recoverable_standard_rated_expenses


def validate_exchange_rate_expense_claim(doc, method):
    if doc.exchange_rate == 0:
        frappe.throw("Exchange Rate should not be zero")


@frappe.whitelist()
def get_incoming_rate(args, raise_error_if_no_rate=True):
    """Get Incoming Rate based on valuation method"""
    from erpnext.stock.stock_ledger import get_previous_sle, get_valuation_rate

    if isinstance(args, str):
        args = json.loads(args)

    in_rate = 0
    if (args.get("serial_no") or "").strip():
        in_rate = get_avg_purchase_rate(args.get("serial_no"), args)
    else:
        valuation_method = get_valuation_method(args.get("item_code"))
        previous_sle = get_previous_sle(args)
        if valuation_method == "FIFO":
            if previous_sle:
                previous_stock_queue = json.loads(previous_sle.get("stock_queue", "[]") or "[]")
                in_rate = (
                    get_fifo_rate(previous_stock_queue, args.get("qty") or 0) if previous_stock_queue else 0
                )
        elif valuation_method == "Moving Average":
            in_rate = previous_sle.get("valuation_rate") or 0

    if not in_rate:
        voucher_no = args.get("voucher_no") or args.get("name")
        in_rate = get_valuation_rate(
            args.get("item_code"),
            args.get("warehouse"),
            args.get("voucher_type"),
            voucher_no,
            args.get("allow_zero_valuation"),
            currency=erpnext.get_company_currency(args.get("company")),
            company=args.get("company"),
            raise_error_if_no_rate=raise_error_if_no_rate,
        )

    return flt(in_rate)


# @frappe.whitelist()
# def get_incoming_rate(args, raise_error_if_no_rate=True):
#     """Get Incoming Rate based on valuation method"""
#     from erpnext.stock.stock_ledger import get_previous_sle, get_valuation_rate
#
#     if isinstance(args, str):
#         args = json.loads(args)
#
#     in_rate = None
#
#     item_details = frappe.get_cached_value(
#         "Item", args.get("item_code"), ["has_serial_no", "has_batch_no"], as_dict=1
#     )
#
#     use_moving_avg_for_batch = frappe.db.get_single_value("Stock Settings", "do_not_use_batchwise_valuation")
#
#     if isinstance(args, dict):
#         args = frappe._dict(args)
#
#     if item_details and item_details.has_serial_no and args.get("serial_and_batch_bundle"):
#         args.actual_qty = args.qty
#         sn_obj = SerialNoValuation(
#             sle=args,
#             warehouse=args.get("warehouse"),
#             item_code=args.get("item_code"),
#         )
#
#         return sn_obj.get_incoming_rate()
#
#     elif (
#             item_details
#             and item_details.has_batch_no
#             and args.get("serial_and_batch_bundle")
#             and not use_moving_avg_for_batch
#     ):
#         args.actual_qty = args.qty
#         batch_obj = BatchNoValuation(
#             sle=args,
#             warehouse=args.get("warehouse"),
#             item_code=args.get("item_code"),
#         )
#
#         return batch_obj.get_incoming_rate()
#
#     elif (args.get("serial_no") or "").strip() and not args.get("serial_and_batch_bundle"):
#         args.actual_qty = args.qty
#         args.serial_nos = get_serial_nos_data(args.get("serial_no"))
#
#         sn_obj = SerialNoValuation(sle=args, warehouse=args.get("warehouse"), item_code=args.get("item_code"))
#
#         return sn_obj.get_incoming_rate()
#     elif args.get("batch_no") and not args.get("serial_and_batch_bundle") and not use_moving_avg_for_batch:
#         args.actual_qty = args.qty
#         args.batch_nos = frappe._dict({args.batch_no: args})
#
#         batch_obj = BatchNoValuation(
#             sle=args,
#             warehouse=args.get("warehouse"),
#             item_code=args.get("item_code"),
#         )
#
#         return batch_obj.get_incoming_rate()
#     else:
#         valuation_method = get_valuation_method(args.get("item_code"))
#         previous_sle = get_previous_sle(args)
#         if valuation_method in ("FIFO", "LIFO"):
#             if previous_sle:
#                 previous_stock_queue = json.loads(previous_sle.get("stock_queue", "[]") or "[]")
#                 in_rate = (
#                     _get_fifo_lifo_rate(previous_stock_queue, args.get("qty") or 0, valuation_method)
#                     if previous_stock_queue
#                     else None
#                 )
#         elif valuation_method == "Moving Average":
#             in_rate = previous_sle.get("valuation_rate")
#
#     if in_rate is None:
#         voucher_no = args.get("voucher_no") or args.get("name")
#         in_rate = get_valuation_rate(
#             args.get("item_code"),
#             args.get("warehouse"),
#             args.get("voucher_type"),
#             voucher_no,
#             args.get("allow_zero_valuation"),
#             currency=erpnext.get_company_currency(args.get("company")),
#             company=args.get("company"),
#             raise_error_if_no_rate=raise_error_if_no_rate,
#         )
#
#     return flt(in_rate)



def get_avg_purchase_rate(serial_nos, args):
    """get average value of serial numbers"""

    serial_nos = get_valid_serial_nos(serial_nos)
    total_rate = 0
    dd = getdate(args.get('posting_date'))
    tt = get_time(args.get('posting_time'))
    posting_time = datetime.datetime.combine(dd, tt)
    for s in serial_nos:
        result = frappe.db.sql("""select ifnull(incoming_rate, 0) from `tabItem Wise Serial No Cost` 
                where parent = '{0}' and item_code ='{1}' 
                and warehouse = '{2}' 
                and update_time < '{3}' 
                order by update_time desc limit 1""".format(s, args.get("item_code"),
                                                            args.get("warehouse"), posting_time))
        rate = result[0][0] if result else 0
        if not rate:
            result = frappe.db.sql("""select ifnull(purchase_rate, 0) from `tabSerial No` 
                where name = '{0}' and item_code ='{1}' 
                and warehouse = '{2}'""".format(s, args.get("item_code"), args.get("warehouse")))
            rate = result[0][0] if result else 0
        if not rate:
            result = frappe.db.sql("""select ifnull(purchase_rate, 0) from `tabSerial No` where name = '{0}' """.format(s))
            rate = result[0][0] if result else 0
        total_rate += rate

    return flt(total_rate/ len(serial_nos))


def remove_incoming_rate_ln_on_sr_no(doc, method):
    items = doc.get("items")
    for res in items:
        if res.get("serial_no"):
            serial_nos = []
            if res.serial_and_batch_bundle:
                sb_doc = frappe.get_doc("Serial and Batch Bundle", res.serial_and_batch_bundle)
                for sr in sb_doc.entries:
                    serial_nos.append(sr.serial_no)
            else:
                serial_nos = res.serial_no.split("\n") if res.serial_no else None
            for s in serial_nos:
                frappe.db.sql("""DELETE FROM `tabItem Wise Serial No Cost` WHERE parent = '{0}' 
                        and voucher_no = '{1}'""".format(s, doc.name))



