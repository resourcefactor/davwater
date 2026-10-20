{% include "davwater/public/js/serial_location.js" %}

frappe.provide("davwater.dav_water");
frappe.ui.form.on('Service Schedule', {
	setup: function (frm) {
		if (frm.doc.docstatus === 0) {
			frm.set_query('contact_person', erpnext.queries.contact_query);
			frm.set_query('customer_address', erpnext.queries.address_query);
			frm.set_query('customer', erpnext.queries.customer);
			erpnext.utils.get_party_details(frm)
		}
	},
	onload: function (frm) {
		if (!frm.doc.status) {
			frm.set_value({ status: 'Draft' });
		}
		if (frm.doc.__islocal) {
			frm.set_value({ transaction_date: frappe.datetime.get_today() });
		}
	},
	refresh: function (frm) {
		setTimeout(() => {
			frm.toggle_display('generate_schedule', !(frm.is_new()));
			frm.toggle_display('schedule', !(frm.is_new()));
		}, 10);

		if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Sales Order'),function () {
                erpnext.utils.map_current_doc({
                    method: "davwater.hook_event.custome_methods.make_service_schedule",
                    source_doctype: "Sales Order",
                    target: frm,
                    setters: {
                        customer: frm.doc.customer || undefined
                    },
                    get_query_filters: {
                        docstatus: 1,
                        company: frm.doc.company
                    }
                });
            }, __("Get Items From"));
        }
        else if (frm.doc.docstatus === 1) {
            let schedules = frm.doc.schedules;
            let flag = schedules.some(schedule => schedule.completion_status === "Pending");
            if (flag) {
                frm.add_custom_button(__('Service Visit'), function () {
                    let options = "";
                    frm.call('get_pending_data', {data_type: "items"}).then(r => {
                        options = r.message;

                        let schedule_id = "";
                        let d = new frappe.ui.Dialog({
                            title: __("Enter Visit Details"),
                            fields: [{
                                fieldtype: "Select",
                                fieldname: "item_name",
                                label: __("Item Name"),
                                options: options,
                                reqd: 1,
                                onchange: function () {
                                    let field = d.get_field("scheduled_date");
                                    frm.call('get_pending_data',
                                        {
                                            item_name: this.value,
                                            data_type: "date"
                                        }).then(r => {
                                        field.df.options = r.message;
                                        field.refresh();
                                    });
                                }
                            },
                            {
                                label: __('Scheduled Date'),
                                fieldname: 'scheduled_date',
                                fieldtype: 'Select',
                                options: "",
                                reqd: 1,
                                onchange: function () {
                                    let field = d.get_field('item_name');
                                    frm.call(
                                        'get_pending_data',
                                        {
                                            item_name: field.value,
                                            s_date: this.value,
                                            data_type: "id"
                                        }).then(r => {
                                        schedule_id = r.message;
                                    });
                                }
                            },
                            ],
                            primary_action_label: 'Create Visit',
                            primary_action(values) {
                                frappe.call({
                                    method: "davwater.dav_water.doctype.service_schedule.service_schedule.make_maintenance_visit",
                                    args: {
                                        item_name: values.item_name,
                                        scheduled_date: values.scheduled_date,
                                        s_id: schedule_id,
                                        source_name: frm.doc.name,
                                    },
                                    callback: function (r) {
                                        if (!r.exc) {
                                            frappe.model.sync(r.message);
                                            frappe.set_route("Form", r.message.doctype, r.message.name);
                                        }
                                    }
                                });
                                d.hide();
                            }
                        });
                        d.show();
                    });
                }, __('Create'));
            }
        }
        if (frm.doc.docstatus == 1){
            frm.add_custom_button(__('Update Location'), function () {
                frappe.call({
                    method: 'davwater.dav_water.doctype.service_schedule.service_schedule.get_serial_no_with_location',
                    args: {
                        doc_name: frm.doc.name
                    },
                    callback: function(r) {
                        set_serial_no_location(frm, r.message)
                    }
                });
            });

            frm.add_custom_button(__('Re-new Service Plan'), function(){
                let newdoc = frappe.model.copy_doc(frm.doc);
                newdoc.existing_service_plan = frm.doc.name;
                newdoc.is_renew_plan = 1
                newdoc.idx = null;
                newdoc.__run_link_triggers = false;
                newdoc['items'].forEach((itm, index) => {
                     itm.start_date = null
                     itm.end_date = null
                });
                frappe.set_route('Form', newdoc.doctype, newdoc.name);
            }).addClass('btn btn-primary');
        }

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
	generate_schedule: function (frm) {
		if (frm.is_new()) {
			frappe.msgprint(__('Please save first'));
		} else {
			frm.call('generate_schedule');
		}
	},
	start_date: function(doc, cdt, cdn) {
        set_no_of_visits(doc, cdt, cdn);
    },
    end_date: function(doc, cdt, cdn) {
	    frm.trigger("set_no_of_visits")
    },
    periodicity: function(doc, cdt, cdn) {
	    frm.trigger("set_no_of_visits")

    },
    no_of_visits: function(doc, cdt, cdn) {
	    frm.trigger("set_no_of_visits")
    },
    set_no_of_visits: function(doc, cdt, cdn) {
        var item = frappe.get_doc(cdt, cdn);
        if (item.start_date && item.periodicity) {
            frm.call('validate_end_date_visits');

        }
    }

})



