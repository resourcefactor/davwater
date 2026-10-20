# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe
import copy
from frappe.model.document import Document
from frappe import _
from frappe.utils import today, flt
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts, get_disposal_account_and_cost_center


class LeaseCancellation(Document):

    @frappe.whitelist()
    def get_scheduler_line(self):
        if self.delivery_note:
            ser_maint = frappe.get_doc("Service Schedule", {'delivery_note': self.delivery_note})
            if ser_maint:
                return ser_maint.as_dict()
            else:
                frappe.throw("Data not found")
        return []

    @frappe.whitelist()
    def get_assets(self):
        if self.delivery_note:
            assets = frappe.get_all("Asset", {'delivery_note': self.delivery_note}, 'name')
            if assets:
                return assets
        return []

    def validate(self):
        if self.get("__islocal") and self.delivery_note:
            assets = frappe.get_all("Asset", {'delivery_note': self.delivery_note}, 'name')
            if assets:
                for a in assets:
                    self.append('assets', {
                        'asset': a.get('name')
                    })

    def on_submit(self):
        la_setting = frappe.get_single("Lease Setting")
        if not la_setting.asset_credit_account or not la_setting.asset_debit_account:
            frappe.throw("Please set Credit / Debit account in <b>Lease Setting</b>")

        if not la_setting.to_warehouse:
            frappe.throw("Please set Asset Return Warehouse in <b>Lease Setting</b>")
        if not la_setting.account:
            frappe.throw("Please set Stock Entry Account in <b>Lease Setting</b>")

        item_details = {}
        for res in self.items:
            item_details.setdefault(res.item_code, []).append(res.serial_no or 'dummy')

        for key in item_details.keys():

            sr_lst = copy.deepcopy(item_details[key])
            sr_lst.append("dscds")
            query = """UPDATE `tabService Schedule Detail` SET completion_status = 'Closed' 
                            WHERE item_code ='{0}' and serial_no in {1}  
                            and completion_status = 'Pending'""".format(key, tuple(sr_lst))
            frappe.db.sql(query)

            asset = frappe.get_doc("Asset", {'delivery_note': self.delivery_note, 'item_code': "LA-" + str(key)})

            serial_no_str = "\n".join(filter(lambda x: x != 'dummy', item_details[key]))
            depreciated_amt = max([x.accumulated_depreciation_amount for x in asset.schedules if x.journal_entry] or [0])

            # stock_en_value = (flt(asset.net_purchase_amount) / asset.qty) * (len(item_details[key])) - (depreciated_amt / asset.qty)
            # per_item_value = stock_en_value / len(item_details[key])
            per_item_value = (flt(asset.net_purchase_amount) / asset.qty) * (len(item_details[key])) - ((depreciated_amt / asset.qty) * len(item_details[key]))


            if asset.qty == len(item_details[key]) or asset.qty == 0:
                if asset.docstatus != 1:
                    frappe.throw(_("Asset {0} must be submitted").format(asset.name))
                elif asset.status in ("Cancelled", "Sold", "Scrapped", "Return"):
                    frappe.throw(
                        _("Asset {0} cannot be Return, as it is already {1}").format(asset.name, asset.status)
                    )

                depreciation_series = frappe.get_cached_value(
                    "Company", asset.company, "series_for_depreciation_entry"
                )

                je = frappe.new_doc("Journal Entry")
                je.voucher_type = "Journal Entry"
                je.naming_series = depreciation_series
                je.posting_date = self.return_date
                je.company = asset.company
                je.lease_cancellation = self.name
                je.remark = "Return Entry for asset {0}".format(asset.name)

                for entry in get_gl_entries_on_asset_disposal(asset):
                    entry.update({"reference_type": "Asset", "reference_name": asset.name})
                    je.append("accounts", entry)

                je.flags.ignore_permissions = True
                je.submit()

                frappe.db.set_value("Asset", asset.name, "disposal_date", today())
                frappe.db.set_value("Asset", asset.name, "journal_entry_for_scrap", je.name)

                frappe.msgprint(_("Asset Return via Journal Entry {0}").format(je.name))

            elif asset.qty != len(item_details[key]) and asset.qty != 0:
                residual_value = frappe.get_value("Delivery Note", self.delivery_note, 'residual_value') or 1
                residual_amt = (asset.net_purchase_amount / 100) * residual_value
                (
                    fixed_asset_account,
                    asset,
                    depreciation_cost_center,
                    accumulated_depr_account,
                    accumulated_depr_amount,
                    disposal_account,
                    value_after_depreciation,
                ) = get_asset_details(asset, None)

                new_asset_cost = (flt(value_after_depreciation) / asset.qty) * (asset.qty - len(item_details[key]))
                # new_asset_cost = flt(value_after_depreciation) - new_asset_cost
                exp_life = (residual_amt / asset.qty) * (asset.qty - len(item_details[key]))

                for ass in asset.finance_books:
                    ass.expected_value_after_useful_life = exp_life
                    ass.db_update()
                s_no_lst = asset.serial_no.split('\n')
                serial_nos_str = "\n".join(filter(lambda x: x not in item_details[key], s_no_lst))
                asset.qty = asset.qty - len(item_details[key])
                asset.serial_no = serial_nos_str


                adj_asset = frappe.new_doc("Asset Value Adjustment")
                adj_asset.date = self.return_date
                adj_asset.asset = asset.name
                adj_asset.company = asset.company
                adj_asset.asset_category = asset.asset_category
                adj_asset.current_asset_value = flt(value_after_depreciation)
                adj_asset.new_asset_value = new_asset_cost
                adj_asset.lease_cancellation = self.name
                adj_asset.flags.ignore_permissions = True
                adj_asset.insert(ignore_permissions=True)
                adj_asset.submit()

            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Receipt"
            stock_entry.purpose = "Material Receipt"
            stock_entry.lease_cancellation = self.name
            stock_entry.posting_date = self.return_date
            stock_entry.set_posting_time = 1
            stock_entry.to_warehouse = la_setting.to_warehouse
            item_doc = frappe.get_doc("Item", key)
            stock_entry.append("items", {
                'item_code': item_doc.item_code,
                'item_name': item_doc.item_name,
                'qty': len(item_details[key]),
                'basic_rate': per_item_value,
                'valuation_rate': per_item_value,
                'conversion_factor': 1,
                'uom': item_doc.stock_uom,
                'stock_uom': item_doc.stock_uom,
                'cost_center': 'Leasing - DW',
                'serial_no': serial_no_str,
                'expense_account': la_setting.account
            })
            # stock_entry.set_missing_values()
            stock_entry.insert(ignore_permissions=True)
            stock_entry.submit()

            asset.set_status("Return")
            asset.db_update()

    def on_cancel(self):
        item_details = {}
        for res in self.items:
            item_details.setdefault(res.item_code, []).append(res.serial_no or 'dummy')

        for key in item_details.keys():
            sr_lst = copy.deepcopy(item_details[key])
            sr_lst.append("dscds")
            query = """UPDATE `tabService Schedule Detail` SET completion_status = 'Pending' 
                                   WHERE item_code ='{0}' and serial_no in {1}  
                                   and completion_status = 'Closed'""".format(key, tuple(sr_lst))
            frappe.db.sql(query)

            asset = frappe.get_doc("Asset", {'delivery_note': self.delivery_note, 'item_code': "LA-" + str(key)})

            serial_no_str = "\n".join(item_details[key])
            asset.qty = int(asset.qty) + len(item_details[key])
            asset.serial_no = str(asset.serial_no) + "\n" + serial_no_str
            asset.set_status("Submitted")
            asset.db_update()


