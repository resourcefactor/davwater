frappe.ui.form.on("Sales Invoice", {
    company: function(frm) {
        if(frm.is_new() || frm.doc.__islocal) {
            var ret_obj = setseries(frm.doc.company);
            frm.set_value("naming_series", ret_obj.series);
        }
    },
    is_return: function(frm) {
        if(frm.is_new() || frm.doc.__islocal) {
            frm.set_value("naming_series", "RET- .###");
        }
    },
    refresh: function(frm) {
        if(frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Service Schedule'), function() {
                make_service_schedule(frm);
            }, __('Create'));
        }
    },
    validate: function(frm) {
        if(frm.is_new() || frm.doc.__islocal) {
            if(frm.doc.is_return) {
                frm.set_value("naming_series", "RET- .###");
            } else {
                var ret_obj = setseries(frm.doc.company);
                frm.set_value("naming_series", ret_obj.series);
            }
        }
    }
});

function setseries(company) {
    var ret_obj = { series: "" };
    switch(company) {
        case "AIR WATER UNITS TRADING LTD": ret_obj.series = "INV-.####"; break;
        case "AIR WATER VENTURES LTD": ret_obj.series = "VL-INV-.####"; break;
    }
    return ret_obj;
}

function make_service_schedule(frm) {
    frappe.model.open_mapped_doc({
        method: "davwater.hook_event.custome_methods.make_sales_inv_service_schedule",
        frm: frm
    });
}