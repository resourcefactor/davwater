# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import add_days, getdate, cint, cstr, date_diff, formatdate
from frappe import throw, _
from erpnext.utilities.transaction_base import TransactionBase, delete_events
from erpnext.stock.utils import get_valid_serial_nos
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
import json


class ServiceSchedule(TransactionBase):
	@frappe.whitelist()
	def generate_schedule(self):
		self.set('schedules', [])
		frappe.db.sql("""delete from `tabService Schedule Detail`
			where parent=%s""", (self.name))
		count = 1
		for d in self.get('items'):
			self.validate_maintenance_detail()
			s_list = []
			s_list = self.create_schedule_list(d.start_date, d.end_date, d.no_of_visits, d.service_team)
			for i in range(d.no_of_visits):
				child = self.append('schedules')
				child.item_code = d.item_code
				child.item_name = d.item_name
				child.scheduled_date = s_list[i].strftime('%Y-%m-%d')
				if d.serial_no:
					child.serial_no = d.serial_no
				child.idx = count
				count = count + 1
				child.service_team = d.service_team
				child.location = d.location
				child.completion_status = "Pending"
				child.item_reference = d.name
		pass

	@frappe.whitelist()
	def validate_end_date_visits(self):
		days_in_period = {
			"Weekly": 7,
			"Monthly": 30,
			"Quarterly": 91,
			"Half Yearly": 182,
			"Yearly": 365
		}
		for item in self.items:
			if item.periodicity and item.periodicity != "Random" and item.start_date:
				if not item.end_date:
					if item.no_of_visits:
						item.end_date = add_days(
							item.start_date, item.no_of_visits * days_in_period[item.periodicity]
						)
					else:
						item.end_date = add_days(item.start_date, days_in_period[item.periodicity])

				diff = date_diff(item.end_date, item.start_date) + 1
				no_of_visits = cint(diff / days_in_period[item.periodicity])

				if not item.no_of_visits or item.no_of_visits == 0:
					item.end_date = add_days(item.start_date, days_in_period[item.periodicity])
					diff = date_diff(item.end_date, item.start_date) + 1
					item.no_of_visits = cint(diff / days_in_period[item.periodicity])

				elif item.no_of_visits > no_of_visits:
					item.end_date = add_days(
						item.start_date, item.no_of_visits * days_in_period[item.periodicity]
					)

				elif item.no_of_visits < no_of_visits:
					item.end_date = add_days(
						item.start_date, item.no_of_visits * days_in_period[item.periodicity]
					)

	def on_submit(self):
		# if not self.get('schedules'):
		# 	throw(_("Please click on 'Generate Schedule' to get schedule"))
		# self.check_serial_no_added()
		self.validate_schedule()
		email_map = {}
		for d in self.get('items'):
			if d.serial_no:
				serial_nos = get_valid_serial_nos(d.serial_no)
				self.validate_serial_no(d.item_code, serial_nos, d.start_date)
				self.update_amc_date(serial_nos, d.end_date)

				sr_doc = frappe.get_doc("Serial No", d.serial_no)
				sr_doc.location = d.location
				sr_doc.flags.ignore_validate_update_after_submit = True
				sr_doc.save()

			no_email_sp = []
			# if d.sales_person not in email_map:
			# 	sp = frappe.get_doc("Sales Person", d.sales_person)
			# 	try:
			# 		email_map[d.sales_person] = sp.get_email_id()
			# 	except frappe.ValidationError:
			# 		no_email_sp.append(d.sales_person)
			#
			# if no_email_sp:
			# 	frappe.msgprint(
			# 		_("Setting Events to {0}, since the Employee attached to the below Sales Persons does not have a User ID{1}").format(
			# 			self.owner, "<br>" + "<br>".join(no_email_sp)
			# 		)
			# 	)

			scheduled_date = frappe.db.sql("""select scheduled_date from
				`tabService Schedule Detail` where service_team=%s and item_code=%s and
				parent=%s""", (d.service_team, d.item_code, self.name), as_dict=1)
			for key in scheduled_date:
				description = frappe._("Reference: {0}, Item Code: {1} and Customer: {2}").format(self.name,
																								  d.item_code,
																								  self.customer)

				event = frappe.get_doc(
					{
						"doctype": "Event",
						"owner": email_map.get(d.service_team, self.owner),
						"subject": description,
						"description": description,
						"starts_on": cstr(key["scheduled_date"]) + " 10:00:00",
						"event_type": "Private",
					}
				)
				event.add_participant(self.doctype, self.name)
				event.insert(ignore_permissions=1)

		self.db_set("status", "Submitted")
		self.make_sales_invoice()

	def make_sales_invoice(self):
		if self.is_renew_plan:
			sale_item = frappe.db.get_single_value("Service Settings", "sales_invoice_item")
			if not sale_item:
				frappe.throw(_("Please set Sale Invoice Item in Service Settings"))

			sale = frappe.new_doc("Sales Invoice")
			sale.customer = self.customer
			sale.due_date = getdate()
			sale.company = self.company
			sale.service_schedule = self.name
			sale.currency = frappe.get_cached_value('Company', self.company, "default_currency")
			for d in self.get('items'):
				var_temp = frappe.get_value("Item", d.item_code, "variant_of")
				inv_item = None
				if var_temp:
					inv_item = frappe.get_value("Item", var_temp, "invoice_item")
				sale.append("items", {
					"item_code": inv_item if inv_item else sale_item,
					"qty": 1,
					"rate": d.rate
				})
			sale.set_missing_values()
			sale.insert(ignore_permissions=True)
			# sale.submit()
			self.db_set("sales_invoice", sale.name)

	def create_schedule_list(self, start_date, end_date, no_of_visit, service_team):
		schedule_list = []
		start_date_copy = start_date
		date_diff = (getdate(end_date) - getdate(start_date)).days
		add_by = date_diff / no_of_visit

		if self.is_renew_plan:
			if not self.first_service_date:
				frappe.throw("Please select first service date")

			for visit in range(cint(no_of_visit)):
				if (getdate(start_date_copy) < getdate(end_date)):
					start_date_copy = add_days(start_date_copy, add_by)
					if visit == 0:
						start_date_copy = self.first_service_date
					if len(schedule_list) < no_of_visit:
						schedule_date = self.validate_schedule_date_for_holiday_list(getdate(start_date_copy),
																					 service_team)
						if schedule_date > getdate(end_date):
							schedule_date = getdate(end_date)
						schedule_list.append(schedule_date)
		else:
			for visit in range(cint(no_of_visit)):
				if (getdate(start_date_copy) < getdate(end_date)):
					start_date_copy = add_days(start_date_copy, add_by)
					if len(schedule_list) < no_of_visit:
						schedule_date = self.validate_schedule_date_for_holiday_list(getdate(start_date_copy),
																					 service_team)
						if schedule_date > getdate(end_date):
							schedule_date = getdate(end_date)
						schedule_list.append(schedule_date)

		return schedule_list

	def validate_schedule_date_for_holiday_list(self, schedule_date, service_team):
		validated = False

		# employee = frappe.db.get_value("Sales Person", sales_person, "employee")
		# if employee:
		# 	holiday_list = get_holiday_list_for_employee(employee)
		# else:
		holiday_list = frappe.get_cached_value('Company', self.company, "default_holiday_list")

		holidays = frappe.db.sql_list('''select holiday_date from `tabHoliday` where parent=%s''', holiday_list)

		if not validated and holidays:

			# max iterations = len(holidays)
			for i in range(len(holidays)):
				if schedule_date in holidays:
					schedule_date = add_days(schedule_date, -1)
				else:
					validated = True
					break

		return schedule_date

	def validate_dates_with_periodicity(self):
		for d in self.get("items"):
			if d.start_date and d.end_date and d.periodicity and d.periodicity != "Random":
				date_diff = (getdate(d.end_date) - getdate(d.start_date)).days + 1
				days_in_period = {
					"Weekly": 7,
					"Monthly": 30,
					"Quarterly": 90,
					"Half Yearly": 180,
					"Yearly": 365
				}

				if date_diff < days_in_period[d.periodicity]:
					throw(
						_(
							"Row {0}: To set {1} periodicity, difference between from and to date must be greater than or equal to {2}")
							.format(d.idx, d.periodicity, days_in_period[d.periodicity]))

	def validate_maintenance_detail(self):
		if not self.get('items'):
			throw(_("Please enter Maintenance Details first"))

		for d in self.get('items'):
			if not d.item_code:
				throw(_("Please select item code"))
			elif not d.start_date or not d.end_date:
				throw(_("Please select Start Date and End Date for Item {0}").format(d.item_code))
			elif not d.no_of_visits:
				throw(_("Please mention no of visits required"))
			elif not d.service_team:
				throw(_("Please select a Service Team for item: {0}").format(d.item_name))

			if getdate(d.start_date) >= getdate(d.end_date):
				throw(_("Start date should be less than end date for Item {0}").format(d.item_code))

	def validate_sales_order(self):
		for d in self.get('items'):
			if d.sales_order:
				chk = frappe.db.sql("""select ms.name from `tabService Schedule` ms,
					`tabService Schedule Item` msi where msi.parent=ms.name and
					msi.sales_order=%s and ms.docstatus=1""", d.sales_order)
				if chk:
					throw(_("Service Schedule {0} exists against {1}").format(chk[0][0], d.sales_order))

	def validate(self):
		self.validate_end_date_visits()
		self.validate_maintenance_detail()
		self.validate_dates_with_periodicity()
		self.validate_sales_order()
		self.generate_schedule()
		self.validate_rate()

	def validate_rate(self):
		if self.is_renew_plan:
			for d in self.get('items'):
				if not d.rate:
					frappe.throw(_("Set rate in row: {0}".format(d.idx)))

	def on_update(self):
		self.db_set("status", "Draft")

	def update_amc_date(self, serial_nos, amc_expiry_date=None):
		for serial_no in serial_nos:
			serial_no_doc = frappe.get_doc("Serial No", serial_no)
			serial_no_doc.amc_expiry_date = amc_expiry_date
			serial_no_doc.save()

	def validate_serial_no(self, item_code, serial_nos, amc_start_date):
		for serial_no in serial_nos:
			sr_details = frappe.db.get_value("Serial No", serial_no,
											 ["warranty_expiry_date", "amc_expiry_date", "warehouse", "delivery_date",
											  "item_code", "delivery_document_type", "delivery_document_no"], as_dict=1)
			if not sr_details:
				frappe.throw(_("Serial No {0} not found").format(serial_no))

			if sr_details.get("item_code") != item_code:
				frappe.throw(_("Serial No {0} does not belong to Item {1}")
							 .format(frappe.bold(serial_no), frappe.bold(item_code)), title="Invalid")

			# if sr_details.amc_expiry_date and getdate(sr_details.amc_expiry_date) >= getdate(amc_start_date):
			# 	throw(_("Serial No {0} is under Service contract upto {1}")
			# 		  .format(serial_no, sr_details.amc_expiry_date))

			if not sr_details.warehouse and sr_details.delivery_date and \
					getdate(sr_details.delivery_date) > getdate(amc_start_date):
				ignore_validation = 0
				if sr_details.delivery_document_type == 'Delivery Note':
					dn = frappe.get_doc(sr_details.delivery_document_type, sr_details.delivery_document_no)
					ignore_validation = dn.ignore_s_validation
				if not ignore_validation:
					throw(_("Service start date can not be before delivery date for Serial No {0}")
						  .format(serial_no))

	def validate_schedule(self):
		item_lst1 = []
		item_lst2 = []
		for d in self.get('items'):
			if d.item_code not in item_lst1:
				item_lst1.append(d.item_code)

		for m in self.get('schedules'):
			if m.item_code not in item_lst2:
				item_lst2.append(m.item_code)

		if len(item_lst1) != len(item_lst2):
			throw(_("Service Schedule is not generated for all the items. Please click on 'Generate Schedule'"))
		else:
			for x in item_lst1:
				if x not in item_lst2:
					throw(_("Please click on 'Generate Schedule'"))

	def check_serial_no_added(self):
		serial_present = []
		for d in self.get('items'):
			if d.serial_no:
				serial_present.append(d.item_code)

		for m in self.get('schedules'):
			if serial_present:
				if m.item_code in serial_present and not m.serial_no:
					throw(_("Please click on 'Generate Schedule' to fetch Serial No added for Item {0}").format(
						m.item_code))

	def on_cancel(self):
		for d in self.get('items'):
			if d.serial_no:
				serial_nos = get_valid_serial_nos(d.serial_no)
				self.update_amc_date(serial_nos)

		self.db_set("status", 'Cancelled')
		delete_events(self.doctype, self.name)

	def on_trash(self):
		delete_events(self.doctype, self.name)

	@frappe.whitelist()
	def get_pending_data(self, data_type, s_date=None, item_name=None):
		if data_type == "date":
			dates = ""
			for schedule in self.schedules:
				serial_name = " - " + schedule.serial_no if schedule.serial_no else ""
				s_item_name = schedule.item_name + str(serial_name)
				if s_item_name == item_name and schedule.completion_status in ("Pending", "Partially Completed"):
					dates = dates + "\n" + formatdate(schedule.scheduled_date, "dd-MM-yyyy")
			return dates
		elif data_type == "items":
			items = ""
			for item in self.items:
				for schedule in self.schedules:
					if item.item_name == schedule.item_name and schedule.completion_status == "Pending":
						serial_name = " - " + item.serial_no if item.serial_no else ""
						items = items + "\n" + item.item_name + str(serial_name)
						break
			return items
		elif data_type == "id":
			for schedule in self.schedules:
				if schedule.item_name == item_name and s_date == formatdate(schedule.scheduled_date, "dd-mm-yyyy"):
					return schedule.name


