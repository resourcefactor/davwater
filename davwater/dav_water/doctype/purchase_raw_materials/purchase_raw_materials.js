// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Raw Materials', {
    onload: function(frm){
        if (frm.doc.__islocal) {
			frm.set_value({ posting_date: frappe.datetime.get_today() });
		}
    },
	refresh: function(frm) {
        frm.fields_dict.get_raw_materials.$input.addClass("btn-primary");
        frm.set_query('purchase_order', function(doc) {
			return {
				filters: {
					'docstatus': 1,
					'is_subcontracted': 'Yes'
				}
			}
		})
        frm.set_query('warehouse', function(doc) {
			return {
				filters: {
					'is_group': 0
				}
			}
		})
	},
	get_raw_materials: function(frm){
	    if (!frm.doc.purchase_order){
	        frappe.throw("Select Purchase Order First")
	    }
        frappe.call({
            method: "get_raw_materials",
            doc: frm.doc,
            callback: function(r) {
                frm.clear_table("items");
                if(r.message) {
                    r.message.forEach(function(d) {
                        var item = frm.add_child("items");
                        item.item_code = d.item_code
                        item.item_name = d.item_name
                        item.warehouse = d.warehouse
                        item.req_qty = d.req_qty
                        item.uom = d.uom
                        item.avl_qty = d.avl_qty
                        item.rate = d.rate
                        item.net_qty = d.net_qty
                        item.minimum_order_qty = d.minimum_order_qty
                        item.ordered_qty = d.ordered_qty
                        item.order_qty = d.order_qty
                        item.purchase_uom = d.purchase_uom
                        item.supplier = d.supplier
                        item.supplier_name = d.supplier_name
                    })
                }
                refresh_field("items");
            }
        });
	},
	warehouse: function(frm){
		let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(frm.doc.items, "warehouse", frm.doc.warehouse);
	}
});

frappe.ui.form.on('Purchase Raw Materials Item', {
    item_code: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]
        if (row.item_code && row.warehouse){
            update_qty(frm, cdt, cdn)
        }
    },
    warehouse: function(frm, cdt, cdn){
        var row = locals[cdt][cdn]
        if (row.item_code && row.warehouse){
            update_qty(frm, cdt, cdn)
        }
    }
});

function update_qty(frm, cdt, cdn){
    var row = locals[cdt][cdn];
    frappe.call({
        method: "davwater.dav_water.doctype.purchase_raw_materials.purchase_raw_materials.update_qty",
        args:{
            item_code: row.item_code,
            warehouse: row.warehouse,
            req_qty: row.req_qty,
        },
        callback: function(r) {
            if(r.message){
                frappe.model.set_value(cdt,cdn,"avl_qty",r.message.avl_qty);
                frappe.model.set_value(cdt,cdn,"net_qty",r.message.net_qty);
                frappe.model.set_value(cdt,cdn,"order_qty",r.message.order_qty);
                refresh_field("avl_qty", cdn, "items");
                refresh_field("net_qty", cdn, "items");
                refresh_field("order_qty", cdn, "items");
            }
        }
    })
}