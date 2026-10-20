// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.ui.form.on('Salary Slip', {
    refresh: function(frm){
        frm.set_query("expense_claim", "expense_claim", function() {
            return {
                filters: {
                    'employee': frm.doc.employee
                }
            };
        });
    },
	validate: function(frm) {
		frm.trigger("get_hourly_rate")
	},
	employee: function(frm) {
		frm.trigger("get_hourly_rate")
	},
	start_date: function(frm) {
		frm.trigger("get_hourly_rate")
	},
	end_date: function(frm) {
		frm.trigger("get_hourly_rate")
	},
	get_hourly_rate: function(frm) {
		frappe.db.get_list("Salary Structure Assignment", {
			filters: {
				"employee": frm.doc.employee,
				"salary_structure": frm.doc.salary_structure,
				"docstatus": 1,
			},
			fields: ["hourly_rate"],
			order_by: "from_date desc",
			limit: 1,
		}).then((result) => {
			if (result.length > 0) {
				frm.set_value("hour_rate", result[0].hourly_rate);
			} else {
				frm.set_value("hour_rate", 0);
			}
		});
	}
});
