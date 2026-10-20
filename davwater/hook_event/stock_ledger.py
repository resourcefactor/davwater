import frappe
import datetime
import copy
from frappe.utils import flt, get_time, getdate, cstr
from erpnext.stock.stock_ledger import update_entries_after
from erpnext.stock.utils import (get_serial_nos_data)


def build(self):
    from erpnext.controllers.stock_controller import future_sle_exists

    if self.args.get("sle_id"):
        self.process_sle_against_current_timestamp()
        if not future_sle_exists(self.args):
            self.update_bin()
    else:
        entries_to_fix = self.get_future_entries_to_fix()

        i = 0
        while i < len(entries_to_fix):
            sle = entries_to_fix[i]
            i += 1

            self.process_sle(sle)
            self.update_bin_data(sle)
            # update_serial_line_incoming_rate(sle)

            if sle.dependant_sle_voucher_detail_no:
                entries_to_fix = self.get_dependent_entries_to_fix(entries_to_fix, sle)

    if self.exceptions:
        self.raise_exceptions()


def update_serial_line_incoming_rate(sle):

    if sle.get("serial_no"):
        serial_nos = cstr(sle.serial_no).split("\n")
        incoming_rate = sle.get("incoming_rate") or sle.get("outgoing_rate")
        if (len(serial_nos) > 0 and sle.get("voucher_type") == "Stock Entry"
                and frappe.get_value("Stock Entry", sle.get("voucher_no"), "stock_entry_type") == "Material Transfer"):

            dd = getdate(sle.get('posting_date'))
            tt = get_time(sle.get('posting_time'))
            posting_time = datetime.datetime.combine(dd, tt)
            for sr_no in serial_nos:
                inc_rate = frappe.db.sql("""select snc.incoming_rate 
                        from `tabItem Wise Serial No Cost` as snc 
                        inner join `tabStock Entry Detail` std on std.s_warehouse = snc.warehouse and std.item_code = snc.item_code
                        where std.name = '{0}' and snc.parent = '{1}'
                        and snc.update_time <= '{2}' limit 1 """.format(sle.get("voucher_detail_no"),
                                                                        sr_no, posting_time))
                if inc_rate:
                    incoming_rate = flt(inc_rate[0][0]) or 0
                    frappe.db.sql(
                        """update `tabItem Wise Serial No Cost` set incoming_rate= {0}
                            where parent = '{1}' and voucher_no = '{2}'""".format(incoming_rate, sr_no, sle.get("voucher_no")))
        else:

            frappe.db.sql(
                """update `tabItem Wise Serial No Cost` set incoming_rate=%s
                    where parent in ({0}) and voucher_no = '{1}'""".format(
                    ", ".join(["%s"] * len(serial_nos)), sle.get("voucher_no")
                ),
                tuple([incoming_rate] + serial_nos),
            )


def get_serialized_values(self, sle):
    from erpnext.stock.serial_batch_bundle import SerialNoValuation

    incoming_rate = flt(sle.incoming_rate)
    actual_qty = flt(sle.actual_qty)
    serial_nos = cstr(sle.serial_no).split("\n")

    if incoming_rate < 0:
        # wrong incoming rate
        incoming_rate = self.wh_data.valuation_rate

    stock_value_change = 0
    if sle.voucher_type == "Delivery Note":
        dl_doc = frappe.get_doc("Delivery Note", sle.voucher_no)
        if dl_doc.is_return:
            incoming_values = self.get_incoming_value_for_serial_nos(sle, serial_nos)
            incoming_rate = flt(incoming_values/ len(serial_nos))
            sle.incoming_rate = incoming_rate
    if actual_qty > 0:
        stock_value_change = actual_qty * incoming_rate
    else:
        # In case of delivery/stock issue, get average purchase rate
        # of serial nos of current entry
        if not sle.is_cancelled:
            new_sle = copy.deepcopy(sle)
            new_sle.qty = new_sle.actual_qty
            new_sle.serial_nos = get_serial_nos_data(new_sle.get("serial_no"))

            sn_obj = SerialNoValuation(
                sle=new_sle, warehouse=new_sle.get("warehouse"), item_code=new_sle.get("item_code")
            )

            outgoing_value = sn_obj.get_incoming_rate()
            stock_value_change = actual_qty * outgoing_value
        else:
            stock_value_change = actual_qty * sle.outgoing_rate

    new_stock_qty = self.wh_data.qty_after_transaction + actual_qty

    if new_stock_qty > 0:
        new_stock_value = (
                                  self.wh_data.qty_after_transaction * self.wh_data.valuation_rate
                          ) + stock_value_change
        if new_stock_value >= 0:
            # calculate new valuation rate only if stock value is positive
            # else it remains the same as that of previous entry
            self.wh_data.valuation_rate = new_stock_value / new_stock_qty

    if self.wh_data.valuation_rate is None and sle.voucher_detail_no:
        allow_zero_rate = self.check_if_allow_zero_valuation_rate(sle.voucher_type, sle.voucher_detail_no)
        if not allow_zero_rate:
            self.wh_data.valuation_rate = self.get_fallback_rate(sle)


