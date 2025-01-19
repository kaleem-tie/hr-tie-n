frappe.ui.form.on('Employee', {
    refresh(frm) {
        // Function to update custom_earnings and custom_deductions child table components
        function update_salary_components(table_field) {
            frm.fields_dict[table_field].grid.get_field('salary_component').get_query = function(doc, cdt, cdn) {
                return {
                    filters: {
                        'type': table_field === 'custom_earnings' ? 'Earning' : 'Deduction'
                    }
                };
            };
        }

        // Update salary component filter for both child tables
        update_salary_components('custom_earnings');
        update_salary_components('custom_deductions');
    }
});
