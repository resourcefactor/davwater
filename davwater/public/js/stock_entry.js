frappe.ui.form.on('Stock Entry', {
	stock_entry_type: function(frm) {
		if (["Manufacture", "Material Transfer for Manufacture", "Send to Subcontractor", "Repack", "Material Transfer"].includes(frm.doc.stock_entry_type)) {
			$.each(frm.doc.items, function(i, d) {
				frappe.db.get_value("Company", frm.doc.company, "stock_adjustment_account", (r) => {
					d.expense_account = r.stock_adjustment_account;
				});
			});
			frm.refresh_field("items");
		}
	},
	company: function(frm) {
		if(frm.is_new() || frm.doc.__islocal) {
			var ret_obj = setseries(frm.doc.company);
			frm.set_value("naming_series", ret_obj.series);
			
		}

		if (["Manufacture", "Material Transfer for Manufacture", "Send to Subcontractor", "Repack", "Material Transfer"].includes(frm.doc.stock_entry_type)) {
			$.each(frm.doc.items, function(i, d) {
				frappe.db.get_value("Company", frm.doc.company, "stock_adjustment_account", (r) => {
					d.expense_account = r.stock_adjustment_account;
				});
			});
			frm.refresh_field("items");
		}
	}
});

frappe.ui.form.on('Stock Entry Detail', {
    item_code: function(frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        if(frm.doc.company){
            frappe.db.get_value("Company", frm.doc.company, "stock_adjustment_account", (r) => {
                frappe.model.set_value(cdt, cdn, "expense_account", r.stock_adjustment_account);
            });
        }
    }
})

function setseries(company) {
	var ret_obj = { series: "" };	
	switch(company) {
		case "AIR WATER UNITS TRADING LTD": ret_obj.series = "STE.###"; break;
		case "AIR WATER VENTURES LTD": ret_obj.series = "VL-STE.###"; break;
	}
	return ret_obj;
}

