# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.utils import formatdate, get_link_to_form


def execute(filters=None):

	vat_accounts = get_sa_vat_accounts(filters)
	get_conditions(filters)
	columns = get_columns()
	data = get_data(filters, vat_accounts)
	return columns, data

def get_sa_vat_accounts(filters):
	sa_vat_accounts = frappe.get_all("UAE VAT Account",
		filters = {"parent": filters.company}, pluck="account")
	if not sa_vat_accounts and not frappe.flags.in_test and not frappe.flags.in_migrate:
		link_to_settings = get_link_to_form("UAE VAT Settings", "", label="UAE VAT Settings")
		frappe.throw(_("Please set VAT Accounts in {0}").format(link_to_settings))
	return sa_vat_accounts

def get_conditions(filters):
	conditions = ""
	for opts in (("company", " and company=%(company)s"),
		("from_date", " and posting_date>=%(from_date)s"),
		("to_date", " and posting_date<=%(to_date)s")):
		if filters.get(opts[0]):
			conditions += opts[1]

	return conditions

def get_columns():
	columns = [
		{
			"fieldname": "posting_date",
			"label": "Posting Date",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "account",
			"label": "Account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 150
		},
		{
			"fieldname": "voucher_type",
			"label": "Voucher Type",
			"fieldtype": "Data",
			"width": 140,
			"hidden": 1
		},
		{
			"fieldname": "voucher_no",
			"label": "Reference",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 150
		},
		{
			"fieldname": "party_type",
			"label": "Party Type",
			"fieldtype": "Data",
			"width": 140,
			"hidden": 1
		},
		{
			"fieldname": "party",
			"label": "Party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 150
		},
		{
			"fieldname": "party_name",
			"label": "Party Name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "tax_id",
			"label": "Tax ID",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "bill_no",
			"label": "Supplier Invoice No.",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "remarks",
			"label": "Details",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "net_amount",
			"label": "Net Amount",
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "tax_amount",
			"label": "Tax Amount",
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "gross_amount",
			"label": "Gross Amount",
			"fieldtype": "Currency",
			"width": 130
		},
	]
	return columns


