# Copyright (c) 2023, RF and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
from frappe import msgprint, _
from calendar import monthrange
from datetime import datetime

status_map = {
	"Absent": "A",
	"Half Day": "HD",
	"Holiday": "<b>H</b>",
	"Weekly Off": "<b>WO</b>",
	"On Leave": "L",
	"Present": "P",
	"Work From Home": "WFH"
	}

day_abbr = [
	"Mon",
	"Tue",
	"Wed",
	"Thu",
	"Fri",
	"Sat",
	"Sun"
]

def execute(filters=None):
	if not filters: filters = {}

	if filters.hide_year_field == 1:
		filters.year = 2020

	conditions, filters = get_conditions(filters)
	columns, days = get_columns(filters)
	att_map = get_attendance_list(conditions, filters)

	if filters.group_by:
		emp_map, group_by_parameters = get_employee_details(filters.group_by, filters.company)
		holiday_list = []
		for parameter in group_by_parameters:
			h_list = [emp_map[parameter][d]["holiday_list"] for d in emp_map[parameter] if emp_map[parameter][d]["holiday_list"]]
			holiday_list += h_list
	else:
		emp_map = get_employee_details(filters.group_by, filters.company)
		holiday_list = [emp_map[d]["holiday_list"] for d in emp_map if emp_map[d]["holiday_list"]]


	default_holiday_list = frappe.get_cached_value('Company',  filters.get("company"),  "default_holiday_list")
	holiday_list.append(default_holiday_list)
	holiday_list = list(set(holiday_list))
	holiday_map = get_holiday(holiday_list, filters["month"],filters["year"])

	data = []

	l_list = None
	if filters.summarized_view:
		leave_types = frappe.db.sql("""select name from `tabLeave Type`""", as_list=True)
		leave_list = [d[0] + ":Float:130" for d in leave_types]
		l_list = [d[0] for d in leave_types]
		columns.extend(leave_list)
		columns.extend([_("Total Late Entries") + ":Float:130", _("Total Early Exits") + ":Float:120"])
		columns.extend([_("Total Late Entries Hour") + ":Float:160", _("Total Early Exits Hour") + ":Float:150"])

	if filters.group_by:
		emp_att_map = {}
		for parameter in group_by_parameters:
			data.append([ "<b>"+ parameter + "</b>"])
			record, aaa = add_data(emp_map[parameter], att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=l_list)
			emp_att_map.update(aaa)
			data += record
	else:
		record, emp_att_map = add_data(emp_map, att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=l_list)
		data += record

	chart_data = get_chart_data(emp_att_map, days)

	return columns, data, None, chart_data

def get_chart_data(emp_att_map, days):
	labels = []
	datasets = [
		{"name": "Absent", "values": []},
		{"name": "Present", "values": []},
		{"name": "Leave", "values": []},
	]
	for idx, day in enumerate(days, start=0):
		p = day.replace("::65", "")
		labels.append(day.replace("::65", ""))
		total_absent_on_day = 0
		total_leave_on_day = 0
		total_present_on_day = 0
		total_holiday = 0
		for emp in emp_att_map.keys():
			if emp_att_map[emp][idx]:
				if emp_att_map[emp][idx] == "A":
					total_absent_on_day += 1
				if emp_att_map[emp][idx] in ["P", "WFH"]:
					total_present_on_day += 1
				if emp_att_map[emp][idx] == "HD":
					total_present_on_day += 0.5
					total_leave_on_day += 0.5
				if emp_att_map[emp][idx] == "L":
					total_leave_on_day += 1


		datasets[0]["values"].append(total_absent_on_day)
		datasets[1]["values"].append(total_present_on_day)
		datasets[2]["values"].append(total_leave_on_day)
	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}
	chart["type"] = "line"

	return chart

