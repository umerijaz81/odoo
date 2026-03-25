# -*- coding: utf-8 -*-
{
    'name': "Nordic Payroll Localization",

    'summary': "Fully functioning Nordic Payroll Engine.",

    'description': """
Custom Nordic Payroll system including:
- Payslips management
- Salary Rule engine
- Nordic Structures
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Human Resources/Payroll',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['hr', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/views.xml',
        'data/hr_payroll_data.xml',
    ],
    'installable': True,
    'application': True,
}
