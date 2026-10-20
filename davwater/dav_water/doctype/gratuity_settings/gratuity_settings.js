// Copyright (c) 2023, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gratuity Settings', {
	setup: function(frm) {
		frm.set_query("gratuity_exp_account", "gratuity_settings_detail", function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: [
					['Account', 'is_group', '=', 0],
					['Account', 'company', '=', d.company]
				]
			};
		});
		frm.set_query("gratuity_accrual_account", "gratuity_settings_detail", function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: [
					['Account', 'is_group', '=', 0],
					['Account', 'company', '=', d.company]
				]
			};
		});
	}
});
