import frappe
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import LandedCostVoucher


class OvrLandedCostVoucher(LandedCostVoucher):
    def update_rate_in_serial_no_for_non_asset_items(self, receipt_document):
        for item in receipt_document.get("items"):
            if not item.is_fixed_asset and item.serial_no:
                serial_nos = get_serial_nos(item.serial_no)
                if serial_nos:
                    frappe.db.sql(
                        "update `tabSerial No` set purchase_rate=%s where name in ({0})".format(
                            ", ".join(["%s"] * len(serial_nos))
                        ),
                        tuple([item.valuation_rate] + serial_nos),
                    )
                    frappe.db.sql(
                        """update `tabItem Wise Serial No Cost` set incoming_rate=%s 
                            where parent in ({0}) and voucher_no = '{1}'""".format(
                            ", ".join(["%s"] * len(serial_nos)), receipt_document.get('name')
                        ),
                        tuple([item.valuation_rate] + serial_nos),
                    )