// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Callout', {
    refresh: function(frm) {
        frm.add_custom_button(__('Create Service Visit'), function () {
            frappe.call({
                method: "make_service_visit",
                doc: frm.doc,
                callback: function(r){
                    if (!r.exc) {
                        frappe.model.sync(r.message);
                        frappe.set_route("Form", r.message.doctype, r.message.name);
                    }
                }
            });
        })
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
    customer: function (frm) {
		erpnext.utils.get_party_details(frm)
	},
	customer_address: function (frm) {
		erpnext.utils.get_address_display(frm, 'customer_address', 'address_display');
	},
    contact_person: function (frm) {
		erpnext.utils.get_contact_details(frm);
	},
	serial_no: function(frm){
	    if(frm.doc.serial_no){
	        return frm.call({
				method: "frappe.client.get",
				args: {
					doctype: "Serial No",
					filters: {name: frm.doc.serial_no}
				},
				callback: function(r) {
					if(r.message){
					    frm.set_value("item_code", r.message.item_code);
					    frm.set_value("warranty_expiry_date", r.message.warranty_expiry_date);
					    frm.set_value("amc_expiry_date", r.message.amc_expiry_date);
					    frm.set_value("warranty_amc_status", r.message.maintenance_status);
					}
				}
			});
	    }
	}
});
