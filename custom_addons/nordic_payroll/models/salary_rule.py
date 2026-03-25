# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SalaryRule(models.Model):
    _name = 'nordic.salary.rule'
    _description = 'Salary Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, help="Used in Python expressions (e.g., BASIC, TAX)")
    sequence = fields.Integer(default=10)
    quantity = fields.Char(default='1.0', help="Quantity as Python expression or Float")
    amount_fix = fields.Float(string='Fixed Amount')
    amount_select = fields.Selection([
        ('fix', 'Fixed Amount'),
        ('percentage', 'Percentage (%)'),
        ('python', 'Python Code'),
    ], default='fix', required=True)
    amount_percentage = fields.Float(string='Percentage (%)')
    amount_python_compute = fields.Text(string='Python Code')
    
    category = fields.Selection([
        ('BASIC', 'Basic Pay'),
        ('ALW', 'Allowance'),
        ('DED', 'Deduction'),
        ('NET', 'Net Pay'),
    ], default='BASIC', required=True)

class PayrollStructure(models.Model):
    _name = 'nordic.payroll.structure'
    _description = 'Payroll Structure'

    name = fields.Char(string='Name', required=True)
    rule_ids = fields.Many2many('nordic.salary.rule', string='Salary Rules')
