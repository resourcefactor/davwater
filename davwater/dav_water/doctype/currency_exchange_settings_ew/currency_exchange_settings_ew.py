# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.utils import nowdate
from frappe.model.document import Document

class CurrencyExchangeSettingsEW(Document):
	@frappe.whitelist()
	def update_data(self):
		if self.enabled:
			curr_lst = []
			# currency = frappe.get_list("Currency", filters={"enabled": 1}, fields=['name'])
			for c in self.to_currencies:
				curr_lst.append(c.currency)

			for res in self.currencies:
				url = str(self.url) + "/" + str(self.api_key) + "/" + str(self.method) + "/" + str(res.currency)
				try:
					data = requests.get(url)
					if data.status_code == 200:
						datas = data.json()
						for key in datas['conversion_rates'].keys():
							lst = frappe.get_list("Currency Exchange", filters={"from_currency": datas['base_code'], "to_currency": key, "exchange_rate": datas['conversion_rates'][key]},fields='*')
							if len(lst) == 0 and datas['base_code'] != key and frappe.db.exists('Currency', datas['base_code']) \
									and frappe.db.exists('Currency', key) and key in curr_lst:
								doc = frappe.new_doc("Currency Exchange")
								doc.from_currency = datas['base_code']
								doc.to_currency = key
								doc.exchange_rate = datas['conversion_rates'][key]
								doc.date = nowdate()
								doc.for_selling = 1
								doc.for_buying = 1
								doc.insert(ignore_permissions=True)

								if datas['base_code'] == 'CNY':
									doc = frappe.new_doc("Currency Exchange")
									doc.from_currency = 'RMB'
									doc.to_currency = key
									doc.exchange_rate = datas['conversion_rates'][key]
									doc.date = nowdate()
									doc.for_selling = 1
									doc.for_buying = 1
									doc.insert(ignore_permissions=True)

				except Exception as e:
					print("------Exception------", e)
					continue

def update_exchange_currency_rate():
	single_doc = frappe.get_single('Currency Exchange Settings EW')
	if single_doc.enabled:
		curr_lst = []
		# currency = frappe.get_list("Currency", filters={"enabled": 1}, fields=['name'])
		for c in single_doc.to_currencies:
			curr_lst.append(c.currency)

		for res in single_doc.currencies:
			url = str(single_doc.url) + "/" + str(single_doc.api_key) + "/" + str(single_doc.method) + "/" + str(res.currency)
			try:
				data = requests.get(url)
				if data.status_code == 200:
					datas = data.json()
					for key in datas['conversion_rates'].keys():
						lst = frappe.get_list("Currency Exchange", filters={"from_currency": datas['base_code'], "to_currency": key, "exchange_rate": datas['conversion_rates'][key]},fields='*')
						if len(lst) == 0 and datas['base_code'] != key and frappe.db.exists('Currency', datas['base_code']) \
								and frappe.db.exists('Currency', key) and key in curr_lst:
							doc = frappe.new_doc("Currency Exchange")
							doc.from_currency = datas['base_code']
							doc.to_currency = key
							doc.exchange_rate = datas['conversion_rates'][key]
							doc.date = nowdate()
							doc.for_selling = 1
							doc.for_buying = 1
							doc.insert(ignore_permissions=True)

							if datas['base_code'] == 'CNY':
								doc = frappe.new_doc("Currency Exchange")
								doc.from_currency = 'RMB'
								doc.to_currency = key
								doc.exchange_rate = datas['conversion_rates'][key]
								doc.date = nowdate()
								doc.for_selling = 1
								doc.for_buying = 1
								doc.insert(ignore_permissions=True)

			except Exception as e:
				print("------Exception------", e)
				continue


