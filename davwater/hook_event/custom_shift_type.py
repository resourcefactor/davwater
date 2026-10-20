
from __future__ import unicode_literals
import frappe
from datetime import timedelta
from frappe.utils import cint, get_datetime
from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours
from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift
from frappe import _


def set_attendance_summary():
    shift_list = frappe.get_all('Shift Type', 'name', {'enable_auto_attendance': '1'}, as_list=True)
    for shift in shift_list:
        set_summary(shift[0])


@frappe.whitelist()
def set_summary(shift=None):
    attendance_list = frappe.get_all('Attendance', 'name', {'attendance_summary_mark': '1', 'shift': shift,'docstatus': 1,
                                                            'status': ['!=', 'On Leave']}, as_list=True)
    for attnd in attendance_list:
        try:
            late_entry_time = early_exit_time = 0
            attendance = frappe.get_doc("Attendance", attnd[0])
            attendance.un_mark_check_out = '0'
            check_attand_record = frappe.db.sql("""select * from `tabEmployee Checkin` where attendance = %s order by time""", attendance.name, as_dict=True)

            if(len(check_attand_record) > 1):
                check_in = frappe.db.sql("""select * from `tabEmployee Checkin` where attendance = %s order by time limit 1""",
                                         attendance.name, as_dict=True)
                if check_in:
                    attendance.in_time = check_in[0].time
                    check_out = frappe.db.sql("""select * from `tabEmployee Checkin` where attendance = %s and name != %s order by time desc limit 1""",(attendance.name, check_in[0].name), as_dict=True)
                    if attendance.late_entry:
                        late_entry_time = (check_in[0].time - check_in[0].shift_start).seconds
                    if check_out:
                        attendance.out_time = check_out[0].time
                        if attendance.early_exit:
                            early_exit_time = (check_out[0].shift_end - check_out[0].time).seconds
                    else:
                        attendance.out_time = None
                        attendance.un_mark_check_out = '1'
                    if attendance.status == 'Absent':
                        attendance.status = 'Present'

                    attendance.late_comming_min = late_entry_time / 60
                    attendance.early_exit_min = early_exit_time / 60
                else:
                    attendance.in_time = None
                    attendance.out_time = None
                    attendance.late_comming_min = 0
                    attendance.early_exit_min = 0

            elif(len(check_attand_record) == 1):
                attendance.in_time = None
                attendance.out_time = None
                shift = frappe.get_doc("Shift Type",check_attand_record[0].shift)
                att_detail1 = frappe.db.sql("""select abs(TIMESTAMPDIFF(hour,start_time , end_time)) as daily_hours from `tabShift Type` where name= %s """,
                    (shift.name), as_dict=True)
                total_hours = 0
                if att_detail1:
                    total_hours = att_detail1[0].daily_hours
                half_time = check_attand_record[0].shift_start + timedelta(hours= total_hours/2)
                late_entry = False
                early_exit = False

                if half_time >= check_attand_record[0].time:
                    attendance.in_time = check_attand_record[0].time
                    if check_attand_record[0].time > check_attand_record[0].shift_start + timedelta(minutes=cint(shift.late_entry_grace_period)):
                        late_entry = True
                        late_entry_time = (check_attand_record[0].time - check_attand_record[0].shift_start).seconds
                else:
                    attendance.out_time = check_attand_record[0].time
                    if check_attand_record[0].time < check_attand_record[0].shift_end - timedelta(minutes=cint(shift.early_exit_grace_period)):
                        early_exit = True
                        early_exit_time = (check_attand_record[0].shift_end - check_attand_record[0].time).seconds

                attendance.late_entry = late_entry
                attendance.early_exit = early_exit
                attendance.late_comming_min = late_entry_time / 60
                attendance.early_exit_min = early_exit_time / 60
                attendance.un_mark_check_out = '1'
                if attendance.status == 'Absent':
                    attendance.status = 'Present'
            attendance.attendance_summary_mark = '0'
            attendance.flags.ignore_validate_update_after_submit = True
            attendance.save(ignore_permissions=True)
        except Exception:
            pass