@frappe.whitelist()
def update_serial_nos(s_id):
	serial_nos = frappe.db.get_value('Service Schedule Detail', s_id, 'serial_no')
	if serial_nos:
		serial_nos = get_serial_nos(serial_nos)
		return serial_nos
	else:
		return False


@frappe.whitelist()
def make_maintenance_visit(source_name, item_name=None, scheduled_date=None):
	s_date = getdate(scheduled_date)
	doc = frappe.get_doc("Service Schedule", source_name)
	service_visit = frappe.new_doc("Service Visit")
	# service_visit.maintenance_type = "Scheduled"
	service_visit.maintenance_schedule = doc.name
	service_visit.customer = doc.customer
	service_visit.company = doc.company
	service_visit.customer_group = doc.customer_group
	service_visit.territory = doc.territory
	service_visit.customer_address = doc.customer_address
	service_visit.contact_person = doc.contact_person

	for res in doc.schedules:
		if res.item_name + str(" - " + res.serial_no if res.serial_no else "") == item_name and getdate(
				formatdate(res.scheduled_date, "dd-MM-yyyy")) == s_date:
			service_visit.maintenance_schedule_detail = res.name
			service_visit.item_code = res.item_code
			service_visit.service_team = res.service_team
			service_visit.serial_no = res.serial_no
			service_visit.location = res.location
	return service_visit.as_dict()