# def get_incoming_value_for_serial_nos(self, sle, serial_nos):
#     # get rate from serial nos within same company
#     # all_serial_nos = frappe.get_all(
#     #     "Serial No", fields=["purchase_rate", "name", "company"], filters={"name": ("in", serial_nos)}
#     # )
#
#     # incoming_values = sum(flt(d.purchase_rate) for d in all_serial_nos if d.company == sle.company)
#     incoming_values = 0
#     dd = getdate(sle.get('posting_date'))
#     tt = get_time(sle.get('posting_time'))
#     posting_time = datetime.datetime.combine(dd, tt)
#     for serial_no in serial_nos:
#         result = frappe.db.sql("""select ifnull(incoming_rate, 0) from `tabItem Wise Serial No Cost`
#                     where parent = '{0}' and item_code ='{1}'
#                     and warehouse = '{2}'
#                     and update_time < '{3}'
#                     order by update_time desc limit 1""".format(serial_no, sle.get("item_code"),
#                                                                 sle.get("warehouse"), posting_time))
#         rate = result[0][0] if result else 0
#         if not rate:
#             result = frappe.db.sql("""select ifnull(purchase_rate, 0) from `tabSerial No`
#                         where name = '{0}' and item_code ='{1}'
#                         and warehouse = '{2}'""".format(serial_no, sle.get("item_code"), sle.get("warehouse")))
#             rate = result[0][0] if result else 0
#         if not rate:
#             result = frappe.db.sql("""select ifnull(purchase_rate, 0) from `tabSerial No`
#                         where name = '{0}'""".format(serial_no))
#             rate = result[0][0] if result else 0
#         incoming_values += rate
#     return incoming_values


def get_incoming_value_for_serial_nos(self, sle, serial_nos):
    # get rate from serial nos within same company
    all_serial_nos = frappe.get_all(
        "Serial No", fields=["purchase_rate", "name", "company"], filters={"name": ("in", serial_nos)}
    )

    # incoming_values = sum(flt(d.purchase_rate) for d in all_serial_nos if d.company == sle.company)
    incoming_values = 0
    dd = getdate(sle.get('posting_date'))
    tt = get_time(sle.get('posting_time'))
    posting_time = datetime.datetime.combine(dd, tt)
    # Get rate for serial nos which has been transferred to other company
    invalid_serial_nos = [d.name for d in all_serial_nos if d.company != sle.company]
    for serial_no in invalid_serial_nos:
        result = frappe.db.sql("""select ifnull(incoming_rate, 0) from `tabItem Wise Serial No Cost` 
                    where parent = '{0}' and item_code ='{1}' 
                    and warehouse = '{2}' 
                    and update_time < '{3}' 
                    order by update_time desc limit 1""".format(serial_no, sle.get("item_code"),
                                                                sle.get("warehouse"), posting_time))
        incoming_rate = result[0][0] if result else 0
        if not incoming_rate:
            incoming_rate = frappe.db.sql(
                """
                select incoming_rate
                from `tabStock Ledger Entry`
                where
                    company = %s
                    and actual_qty > 0
                    and is_cancelled = 0
                    and (serial_no = %s
                        or serial_no like %s
                        or serial_no like %s
                        or serial_no like %s
                    )
                order by posting_date desc
                limit 1
            """,
                (sle.company, serial_no, serial_no + "\n%", "%\n" + serial_no, "%\n" + serial_no + "\n%"),
            )
        if not incoming_rate:
            result = frappe.db.sql("""select ifnull(purchase_rate, 0) from `tabSerial No` 
                        where name = '{0}' and item_code ='{1}' 
                        and warehouse = '{2}'""".format(serial_no, sle.get("item_code"), sle.get("warehouse")))
            incoming_rate = result[0][0] if result else 0
        if not incoming_rate:
            result = frappe.db.sql("""select ifnull(purchase_rate, 0) from `tabSerial No` 
                        where name = '{0}'""".format(serial_no))
            incoming_rate = result[0][0] if result else 0

        incoming_values += flt(incoming_rate[0][0]) if incoming_rate else 0

    return incoming_values


update_entries_after.build = build
update_entries_after.get_serialized_values = get_serialized_values
update_entries_after.get_incoming_value_for_serial_nos = get_incoming_value_for_serial_nos