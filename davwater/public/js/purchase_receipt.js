frappe.ui.form.on('Purchase Receipt', {
	refresh: function(frm){
	     if (frm.doc.docstatus == 1) {
	        frappe.call({
                method: 'davwater.hook_event.Override_purchase_receipt.check_qc_is_created',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(r) {
                    if(!r.message){
                         frm.add_custom_button(__('Quality Inspection'), function () {
                             frappe.call({
                                method: 'davwater.hook_event.Override_purchase_receipt.make_qc',
                                args: {
                                    doc_name: frm.doc.name
                                },
                                callback: function(r) {
                                    frm.reload_doc();
                                }
                             })
                         }, __('Create'));
                    }
                }
            });

        }
	}
});