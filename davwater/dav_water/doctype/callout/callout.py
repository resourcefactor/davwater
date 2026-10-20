# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.jinja import render_template
from davwater.hook_event.schedulars_methods import send_mail

class Callout(Document):
	@frappe.whitelist()
	def make_service_visit(self):
		service_visit = frappe.new_doc("Service Visit")
		service_visit.maintenance_type = "Scheduled"
		service_visit.callout = self.name
		service_visit.customer = self.customer
		service_visit.company = self.company
		service_visit.customer_group = self.customer_group
		service_visit.territory = self.territory
		service_visit.customer_address = self.customer_address
		service_visit.contact_person = self.contact_person
		service_visit.item_code = self.item_code
		service_visit.serial_no = self.serial_no
		return service_visit.as_dict()

	def validate(self):
		if self.status == 'Closed' and not self.send_message and self.contact_email:
			is_send_notification = frappe.db.get_single_value("Service Settings", "is_send_callout_notification")
			content = frappe.db.get_single_value("Service Settings", "callout_response")
			sender = frappe.db.get_single_value("Service Settings", "sender")
			sender_name = frappe.db.get_single_value("Service Settings", "sender_name")
			if is_send_notification and content:
				email_content = render_template(content, self.as_dict())
				send_mail("Callout", self.name, email_content, "For issue resolution", sender, sender_name, self.contact_email)