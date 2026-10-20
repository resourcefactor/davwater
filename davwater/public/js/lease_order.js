erpnext.SetLeasePackInfo = Class.extend({
	init: function(opts, show_dialog) {
		$.extend(this, opts);
		let d = this.item;
		this.setup();
	},
	setup: function() {
		this.make_dialog();
		this.on_close_dialog();
	},
	make_dialog: function() {
		var me = this;
		this.data = this.oldest ? this.oldest : [];
		let title = "Lease with Service Pack Detail";
		let fields = [
			{
				fieldname: 'lease_period',
				fieldtype:'Select',
				label: __('Lease Period'),
				reqd: 1,
				options:"\n1Year\n2Year\n3Year\n4Year\n5Year",
				onchange: function () {
                    let str_field = me.dialog.get_field("start_date");
                    let end_field = me.dialog.get_field("end_date");
                    frappe.call({
                        method: "davwater.hook_event.delivery_note.get_to_date",
                        args: {
                            period: this.value,
                            start_date: str_field.value
                        },
                        callback: function(r) {
                            end_field.value = r.message;
                            end_field.refresh();
                        }
                    })
                }
			},
			{
				fieldname: 'start_date',
				fieldtype:'Date',
				label: __('Start Date'),
				reqd: 1,
				default: this.posting_date,
				onchange: function () {
                    let lease_period = me.dialog.get_field("lease_period");
                    let end_field = me.dialog.get_field("end_date");
                    if(lease_period.value){
                        frappe.call({
                            method: "davwater.hook_event.delivery_note.get_to_date",
                            args: {
                                period: lease_period.value,
                                start_date: this.value
                            },
                            callback: function(r) {
                                end_field.value = r.message;
                                end_field.refresh();
                            }
                        })
                    }
                }
			},
			{
				fieldname: 'end_date',
				fieldtype:'Date',
				label: __('End Date'),
				reqd: 1
			},
			{
				fieldname: 'residual_value',
				fieldtype:'Percent',
				label: __('Residual Value(%)'),
				reqd: 1,
				default: 50
			},
			{fieldtype:'Column Break'},
			{
				fieldname: 'periodicity',
				fieldtype:'Select',
				options: "\nWeekly\nMonthly\nQuarterly\nHalf Yearly\nYearly\nRandom",
				label: __('Periodicity'),
				onchange: function () {
                    let str_field = me.dialog.get_field("start_date");
                    let end_field = me.dialog.get_field("end_date");
                    let no_of_visits = me.dialog.get_field("no_of_visits");
                    frappe.call({
                        method: "davwater.hook_event.delivery_note.get_no_visits",
                        args: {
                            periodicity: this.value,
                            start_date: str_field.value,
                            end_date: end_field.value
                        },
                        callback: function(r) {
                            no_of_visits.value = r.message;
                            no_of_visits.refresh();
                        }
                    })
                }
			},
			{
				fieldname: 'no_of_visits',
				fieldtype:'Int',
				label: __('No of Visits'),
				reqd: 1
			},
			{
				fieldname: 'service_team',
				fieldtype:'Link',
				options: 'Service Team',
				label: __('Service Team'),
				reqd: 1
			},
			{
				fieldname: 'location',
				fieldtype:'Link',
				options: 'Location',
				label: __('Location'),
			}
		];
		this.dialog = new frappe.ui.Dialog({
			title: title,
			fields: fields
		});

		this.dialog.set_primary_action(__('Insert'), function() {
			me.values = me.dialog.get_values();
//			if(me.validate()) {
			    let frm = me.frm;
			    frm.doc.lease_period = me.values.lease_period
			    frm.doc.start_date = me.values.start_date
			    frm.doc.end_date = me.values.end_date
			    frm.doc.no_of_visits = me.values.no_of_visits
			    frm.doc.service_team = me.values.service_team
			    frm.doc.periodicity = me.values.periodicity
			    frm.doc.location = me.values.location
			    frm.doc.residual_value = me.values.residual_value
			    frm.doc.items.forEach((item) => {
			        if(item.is_service_pack_item){
			            item.lease_period = me.values.lease_period
                        item.start_date = me.values.start_date
                        item.end_date = me.values.end_date
                        item.no_of_visits = me.values.no_of_visits
                        item.service_team = me.values.service_team
                        item.periodicity = me.values.periodicity
                        item.location = me.values.location
			        }
                })
			    frm.refresh_fields();
				me.dialog.hide()
//			}
		});
		this.dialog.show();
	},
	on_close_dialog: function() {
		this.dialog.get_close_btn().on('click', () => {
			this.on_close && this.on_close(this.item);
		});
	},
	validate: function() {
		let values = this.values;
		if(!values.start_date) {
			frappe.throw(__("Please select a Start Date"));
			return false;
		}
		if(!values.end_date) {
			frappe.throw(__("Please select a End Date"));
			return false;
		}
		if(!values.sales_person) {
			frappe.throw(__("Please select a Sales Person"));
			return false;
		}
		if(!values.no_of_visits) {
			frappe.throw(__("Please select a No. of Visit"));
			return false;
		}
		return true;
	}
});
