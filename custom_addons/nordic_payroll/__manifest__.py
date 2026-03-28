# -*- coding: utf-8 -*-
{
    'name': "Nordic Payroll Localization",

    'summary': "Fully functioning Nordic Payroll Engine with PDF Reporting.",

    'description': """
Custom Nordic Payroll system including:
- Payslips management
- Python-based Salary Rule engine
- Nordic Employee Extensions (Wage, Tax, Pension)
- QWeb PDF Payslip Reporting
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Human Resources/Payroll',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['hr', 'mail', 'auth_oauth', 'hr_expense', 'website_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/views.xml',
        'data/hr_payroll_data.xml',
        'data/hr_payroll_rules.xml',
        'data/sso_configuration.xml',
        'data/hr_expense_data.xml',
        'reports/report_payslip.xml',
    ],
    'installable': True,
    'application': True,
}