@frappe.whitelist()
def update_mark_attendance(doc_name=None):
    attendance = frappe.get_doc("Attendance", doc_name)
    shift = frappe.get_doc("Shift Type", attendance.shift)

    filters = {
        'attendance': attendance.name,
        'shift': attendance.shift
    }
    logs = frappe.db.get_list('Employee Checkin', fields="*", filters=filters, order_by="employee,time")
    late_entry = early_exit = False
    late_entry_time = early_exit_time = 0
    attendance_status = None
    total_working_hours, in_time, out_time = calculate_working_hours(logs, shift.determine_check_in_and_check_out,
                                                                     shift.working_hours_calculation_based_on)
    if cint(shift.enable_entry_grace_period) and in_time and in_time > logs[0].shift_start + timedelta(minutes=cint(shift.late_entry_grace_period)):
        late_entry = True

    if cint(shift.enable_exit_grace_period) and out_time and out_time < logs[0].shift_end - timedelta(
            minutes=cint(shift.early_exit_grace_period)):
        early_exit = True

    if shift.working_hours_threshold_for_absent and total_working_hours < shift.working_hours_threshold_for_absent:
        attendance_status = 'Absent'
    elif shift.working_hours_threshold_for_half_day and total_working_hours < shift.working_hours_threshold_for_half_day:
        attendance_status = 'Half Day'
    else:
        attendance_status = 'Present'

    attendance.early_exit = early_exit
    attendance.late_entry = late_entry
    attendance.working_hours = total_working_hours
    attendance.status = attendance_status
    attendance.un_mark_check_out = '0'

    check_attand_record = frappe.db.sql("""select * from `tabEmployee Checkin` where attendance = %s order by time""",
                                        attendance.name, as_dict=True)

    if (len(check_attand_record) > 1):
        check_in = frappe.db.sql("""select * from `tabEmployee Checkin` where attendance = %s order by time limit 1""",
                                 attendance.name, as_dict=True)
        if check_in:
            attendance.in_time = check_in[0].time
            check_out = frappe.db.sql(
                """select * from `tabEmployee Checkin` where attendance = %s and name != %s order by time desc limit 1""",
                (attendance.name, check_in[0].name), as_dict=True)
            if late_entry:
                late_entry_time = (check_in[0].time - check_in[0].shift_start).seconds
            if check_out:
                attendance.out_time = check_out[0].time
                if early_exit:
                    early_exit_time = (check_out[0].shift_end - check_out[0].time).seconds
            else:
                attendance.out_time = None
                attendance.un_mark_check_out = '1'
            if attendance_status == 'Absent':
                attendance.status = 'Present'

            attendance.late_comming_min = late_entry_time / 60
            attendance.early_exit_min = early_exit_time / 60
        else:
            attendance.in_time = None
            attendance.out_time = None
            attendance.late_comming_min = 0
            attendance.early_exit_min = 0

    elif (len(check_attand_record) == 1):
        attendance.in_time = None
        attendance.out_time = None

        att_detail1 = frappe.db.sql(
            """select abs(TIMESTAMPDIFF(hour,start_time , end_time)) as daily_hours from `tabShift Type` where name= %s """,
            (shift.name), as_dict=True)
        total_hours = 0
        if att_detail1:
            total_hours = att_detail1[0].daily_hours
        half_time = check_attand_record[0].shift_start + timedelta(hours=total_hours / 2)
        late_entry = False
        early_exit = False

        if half_time >= check_attand_record[0].time:
            attendance.in_time = check_attand_record[0].time
            if check_attand_record[0].time > check_attand_record[0].shift_start + timedelta(
                    minutes=cint(shift.late_entry_grace_period)):
                late_entry = True
                late_entry_time = (check_attand_record[0].time - check_attand_record[0].shift_start).seconds
        else:
            attendance.out_time = check_attand_record[0].time
            if check_attand_record[0].time < check_attand_record[0].shift_end - timedelta(
                    minutes=cint(shift.early_exit_grace_period)):
                early_exit = True
                early_exit_time = (check_attand_record[0].shift_end - check_attand_record[0].time).seconds

        attendance.late_entry = late_entry
        attendance.early_exit = early_exit
        attendance.late_comming_min = late_entry_time / 60
        attendance.early_exit_min = early_exit_time / 60
        attendance.un_mark_check_out = '1'
        if attendance.status == 'Absent':
            attendance.status = 'Present'
    attendance.attendance_summary_mark = '0'
    attendance.flags.ignore_validate_update_after_submit = True
    attendance.save(ignore_permissions=True)


# def fetch_shift(self, method):
#     shift_actual_timings = get_actual_start_end_datetime_of_shift(self.employee, get_datetime(self.time), True)
#     if shift_actual_timings[0] and shift_actual_timings[1]:
#         self.shift = shift_actual_timings[2].shift_type.name
#         self.shift_actual_start = shift_actual_timings[0]
#         self.shift_actual_end = shift_actual_timings[1]
#         self.shift_start = shift_actual_timings[2].start_datetime
#         self.shift_end = shift_actual_timings[2].end_datetime
#     else:
#         self.shift = None
        
        
def fetch_shift(self, method):
    shift_actual_timings = get_actual_start_end_datetime_of_shift(
        self.employee, get_datetime(self.time), True
    )

    if shift_actual_timings.get("actual_start") and shift_actual_timings.get("actual_end"):
        shift_type = shift_actual_timings.get("shift_type", {})
        self.shift = shift_type.get("name")
        self.shift_actual_start = shift_actual_timings["actual_start"]
        self.shift_actual_end = shift_actual_timings["actual_end"]
        self.shift_start = shift_actual_timings.get("start_datetime")
        self.shift_end = shift_actual_timings.get("end_datetime")
    else:
        self.shift = None

