frappe.ui.form.on('Quality Inspection', {
    refresh: function(frm){
        frm.set_query('bom_template', () => {
			return {
				filters: {
					is_qc_template: 1,
					docstatus: 1
				}
			};
		});
        frm.set_query('s_warehouse', () => {
			return {
				filters: {
					is_group: 0
				}
			};
		});
        frm.set_query('t_warehouse', () => {
			return {
				filters: {
					is_group: 0
				}
			};
		});
    },
    bom_template: function(frm){
        frappe.call({
            method: "davwater.hook_event.customize_quality_inspection.get_bom_material",
            args: {
                bom: frm.doc.bom_template
            },
            callback: function(r) {
                cur_frm.clear_table("raw_material_item");
                cur_frm.clear_table("finish_item");
                r.message.material.forEach(function(element) {
                    var c = frm.add_child("raw_material_item");
                    c.item_code = element.item_code;
                    c.item_name = element.item_name;
                    c.uom = element.uom;
                    c.qty = element.qty;
                    c.rate = element.rate;
                    c.amount = element.amount;
                });

                r.message.finish.forEach(function(element) {
                    var c = frm.add_child("finish_item");
                    c.item_code = element.item_code;
                    c.item_name = element.item_name;
                    c.uom = element.uom;
                    c.qty = element.qty;
                });

                refresh_field("raw_material_item");
                refresh_field("finish_item");
            }
        })
    },
    s_warehouse: function(frm, cdt, cdn) {
        erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "raw_material_item", "s_warehouse");
	},
	t_warehouse: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "finish_item", "t_warehouse");
	}
});


frappe.ui.form.on('Quality Inspection Material Item', {
    item_code: function(frm, cdt, cdn){
        var item = locals[cdt][cdn];
        if (item.item_code){
            frappe.call({
                method: "davwater.hook_event.customize_quality_inspection.get_valuation_rate",
                args: {
                    item_code: item.item_code,
                    company: frappe.defaults.get_default('company'),
                    warehouse: item.s_warehouse
                },
                callback: function(r) {
                     frappe.model.set_value( cdt, cdn, 'rate',r.message)
                     calculate_processing_cost_amount(frm, cdt, cdn)
                }
            })
        }
        frappe.model.set_value(cdt,cdn,"s_warehouse",frm.doc.s_warehouse);
    },
    qty: function(frm, cdt, cdn) {
        calculate_processing_cost_amount(frm, cdt, cdn)
	},
	rate: function(frm, cdt, cdn) {
        calculate_processing_cost_amount(frm, cdt, cdn)
	},
	s_warehouse:function(frm, cdt, cdn){
        var item = locals[cdt][cdn];
        if (item.item_code){
            frappe.call({
                method: "davwater.hook_event.customize_quality_inspection.get_valuation_rate",
                args: {
                    item_code: item.item_code,
                    company: frappe.defaults.get_default('company'),
                    warehouse: item.s_warehouse
                },
                callback: function(r) {
                     frappe.model.set_value( cdt, cdn, 'rate',r.message)
                     calculate_processing_cost_amount(frm, cdt, cdn)
                }
            })
        }
    },
});

frappe.ui.form.on('Quality Inspection Finish Item', {
    item_code: function(frm, cdt, cdn){
        frappe.model.set_value(cdt,cdn,"t_warehouse",frm.doc.t_warehouse);
    },
    qty: function(frm, cdt, cdn) {
        calculate_processing_cost_amount(frm, cdt, cdn)
	},
	rate: function(frm, cdt, cdn) {
        calculate_processing_cost_amount(frm, cdt, cdn)
	}
});

function calculate_processing_cost_amount(frm, cdt, cdn){
    var row = locals[cdt][cdn];
    let amount = row.qty * row.rate
    frappe.model.set_value(cdt,cdn,"amount",amount);
}
