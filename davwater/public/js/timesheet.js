frappe.ui.form.on('Timesheet', {
    validate: function (frm, cdt, cdn) {
        frm.doc.total_ot_hours = 0;
        $.each(frm.doc.time_logs, function(i, v) {
            frm.doc.total_ot_hours += v.ot_hours;
        });
    },
    employee: function(frm, cdt, cdn){
        set_ot(frm, cdt, cdn);
    }
});

frappe.ui.form.on('Timesheet Detail', {
    hours: function(frm, cdt, cdn){
        set_ot(frm, cdt, cdn);
    },
    from_time: function(frm, cdt, cdn){
        set_ot(frm, cdt, cdn);
    },
    to_time: function(frm, cdt, cdn){
        set_ot(frm, cdt, cdn);
    },
});


function set_ot(frm, cdt, cdn) {
    var d = locals[cdt][cdn];

    if (frm.doc.employee && d.hours) {
        frappe.db.get_value("Employee", {"name": frm.doc.employee}, "holiday_list", (r) => {
            if (r.holiday_list) {
                frappe.call({
                    method: "davwater.hook_event.timesheet.validate_holidays",
                    args: {
                        holiday: r.holiday_list,
                        date: d.from_time
                    },
                    callback: function(r) {
                        if (r) {
                            if (r.message == 0) {
                                frappe.model.set_value(cdt, cdn, 'ot_percentage', 1.25);
                                frappe.model.set_value(cdt, cdn, 'ot_hours', d.hours * 1.25);
                            }
                            else if (r.message == 1) {
                                frappe.model.set_value(cdt, cdn, 'ot_percentage', 1.5);
                                frappe.model.set_value(cdt, cdn, 'ot_hours', d.hours * 1.5);
                            }

                        }
                    }
                });
            } else {
                frappe.model.set_value(cdt, cdn, 'ot_percentage', 1.25);
                frappe.model.set_value(cdt, cdn, 'ot_hours', d.hours * 1.25);
            }
        });
    }
}