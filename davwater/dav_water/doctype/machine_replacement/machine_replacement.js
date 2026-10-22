// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Machine Replacement', {
    onload: function(frm){
        if (frm.doc.__islocal) {
			frm.set_value({ issue_date: frappe.datetime.get_today() });
		}
    },
	setup: function(frm) {
        frm.set_query("old_machine_serial_no", function () {
            return {
                filters: {
                    customer: ["=", frm.doc.customer],
                }
            }
        });
        frm.set_query("new_machine_serial_no", function () {
            return {
                filters: {
                    status: 'Active',
                    warehouse: ['is', 'set'],
                }
            }
        });
	},
	refresh: function(frm){
	    if(frm.doc.docstatus == 1 && frm.doc.is_chargeable && frm.doc.chargeable_item){
	        frappe.call({
                method: 'davwater.dav_water.doctype.machine_replacement.machine_replacement.check_sales_invoice',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(r) {
                    if(!r.message){
                        frm.add_custom_button(__('Create Sales Invoice'), function () {
                            frappe.call({
                                method: "make_sales_invoice",
                                doc: frm.doc,
                                callback: function(r){
                                    if (!r.exc) {
                                        frappe.model.sync(r.message);
                                        frappe.set_route("Form", r.message.doctype, r.message.name);
                                    }
                                }
                            });
                        }).addClass("btn-primary");
                    }
                }
            })
        }
	},
	customer: function (frm) {
		erpnext.utils.get_party_details(frm)
	},

	contact_person: function (frm) {
		erpnext.utils.get_contact_details(frm);
	},
	old_machine_serial_no: function(frm){
	    if(!frm.doc.customer){
	        frappe.throw("Please select Customer first")
	    }
	    if(frm.doc.old_machine_serial_no){
	        frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Serial No",
					filters: {name: frm.doc.old_machine_serial_no},
					fieldname: ['item_code','item_name','warranty_expiry_date','maintenance_status']
				},
				callback: function(r) {
					if(r.message){
						frm.set_value("old_item_code", r.message.item_code);
						frm.set_value("old_item_name", r.message.item_name);
						frm.set_value("old_warranty_expiry_date", r.message.warranty_expiry_date);
						frm.set_value("old_amc_status", r.message.maintenance_status);
					}
				}
			});
	    }
	    else{
            frm.set_value("old_item_code", null);
            frm.set_value("old_item_name", null);
            frm.set_value("old_warranty_expiry_date", null);
            frm.set_value("old_amc_status", null);
	    }
	},
	new_machine_serial_no: function(frm){
	    if(frm.doc.new_machine_serial_no){
	        frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Serial No",
					filters: {name: frm.doc.new_machine_serial_no},
					fieldname: ['item_code','item_name','warranty_expiry_date','maintenance_status','warehouse']
				},
				callback: function(r) {
					if(r.message){
						frm.set_value("new_item_code", r.message.item_code);
						frm.set_value("new_item_name", r.message.item_name);
						frm.set_value("new_warranty_expiry_date", r.message.warranty_expiry_date);
						frm.set_value("new_amc_status", r.message.maintenance_status);
						frm.set_value("warehouse", r.message.warehouse);
					}
				}
			});
	    }
	    else{
            frm.set_value("new_item_code", null);
            frm.set_value("new_item_name", null);
            frm.set_value("new_amc_status", null);
            frm.set_value("new_warranty_expiry_date", null);
            frm.set_value("warehouse", null);
	    }
	},
	is_chargeable: function(frm){
	    frm.clear_table("chargeable_item");
        var item = frm.add_child("chargeable_item");
        item.item_code = frm.doc.new_item_code
        item.item_name = frm.doc.new_item_name
        refresh_field("chargeable_item");
	}
});

function calculate_amount(frm, cdt, cdn){
    var row = locals[cdt][cdn];
    let amount = row.rate * row.qty
    frappe.model.set_value(cdt,cdn,"amount",amount);
    refresh_field("amount", cdn, "chargeable_item");
}

frappe.ui.form.on('Chargeable Service Item', {
    qty: function(frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn)
	},
	rate: function(frm, cdt, cdn) {
        calculate_amount(frm, cdt, cdn)
	},
})

