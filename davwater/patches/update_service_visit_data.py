import frappe

def execute():
    frappe.db.sql("""UPDATE `tabService Visit` SET 
                tds_4th_cup = 0 WHERE tds_4th_cup is null""")
    frappe.db.sql("""UPDATE `tabService Visit` SET 
                water_total_taken_at_visit = 0 WHERE water_total_taken_at_visit is null""")
    frappe.db.sql("""UPDATE `tabService Visit` SET 
                total_compressor_hours = 0 WHERE total_compressor_hours is null""")