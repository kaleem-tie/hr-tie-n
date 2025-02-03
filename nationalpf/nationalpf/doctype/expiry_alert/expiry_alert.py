# Copyright (c) 2025, MD Kaleem  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate,add_days


class ExpiryAlert(Document):
	pass




@frappe.whitelist()
def email_alert_for_expiry_date():
    try:
        alert_docs = frappe.db.get_all("Expiry Alert", fields=["expiry_date", "employee", "employee_name"])
        message_template = """
            Dear {hr_name},<br>
            The passport of employee <b>{employee_name}</b> has expired on <b>{expiry_date}</b>. Please take the necessary action.
            <br>
        """
        for alert in alert_docs:
            expiry_date = frappe.utils.getdate(alert['expiry_date'])
        
            new_date = frappe.utils.add_days(expiry_date, -30)
            fifteen_days_alert = frappe.utils.add_days(expiry_date, -15)
            
            if new_date == frappe.utils.getdate(frappe.utils.nowdate()) or fifteen_days_alert == frappe.utils.getdate(frappe.utils.nowdate()):
                users_with_hr_role = frappe.get_all('User', fields=['name', 'full_name', 'email'])

                for user in users_with_hr_role:
                    if not user.get('email'):
                        frappe.log_error(f"User {user['name']} does not have a valid email address.")
                        continue  
                    
                    roles = frappe.get_roles(user['name'])
                    if any(role in roles for role in ['HR User', 'HR Manager']):
                        message = message_template.format(
                            hr_name=user.get('full_name'),
                            employee_name=alert['employee_name'],
                            expiry_date=expiry_date
                        )

                        frappe.sendmail(
                            recipients=user['email'],
                            subject="Expiry Date of Employee Passport",
                            message=message,
                            now=True
                        )
                    else:
                        frappe.log_error(f"User {user['name']} does not have HR roles.")
    except Exception as ex:
        frappe.log_error({"success": False, "Error": str(ex)})
