// Copyright (c) 2025, MD Kaleem  and contributors
// For license information, please see license.txt


frappe.ui.form.on("Loan Application", {
    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Employee",
                    name: frm.doc.employee
                },
                callback: function(r) {
                    if (r.message && r.message.custom_earnings) {
                        let basicPay = 0;
                        r.message.custom_earnings.forEach(function(earning) {
                            if (earning.salary_component === "Basic") {
                                basicPay = earning.amount;  
                            }
                        });
                        frm.set_value('basic_pay', basicPay);

                        
                        let loanAmount = basicPay * 0.30;
                        frm.set_value('loan_amount', loanAmount);
                    }
                }
            });
        } else {
            frm.set_value('basic_pay', 0);
            frm.set_value('loan_amount', 0);  
        }
    }
});