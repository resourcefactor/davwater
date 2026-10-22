frappe.ui.form.on('Quotation', {
    order_type: function(frm){
        if(frm.doc.order_type == 'Lease Proposal'){
            frappe.require("assets/davwater/js/lease_order.js", function() {
                new erpnext.SetLeasePackInfo({
                    frm: frm,
                    posting_date: frm.doc.transaction_date
                });
            });
            davwater.settings.set_leasing_cost_center(frm);
        }
    },
	validate: async function(frm, cdt, cdn){
	    await davwater.settings.set_leasing_cost_center(frm);
	}
});

frappe.ui.form.on('Quotation Item', {
    is_service_pack_item: function(frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        if(item.is_service_pack_item && frm.doc.order_type == 'Lease Proposal'){
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