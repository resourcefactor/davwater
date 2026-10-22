frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {
        if(frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Service Schedule'), function() {
                make_service_schedule(frm);
            }, __('Create'));
        }
    }
});

function make_service_schedule(frm) {
    frappe.model.open_mapped_doc({
        method: "davwater.hook_event.custome_methods.make_sales_inv_service_schedule",
        frm: frm
    });
}
