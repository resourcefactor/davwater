# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.accounts.party import get_party_account_currency

class PurchaseRawMaterials(Document):

	@frappe.whitelist()
	def get_raw_materials(self):
		if self:
			query = """select 
				p.set_warehouse as warehouse,
				ps.rm_item_code as item_code,
				i.item_name,
				i.stock_uom as uom,
				sum(ps.required_qty) as req_qty,
				0 as avl_qty,
				0 as net_qty,
				0 as ordered_qty,
				0 as order_qty,
				itd.default_supplier as supplier,
				s.supplier_name as supplier_name,
				sum(i.min_order_qty) as minimum_order_qty,
				ps.rate,
				i.purchase_uom
				from
					`tabPurchase Order` as p
				inner join
					`tabPurchase Order Item Supplied` as ps on ps.parent = p.name
				inner join 
					`tabItem` as i on i.name = ps.rm_item_code
				left join
					`tabItem Default` as itd on itd.parent = i.name 
				left join
					`tabSupplier` as s on s.name = itd.default_supplier
				where
					p.name = '{0}'
				group by 
					p.set_warehouse,
					ps.rm_item_code,
					i.item_name,
					i.stock_uom,
					itd.default_supplier,
					s.supplier_name,
					ps.rate,
					i.purchase_uom
				""".format(self.purchase_order)
			result = frappe.db.sql(query, as_dict=True)
			for res in result:
				actual_qty = frappe.db.get_value(
					"Bin", {"item_code": res.get('item_code'), "warehouse": res.get('warehouse')}, "actual_qty"
				)
				res['avl_qty'] = flt(actual_qty)
				ordered_qty = float(frappe.db.sql("""select sum(order_qty) from `tabPurchase Raw Materials Item` as prmi 
								inner join `tabPurchase Raw Materials` as prm on prm.name = prmi.parent
								where prm.purchase_order = '{0}' 
								and prm.docstatus = 1 
								and prm.name != '{1}' 
								and prmi.item_code = '{2}' 
								and prmi.warehouse = '{3}' 
								and prmi.supplier = '{4}' 
								""".format(self.purchase_order,
									self.get('name') if self.get('name') else None,
									res.get('item_code'),res.get('warehouse'),res.get('supplier')))[0][0] or 0)
				res['ordered_qty'] = ordered_qty

				res['net_qty'] = flt(res.get('req_qty')) - flt(actual_qty)
				order_qty = flt(res.get('req_qty')) - flt(actual_qty)
				if flt(res['minimum_order_qty']) > order_qty:
					res['order_qty'] = flt(res['minimum_order_qty'])
				else:
					res['order_qty'] = order_qty
			return result

	def validate(self):
		if self:
			for res in self.items:
				if res.minimum_order_qty > 0 and res.minimum_order_qty > res.order_qty:
					frappe.throw("Order Qty is greater then the Minimum Order Qty in <b> row no {0}</b>.".format(res.idx))

	def on_submit(self):
		self.make_purchase_order()

	def make_purchase_order(self):
		if self:
			item_details = {}
			for res in self.items:
				item_details.setdefault(res.supplier, []).append(res)    #grouping items supplier wise

			for key in item_details.keys():
				po = frappe.new_doc("Purchase Order")
				po.supplier = key
				po.company = self.company
				po.transaction_date = self.posting_date
				po.schedule_date = self.required_date
				po.purchase_raw_materials = self.name
				po.set_posting_time = 1
				items = item_details[key]
				party_account_currency = get_party_account_currency('Supplier', key, self.company)
				po.currency = party_account_currency
				po.ignore_pricing_rule = 1
				for res in items:
					if res.order_qty > 0:
						item = frappe.get_doc("Item", res.item_code)
						po.append("items", {
							"item_code": res.item_code,
							"description": item.description,
							"brand": item.brand,
							"warehouse": res.warehouse,
							"qty": res.order_qty,
							"rate": res.rate,
							"stock_uom": res.uom,
							"uom": res.purchase_uom,
							"allow_zero_valuation_rate": 0
						})
				po.set_missing_values()
				po.insert(ignore_permissions=True)
				if self.submit_po:
					po.submit()

@frappe.whitelist()
def update_qty(item_code, warehouse,req_qty=0):
	if item_code and warehouse:
		actual_qty = flt(frappe.db.get_value(
			"Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"
		))
		net_qty = flt(req_qty) - actual_qty
		return {'avl_qty': actual_qty, 'net_qty': net_qty, 'order_qty': net_qty}
