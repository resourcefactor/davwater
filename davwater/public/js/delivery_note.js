{% include "davwater/public/js/serial_location.js" %}

frappe.ui.form.on('Delivery Note', {
	refresh: function(frm){
	    if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Service Schedule'), function () {
                frappe.call({
                    method: 'davwater.hook_event.delivery_note.create_service_schedule',
                    args: {
                        doc_name: frm.doc.name
                    },
                    callback: function(r) {
                        var doc = frappe.model.sync(r.message);
                        frappe.set_route('Form', doc[0].doctype, doc[0].name);
                    }
                });
            }, __('Create'));

            if(frm.doc.type_of_sale == 'Lease with Service Pack' || frm.doc.type_of_sale == 'Pay Per Liter'){
                frm.add_custom_button(__('Update Location'), function () {
                    frappe.call({
                        method: 'davwater.hook_event.delivery_note.get_serial_no_with_location',
                        args: {
                            doc_name: frm.doc.name
                        },
                        callback: function(r) {
                            set_serial_no_location(frm, r.message)
                        }
                    });
                });
            }

        }
	},
	posting_date: function(frm){
	    let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(frm.doc.items, "start_date", frm.doc.posting_date);
		frm.set_value("start_date", frm.doc.posting_date)
	},
	type_of_sale: function(frm){
	    if(frm.doc.type_of_sale == 'Lease with Service Pack' || frm.doc.type_of_sale == 'Pay Per Liter'){
	        frappe.require("assets/davwater/js/lease_order.js", function() {
                new erpnext.SetLeasePackInfo({
                    frm: frm,
                    posting_date: frm.doc.posting_date
                });
            });
	    }
	},
	residual_value: function(frm){
        frm.doc.items.forEach((item) => {
            item.asset_amount = Math.round(((item.rate * item.qty) / 100) * frm.doc.residual_value)
        })
        frm.refresh_field("items");
	},
	lease_period: function(frm){
	    if(frm.doc.lease_period && frm.doc.start_date){
            frappe.call({
                method: "davwater.hook_event.delivery_note.get_to_date",
                args: {
                    period: frm.doc.lease_period,
                    start_date: frm.doc.start_date
                },
                callback: function(r) {
                    frm.doc.end_date = r.message;
                    frm.refresh_field("end_date");
                }
            })
        }
	},
	start_date: function(frm){
	    if(frm.doc.lease_period && frm.doc.start_date){
            frappe.call({
                method: "davwater.hook_event.delivery_note.get_to_date",
                args: {
                    period: frm.doc.lease_period,
                    start_date: frm.doc.start_date
                },
                callback: function(r) {
                    frm.doc.end_date = r.message;
                    frm.refresh_field("end_date");
                }
            })
        }
	}
});

frappe.ui.form.on('Delivery Note Item', {
    is_service_pack_item: function(frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        if(item.is_service_pack_item && frm.doc.type_of_sale == 'Sales with Servicing Pack'){
            set_service_pack_info(frm, item);
        }
        if(item.is_service_pack_item && (frm.doc.type_of_sale == 'Lease with Service Pack' || frm.doc.type_of_sale == 'Pay Per Liter')){
            item.lease_period = frm.doc.lease_period
            item.start_date = frm.doc.start_date
            item.end_date = frm.doc.end_date
            item.no_of_visits = frm.doc.no_of_visits
            item.service_team = frm.doc.service_team
            item.periodicity = frm.doc.periodicity
            item.location = frm.doc.location
        }
	},
	item_code: function(frm, cdt, cdn){
	    var d = locals[cdt][cdn]
	    if (d.item_code){
	        frappe.db.get_value('Item', {'item_code': d.item_code}, 'item_group', async (r) => {
	            if(r.item_group == 'Products'){
	                let trial_account = await davwater.settings.get("trial_cogs_account");
	                if(trial_account){
	                    frappe.model.set_value(cdt, cdn, "expense_account", trial_account);
	                }
	            }
	        })
	    }
	},
	qty: function(frm, cdt,cdn){
	    var d = locals[cdt][cdn]
	    let asset_amount = Math.round(((d.rate * d.qty) / 100) * frm.doc.residual_value)
	    frappe.model.set_value(cdt, cdn, "asset_amount", asset_amount);

	},
	rate: function(frm, cdt,cdn){
	    var d = locals[cdt][cdn]
	    let asset_amount = Math.round(((d.rate * d.qty) / 100) * frm.doc.residual_value)
	    frappe.model.set_value(cdt, cdn, "asset_amount", asset_amount);

	}
});

function set_service_pack_info(frm, item){
	frappe.require("assets/davwater/js/util.js", function() {
		new erpnext.SetServicePackInfo({
			frm: frm,
			item: item,
			posting_date: frm.doc.posting_date
		});
	});
}

