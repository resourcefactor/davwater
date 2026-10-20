import frappe
from frappe import _
from frappe.utils import cint, nowtime, flt
# from davwater.hook_event.util import get_incoming_rate
from erpnext.controllers.sales_and_purchase_return import get_return_against_item_fields, get_filters
from erpnext.controllers.selling_controller import SellingController
from erpnext.stock.utils import get_incoming_rate



def make_sl_entries(self, sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
    from erpnext.stock.stock_ledger import make_sl_entries

    make_sl_entries(sl_entries, allow_negative_stock, via_landed_cost_voucher)


def set_incoming_rate(self):
    if self.doctype not in ("Delivery Note", "Sales Invoice"):
        return

    items = self.get("items") + (self.get("packed_items") or [])
    for d in items:
        if not self.get("return_against"):
            # Get incoming rate based on original item cost based on valuation method
            qty = flt(d.get("stock_qty") or d.get("actual_qty"))

            if not (self.get("is_return") and d.incoming_rate):
                d.incoming_rate = get_incoming_rate(
                    {
                        "item_code": d.item_code,
                        "warehouse": d.warehouse,
                        "posting_date": self.get("posting_date") or self.get("transaction_date"),
                        "posting_time": self.get("posting_time") or nowtime(),
                        "qty": qty if cint(self.get("is_return")) else (-1 * qty),
                        "serial_no": d.get("serial_no"),
                        "company": self.company,
                        "voucher_type": self.doctype,
                        "voucher_no": self.name,
                        "allow_zero_valuation": d.get("allow_zero_valuation"),
                    },
                    raise_error_if_no_rate=False,
                )

            # For internal transfers use incoming rate as the valuation rate
            if self.is_internal_transfer():
                if d.doctype == "Packed Item":
                    incoming_rate = flt(
                        flt(d.incoming_rate, d.precision("incoming_rate")) * d.conversion_factor,
                        d.precision("incoming_rate"),
                    )
                    if d.incoming_rate != incoming_rate:
                        d.incoming_rate = incoming_rate
                else:
                    rate = flt(
                        flt(d.incoming_rate, d.precision("incoming_rate")) * d.conversion_factor,
                        d.precision("rate"),
                    )
                    if d.rate != rate:
                        d.rate = rate
                        frappe.msgprint(
                            _(
                                "Row {0}: Item rate has been updated as per valuation rate since its an internal stock transfer"
                            ).format(d.idx),
                            alert=1,
                        )

                    d.discount_percentage = 0.0
                    d.discount_amount = 0.0
                    d.margin_rate_or_amount = 0.0

        elif self.get("return_against"):
            # Get incoming rate of return entry from reference document
            # based on original item cost as per valuation method
            d.incoming_rate = get_rate_for_return(
                self.doctype, self.name, d.item_code, self.return_against, item_row=d, dl_note=self
            )


def get_rate_for_return(
        voucher_type,
        voucher_no,
        item_code,
        return_against=None,
        item_row=None,
        voucher_detail_no=None,
        sle=None,
        dl_note=None,
):
    if not return_against:
        return_against = frappe.get_cached_value(voucher_type, voucher_no, "return_against")

    return_against_item_field = get_return_against_item_fields(voucher_type)

    filters = get_filters(
        voucher_type,
        voucher_no,
        voucher_detail_no,
        return_against,
        item_code,
        return_against_item_field,
        item_row,
    )

    if voucher_type in ("Purchase Receipt", "Purchase Invoice"):
        select_field = "incoming_rate"
    else:
        select_field = "abs(stock_value_difference / actual_qty)"

    rate = flt(frappe.db.get_value("Stock Ledger Entry", filters, select_field))
    if not (rate and return_against) and voucher_type in ["Sales Invoice"]:
        rate = frappe.db.get_value(f"{voucher_type} Item", voucher_detail_no, "incoming_rate")
        if not rate and sle:
            rate = get_incoming_rate(
                {
                    "item_code": sle.item_code,
                    "warehouse": sle.warehouse,
                    "posting_date": sle.get("posting_date"),
                    "posting_time": sle.get("posting_time"),
                    "qty": sle.actual_qty,
                    "serial_no": sle.get("serial_no"),
                    "company": sle.company,
                    "voucher_type": sle.voucher_type,
                    "voucher_no": sle.voucher_no,
                },
                raise_error_if_no_rate=False,
            )

    if return_against and voucher_type in ["Delivery Note"]:
        qty = flt(item_row.get("stock_qty") or item_row.get("actual_qty"))
        rate = get_incoming_rate(
            {
                "item_code": item_row.item_code,
                "warehouse": item_row.warehouse,
                "posting_date": dl_note.get("posting_date") or dl_note.get("transaction_date"),
                "posting_time": dl_note.get("posting_time") or nowtime(),
                "qty": qty if cint(dl_note.get("is_return")) else (-1 * qty),
                "serial_no": item_row.get("serial_no"),
                "company": dl_note.company,
                "voucher_type": dl_note.doctype,
                "voucher_no": dl_note.name,
                "allow_zero_valuation": item_row.get("allow_zero_valuation"),
            },
            raise_error_if_no_rate=False,
        )
    return rate


SellingController.make_sl_entries = make_sl_entries
SellingController.set_incoming_rate = set_incoming_rate
