import frappe
import json
from frappe.utils import flt
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry, get_previous_sle
# from davwater.hook_event.util import get_incoming_rate
from erpnext.stock.utils import get_incoming_rate


class OvrStockEntry(StockEntry):

    def validate(self):
        super(OvrStockEntry, self).validate()
        if self.stock_entry_type in ["Manufacture", "Material Transfer for Manufacture", "Send to Subcontractor", "Repack", "Material Transfer"]:
            stock_adjustment_account = frappe.get_value("Company", self.company, "stock_adjustment_account")
            if not stock_adjustment_account:
                frappe.throw("Set stock adjustment account on company level.")
            for res in self.items:
                res.expense_account = stock_adjustment_account

    def set_rate_for_outgoing_items(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
        outgoing_items_cost = 0.0
        for d in self.get("items"):
            if d.s_warehouse:
                if reset_outgoing_rate:
                    args = self.get_args_for_incoming_rate(d)
                    rate = get_incoming_rate(args, raise_error_if_no_rate)
                    if rate > 0:
                        d.basic_rate = rate

                d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))
                if not d.t_warehouse:
                    outgoing_items_cost += flt(d.basic_amount)

        return outgoing_items_cost

    def validate_serial_nos_and_batches_with_bundle(self, row):
        # the "bundle already created, remove serial/batch values" error is intentionally disabled
        pass


@frappe.whitelist()
def get_warehouse_details(args):
    if isinstance(args, str):
        args = json.loads(args)

    args = frappe._dict(args)

    ret = {}
    if args.warehouse and args.item_code:
        args.update(
            {
                "posting_date": args.posting_date,
                "posting_time": args.posting_time,
            }
        )
        ret = {
            "actual_qty": get_previous_sle(args).get("qty_after_transaction") or 0,
            "basic_rate": get_incoming_rate(args),
        }
    return ret
