import json
import frappe
from frappe import _
from frappe.utils import getdate, add_years, add_days, cint, date_diff, add_months
from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry
from davwater.hook_event.util import get_dav_setting


def set_item_level_lease_value(doc, method):
    if doc.type_of_sale in ["Lease with Service Pack", "Pay Per Liter"]:
        if not doc.lease_period:
            frappe.throw(_("Please select lease service pack Lease Period"))
        if not doc.start_date:
            frappe.throw(_("Please select lease service pack Start Date"))
        if not doc.end_date:
            frappe.throw(_("Please select lease service pack End Date"))
        if not doc.no_of_visits:
            frappe.throw(_("Please select lease service pack No. of Visit"))
        if not doc.service_team:
            frappe.throw(_("Please select lease service pack Service Team"))

        for item in doc.items:
            if item.get('is_service_pack_item'):
                item.lease_period = doc.lease_period
                item.start_date = doc.start_date
                item.end_date = doc.end_date
                item.no_of_visits = doc.no_of_visits
                item.service_team = doc.service_team
                item.periodicity = doc.periodicity
                item.location = doc.location


def validate_service_pack_item(dnote, method):
    if dnote.type_of_sale in ["Sales with Servicing Pack", "Lease with Service Pack", "Pay Per Liter"] and not dnote.is_return:
        lst = []
        charge_lst = []
        if dnote.type_of_sale in ['Lease with Service Pack', 'Pay Per Liter'] and dnote.residual_value <= 0:
            frappe.throw(_("Residual Value should be greater than the zero."))
        for res in dnote.items:
            if res.is_service_pack_item:
                if not res.start_date:
                    frappe.throw(_("Please select service pack item Start Date in <b>row:{0}</b>".format(res.idx)))
                if not res.end_date:
                    frappe.throw(_("Please select service pack item End Date in <b>row:{0}</b>".format(res.idx)))
                if not res.no_of_visits:
                    frappe.throw(_("Please select service pack item No. of Visits in <b>row:{0}</b>".format(res.idx)))
                if not res.service_team:
                    frappe.throw(_("Please select service pack item Service Team in <b>row:{0}</b>".format(res.idx)))
                if dnote.type_of_sale in ["Lease with Service Pack", "Pay Per Liter"] and not res.lease_period:
                    frappe.throw(
                        _("Please select lease service pack item Lease Period in <b>row:{0}</b>".format(res.idx)))
                lst.append(1)
            else:
                lst.append(0)
            if res.asset_amount == 0:
                res.asset_amount = (res.amount / 100) * dnote.residual_value if dnote.residual_value else 0
            if res.is_charge_item:
                charge_lst.append(1)

        if 1 not in lst:
            frappe.throw(_("With Service Pack Sales minimum one Item required Is Service Pack"))
        if 1 not in charge_lst and dnote.type_of_sale != "Sales with Servicing Pack":
            frappe.throw(_("Lease / Pay per Liter minimum one Item required Is Charge Item."))


def check_service_schedule(doc, method):
    ss = frappe.get_list("Service Schedule", filters={'delivery_note': doc.name, 'docstatus': 1}, fields='*')
    if ss:
        frappe.throw("Delivery Note link with the submitted Service Schedule.<br/>Please cancel Service Schedule")


