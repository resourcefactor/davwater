# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, sbool
from frappe.model.document import Document
from erpnext.controllers.sales_and_purchase_return import make_return_doc

class MachineReplacement(Document):
	def validate(self):
		if self.is_chargeable:
			for res in self.chargeable_item:
				if res.qty <= 0:
					frappe.throw(_("Qty should be greater than One."))
				if res.rate <= 0:
					frappe.throw(_("Rate should be greater than One."))

		location = frappe.db.sql("""select location from `tabService Schedule Item` 
							WHERE item_code ='{0}' and serial_no = '{1}' limit 1""".format(self.old_item_code,
																						self.old_machine_serial_no),
								 as_dict=True)

		if location:
			self.location = location[0].get('location')

	def on_submit(self):
		self.make_stock_entry()

	def make_stock_entry(self):
		# self.received_entry()
		# self.issue_entry()
		# self.create_service_schedule()
		self.return_delivery_note()
		self.create_new_delivery_note()
		self.update_service_schedule_status()


	def return_delivery_note(self):
		serial_no = frappe.get_doc("Serial No", self.old_machine_serial_no)
		if serial_no.delivery_document_type == 'Delivery Note':
			re_del_note = make_return_doc("Delivery Note", serial_no.delivery_document_no, None)
			delivery_dict = re_del_note.as_dict()
			item_child = None
			for res in delivery_dict.get('items'):
				if res.get('item_code') == self.old_item_code:
					res['serial_no'] = self.old_machine_serial_no
					res['qty'] = -1
					res['stock_qty'] = -1
					res['warehouse'] = 'Stock under IQC UAE - DW'
					item_child = res
					break
			delivery_dict['items'] = [item_child]
			delivery_dict['machine_replacement_request'] = self.name
			delivery_dict['set_warehouse'] = 'Stock under IQC UAE - DW'
			delivery_dict['posting_date'] = self.issue_date
			delivery_dict['set_posting_time'] = 1
			doc = frappe.get_doc(delivery_dict)
			doc.insert(ignore_permissions=True, ignore_mandatory=True, ignore_if_duplicate=True)
			doc.submit()

	def create_new_delivery_note(self):
		start_date = self.start_date
		end_date = self.end_date
		periodicity = self.periodicity
		service_team = self.service_team
		no_of_visits = self.no_of_visits

		is_service_pack_item = sbool(self.create_new_service)

		if not self.create_new_service:
			s_s_item = frappe.get_value("Service Schedule Item", {'serial_no': self.old_machine_serial_no,
										'item_code': self.old_item_code}, "name")
			if s_s_item:
				ss_doc = frappe.get_doc("Service Schedule Item", s_s_item)
				end_date = ss_doc.end_date
				periodicity = ss_doc.periodicity
				service_team = ss_doc.service_team

				s_s_detail = frappe.get_list("Service Schedule Detail",fields=["name", 'scheduled_date'],
									filters={'serial_no': self.old_machine_serial_no, 'item_code': self.old_item_code,
									'completion_status': 'Pending'}, order_by='scheduled_date')
				d_lst = []
				if s_s_detail:
					for ss in s_s_detail:
						d_lst.append(ss.get('scheduled_date'))
					start_date = s_s_detail[0].get('scheduled_date')
					no_of_visits = len(d_lst) or 1
				else:
					frappe.throw(_("No pending services found Serial no <b>{0}</b> Item.".format(self.old_machine_serial_no)))
			else:
				# frappe.throw(_("Service Scheduler not found Serial no <b>{0}</b> Item.".format(self.old_machine_serial_no)))
				is_service_pack_item = 0

		dn = frappe.new_doc("Delivery Note")
		dn.posting_date = self.issue_date
		dn.type_of_sale = 'Sales with Servicing Pack' if is_service_pack_item else "Sales without Servicing Pack"
		dn.company = self.company
		dn.set_warehouse = self.warehouse
		dn.customer = self.customer
		dn.set_posting_time = 1
		dn.residual_value = 0
		dn.machine_replacement_request = self.name
		dn.ignore_s_validation = 0 if self.create_new_service else 1

		if not service_team:
			service_team = 'Rencee'
		dn.append(
			"items",
			{
				"item_code": self.new_item_code,
				"warehouse": self.warehouse,
				"qty": 1,
				"rate": 0,
				"price_list_rate": 0,
				"serial_no": self.new_machine_serial_no,
				"is_service_pack_item": is_service_pack_item,
				"start_date": start_date,
				"end_date": end_date,
				"periodicity": periodicity,
				"service_team": service_team,
				"no_of_visits": no_of_visits,
				"location": self.location,
				"is_charge_item": 1 if dn.type_of_sale in ["Sales with Servicing Pack", "Lease with Service Pack", "Pay Per Liter"] else 0,
			},
		)
		dn.set_missing_values()
		dn.insert(ignore_permissions=True)
		dn.submit()
		dn.per_billed = 100
		dn.status = "Completed"
		dn.db_update()

	# def issue_entry(self):
	# 	stock_entry = frappe.new_doc("Stock Entry")
	# 	stock_entry.stock_entry_type = "Material Issue"
	# 	stock_entry.purpose = "Material Issue"
	# 	stock_entry.machine_replacement_request = self.name
	# 	stock_entry.posting_date = self.issue_date
	# 	stock_entry.from_warehouse = self.warehouse
	# 	stock_entry.set_posting_time = 1
	# 	stock_entry.append("items", {
	# 		'item_code': self.new_item_code,
	# 		'item_name': self.new_item_name,
	# 		'qty': 1,
	# 		'allow_zero_valuation_rate': 1,
	# 		'serial_no': self.new_machine_serial_no
	# 	})
	# 	stock_entry.set_missing_values()
	# 	stock_entry.insert(ignore_permissions=True)
	# 	stock_entry.submit()
	#
	# def received_entry(self):
	# 	serial_no = frappe.get_doc("Serial No", self.old_machine_serial_no)
	# 	warehouse = serial_no.warehouse
	# 	rate = 0
	# 	if serial_no.delivery_document_type == 'Delivery Note':
	# 		del_wr = frappe.db.sql("""select di.warehouse, di.rate from `tabDelivery Note Item` as di
	# 								inner join `tabDelivery Note` as d on d.name = di.parent
	# 								where d.docstatus = 1
	# 								and d.name = '{0}'
	# 								and di.serial_no like '%{1}%' limit 1""".format(serial_no.delivery_document_no,
	# 																				self.old_machine_serial_no))
	# 		if del_wr:
	# 			warehouse = del_wr[0][0]
	# 			rate = del_wr[0][1]
	#
	# 	stock_entry = frappe.new_doc("Stock Entry")
	# 	stock_entry.stock_entry_type = "Material Receipt"
	# 	stock_entry.purpose = "Material Receipt"
	# 	stock_entry.machine_replacement_request = self.name
	# 	stock_entry.posting_date = self.issue_date
	# 	stock_entry.to_warehouse = warehouse
	# 	stock_entry.set_posting_time = 1
	# 	stock_entry.append("items", {
	# 		'item_code': self.old_item_code,
	# 		'item_name': self.old_item_name,
	# 		'qty': 1,
	# 		'basic_rate': rate,
	# 		'serial_no': self.old_machine_serial_no,
	# 		# 'allow_zero_valuation_rate': 1,
	# 	})
	# 	stock_entry.set_missing_values()
	# 	stock_entry.insert(ignore_permissions=True)
	# 	stock_entry.submit()

	def update_service_schedule_status(self):
		query = """UPDATE `tabService Schedule Detail` SET completion_status = 'Closed' 
				WHERE item_code ='{0}' and serial_no = '{1}' 
				and completion_status = 'Pending'""".format(self.old_item_code, self.old_machine_serial_no)
		frappe.db.sql(query)

	def on_cancel(self):
		query = """UPDATE `tabService Schedule Detail` SET completion_status = 'Pending'
						WHERE item_code ='{0}' and serial_no = '{1}' 
						and completion_status = 'Closed'""".format(self.old_item_code, self.old_machine_serial_no)
		frappe.db.sql(query)


	# def create_service_schedule(self):
	# 	if self.create_new_service:
	# 		s_schedule = frappe.new_doc("Service Schedule")
	# 		s_schedule.customer = self.customer
	# 		s_schedule.machine_replacement_request = self.name
	# 		s_schedule.transaction_date = self.issue_date
	# 		s_schedule.append("items", {
	# 			"item_code": self.new_item_code,
	# 			"start_date": self.start_date,
	# 			"end_date": self.end_date,
	# 			"no_of_visits": self.no_of_visits,
	# 			"periodicity": self.periodicity,
	# 			"service_team": self.service_team,
	# 			"serial_no": self.new_machine_serial_no
	# 		})
	# 		s_schedule.insert(ignore_permissions=True)
	# 		s_schedule.submit()
	# 		frappe.msgprint(_("Service Schedule <b><a href='/app/service-schedule/{0}'>{0}</a></b> is Created.".format(
	# 			s_schedule.name,
	# 			s_schedule.name)))

	@frappe.whitelist()
	def make_sales_invoice(self):
		if self.is_chargeable and self.chargeable_item:
			sale = frappe.new_doc("Sales Invoice")
			sale.customer = self.customer
			sale.due_date = getdate()
			sale.company = self.company
			sale.machine_replacement_request = self.name
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
def check_sales_invoice(doc_name):
	if doc_name:
		names = frappe.get_all("Sales Invoice", fields="name",
							filters={"machine_replacement_request": doc_name, "docstatus": ['!=', 2]}, distinct=1)
		if len(names) >= 1:
			return 1
		else:
			return 0
