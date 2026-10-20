frappe.ui.form.on('Expense Claim', {
	currency: function(frm){
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		if (frm.doc.currency == 'AED'){
			frm.set_value("exchange_rate", 1);
		}
		else {
			frappe.db.get_value("Currency Exchange", {"from_currency": frm.doc.currency, "to_currency": company_currency, "date": frm.doc.posting_date}, "exchange_rate", (r) => {
				if(r.exchange_rate) {
					frm.set_value("exchange_rate", r.exchange_rate);
				}
				else {
					frappe.db.get_value("Currency Exchange", {"from_currency": frm.doc.currency, "to_currency": company_currency}, "exchange_rate", (r) => {
						frm.set_value("exchange_rate", r.exchange_rate);
					});
				}
			});
		}
	},
	posting_date: function(frm){
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		if (frm.doc.currency == 'AED'){
			frm.set_value("exchange_rate", 1);
		}
		else {
			frappe.db.get_value("Currency Exchange", {"from_currency": frm.doc.currency, "to_currency": company_currency, "date": frm.doc.posting_date}, "exchange_rate", (r) => {
				if(r.exchange_rate) {
					frm.set_value("exchange_rate", r.exchange_rate);
				}
				else {
					frappe.db.get_value("Currency Exchange", {"from_currency": frm.doc.currency, "to_currency": company_currency}, "exchange_rate", (r) => {
						frm.set_value("exchange_rate", r.exchange_rate);
					});
				}
			});
		}
	}
})

frappe.ui.form.on('Expense Claim Detail', {
    item_tax_template: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
        frappe.call({
			method: "davwater.hook_event.expense_claim.get_tax_template_tax",
			args: {
				"item_tax_template": d.item_tax_template,
				"total_sanctioned_amount": frm.doc.total_sanctioned_amount,
				"data": d
			},
			callback: function(r) {
				if (r.message) {
                    r.message.forEach(function(d) {
                        var t = frm.add_child("taxes");
                        t.account_head = d.tax
                        t.description = d.tax
                        t.rate = d.rate
                        t.taxable_amount = d.taxable_amount
                        t.tax_amount = d.amount
                        t.total = d.total
                    });
                    refresh_field("taxes");
                    frm.trigger("get_taxes");
				}
			}
		});
    },
	base_amount: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.exchange_rate) {
			frappe.model.set_value(cdt, cdn, "base_sanctioned_amount", d.base_amount);
			frappe.model.set_value(cdt, cdn, "amount", d.base_amount * d.exchange_rate);
			frappe.model.set_value(cdt, cdn, "sanctioned_amount", d.base_sanctioned_amount * d.exchange_rate);
			frm.refresh_fields();
		}
		else{
			frappe.model.set_value(cdt, cdn, "base_sanctioned_amount", d.base_amount);
			frappe.model.set_value(cdt, cdn, "amount", d.base_amount);
			frappe.model.set_value(cdt, cdn, "sanctioned_amount", d.base_sanctioned_amount);
			frm.refresh_fields();
		}
	},
	base_sanctioned_amount: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.exchange_rate) {
			frappe.model.set_value(cdt, cdn, "sanctioned_amount", d.base_sanctioned_amount * d.exchange_rate);
			frm.refresh_fields();
		}
		else{
			frappe.model.set_value(cdt, cdn, "sanctioned_amount", d.base_sanctioned_amount);
			frm.refresh_fields();
		}
	},
	expense_type: function(frm, cdt, cdn){
		if(frm.doc.is_multi_currency){
			frappe.model.set_value(cdt, cdn, "currency", frm.doc.currency);
			frappe.model.set_value(cdt, cdn, "exchange_rate", frm.doc.exchange_rate);
			frm.refresh_fields();
		}
		else{
			frappe.model.set_value(cdt, cdn, "currency", 'AED');
			frappe.model.set_value(cdt, cdn, "exchange_rate", 1);
			frm.refresh_fields();
		}
	},
	exchange_rate: function(frm, cdt, cdn){
		var d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "sanctioned_amount", d.base_sanctioned_amount * d.exchange_rate);
		frappe.model.set_value(cdt, cdn, "amount", d.base_amount * d.exchange_rate);
		frm.refresh_fields();
	},
	currency: function(frm, cdt, cdn){
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		var d = locals[cdt][cdn];
		if (frm.doc.currency == 'AED'){
			frm.set_value("exchange_rate", 1);
		}
		else {
			frappe.db.get_value("Currency Exchange", {"from_currency": d.currency, "to_currency": company_currency, "date": frm.doc.posting_date}, "exchange_rate", (r) => {
				if(r.exchange_rate) {
					frappe.model.set_value(cdt, cdn, "exchange_rate", r.exchange_rate);
				}
				else {
					frappe.db.get_value("Currency Exchange", {"from_currency": d.currency, "to_currency": company_currency}, "exchange_rate", (r) => {
						frappe.model.set_value(cdt, cdn, "exchange_rate", r.exchange_rate);
					});
				}
			});
		}
		frappe.model.set_value(cdt, cdn, "sanctioned_amount", d.base_sanctioned_amount * d.exchange_rate);
		frappe.model.set_value(cdt, cdn, "amount", d.base_amount * d.exchange_rate);
		frm.refresh_fields();
	}
})

frappe.ui.form.on("Expense Taxes and Charges", {
	account_head: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "taxable_amount", frm.doc.total_sanctioned_amount)
		refresh_field("taxable_amount", cdn, "taxes");
	},
	rate: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(!child.amount) {
			child.tax_amount = flt(child.taxable_amount) * (flt(child.rate)/100);
		}
		frm.trigger("calculate_total_tax", cdt, cdn);
	},
	taxable_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(!child.amount) {
			child.tax_amount = flt(child.taxable_amount) * (flt(child.rate)/100);
		}
		frm.trigger("calculate_total_tax", cdt, cdn);
	},
})