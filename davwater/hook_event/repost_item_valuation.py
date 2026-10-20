import frappe
from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import RepostItemValuation


class OverrideRepostItemValuation(RepostItemValuation):
    def validate(self):
        self.set_company()
        # self.validate_period_closing_voucher()
        self.set_status(write=False)
        self.reset_field_values()
        self.validate_accounts_freeze()
        self.reset_recreate_stock_ledgers()
        self.validate_recreate_stock_ledgers()