def get_gl_entries_on_asset_disposal(asset, selling_amount=0, finance_book=None):
    la_setting = frappe.get_single("Lease Setting")
    (
        fixed_asset_account,
        asset,
        depreciation_cost_center,
        accumulated_depr_account,
        accumulated_depr_amount,
        disposal_account,
        value_after_depreciation,
    ) = get_asset_details(asset, finance_book)

    profit_amount = flt(value_after_depreciation)
    debit_or_credit = profit_amount
    gl_entries = [
        {
            "account": la_setting.asset_credit_account,
            "credit_in_account_currency": asset.net_purchase_amount,
            "credit": asset.net_purchase_amount,
            "cost_center": depreciation_cost_center,
        },
        {
            "account": accumulated_depr_account,
            "debit_in_account_currency": accumulated_depr_amount,
            "debit": accumulated_depr_amount,
            "cost_center": depreciation_cost_center,
        },
        {
            "account": la_setting.asset_debit_account,
            "cost_center": depreciation_cost_center,
            "debit_in_account_currency": abs(flt(value_after_depreciation)),
            "debit": abs(flt(value_after_depreciation))
        }
    ]
    return gl_entries


def get_asset_details(asset, finance_book=None):

    fixed_asset_account, accumulated_depr_account, depr_expense_account = get_depreciation_accounts(
        asset
    )
    disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(asset.company)
    depreciation_cost_center = asset.cost_center or depreciation_cost_center

    idx = 1
    if finance_book:
        for d in asset.finance_books:
            if d.finance_book == finance_book:
                idx = d.idx
                break

    value_after_depreciation = (
        asset.finance_books[idx - 1].value_after_depreciation
        if asset.calculate_depreciation
        else asset.value_after_depreciation
    )
    accumulated_depr_amount = flt(asset.net_purchase_amount) - flt(value_after_depreciation)

    return (
        fixed_asset_account,
        asset,
        depreciation_cost_center,
        accumulated_depr_account,
        accumulated_depr_amount,
        disposal_account,
        value_after_depreciation,
    )
