// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Currency Exchange Settings EW', {
    refresh: function(frm) {
        if(frm.doc.enabled){
            frm.fields_dict.update_data.$input.addClass("btn-primary");
        }
    },
    update_data: function(frm){
        frappe.call({
            method: "update_data",
            doc: frm.doc,
            freeze: true,
			freeze_message: __('...Data Uploading'),
            callback: function(r){
                frappe.msgprint(__('Data Uploaded'));
            }
        });
	}
});