@frappe.whitelist()
def make_service_schedule(dnote, method):
    if dnote.type_of_sale in ["Sales with Servicing Pack", "Lease with Service Pack", "Pay Per Liter"] and not dnote.is_return:
        s_schedule = frappe.new_doc("Service Schedule")
        s_schedule.customer = dnote.customer
        s_schedule.delivery_note = dnote.name
        s_schedule.transaction_date = dnote.posting_date
        s_schedule.machine_replacement_request = dnote.machine_replacement_request
        for res in dnote.items:
            if res.is_service_pack_item:
                if frappe.db.get_value('Item', res.item_code, 'has_serial_no'):
                    serial_nos = []
                    if res.serial_and_batch_bundle:
                        sb_doc = frappe.get_doc("Serial and Batch Bundle", res.serial_and_batch_bundle)
                        for sr in sb_doc.entries:
                            serial_nos.append(sr.serial_no)
                    else:
                        serial_nos = res.serial_no.split("\n") if res.serial_no else None
                    if serial_nos:
                        for s in serial_nos:
                            if s and s != " ":
                                s_schedule.append("items", {
                                    "item_code": res.item_code,
                                    "start_date": res.start_date,
                                    "end_date": res.end_date,
                                    "no_of_visits": res.no_of_visits,
                                    "periodicity": res.periodicity,
                                    "service_team": res.service_team,
                                    "location": res.location,
                                    "serial_no": s
                                })
                else:
                    s_schedule.append("items", {
                        "item_code": res.item_code,
                        "start_date": res.start_date,
                        "end_date": res.end_date,
                        "no_of_visits": res.no_of_visits,
                        "periodicity": res.periodicity,
                        "service_team": res.service_team,
                        "location": res.location
                    })
        s_schedule.insert(ignore_permissions=True)
        s_schedule.submit()
        frappe.msgprint(
            _("Service Schedule <b><a href='/app/service-schedule/{0}'>{0}</a></b> is Created.".format(s_schedule.name,
                                                                                                       s_schedule.name)),
            indicator="green", alert=True)


@frappe.whitelist()
def create_service_schedule(doc_name=None):
    if doc_name:
        dnote = frappe.get_doc("Delivery Note", doc_name)
        s_schedule = frappe.new_doc("Service Schedule")
        s_schedule.customer = dnote.customer
        s_schedule.delivery_note = dnote.name
        s_schedule.transaction_date = dnote.posting_date
        s_schedule.is_renew_plan = 1
        for res in dnote.items:
            if frappe.db.get_value('Item', res.item_code, 'has_serial_no'):
                serial_nos = []
                if res.serial_and_batch_bundle:
                    sb_doc = frappe.get_doc("Serial and Batch Bundle", res.serial_and_batch_bundle)
                    for sr in sb_doc.entries:
                        serial_nos.append(sr.serial_no)
                else:
                    serial_nos = res.serial_no.split("\n") if res.serial_no else None

                if serial_nos:
                    for s in serial_nos:
                        s_schedule.append("items", {
                            "item_code": res.item_code,
                            "start_date": res.start_date,
                            "end_date": res.end_date,
                            "no_of_visits": res.no_of_visits,
                            "periodicity": res.periodicity,
                            "service_team": res.service_team,
                            "location": res.location,
                            "serial_no": s
                        })
            else:
                s_schedule.append("items", {
                    "item_code": res.item_code,
                    "start_date": res.start_date,
                    "end_date": res.end_date,
                    "no_of_visits": res.no_of_visits,
                    "periodicity": res.periodicity,
                    "service_team": res.service_team,
                    "location": res.location
                })
        return s_schedule.as_dict()


def set_expense_account(doc, method):
    if doc.type_of_sale == "Trial":
        trial_cogs_account = get_dav_setting("trial_cogs_account")
        for res in doc.items:
            item_group = frappe.get_value("Item", {'item_code': res.item_code}, "item_group")
            if item_group == 'Products':
                res.expense_account = trial_cogs_account


