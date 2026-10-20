// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.ui.form.on('Salary Structure', {
	refresh: function(frm) {
		frm.trigger("toggle_fields");
	},
	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_reqd(['hour_rate'], !frm.doc.salary_slip_based_on_timesheet);
	}
});
