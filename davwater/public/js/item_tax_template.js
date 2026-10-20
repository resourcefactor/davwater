frappe.ui.form.on('Item Tax Template', {
    is_out_of_scope: function(frm){
        if(frm.doc.is_out_of_scope){
            frm.doc.is_exempt = 0
            frm.doc.is_zero_rated = 0
        }
        frm.refresh_fields();
    },
    is_exempt: function(frm){
        if(frm.doc.is_exempt){
            frm.doc.is_out_of_scope = 0
            frm.doc.is_zero_rated = 0
        }
        frm.refresh_fields();
    },
    is_zero_rated: function(frm){
        if(frm.doc.is_exempt){
            frm.doc.is_out_of_scope = 0
            frm.doc.is_exempt = 0
        }
        frm.refresh_fields();
    },

})