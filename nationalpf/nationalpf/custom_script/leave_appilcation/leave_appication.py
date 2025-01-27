import frappe




@frappe.whitelist()
def alert_for_leave_appication(self, method):
    employee_doc = frappe.get_doc("Employee", self.employee)
    leave_type = frappe.get_doc("Leave Type", self.leave_type)
    
    if employee_doc and leave_type:
        if leave_type.custom_applicable_to and employee_doc.gender:
            if employee_doc.gender != leave_type.custom_applicable_to:
                frappe.throw("Please select the correct Leave Type based on Gender.")
        
        if leave_type.custom_religion_group and employee_doc.custom_religion_group:
            if leave_type.custom_religion_group != employee_doc.custom_religion_group:
                frappe.throw("Please select the correct Leave Type based on Religion Group.")