def add_data(employee_map, att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=None):
	record = []
	emp_att_map = {}
	for emp in employee_map:
		emp_det = employee_map.get(emp)
		if not emp_det or emp not in att_map:
			continue

		row = []
		if filters.group_by:
			row += [" "]
		row += [emp, emp_det.employee_name]

		total_p = total_a = total_l = total_h = total_um = total_days_in_month = 0.0
		emp_status_map = []
		att_detail1 = frappe.db.sql("""select sum(working_hours) as whh from `tabAttendance` where employee = %s and company = %s and month(attendance_date) = %s and year(attendance_date) = %s and docstatus = 1 limit 1""",(emp, filters.get('company'), filters.get('month'), filters.get('year')),as_dict=True)
		total_worked_hours = 0
		if att_detail1:
			total_worked_hours = att_detail1[0].whh
		att_detail1 = frappe.db.sql("""select abs(TIMESTAMPDIFF(hour,start_time , end_time)) as daily_hours, start_time, end_time from `tabShift Type` st inner join `tabEmployee` te on st.name=te.default_shift where te.name= %s """,(emp),as_dict=True)
		total_hours = 0
		if att_detail1:
			total_hours = att_detail1[0].daily_hours
		for day in range(filters["total_days_in_month"]):
			status = None
			status = att_map.get(emp).get(day + 1)
			if status is None and holiday_map:
				emp_holiday_list = emp_det.holiday_list if emp_det.holiday_list else default_holiday_list

				if emp_holiday_list in holiday_map:
					for idx, ele in enumerate(holiday_map[emp_holiday_list]):
						if day+1 == holiday_map[emp_holiday_list][idx][0]:
							if holiday_map[emp_holiday_list][idx][0]:
								status = "Weekly Off"
							else:
								status = "Holiday"
							total_h += 1
			abbr = status_map.get(status, "")
			if abbr not in ['<b>H</b>', 'L', '<b>WO</b>']:
				attendance_date = filters.get('year') + "-" + filters.get('month') + "-" + str(day + 1)
				att_detail = frappe.db.sql("""select * from `tabAttendance` where attendance_date =%s and 
							employee = %s and company = %s and docstatus = 1 limit 1""", (attendance_date, emp, filters.get('company')),as_dict=True)
				if att_detail:
					in_time = ''
					out_time = ''
					check_in = att_detail[0].in_time
					if check_in:
						in_time = check_in.time()
						in_time = str(in_time.strftime("%H:%M"))
					check_out = att_detail[0].out_time
					if check_out:
						out_time = (check_out).time()
						out_time = str(out_time.strftime("%H:%M"))
					working_hour = (str(round(att_detail[0].working_hours,1)) if att_detail[0].working_hours else str(0))
					full_str = "(" + in_time + " - " + out_time+")" + working_hour
					emp_status_map.append(full_str)

					if att_detail[0].un_mark_check_out:
						total_um += 1
				else:
					emp_status_map.append(" ")

			else:
				emp_status_map.append(abbr)

			if filters.summarized_view:
				if status == "Present" or status == "Work From Home":
					total_p += 1
				elif status == "Absent":
					total_a += 1
				elif status == "On Leave":
					total_l += 1
				elif status == "Half Day":
					total_p += 0.5
					total_a += 0.5
					# total_l += 0.5
				# elif not status:
				# 	total_um += 1
				total_days_in_month += 1

		if not filters.summarized_view:
			row += emp_status_map

		if not filters.get("employee"):
			filters.update({"employee": emp})
			conditions += " and employee = %(employee)s"
		elif not filters.get("employee") == emp:
			filters.update({"employee": emp})

		if filters.summarized_view:
			leave_details = frappe.db.sql("""select leave_type, status, count(*) as count from `tabAttendance`\
				where leave_type is not NULL and docstatus = 1 %s group by leave_type, status""" % conditions, filters, as_dict=1)

			time_default_counts = frappe.db.sql("""select (select count(*) from `tabAttendance` where \
				late_entry = 1 and docstatus = 1 %s) as late_entry_count, (select count(*) from tabAttendance where \
				early_exit = 1 and docstatus = 1 %s) as early_exit_count""" % (conditions, conditions), filters)

			late_entry = frappe.db.sql("""select late_comming_min
					from `tabAttendance` where late_entry = 1 and docstatus = 1 %s and status != 'On Leave'"""% (conditions), filters, as_dict=1)
			total_late_entry_min = 0
			for le in late_entry:
				total_late_entry_min += le.late_comming_min

			early_going = frappe.db.sql("""select early_exit_min
					from `tabAttendance` where early_exit = 1 and docstatus = 1 %s and status != 'On Leave'"""% (conditions), filters, as_dict=1)
			total_early_exit_min = 0
			for le in early_going:
				total_early_exit_min += le.early_exit_min

			late_hour = round(total_late_entry_min / 60, 2)
			early_hour = round(total_early_exit_min / 60, 2)

			total_working_hours = total_p * total_hours
			#-----------------------------unmarked shor hour -----------------
			unmarked_short_hour = total_um * 2
			#----------------------------------------------------------
			total_short_hours = unmarked_short_hour + late_hour + early_hour
			row += [total_days_in_month, total_p, total_l, total_a, total_h, total_um, unmarked_short_hour, total_worked_hours, total_hours, total_working_hours, total_short_hours]

			leaves = {}
			for d in leave_details:
				if d.status == "Half Day":
					d.count = d.count * 0.5
				if d.leave_type in leaves:
					leaves[d.leave_type] += d.count
				else:
					leaves[d.leave_type] = d.count
			for d in leave_list:
				if d in leaves:
					row.append(leaves[d])
				else:
					row.append("0.0")
			row.extend([time_default_counts[0][0],time_default_counts[0][1]])
			row.append(late_hour)
			row.append(early_hour)
		emp_att_map[emp] = emp_status_map
		record.append(row)

	return record, emp_att_map

