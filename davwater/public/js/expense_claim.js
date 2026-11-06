// Multi currency is handled by HRMS at claim level: amounts are entered in the claim currency and the
// company-currency (base_*) values are computed from the claim exchange rate. The claim currency and
// exchange rate are copied to every expense row so they never have to be entered again on the line.
const sync_expense_row_currency = function(frm) {
	(frm.doc.expenses || []).forEach(function(row) {
		if (row.currency !== frm.doc.currency) {
			frappe.model.set_value(row.doctype, row.name, "currency", frm.doc.currency);
		}
		if (flt(row.exchange_rate) !== flt(frm.doc.exchange_rate)) {
			frappe.model.set_value(row.doctype, row.name, "exchange_rate", frm.doc.exchange_rate);
		}
	});
};

frappe.ui.form.on('Expense Claim', {
	currency: function(frm) {
		sync_expense_row_currency(frm);
	},
	exchange_rate: function(frm) {
		sync_expense_row_currency(frm);
	},
	before_save: function(frm) {
		sync_expense_row_currency(frm);
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
	expense_type: function(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "currency", frm.doc.currency);
		frappe.model.set_value(cdt, cdn, "exchange_rate", frm.doc.exchange_rate);
	},
	expenses_add: function(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "currency", frm.doc.currency);
		frappe.model.set_value(cdt, cdn, "exchange_rate", frm.doc.exchange_rate);
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