@frappe.whitelist()
def get_events(start, end, filters=None):
	events = []
	if filters:
		service_sch_dict = {}
		service_sch_itm_dict = {}
		service_sch_dtl_dict = {}
		service_sch_lst = [s.get('name') for s in frappe.get_list('Service Schedule', fields=('name'))]
		filters = json.loads(filters)
		for res in filters:
			if res[0] == 'Service Schedule':
				service_sch_dict[res[1]] = [res[2], res[3]]
			if res[0] == 'Service Schedule Item':
				service_sch_itm_dict[res[1]] = [res[2], res[3]]
			if res[0] == 'Service Schedule Detail':
				service_sch_dtl_dict[res[1]] = [res[2], res[3]]

			if service_sch_dict:
				service_schedules = frappe.get_list('Service Schedule', filters=service_sch_dict, fields=('name'))
				service_sch_lst = []
				for s in service_schedules:
					service_sch_lst.append(s.get('name'))

			if service_sch_itm_dict and service_sch_lst:
				service_sch_itm_dict['parent'] = ['in', service_sch_lst]
				service_schedule_item = frappe.get_list('Service Schedule Item', filters=service_sch_itm_dict,
														fields=('parent'))
				service_sch_lst = []
				for s in service_schedule_item:
					if s.get('parent') not in service_sch_lst:
						service_sch_lst.append(s.get('parent'))

			if service_sch_dtl_dict and service_sch_lst:
				service_sch_dtl_dict['parent'] = ['in', service_sch_lst]
				service_schedule_detail = frappe.get_list('Service Schedule Detail', filters=service_sch_dtl_dict,
														  fields=('parent'))
				service_sch_lst = []
				for s in service_schedule_detail:
					if s.get('parent') not in service_sch_lst:
						service_sch_lst.append(s.get('parent'))

		if service_sch_lst:
			service_sch_dtl_dict['parent'] = ['in', service_sch_lst]
			service_schedule_details = frappe.get_list('Service Schedule Detail', filters=service_sch_dtl_dict,
													   fields=('name'))
			for res in service_schedule_details:
				d = frappe.get_doc('Service Schedule Detail', res.name)
				color = None
				if d.completion_status == "Pending":
					color = '#449CF0'
				if d.completion_status == "Partially Completed":
					color = '#ECAD4B'
				if d.completion_status == "Fully Completed":
					color = '#29CD42'
				e = {
					"name": d.parent,
					"doctype": "Service Schedule",
					"from_date": d.scheduled_date,
					"to_date": d.scheduled_date,
					"docstatus": d.docstatus,
					"color": color,
					"title": cstr(d.service_team) + " (" + cstr(d.parent) + ")"
				}
				events.append(e)
	return events


@frappe.whitelist()
def get_serial_no_with_location(doc_name):
	doc = frappe.get_doc("Service Schedule", doc_name)
	lst = []
	for item in doc.items:
		lst.append({'serial_no': item.serial_no, 'location': item.location})
	return lst
