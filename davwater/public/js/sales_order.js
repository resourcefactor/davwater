frappe.ui.form.on('Sales Order', {
	delivery_date: function(frm){
	    let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(frm.doc.items, "start_date", frm.doc.delivery_date);
		frm.set_value("start_date", frm.doc.delivery_date)
	},
	type_of_sale: function(frm){
	    if(frm.doc.type_of_sale == 'Lease with Service Pack' || frm.doc.type_of_sale == 'Pay Per Liter'){
	        frappe.require("assets/davwater/js/lease_order.js", function() {
                new erpnext.SetLeasePackInfo({
                    frm: frm,
                    posting_date: frm.doc.delivery_date
                });
            });
            frm.doc.items.forEach(function(item) {
                frappe.model.set_value(item.doctype, item.name, 'cost_center', 'Leasing - DW')
            })
	    }
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
	},
	validate: function(frm, cdt, cdn){
	    frm.doc.items.forEach(function(item) {
	        frappe.model.set_value(item.doctype, item.name, 'cost_center', 'Leasing - DW')
	    })
	}
});

frappe.ui.form.on('Sales Order Item', {
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
	}
});

function set_service_pack_info(frm, item){
	frappe.require("assets/davwater/js/util.js", function() {
		new erpnext.SetServicePackInfo({
			frm: frm,
			item: item,
			posting_date: frm.doc.delivery_date
		});
	});
}