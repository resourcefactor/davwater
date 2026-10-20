import frappe
import copy
from datetime import datetime
from frappe import _
from frappe.desk.form.assign_to import add as assign_to
from frappe.utils import nowdate, add_months, getdate, flt
from frappe.automation.doctype.auto_repeat.auto_repeat import AutoRepeat


class OverrideAutoRepeat(AutoRepeat):
    def _insert_new_doc(self, new_doc, reference_doc, assignee=None):
        self.update_doc(new_doc, reference_doc)
        new_doc.flags.updater_reference = {
            "doctype": self.doctype,
            "docname": self.name,
            "label": _("via Auto Repeat"),
        }
        new_doc.insert(ignore_permissions=True)

        if assignee:
            assign_to(
                args={
                    "assign_to": assignee,
                    "doctype": self.reference_doctype,
                    "name": new_doc.name,
                    "description": new_doc.get_title(),
                }
            )

        if self.submit_on_creation:
            new_doc.submit()

        return new_doc

    def make_new_document(self, assignee=None):
        reference_doc = frappe.get_doc(self.reference_doctype, self.reference_document)
        frappe.has_permission(self.reference_doctype, "read", reference_doc, user=self.owner, throw=True)
        new_doc = frappe.copy_doc(reference_doc, ignore_no_copy=False)

        start_date = getdate(str(add_months(nowdate(), -1)))
        month_name = datetime.strptime(str(start_date.month), "%m").strftime("%b")
        start_date = month_name + "-" + str(start_date.year)

        if self.reference_doctype == "Sales Invoice":
            si_inv = frappe.get_doc(self.reference_doctype, self.reference_document)
            if si_inv.docstatus ==1:
                delivery_lst = []
                for res in reference_doc.items:
                    if res.delivery_note and res.delivery_note not in delivery_lst:
                        delivery_lst.append(res.delivery_note)
                if delivery_lst:
                    service_items = []
                    charge_item = []
                    for dn in set(delivery_lst):
                        dn_doc = frappe.get_doc("Delivery Note", dn)
                        if dn_doc.type_of_sale in ["Lease with Service Pack", "Pay Per Liter"]:
                            for item in dn_doc.items:
                                if item.get('is_service_pack_item'):
                                    service_items.append(item)
                                if item.get('is_charge_item'):
                                    charge_item.append(item)
                            item_details = []
                            if charge_item:
                                c_item = copy.deepcopy(charge_item[0])
                                if dn_doc.type_of_sale == "Pay Per Liter":
                                    for s_item in service_items:
                                        serial_nos = s_item.serial_no.split("\n") if s_item.serial_no else None
                                        if serial_nos:
                                            for sr in serial_nos:
                                                c_item = copy.deepcopy(charge_item[0])
                                                c_item.machine = s_item.machine
                                                qty = 1
                                                if frappe.db.exists("Device List", sr):
                                                    div_doc = frappe.get_doc("Device List", sr)
                                                    for dli in div_doc.items:
                                                        if dli.date == start_date:
                                                            qty = flt(dli.water_dispense)
                                                if qty > c_item.qty:
                                                    c_item.qty = flt(qty)
                                                    a = "<p>" + str(c_item.item_name) + " - <b>" + str(sr) + "</b></p>"
                                                    c_item.description = a
                                                    item_details.append(c_item.as_dict())
                                                else:
                                                    a = "<p>" + str(c_item.item_name) + " - <b>" + str(sr) + "</b></p>"
                                                    c_item.description = a
                                                    item_details.append(c_item.as_dict())
                                        else:
                                            item_details.append(c_item.as_dict())
                                else:
                                    for c in charge_item:
                                        item_details.append(c.as_dict())

                                new_doc.delete_key("items")
                                new_doc.extend("items",item_details)
                                return self._insert_new_doc(new_doc, reference_doc, assignee)

                return self._insert_new_doc(new_doc, reference_doc, assignee)
        else:
            return self._insert_new_doc(new_doc, reference_doc, assignee)