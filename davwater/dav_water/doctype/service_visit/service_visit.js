
// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("davwater.dav_water");
var serial_nos = [];
frappe.ui.form.on('Service Visit', {
	refresh: function (frm) {
	    frm.fields_dict['item_replace_in_future'].grid.get_field("serial_no").get_query = function(doc, cdt, cdn) {
            var child = locals[cdt][cdn];
            return {
                filters:[
                   ['item_code', '=', child.item_code]
                ]
            }
        }
        if(frm.doc.docstatus == 1 && frm.doc.is_chargeable && frm.doc.chargeable_item){
            frm.add_custom_button(__('Sales Invoice'), function () {
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
            }, __('Create'));
        }
        if(frm.doc.docstatus == 1 && frm.doc.callout){
            frm.add_custom_button(__('Machine Replacement'), function () {
                frappe.call({
                    method: "make_machine_replacement",
                    doc: frm.doc,
                    callback: function(r){
                        if (!r.exc) {
                            frappe.model.sync(r.message);
                            frappe.set_route("Form", r.message.doctype, r.message.name);
                        }
                    }
                });
            }, __('Create'));
        }
        frm.page.set_inner_btn_group_as_primary(__('Create'));
        frm.set_query('contact_person', function(doc) {
			return {
				query: "erpnext.selling.doctype.customer.customer.get_customer_primary_contact",
				filters: {
					'customer': doc.customer
				}
			}
		})
		frm.set_query('customer_address', function(doc) {
			return {
				filters: {
					'link_doctype': 'Customer',
					'link_name': doc.customer
				}
			}
		})
	},
	setup: function (frm) {
	    frm.set_query("serial_no", function () {
			return {
				filters: {
					item_code: frm.doc.item_code,
				},
			};
		});
		frm.set_query('contact_person', erpnext.queries.contact_query);
		frm.set_query('customer_address', erpnext.queries.address_query);
		frm.set_query('customer', erpnext.queries.customer);
		erpnext.utils.get_party_details(frm)
	},
	customer: function (frm) {
		erpnext.utils.get_party_details(frm);
	},
	customer_address: function (frm) {
		erpnext.utils.get_address_display(frm, 'customer_address', 'address_display');
	},
	contact_person: function (frm) {
		erpnext.utils.get_contact_details(frm);
	},
	water_taste_10: function(frm){
	    if (frm.doc.water_taste_10 > 10){
		    frm.set_value('water_taste_10', 0);
            frm.refresh_field("water_taste_10");
            frappe.throw("Water Taste is must between 0 to 10.")
	    }
	},
	serial_no: function(frm){
	    if(frm.doc.serial_no){
	        return frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Serial No",
					filters: {name: frm.doc.serial_no},
					fieldname: ["item_code","customer"]
				},
				callback: function(r) {
					if(r.message){
					    frm.set_value("item_code", r.message.item_code);
					    frm.set_value("customer", r.message.customer);
					}
				}
			});
	    }
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
