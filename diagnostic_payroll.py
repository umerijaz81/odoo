# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

def check_payroll_setup(env):
    print("--- Diagnostic Report ---")
    
    # Check Nordic Payslip Model
    model = env['ir.model'].search([('model', '=', 'nordic.payslip')])
    if not model:
        print("ERROR: nordic.payslip model not found!")
    else:
        print(f"Model nordic.payslip found. ID: {model.id}")
        fields = env['nordic.payslip'].fields_get()
        print(f"Fields count: {len(fields)}")
        if 'employee_id' in fields:
            print("SUCCESS: employee_id field exists.")
        else:
            print("ERROR: employee_id field MISSING in registry!")

    # Check Views
    views = env['ir.ui.view'].search([('model', '=', 'nordic.payslip'), ('type', '=', 'form')])
    print(f"Form views found: {len(views)}")
    for view in views:
        print(f"View: {view.name} (ID: {view.id}, XML_ID: {view.xml_id})")

    # Check Employee record
    employee = env['hr.employee'].search([], limit=1)
    if employee:
        emp_fields = employee.fields_get()
        if 'nordic_wage' in emp_fields:
            print(f"SUCCESS: hr.employee has nordic_wage field.")
        else:
            print(f"ERROR: hr.employee MISSING nordic_wage!")

    print("--- End of Report ---")

if __name__ == "__main__":
    # This part is for running with odoo-bin shell
    check_payroll_setup(env)
