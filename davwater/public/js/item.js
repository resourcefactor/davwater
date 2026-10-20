frappe.ui.form.on('Item', {
	item_group_code: function (frm) {
		frm.set_value('cust_item_code', generate_name(frm));
	},
	machine_code: function (frm) {
		frm.set_value('cust_item_code', generate_name(frm));
	},
	before_save: function(frm){
		if (frm.doc.generate_auto_item_code) {
			var cust_item_code = "";
			if (frm.doc.machine_code) {
				if (frm.doc.item_group_code) {
					cust_item_code +=  frm.doc.machine_code + "-";
				}
				else {
					cust_item_code +=  frm.doc.machine_code;
				}
			}
			if (frm.doc.item_group_code) {
				cust_item_code += frm.doc.item_group_code;
			}
			frm.set_value('cust_item_code', cust_item_code);
		}
		else{
			frm.set_value('cust_item_code', 'I');
		}
	},
//	after_save: function(frm){
//		frm.set_value('item_code', frm.doc.name);
//		frm.refresh_fields();
//	}
});

function generate_name(frm) {
	if (frm.doc.generate_auto_item_code) {
		var cust_item_code = "";
		if (frm.doc.item_group_code) {
			cust_item_code += frm.doc.item_group_code;
		}
		if (frm.doc.machine_code) {
			cust_item_code += "-" + frm.doc.machine_code;
		}
		return cust_item_code;
	}
	else {
		return frm.doc.item_code;
	}
}