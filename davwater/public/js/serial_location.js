
function set_serial_no_location(frm, serial_no_lst){
//    let data = JSON.parse(serial_no_lst || '[]')
    let data = serial_no_lst
    let dialog = new frappe.ui.Dialog({
        title: __('Serial No. Locations'),
        fields: [
            {
                fieldname: 'locations',
                fieldtype: 'Table',
                label: __('Locations'),
                in_editable_grid: true,
                reqd: 1,
                fields: [{
                    fieldtype: 'Read Only',
                    fieldname: 'serial_no',
                    in_list_view: 1,
                    label: __('Serial No'),
                    columns: 2,
                },
                {
                    fieldtype: 'Link',
                    fieldname: 'location',
                    label: __('Location'),
                    options: 'Location',
                    in_list_view: 1,
                    reqd: 1,
                    columns: 3
                }],
                data: data
            },
        ],
        primary_action_label: __('Update'),
        primary_action: function(values) {
            let child_data = values.locations;
            frappe.call({
                method: 'davwater.hook_event.delivery_note.set_serial_no_location',
                args: {
                    doc_name: frm.doc.name,
                    location_lst: child_data
                },
                callback: function(r) {
                    dialog.hide();
                    frm.reload_doc();
                }
            });
        }
    });
    dialog.show();
}
