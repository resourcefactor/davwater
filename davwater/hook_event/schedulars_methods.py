import frappe
from frappe import _
from frappe.utils import getdate, cint, formatdate, month_diff, add_years, get_first_day
from frappe.core.doctype.communication.email import make
from frappe.utils.jinja import render_template


def send_customer_notification():
    schedulers = frappe.get_list("Service Schedule", filters={'docstatus': 1}, fields=['name'], ignore_permissions=True,
                                 order_by='creation desc')
    for res in schedulers:
        doc = frappe.get_doc("Service Schedule", res.name)
        send_customer = frappe.db.get_single_value("Service Settings", "send_customer")
        sender = frappe.db.get_single_value("Service Settings", "sender")
        sender_name = frappe.db.get_single_value("Service Settings", "sender_name")
        customer_mail_temp = frappe.db.get_single_value("Service Settings", "for_customer")
        sales_per_mail_temp = frappe.db.get_single_value("Service Settings", "for_employee")
        notification_alert = frappe.db.get_single_value("Service Settings", "notf_alert")
        notify_person = frappe.db.get_single_value("Service Settings", "notify_person")

        for line in doc.items:
            month = month_diff(getdate(), line.end_date) - 1
            first_date = get_first_day(getdate())

            # for customer
            if send_customer:
                if cint(month) == -cint(notification_alert) and first_date == getdate() and doc.contact_email:
                    content = """Dear Customer,<br>
                        Your Service plan: <b>{name}</b> is going to expire on <b>{end_date}</b>.<br>
                        If you want to continue, you can renew our service plan.<br>
                        Thanks,<br>
                        Support Team
                        """.format(name=doc.name,
                                   start_date=formatdate(line.start_date),
                                   end_date=formatdate(line.end_date),
                                   customer=doc.customer_name,
                                   sales_person=line.sales_person,
                                   item_code=line.item_code,
                                   item_name=line.item_name,
                                   serial_no=line.serial_no,
                                   delivery_note=doc.delivery_note,
                                   sales_invoice=doc.sales_invoice)
                    if customer_mail_temp:
                        content = customer_mail_temp.format(name=doc.name,
                                                            start_date=formatdate(line.start_date),
                                                            end_date=formatdate(line.end_date),
                                                            customer=doc.customer_name,
                                                            sales_person=line.sales_person,
                                                            item_code=line.item_code,
                                                            item_name=line.item_name,
                                                            serial_no=line.serial_no,
                                                            delivery_note=doc.delivery_note,
                                                            sales_invoice=doc.sales_invoice)

                    send_mail("Service Schedule", doc.name, content, "Reminder of Service Plan ending", sender,
                              sender_name, doc.contact_email, notify_person)

            # for sales person
            user = frappe.get_value("Service Team", line.service_team, "user")
            if user:
                user_doc = frappe.get_doc("User", user)
                if cint(month) == -cint(notification_alert) and first_date == getdate() and user_doc.email:
                    content = """Dear Sale Person,<br>
                        Service plan: <b>{name}</b> is going to expire on <b>{end_date}</b>.<br>
                        Please contact the customer to take action.<br>
                        Thanks                        
                        """.format(name=doc.name,
                                   start_date=formatdate(line.start_date),
                                   end_date=formatdate(line.end_date),
                                   customer=doc.customer_name,
                                   sales_person=line.sales_person,
                                   item_code=line.item_code,
                                   item_name=line.item_name,
                                   serial_no=line.serial_no)
                    if sales_per_mail_temp:
                        content = sales_per_mail_temp.format(name=doc.name,
                                                             start_date=formatdate(line.start_date),
                                                             end_date=formatdate(line.end_date),
                                                             customer=doc.customer_name,
                                                             sales_person=line.sales_person,
                                                             item_code=line.item_code,
                                                             item_name=line.item_name,
                                                             serial_no=line.serial_no)
                    send_mail("Service Schedule", doc.name, content, "Reminder of Service Plan ending", sender,
                              sender_name, user_doc.email, notify_person)


def send_without_service_pack_notification():
    is_send_notification = frappe.db.get_single_value("Service Settings", "is_send_notification")
    periods = frappe.db.get_single_value("Service Settings", "periods")
    content = frappe.db.get_single_value("Service Settings", "without_service_notification")
    sender = frappe.db.get_single_value("Service Settings", "sender")
    sender_name = frappe.db.get_single_value("Service Settings", "sender_name")
    if is_send_notification and periods and content:
        delivery_notes = frappe.get_list("Delivery Note",
                                         filters={'docstatus': 1, 'type_of_sale': 'Sales with Servicing Pack'},
                                         fields=['name'], ignore_permissions=True,
                                         order_by='creation desc')
        for res in delivery_notes:
            doc = frappe.get_doc("Delivery Note", res.name)
            end_year_date = add_years(doc.posting_date, 1)
            month = month_diff(getdate(), end_year_date) - 1
            first_date = get_first_day(getdate())
            if cint(month) == -cint(periods) and first_date == getdate():
                email_content = render_template(content, doc.as_dict())
                customer_email_id = frappe.get_value("Contact", doc.contact_person, "email_id")
                if customer_email_id:
                    send_mail("Delivery Note", doc.name, email_content, "For confirmation of service pack", sender,
                              sender_name, customer_email_id, None)


def send_mail(doctype, name, content, subject, sender, sender_full_name, recipients, cc):
    make(doctype=doctype,
         name=name,
         content=content,
         subject=subject,
         sent_or_received="Sent",
         sender=sender,
         sender_full_name=sender_full_name,
         recipients=recipients,
         communication_medium="Email",
         send_email=True,
         print_html=None,
         print_format=None,
         attachments='[]',
         send_me_a_copy=True,
         cc=cc,
         bcc=None,
         flags=None,
         read_receipt=None,
         print_letterhead=True,
         email_template=None,
         communication_type=None,
         ignore_permissions=False)
