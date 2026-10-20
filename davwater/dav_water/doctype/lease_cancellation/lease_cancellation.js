// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lease Cancellation', {
	onload: function(frm){
        if (frm.doc.__islocal) {
			frm.set_value({ return_date: frappe.datetime.get_today() });
		}
    },
    refresh: function(frm){
        cur_frm.fields_dict["items"].grid.wrapper.find('.grid-add-row').hide();
    },
	setup: function(frm) {
        frm.set_query("delivery_note", function () {
            return {
                filters: {
                    customer: ["=", frm.doc.customer],
                    type_of_sale: ["in", ['Lease with Service Pack', 'Pay Per Liter']],
                    docstatus: 1,
                    is_return: 0
                }
            }
        });
    },
    delivery_note: function(frm){
        frappe.call({
            method: "get_scheduler_line",
            doc: frm.doc,
            callback: function(r){
                frm.clear_table("items");
                if(r.message) {
                    var data = r.message.items
                    data.forEach(function(d) {
                        var item = frm.add_child("items");
                        item.item_code = d.item_code
                        item.item_name = d.item_name
                        item.serial_no = d.serial_no
                    })
                }
                refresh_field("items");
            }
        });
        frappe.call({
            method: "get_assets",
            doc: frm.doc,
            callback: function(r){
                frm.clear_table("assets");
                if(r.message) {
                    var data = r.message
                    data.forEach(function(d) {
                        var item = frm.add_child("assets");
                        item.asset = d.name
                    })
                }
                refresh_field("assets");
            }
        });
    }
});
