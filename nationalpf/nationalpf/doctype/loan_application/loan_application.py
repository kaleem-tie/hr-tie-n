# Copyright (c) 2025, MD Kaleem  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import frappe
from frappe.utils import getdate, add_months

class LoanApplication(Document):

    def on_submit(self):
        loan_amount = self.loan_amount
        instalment = self.noof_period
        amount_per_month = loan_amount / instalment

        insdate_start = getdate(self.insdate_start)
        
        to_date = add_months(insdate_start, self.noof_period-1)

        to_date_str = to_date.strftime("%Y-%m-%d")
        
        new_additional_salary = frappe.new_doc("Additional Salary")
        new_additional_salary.update({
            "employee": self.employee,
            "is_recurring": 1,
            "from_date": self.insdate_start,
            "to_date": to_date_str,
            "salary_component": "Loan Installment Deduction",
            "currency": "AED",
            "amount": amount_per_month,
            "docstatus": 1
        })
        
        new_additional_salary.insert()
        frappe.db.commit()