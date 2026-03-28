# -*- coding: utf-8 -*-

from odoo import models, fields, api
from . import a_melding
from . import payslip

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    nordic_ssn = fields.Char(string='Social Security Number (SSN)', groups="hr.group_hr_user", tracking=True)
    tax_zone = fields.Selection([
        ('1', 'Zone 1 (14.1%)'),
        ('1a', 'Zone 1a (10.6%)'),
        ('2', 'Zone 2 (10.6%)'),
        ('3', 'Zone 3 (6.4%)'),
        ('4', 'Zone 4 (5.1%)'),
        ('5', 'Zone 5 (0.0%)'),
    ], string='Tax Zone (AGA)', default='1', groups="hr.group_hr_user", tracking=True)
    nordic_wage = fields.Float(string='Monthly Wage (NOK)', groups="hr.group_hr_user")
    tax_table = fields.Char(string='Tax Table', groups="hr.group_hr_user")
    pension_percentage = fields.Float(string='Pension Contribution (%)', default=2.0, groups="hr.group_hr_user")

    # Moved from hr.contract due to missing module in environment
    wage_type = fields.Selection([
        ('monthly', 'Monthly Salary'),
        ('hourly', 'Hourly Wage'),
    ], string='Wage Type', default='monthly', required=True)
    
    pension_scheme_id = fields.Many2one('res.partner', string='Pension Provider', groups="hr.group_hr_user")
    deduction_rules_ids = fields.Many2many('nordic.salary.rule', string='Custom Deductions', groups="hr.group_hr_user")
    overtime_pct = fields.Float(string='Overtime Multiplier (%)', default=150.0)

    # Moved from hr.contract due to missing module in environment
    wage_type = fields.Selection([
        ('monthly', 'Monthly Salary'),
        ('hourly', 'Hourly Wage'),
    ], string='Wage Type', default='monthly', required=True)
    
    pension_scheme_id = fields.Many2one('res.partner', string='Pension Provider', groups="hr.group_hr_user")
    deduction_rules_ids = fields.Many2many('nordic.salary.rule', string='Custom Deductions', groups="hr.group_hr_user")
    overtime_pct = fields.Float(string='Overtime Multiplier (%)', default=150.0)
