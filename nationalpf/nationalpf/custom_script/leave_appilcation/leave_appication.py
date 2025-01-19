import frappe




@frappe.whitelist()
def alert_for_leave_appication(self,method):
	emplyee_doc = frappe.get_doc("Employee",self.employee)
	leave_type = frappe.get_doc("Leave Type",self.leave_type)
	if emplyee_doc and leave_type:
		if emplyee_doc.gender != leave_type.custom_applicable_to:
			frappe.throw("Please select the Proper Leave Type")
		if leave_type.custom_religion_group != emplyee_doc.custom_religion_group:
			frappe.throw("Please select the Proper Leave Type")
