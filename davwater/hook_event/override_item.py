import frappe
from erpnext.stock.doctype.item.item import Item
from erpnext.controllers.item_variant import (make_variant_item_code)
from frappe.utils import strip
from frappe.model.naming import make_autoname


class OverrideItem(Item):
    def autoname(self):
        if not self.custom_name_code:
            if frappe.db.get_default("item_naming_by") == "Naming Series":
                if self.variant_of:
                    if not self.item_code:
                        template_item_name = frappe.db.get_value("Item", self.variant_of, "item_name")
                        make_variant_item_code(self.variant_of, template_item_name, self)
                else:
                    from frappe.model.naming import set_name_by_naming_series
                    if self.generate_auto_item_code:
                        machine_code = self.machine_code if self.machine_code else ""
                        item_group_code = self.item_group_code if self.item_group_code else ""
                        name = make_autoname(machine_code + "-" + item_group_code + "-.###", "Item", self)
                        self.item_code = self.name = name
                    else:
                        set_name_by_naming_series(self)
                        self.item_code = self.name

            self.item_code = strip(self.item_code)
            self.name = self.item_code
        else:
            self.item_code = strip(self.item_code)
            self.name = self.item_code
