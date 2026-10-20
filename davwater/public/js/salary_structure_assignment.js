// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.ui.form.on('Salary Structure Assignment', {
	refresh: function(frm) {
		frm.trigger("calculate_hourly_rate");
	},
	validate: function(frm) {
		frm.trigger("calculate_hourly_rate");
	},
	base: function(frm) {
		frm.trigger("calculate_hourly_rate")
	},
	employee: function(frm) {
		frm.trigger("calculate_hourly_rate")
	},
	calculate_hourly_rate: function(frm) {
		if (frm.doc.docstatus != 1) {
			var hourly_rate = (frm.doc.base * 12 / 365) / 8
			frm.set_value("hourly_rate", hourly_rate);
		}
	}
});