def get_columns(filters):

	columns = []

	if filters.group_by:
		columns = [_(filters.group_by)+ ":Link/Branch:120"]

	columns += [
		_("Employee") + ":Link/Employee:120", _("Employee Name") + ":Data/:120"
	]
	days = []
	for day in range(filters["total_days_in_month"]):
		date = str(filters.year) + "-" + str(filters.month)+ "-" + str(day+1)
		day_name = day_abbr[getdate(date).weekday()]
		days.append(cstr(day+1)+ " " +day_name +"::120")
	if not filters.summarized_view:
		columns += days

	if filters.summarized_view:
		columns += [_("Total days in Month") + ":Float:140", _("Total Present") + ":Float:120", _("Total Leaves") + ":Float:120",  _("Total Absent") + ":Float:120", _("Total Holidays")
			+ ":Float:120", _("Unmarked In-Out") + ":Float:120", _("Unmarked Short Hour") + ":Float:150",_("Worked Hours") + ":Float:120",_("Hours Per Day") + ":Float:120", _("Total Working Hours") + ":Float:140", _("Total Short Hours") + ":Float:140", ]
	return columns, days

def get_attendance_list(conditions, filters):
	attendance_list = frappe.db.sql("""select employee, day(attendance_date) as day_of_month,
		status from tabAttendance where docstatus = 1 %s order by employee, attendance_date""" %
		conditions, filters, as_dict=1)

	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.employee, frappe._dict()).setdefault(d.day_of_month, "")
		att_map[d.employee][d.day_of_month] = d.status

	return att_map

def get_conditions(filters):
	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	filters["total_days_in_month"] = monthrange(cint(filters.year), cint(filters.month))[1]

	conditions = " and month(attendance_date) = %(month)s and year(attendance_date) = %(year)s"

	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters

def get_employee_details(group_by, company):
	emp_map = {}
	query = """select name, employee_name, designation, department, branch, company,
		holiday_list from `tabEmployee` where company = %s """ % frappe.db.escape(company)

	if group_by:
		group_by = group_by.lower()
		query += " order by " + group_by + " ASC"

	employee_details = frappe.db.sql(query , as_dict=1)

	group_by_parameters = []
	if group_by:

		group_by_parameters = list(set(detail.get(group_by, "") for detail in employee_details if detail.get(group_by, "")))
		for parameter in group_by_parameters:
				emp_map[parameter] = {}


	for d in employee_details:
		if group_by and len(group_by_parameters):
			if d.get(group_by, None):

				emp_map[d.get(group_by)][d.name] = d
		else:
			emp_map[d.name] = d

	if not group_by:
		return emp_map
	else:
		return emp_map, group_by_parameters

def get_holiday(holiday_list, month, year):
	holiday_map = frappe._dict()
	for d in holiday_list:
		if d:
			holiday_map.setdefault(d, frappe.db.sql('''select day(holiday_date) from `tabHoliday`
				where parent=%s and month(holiday_date)=%s and year(holiday_date) = %s''', (d, month, year)))

	return holiday_map

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(attendance_date) from tabAttendance ORDER BY YEAR(attendance_date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
