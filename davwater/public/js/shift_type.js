frappe.ui.form.on('Shift Type', {
	refresh: function(frm) {
	    if (!frm.doc.__islocal) {
	        frm.add_custom_button(__("Set Attendance Summary"), function() {
	            frm.call({
				    method: "davwater.hook_event.custom_shift_type.set_summary",
                    args: {
                        "shift": frm.doc.name
                    },
                    freeze: true,
                    callback: () => {
                        frappe.msgprint(__("Attendance Summary has been update as per employee check-ins"));
                    }
                });
            });
	    }
	}
});
