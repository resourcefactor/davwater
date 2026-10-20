# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe import _

class ServiceVisit(Document):
	def on_submit(self):
		if self.maintenance_schedule_detail:
			doc = frappe.get_doc("Service Schedule Detail", self.maintenance_schedule_detail)
			doc.completion_status = self.completion_status
			doc.actual_date = self.mntc_date
			doc.db_update()
		if self.callout:
			doc = frappe.get_doc("Callout", self.callout)
			if self.completion_status == 'Fully Completed':
				doc.status = 'Closed'
			if self.completion_status == 'Partially Completed':
				doc.status = 'Work In Progress'
			doc.resolution_date = getdate()
			doc.resolved_by = frappe.session.user
			doc.resolution_details = self.work_done
			doc.save(ignore_permissions=True)
		self.make_stock_entry()

	@frappe.whitelist()
	def make_sales_invoice(self):
		if self.is_chargeable and self.chargeable_item:
			sale = frappe.new_doc("Sales Invoice")
			sale.customer = self.customer
			sale.due_date = getdate()
			sale.company = self.company
			sale.service_visit = self.name
			sale.currency = frappe.get_cached_value('Company', self.company, "default_currency")
			for d in self.get('chargeable_item'):
				sale.append("items", {
					"item_code": d.item_code,
					"qty": d.qty,
					"rate": d.rate
				})
			sale.set_missing_values()
			return sale.as_dict()

	@frappe.whitelist()
	def make_machine_replacement(self):
		mr = frappe.new_doc("Machine Replacement")
		mr.customer = self.customer
		mr.customer_name = self.customer_name
		mr.issue_date = self.mntc_date
		mr.old_item_code = self.item_code
		mr.old_item_name = self.item_name
		mr.old_machine_serial_no = self.serial_no
		mr.service_visit = self.name
		return mr.as_dict()

	def make_stock_entry(self):
		if self.item_replaced:
			svs = frappe.get_single('Service Visit Settings')
			if not svs.enable:
				frappe.throw(_("Please enable <b><a href='/app/service-visit-settings'>Service Visit Settings</a>"))

			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.stock_entry_type = "Material Issue"
			stock_entry.purpose = "Material Issue"
			stock_entry.service_visit = self.name
			stock_entry.posting_date = self.mntc_date
			stock_entry.set_posting_time = 1
			stock_entry.from_warehouse = svs.warehouse
			for res in self.item_replaced:
				item_doc = frappe.get_doc("Item", res.item_code)
				stock_entry.append("items", {
					'item_code': res.item_code,
					'item_name': res.item_name,
					'qty': res.qty,
					'conversion_factor': 1,
					'allow_zero_valuation_rate': 1,
					'uom': item_doc.stock_uom,
					'stock_uom': item_doc.stock_uom,
					'cost_center': 'Customer care - DW'
				})
			stock_entry.set_missing_values()
			stock_entry.insert(ignore_permissions=True)
			stock_entry.submit()

	def on_cancel(self):
		stock_entry = frappe.get_list("Stock Entry", filters={'service_visit': self.name, 'docstatus': 1}, fields='*')
		if stock_entry:
			frappe.throw("Service Visit link with the submitted Stock Entry.<br/>Please cancel Stock Entry")

