# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt
import frappe
import requests
from bs4 import BeautifulSoup
from frappe.utils import nowdate
from frappe.model.document import Document

class XECurrencyExchangeSetting(Document):
	@frappe.whitelist()
	def update_data(self):
		if self.enabled:
			for f in self.f_currency:
				for t in self.t_currency:
					try:
						if f.currency != t.currency:
							url = str(self.url) + "/?Amount=1&From={0}&To={1}".format(f.currency, t.currency)
							page = requests.get(url)
							soup = BeautifulSoup(page.content, 'html.parser')
							# exc_rate_data = soup.findAll('p', {'class': 'result__BigRate-sc-1bsijpp-1 iGrAod'})
							# exc_rate_data = soup.findAll('p', {'class': 'result__BigRate-sc-1bsijpp-1'})
							exc_rate_data = soup.findAll('p', {'class': 'sc-e08d6cef-1 fwpLse'})
							# exc_rate_data = soup.findAll('p', {'class': 'sc-1c293993-1 fxoXHw'})
							if exc_rate_data:
								exchange_rate = float(exc_rate_data[0].text.split(" ")[0] or 0)
								lst = frappe.get_list("Currency Exchange",
													filters={"from_currency": f.currency, "to_currency": t.currency,
															"exchange_rate": exchange_rate}, fields='*')
								if len(lst) == 0:
									doc = frappe.new_doc("Currency Exchange")
									doc.from_currency = f.currency
									doc.to_currency = t.currency
									doc.exchange_rate = exchange_rate
									doc.date = nowdate()
									doc.for_selling = 1
									doc.for_buying = 1
									doc.insert(ignore_permissions=True)

									if f.currency == 'CNY':
										doc = frappe.new_doc("Currency Exchange")
										doc.from_currency = 'RMB'
										doc.to_currency = t.currency
										doc.exchange_rate = exchange_rate
										doc.date = nowdate()
										doc.for_selling = 1
										doc.for_buying = 1
										doc.insert(ignore_permissions=True)

					except Exception as e:
						print("------Exception------", e)
						continue

def update_xe_exchange_currency_rate():
	single_doc = frappe.get_single('XE Currency Exchange Setting')
	if single_doc.enabled:
		for f in single_doc.f_currency:
			for t in single_doc.t_currency:
				try:
					if f.currency != t.currency:
						url = str(single_doc.url) + "/?Amount=1&From={0}&To={1}".format(f.currency, t.currency)
						page = requests.get(url)
						soup = BeautifulSoup(page.content, 'html.parser')
						# exc_rate_data = soup.findAll('p', {'class': 'result__BigRate-sc-1bsijpp-1 iGrAod'})
						exc_rate_data = soup.findAll('p', {'class': 'sc-e08d6cef-1 fwpLse'})
						if exc_rate_data:
							exchange_rate = float(exc_rate_data[0].text.split(" ")[0] or 0)
							lst = frappe.get_list("Currency Exchange",
												filters={"from_currency": f.currency, "to_currency": t.currency,
														"exchange_rate": exchange_rate}, fields='*')
							if len(lst) == 0:
								doc = frappe.new_doc("Currency Exchange")
								doc.from_currency = f.currency
								doc.to_currency = t.currency
								doc.exchange_rate = exchange_rate
								doc.date = nowdate()
								doc.for_selling = 1
								doc.for_buying = 1
								doc.insert(ignore_permissions=True)

								if f.currency == 'CNY':
									doc = frappe.new_doc("Currency Exchange")
									doc.from_currency = 'RMB'
									doc.to_currency = t.currency
									doc.exchange_rate = exchange_rate
									doc.date = nowdate()
									doc.for_selling = 1
									doc.for_buying = 1
									doc.insert(ignore_permissions=True)

				except Exception as e:
					print("------Exception------", e)
					continue