def create_trial_type_jv(doc, method):
    if doc.type_of_sale == "Trial":
        if not doc.is_return:
            trial_cogs_account = get_dav_setting("trial_cogs_account")
            gl_entry = frappe.get_all("GL Entry", {'voucher_no': doc.name},
                                      ['name', 'account', 'debit_in_account_currency', 'credit_in_account_currency'])

            for gl in gl_entry:
                if trial_cogs_account in gl.get('account'):
                    credit_account = gl.get('account')
                    amount = gl.get('debit_in_account_currency')

                    debit_account = get_dav_setting("machine_on_trial_account")
                    if amount > 0:
                        jv = frappe.new_doc('Journal Entry')
                        jv.voucher_type = 'Journal Entry'
                        jv.naming_series = 'JV-'
                        jv.posting_date = doc.posting_date
                        jv.company = doc.company
                        jv.delivery_note = doc.name

                        jv.append('accounts', {
                            'account': debit_account,
                            'debit_in_account_currency': amount,
                            'is_advance': 'No',
                            'machine': gl.get('machine')
                        })
                        jv.append('accounts', {
                            'account': credit_account,
                            'credit_in_account_currency': amount,
                            'is_advance': 'No',
                            'machine': gl.get('machine')
                        })
                        jv.save(ignore_permissions=True)
                        jv.submit()

        if doc.is_return:
            dn_doc = frappe.get_doc("Delivery Note", doc.return_against)
            if dn_doc.status != "Completed":
                journal_entry = frappe.get_all("Journal Entry", {'delivery_note': doc.return_against, "docstatus":1})
                for jv in journal_entry:
                    reverse_jv = make_reverse_journal_entry(jv.get('name'))
                    reverse_jv = reverse_jv.as_dict()
                    reverse_jv['posting_date'] = doc.posting_date
                    reverse_jv['delivery_note'] = doc.name
                    reverse_jv = frappe.get_doc(reverse_jv)
                    reverse_jv.save(ignore_permissions=True)
                    reverse_jv.submit()


def create_reverse_jv(doc, method):
    if not doc.is_return:
        delivery_lst = []
        for res in doc.items:
            if res.delivery_note:
                delivery_lst.append(res.delivery_note)
        if delivery_lst:
            for dn in set(delivery_lst):
                dn_doc = frappe.get_doc("Delivery Note", dn)
                if dn_doc.type_of_sale == "Trial":
                    journal_entry = frappe.get_all("Journal Entry", {'delivery_note': doc.return_against, "docstatus":1})
                    for jv in journal_entry:
                        reverse_jv = make_reverse_journal_entry(jv.get('name'))
                        reverse_jv = reverse_jv.as_dict()
                        reverse_jv['posting_date'] = doc.posting_date
                        reverse_jv['sales_invoice'] = doc.name
                        reverse_jv = frappe.get_doc(reverse_jv)
                        reverse_jv.save(ignore_permissions=True)
                        reverse_jv.submit()


@frappe.whitelist()
def get_to_date(period, start_date):
    period = int(period.split("Year")[0])
    start_date = getdate(start_date)
    to_date = add_days(add_years(start_date, period), -1)
    return to_date


@frappe.whitelist()
def get_no_visits(periodicity, start_date, end_date):
    if periodicity != 'Random':
        days_in_period = {"Weekly": 7, "Monthly": 30, "Quarterly": 91, "Half Yearly": 182, "Yearly": 365}[periodicity]
        diff = date_diff(getdate(end_date), getdate(start_date)) + 1
        no_of_visits = cint(diff / days_in_period)
        return no_of_visits or 1
    return 1


def get_months(start_date, end_date):
    diff = (12 * end_date.year + end_date.month) - (12 * start_date.year + start_date.month)
    return diff + 1


