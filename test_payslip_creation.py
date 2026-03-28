# -*- coding: utf-8 -*-
def create_test_payslip(env):
    print("--- Shell Model Test ---")
    employee = env['hr.employee'].search([('name', '=', 'Mitchell Admin')], limit=1)
    if not employee:
        print("Mitchell Admin not found, creating...")
        employee = env['hr.employee'].create({'name': 'Mitchell Admin', 'nordic_wage': 50000})
    
    struct = env['nordic.payroll.structure'].search([], limit=1)
    if not struct:
        print("No structure found!")
        return

    try:
        payslip = env['nordic.payslip'].create({
            'employee_id': employee.id,
            'struct_id': struct.id,
            'date_from': '2026-03-01',
            'date_to': '2026-03-31',
        })
        print(f"Payslip created! ID: {payslip.id}, Name: {payslip.name}")
        payslip.compute_sheet()
        print(f"Payslip computed! Net: {payslip.net_amount}")
    except Exception as e:
        print(f"Error creating payslip: {e}")

if __name__ == "__main__":
    create_test_payslip(env)