def get_data(filters, vat_accounts):
	item_details = {}
	sales_inv_list = ['asas', 'asas']
	purchase_inv_list = ['asas', 'asas']
	purchase_result = frappe.db.sql("""select pi.posting_date, pi.name as voucher_no, pi.remarks, pi.credit_to as account, 
				pii.item_code, 
				ixd.tax_type as account_head,
				ixd.tax_rate,			
				pii.base_net_amount as net_amount,
				pii.base_net_amount, (pii.base_net_amount * ixd.tax_rate)/ 100 as tax_amount,
				pii.base_net_amount+((pii.base_net_amount * ixd.tax_rate)/ 100) as gross_amount,
				ix.is_zero_rated, ix.is_exempt, ix.is_out_of_scope,
				"Supplier" as party_type,
				pi.supplier as party,			
				pi.supplier_name as party_name,			
				pi.tax_id,			
				pi.bill_no,			
				"Purchase Invoice" as voucher_type,
				pi.reverse_charge
				from `tabPurchase Invoice Item` as pii
				inner join `tabPurchase Invoice` pi on pi.name = pii.parent
				inner join `tabItem Tax Template` ix on ix.name = pii.item_tax_template 
				inner join `tabItem Tax Template Detail` ixd on ixd.parent = ix.name 
				where pi.docstatus = 1 and pii.item_tax_template is not null and pii.item_tax_template != '' 
				and pi.company=%(company)s 
				and pi.posting_date>=%(from_date)s 
				and pi.posting_date<=%(to_date)s 
				order by pi.posting_date, ixd.tax_rate desc""", {"company": filters.get('company'), "from_date": filters.get('from_date'),
											  "to_date": filters.get('to_date')}, as_dict=True)

	for res in purchase_result:
		if res.account_head in vat_accounts:
			rate = res.tax_rate
			label = frappe.bold("Purchase - Rate" + " " + str(rate) + "%")
			if res.reverse_charge == 'Y':
				label = frappe.bold("Purchase Reverse Charges")
			elif res.is_exempt:
				label = frappe.bold("Purchase Exempted - Rate" + " " + str(rate) + "%")
			elif res.is_out_of_scope:
				label = frappe.bold("Purchase Out of Scope - Rate" + " " + str(rate) + "%")
			item_details.setdefault(label, []).append(res)
			purchase_inv_list.append(res.voucher_no)

	pur_tax_line = frappe.db.sql("""select pi.posting_date, 
						pi.name as voucher_no, 
						pi.remarks, 
						pi.credit_to as account, 
						pix.is_zero_rated, 
						pix.base_tax_amount_after_discount_amount as tax_amount,
						pi.base_total as net_amount,
						(pix.base_tax_amount_after_discount_amount + pi.base_total) as gross_amount,
						pix.account_head,
						pix.rate as tax_rate,
						"Supplier" as party_type,
						pi.supplier as party,			
						pi.supplier_name as party_name,			
						pi.tax_id,			
						pi.bill_no,			
						"Purchase Invoice" as voucher_type,
						pi.reverse_charge,
						0 as is_exempt,
						0 as is_out_of_scope
						from `tabPurchase Taxes and Charges` pix
						inner join `tabPurchase Invoice` pi on pi.name = pix.parent
						where pi.docstatus = 1 
						and pi.name not in {0} 
						and pi.company=%(company)s 
						and pi.posting_date>=%(from_date)s 
						and pi.posting_date<=%(to_date)s """.format(tuple(purchase_inv_list)),
						{"company": filters.get('company'), "from_date": filters.get('from_date'),
						 "to_date": filters.get('to_date')}, as_dict=True)

	for res in pur_tax_line:
		if res.account_head in vat_accounts:
			rate = res.tax_rate
			label = frappe.bold("Purchase - Rate" + " " + str(rate) + "%")
			if res.reverse_charge == 'Y':
				label = frappe.bold("Purchase Reverse Charges")
			elif res.is_exempt:
				label = frappe.bold("Purchase Exempted - Rate" + " " + str(rate) + "%")
			elif res.is_out_of_scope:
				label = frappe.bold("Purchase Out of Scope - Rate" + " " + str(rate) + "%")
			item_details.setdefault(label, []).append(res)

	sales_result = frappe.db.sql("""select pi.posting_date, pi.name as voucher_no, pi.remarks, pi.debit_to as account, 
			pii.item_code, 
			ixd.tax_type as account_head,
			ixd.tax_rate,
			pii.base_net_amount as net_amount,
			pii.base_net_amount, (pii.base_net_amount * ixd.tax_rate)/ 100 as tax_amount,
			pii.base_net_amount+((pii.base_net_amount * ixd.tax_rate)/ 100) as gross_amount,
			ix.is_zero_rated, ix.is_exempt, ix.is_out_of_scope,
			"Customer" as party_type,
			pi.customer as party,
			pi.customer_name as party_name,
			c.tax_id,
			"Sales Invoice" as voucher_type,
			pi.reverse_charge_applicable as reverse_charge
			from `tabSales Invoice Item` as pii
			inner join `tabSales Invoice` pi on pi.name = pii.parent
			inner join `tabCustomer` c on c.name = pi.customer
			inner join `tabItem Tax Template` ix on ix.name = pii.item_tax_template 
			inner join `tabItem Tax Template Detail` ixd on ixd.parent = ix.name 
			where pi.docstatus = 1 and pii.item_tax_template is not null 
			and pii.item_tax_template != '' 
			and pi.company=%(company)s 
			and pi.posting_date>=%(from_date)s 
			and pi.posting_date<=%(to_date)s 
			order by pi.posting_date, ixd.tax_rate desc""", {"company": filters.get('company'), "from_date": filters.get('from_date'),
												"to_date": filters.get('to_date')}, as_dict=True)

	for res in sales_result:
		if res.account_head in vat_accounts:
			rate = res.tax_rate
			label = frappe.bold("Sales - Rate" + " " + str(rate) + "%")
			if res.reverse_charge == 'Y':
				label = frappe.bold("Sales Reverse Charges")
			elif res.is_exempt:
				label = frappe.bold("Sales Exempted - Rate" + " " + str(rate) + "%")
			elif res.is_out_of_scope:
				label = frappe.bold("Sales Out of Scope - Rate" + " " + str(rate) + "%")
			item_details.setdefault(label, []).append(res)
			sales_inv_list.append(res.voucher_no)

	sale_tax_line = frappe.db.sql("""select pi.posting_date, 
							pi.name as voucher_no, 
							pi.remarks, 
							pi.debit_to as account, 
							pix.is_zero_rated, 
							pix.base_tax_amount_after_discount_amount as tax_amount,
							pi.base_total as net_amount,
							(pix.base_tax_amount_after_discount_amount + pi.base_total) as gross_amount,
							pix.account_head,
							pix.rate as tax_rate,
							"Customer" as party_type,
							pi.customer as party,			
							pi.customer_name as party_name,			
							c.tax_id,			
							"Sales Invoice" as voucher_type,							
							pi.reverse_charge_applicable as reverse_charge,
							0 as is_exempt,
							0 as is_out_of_scope
							from `tabSales Taxes and Charges` pix
							inner join `tabSales Invoice` pi on pi.name = pix.parent							
							inner join `tabCustomer` c on c.name = pi.customer
							where pi.docstatus = 1 
							and pi.name not in {0} 
							and pi.company=%(company)s 
							and pi.posting_date>=%(from_date)s 
							and pi.posting_date<=%(to_date)s """.format(tuple(sales_inv_list)),
								 {"company": filters.get('company'), "from_date": filters.get('from_date'),
								  "to_date": filters.get('to_date')}, as_dict=True)

	for res in sale_tax_line:
		if res.account_head in vat_accounts:
			rate = res.tax_rate
			label = frappe.bold("Sales - Rate" + " " + str(rate) + "%")
			if res.reverse_charge == 'Y':
				label = frappe.bold("Sales Reverse Charges")
			elif res.is_exempt:
				label = frappe.bold("Sales Exempted - Rate" + " " + str(rate) + "%")
			elif res.is_out_of_scope:
				label = frappe.bold("Sales Out of Scope - Rate" + " " + str(rate) + "%")
			item_details.setdefault(label, []).append(res)

	exp_query = frappe.db.sql("""select 					
			etc.rate,
			e.posting_date,
			e.payable_account as account,
			etc.tax_amount,
			etc.taxable_amount as net_amount,
			etc.tax_amount + etc.taxable_amount as gross_amount,
			e.name as voucher_no,
			'Supplier' as party_type,    
			ed.supplier as party,
			'Expense Claim' as voucher_type,
			'No Remakrs' as remarks
			from 
			`tabExpense Claim` as e
			inner join
			`tabExpense Claim Detail` as ed on ed.parent = e.name and ed.item_tax_template is not null and ed.supplier is not null
			inner join 
			`tabExpense Taxes and Charges` as etc on etc.parent = e.name and etc.taxable_amount = ed.sanctioned_amount
			where 
			e.docstatus = 1 
			and company=%(company)s 
			and posting_date>=%(from_date)s 
			and posting_date<=%(to_date)s 
			group by
			etc.rate,
			e.posting_date,
			account,
			voucher_no,
			party_type,    
			ed.supplier,
			voucher_type,
			remarks			
			ORDER BY posting_date desc""",{"company": filters.get('company'), "from_date": filters.get('from_date'),
												"to_date": filters.get('to_date')}, as_dict=1)

	for res in exp_query:
		rate = res.tax_rate
		label = frappe.bold("Expense - Rate" + " " + str(rate) + "%")
		item_details.setdefault(label, []).append(res)

	data = []
	count = 0
	for key in item_details.keys():
		total_gross = total_tax = total_net = 0
		if count >= 1:
			data.append({})
		count += 1
		data.append({"posting_date": key})

		for res in item_details[key]:
			total_gross += res.get("gross_amount")
			total_tax += res.get("tax_amount")
			total_net += res.get("net_amount")
			row = {}
			row["account"] = res.get("account")
			row["posting_date"] = formatdate(res.get("posting_date"), "dd-mm-yyyy")
			row["voucher_type"] = res.get("voucher_type")
			row["voucher_no"] = res.get("voucher_no")
			row["party_type"] = res.get("party_type")
			row["party"] = res.get("party")
			row["party_name"] = res.get("party_name")
			row["tax_id"] = res.get("tax_id")
			row["bill_no"] = res.get("bill_no")
			row["remarks"] = res.get("remarks")
			row["gross_amount"] = res.get("gross_amount")
			row["tax_amount"] = res.get("tax_amount")
			row["net_amount"] = res.get("net_amount")
			data.append(row)

		total = {
			"posting_date": frappe.bold(_("Total")),
			"gross_amount": total_gross,
			"tax_amount": total_tax,
			"net_amount": total_net,
			"bold":1
		}
		data.append(total)

	return data