@frappe.whitelist()
def create_assets_item_and_asset_recode(doc, method):
    if doc.type_of_sale in ["Lease with Service Pack", "Pay Per Liter"] and not doc.is_return:
        if doc.residual_value <= 0:
            frappe.throw(_("Residual Value should be greater than the zero."))
        for item in doc.items:
            if item.get('is_service_pack_item'):
                asset_name = "LA-" + str(item.item_code)
                if not frappe.db.exists("Item", asset_name):
                    item_doc = frappe.get_doc("Item", item.item_code)
                    ass_item_doc = frappe.copy_doc(item_doc)
                    ass_item_doc.naming_series = "####"
                    ass_item_doc.custom_name_code = 1
                    ass_item_doc.name = asset_name
                    ass_item_doc.item_code = asset_name
                    ass_item_doc.item_name = asset_name
                    ass_item_doc.item_group = "Fixed Assets"
                    ass_item_doc.is_fixed_asset = 1
                    ass_item_doc.asset_category = 'Leased Asset'
                    ass_item_doc.is_stock_item = 0
                    ass_item_doc.has_variants = 0
                    ass_item_doc.variant_of = None
                    ass_item_doc.default_bom = None
                    ass_item_doc.attributes = []
                    ass_item_doc.insert(ignore_links=True, ignore_permissions=True, ignore_mandatory=True)

                amount = abs(frappe.get_value("Stock Ledger Entry",
                                              {'voucher_type': "Delivery Note",
                                               'voucher_no': doc.name,
                                               'voucher_detail_no': item.name,
                                               'item_code': item.item_code
                                               }, "stock_value_difference") or 0)

                if frappe.db.exists("Item", asset_name):
                    ass_item = frappe.get_doc("Item", asset_name)
                    asset_doc = frappe.new_doc("Asset")
                    asset_doc.company = doc.company
                    asset_doc.asset_name = asset_name
                    asset_doc.item_code = asset_name
                    asset_doc.item_name = ass_item.item_name
                    asset_doc.asset_owner = "Customer"
                    asset_doc.customer = doc.customer
                    asset_doc.asset_category = ass_item.asset_category
                    asset_doc.customer_name = doc.customer_name
                    asset_doc.location = item.location
                    asset_doc.asset_type = "Existing Asset"
                    asset_doc.delivery_note = doc.name
                    asset_doc.qty = item.qty
                    asset_doc.machine = item.machine
                    asset_doc.serial_no = item.serial_no
                    asset_doc.net_purchase_amount = amount
                    asset_doc.purchase_date = item.start_date
                    asset_doc.available_for_use_date = item.start_date
                    asset_doc.calculate_depreciation = 1
                    asset_doc.cost_center = get_dav_setting("leasing_cost_center", required=False) or asset_doc.cost_center

                    date_str = str(item.start_date).split("-")
                    if int(date_str[2]) < 28:
                        date_str[2] = str(28)
                    else:
                        dd = add_months(item.start_date, 1)
                        date_str = str(dd).split("-")
                        date_str[2] = str(28)
                    dep_start_date = "-".join(date_str)

                    asset_doc.append("finance_books", {
                        "depreciation_method": "Straight Line",
                        "total_number_of_depreciations": get_months(item.start_date, item.end_date),
                        "frequency_of_depreciation": 1,
                        "depreciation_start_date": getdate(dep_start_date),
                        "expected_value_after_useful_life": (amount / 100) * doc.residual_value
                    })
                    asset_doc.insert(ignore_links=True, ignore_permissions=True, ignore_mandatory=True)
                    asset_doc.submit()
                    frappe.msgprint(_("Asset <b><a href='/app/asset/{0}'>{0}</a></b> is Created.".format(asset_doc.name,
                                                                                                         asset_doc.name)),
                                    indicator="green", alert=True)

                create_lease_type_journal_entry(doc, amount, item.machine)


def create_lease_type_journal_entry(doc, amount, machine=None):
    if amount > 0:
        credit_account = get_dav_setting("cogs_account")
        debit_account = get_dav_setting("lease_assets_cost_account")

        jv = frappe.new_doc('Journal Entry')
        jv.voucher_type = 'Journal Entry'
        jv.posting_date = doc.posting_date
        jv.company = doc.company
        jv.delivery_note = doc.name

        jv.append('accounts', {
            'account': debit_account,
            'debit_in_account_currency': amount,
            'machine': machine,
            'is_advance': 'No'
        })
        jv.append('accounts', {
            'account': credit_account,
            'credit_in_account_currency': amount,
            'machine': machine,
            'is_advance': 'No'
        })
        jv.save(ignore_permissions=True)
        jv.submit()


