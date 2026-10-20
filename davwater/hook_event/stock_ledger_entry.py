import frappe
from frappe import _
import datetime
from frappe.utils import cint,flt, get_datetime, getdate, get_time
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import StockLedgerEntry
# from erpnext.stock.doctype.serial_no.serial_no import (get_item_details, validate_serial_no, get_auto_serial_nos,
#                                                        get_serial_nos, get_link_to_form, get_items_html)


class OvrStockLedgerEntry(StockLedgerEntry):
    def on_submit(self):
        self.check_stock_frozen_date()
        self.calculate_batch_qty()

        # if not self.get("via_landed_cost_voucher"):
        #     process_serial_no(self)


# def process_serial_no(sle):
#     item_det = get_item_details(sle.item_code)
#     validate_serial_no(sle, item_det)
#     update_serial_nos(sle, item_det)


# def update_serial_nos(sle, item_det):
#     if sle.skip_update_serial_no:
#         return
#     if (
#             not sle.is_cancelled
#             and not sle.serial_no
#             and cint(sle.actual_qty) > 0
#             and item_det.has_serial_no == 1
#             and item_det.serial_no_series
#     ):
#         serial_nos = get_auto_serial_nos(item_det.serial_no_series, sle.actual_qty)
#         sle.db_set("serial_no", serial_nos)
#         validate_serial_no(sle, item_det)
#     if sle.serial_no:
#         auto_make_serial_nos(sle)
#
#
# def auto_make_serial_nos(args):
#     serial_nos = get_serial_nos(args.get("serial_no"))
#     created_numbers = []
#     voucher_type = args.get("voucher_type")
#     item_code = args.get("item_code")
#     for serial_no in serial_nos:
#         is_new = False
#         if frappe.db.exists("Serial No", serial_no):
#             sr = frappe.get_cached_doc("Serial No", serial_no)
#         elif args.get("actual_qty", 0) > 0:
#             sr = frappe.new_doc("Serial No")
#             is_new = True
#
#         sr = update_args_for_serial_no(sr, serial_no, args, is_new=is_new)
#         if is_new:
#             created_numbers.append(sr.name)
#
#     form_links = list(map(lambda d: get_link_to_form("Serial No", d), created_numbers))
#
#     # Setting up tranlated title field for all cases
#     singular_title = _("Serial Number Created")
#     multiple_title = _("Serial Numbers Created")
#
#     if voucher_type:
#         multiple_title = singular_title = _("{0} Created").format(voucher_type)
#
#     if len(form_links) == 1:
#         frappe.msgprint(_("Serial No {0} Created").format(form_links[0]), singular_title)
#     elif len(form_links) > 0:
#         message = _("The following serial numbers were created: <br><br> {0}").format(
#             get_items_html(form_links, item_code)
#         )
#         frappe.msgprint(message, multiple_title)
#
#
# def update_args_for_serial_no(serial_no_doc, serial_no, args, is_new=False):
#     for field in ["item_code", "work_order", "company", "batch_no", "supplier", "location"]:
#         if args.get(field):
#             serial_no_doc.set(field, args.get(field))
#
#     serial_no_doc.via_stock_ledger = args.get("via_stock_ledger") or True
#     serial_no_doc.warehouse = args.get("warehouse") if args.get("actual_qty", 0) > 0 else None
#
#     update_exit = True
#     incoming_rate = flt(args.get("incoming_rate")) if flt(args.get("incoming_rate")) else flt(serial_no_doc.get('purchase_rate'))
#     print("------update_exit", update_exit, incoming_rate)
#     if args.get("voucher_type") == "Delivery Note":
#         is_return = frappe.get_value("Delivery Note", args.get("voucher_no"), "is_return")
#         if not is_return:
#             update_exit = False
#         else:
#             inc_rate = get_delivery_note_return_in_rate(serial_no)
#             if flt(inc_rate) > 0:
#                 incoming_rate = inc_rate
#     else:
#         if args.get("voucher_type") == "Stock Entry":
#             stock_entry_type = frappe.get_value("Stock Entry", args.get("voucher_no"), "stock_entry_type")
#             if stock_entry_type == "Material Issue":
#                 update_exit = False
#             if stock_entry_type == "Material Transfer":
#                 incoming_rate = flt(serial_no_doc.get('purchase_rate'))
#     print("---------fff", incoming_rate)
#     if "item_s_cost" in serial_no_doc.as_dict().keys() and serial_no_doc.get('item_s_cost'):
#         for res in serial_no_doc.get('item_s_cost'):
#             if (res.item_code == args.get("item_code") and res.warehouse == args.get("warehouse")
#                     and res.voucher_no == args.get("voucher_no") and flt(res.incoming_rate) == incoming_rate):
#                 print("-----ddddd")
#                 update_exit = False
#     print("--------4------", update_exit)
#     dd = getdate(args.get('posting_date'))
#     tt = get_time(args.get('posting_time'))
#     posting_time = datetime.datetime.combine(dd, tt)
#     if update_exit and flt(args.get("incoming_rate")):
#         serial_no_doc.append("item_s_cost", {
#             "item_code": args.get("item_code"),
#             "warehouse": args.get("warehouse"),
#             "incoming_rate":  incoming_rate,
#             "update_time":  posting_time,
#             "voucher_no":  args.get("voucher_no")
#         })
#
#     if is_new:
#         serial_no_doc.serial_no = serial_no
#
#     if (
#             serial_no_doc.sales_order
#             and args.get("voucher_type") == "Stock Entry"
#             and not args.get("actual_qty", 0) > 0
#     ):
#         serial_no_doc.sales_order = None
#
#     serial_no_doc.validate_item()
#     serial_no_doc.update_serial_no_reference(serial_no)
#
#     if is_new:
#         serial_no_doc.insert(ignore_permissions=True, ignore_mandatory=True)
#     else:
#         serial_no_doc.save(ignore_permissions=True)
#
#     return serial_no_doc
#
#
# def get_delivery_note_return_in_rate(serial_no):
#     result = frappe.db.sql("""select ifnull(incoming_rate, 0) from `tabItem Wise Serial No Cost`
#             where parent = '{0}'
#             order by update_time desc limit 1""".format(serial_no))
#     rate = result[0][0] if result else 0
#
#     if not rate:
#         result = frappe.db.sql("""select ifnull(purchase_rate, 0)
#             from `tabSerial No` where name = '{0}' """.format(serial_no))
#         rate = result[0][0] if result else 0
#
#     return flt(rate)