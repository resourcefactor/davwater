frappe.ui.form.on('Attendance', {
    refresh: function(frm){
        if(frm.doc.attendance_summary_mark){
            frm.add_custom_button(__('Update Mark Attendance'), function() {
                frappe.call({
                    method: "davwater.hook_event.custom_shift_type.update_mark_attendance",
                    args: {
                        doc_name: frm.doc.name
                    },
                    callback: function (r) {
                        frm.reload_doc();
                    }
                });
            }).addClass('btn-primary');
        }
    }
});