def create_sales_invoice_auto_repeat(doc, method):
    if not doc.is_return and not doc.auto_repeat:
        delivery_lst = []
        for res in doc.items:
            if res.delivery_note:
                delivery_lst.append(res.delivery_note)
        if delivery_lst:
            for dn in set(delivery_lst):
                dn_doc = frappe.get_doc("Delivery Note", dn)
                if dn_doc.type_of_sale in ["Lease with Service Pack", "Pay Per Liter"]:
                    auto_rep = frappe.new_doc("Auto Repeat")
                    auto_rep.reference_doctype = "Sales Invoice"
                    auto_rep.reference_document = doc.name
                    auto_rep.start_date = getdate(doc.posting_date)
                    auto_rep.end_date = dn_doc.end_date
                    auto_rep.frequency = "Monthly"
                    auto_rep.repeat_on_day = 1
                    auto_rep.insert(ignore_permissions=True)

                    if dn_doc.type_of_sale == "Pay Per Liter":
                        dn_doc.status = "Completed"
                        dn_doc.per_billed = 100
                        dn_doc.db_update()


@frappe.whitelist()
def get_serial_no_with_location(doc_name):
    dnote = frappe.get_doc("Delivery Note", doc_name)
    lst = []
    for item in dnote.items:
        if item.get('is_service_pack_item'):
            serial_nos = []
            if item.serial_and_batch_bundle:
                sb_doc = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
                for sr in sb_doc.entries:
                    serial_nos.append(sr.serial_no)
            else:
                serial_nos = item.serial_no.split("\n") if item.serial_no else None
            if serial_nos:
                for s in serial_nos:
                    lst.append({'serial_no': s, 'location': item.location})
    return lst


@frappe.whitelist()
def set_serial_no_location(doc_name, location_lst):
    if location_lst:
        locations = json.loads(location_lst)
        for res in locations:
            query = """UPDATE `tabService Schedule Item` SET location = '{0}' 
                        WHERE serial_no = '{1}'""".format(res.get('location'), res.get('serial_no'))
            frappe.db.sql(query)

            query = """UPDATE `tabService Schedule Detail` SET location = '{0}' 
                        WHERE serial_no = '{1}' 
                        and completion_status = 'Pending'""".format(res.get('location'), res.get('serial_no'))
            frappe.db.sql(query)

            sr_doc = frappe.get_doc("Serial No", res.get('serial_no'))
            sr_doc.location = res.get('location')
            sr_doc.flags.ignore_validate_update_after_submit = True
            sr_doc.save()


def create_device_list_entry(doc, method):
    if doc:
        if doc.type_of_sale == "Pay Per Liter":
            for res in doc.items:
                if res.is_service_pack_item:
                    serial_nos = []
                    if res.serial_and_batch_bundle:
                        sb_doc = frappe.get_doc("Serial and Batch Bundle", res.serial_and_batch_bundle)
                        for sr in sb_doc.entries:
                            serial_nos.append(sr.serial_no)
                    else:
                        serial_nos = res.serial_no.split("\n") if res.serial_no else None
                    if serial_nos:
                        for sr in serial_nos:
                            try:
                                dl_doc = frappe.new_doc("Device List")
                                dl_doc.serial_no = sr
                                dl_doc.customer = doc.customer
                                dl_doc.customer_name = frappe.get_value("Customer", doc.customer, "customer_name")
                                dl_doc.start_date = res.start_date
                                dl_doc.expiry_date = res.end_date
                                dl_doc.item_code = res.item_code
                                dl_doc.item_name = res.item_name
                                dl_doc.warehouse = res.warehouse
                                dl_doc.delivery_note = doc.name
                                dl_doc.insert(ignore_permissions=True)
                                dl_doc.submit()
                            except Exception as e:
                                frappe.log_error(title="Device List Creation Error", message=e)
                                frappe.msgprint("Device List Creation Error", indicator='red', alert=True)
                                continue
