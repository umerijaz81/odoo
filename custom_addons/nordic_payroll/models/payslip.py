# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

class Payslip(models.Model):
    _name = 'nordic.payslip'
    _description = 'Employee Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, readonly=True, default='/')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)
    struct_id = fields.Many2one('nordic.payroll.structure', string='Structure')
    line_ids = fields.One2many('nordic.payslip.line', 'slip_id', string='Payslip Lines', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, default='draft', tracking=True)

    # Computed fields for Dashboard/Reporting
    gross_amount = fields.Float(string='Gross Pay', compute='_compute_totals', store=True)
    tax_amount = fields.Float(string='Income Tax', compute='_compute_totals', store=True)
    net_amount = fields.Float(string='Net Pay', compute='_compute_totals', store=True)

    @api.depends('line_ids.amount')
    def _compute_totals(self):
        for slip in self:
            gross = sum(line.amount for line in slip.line_ids if line.category in ['BASIC', 'ALW'])
            tax = sum(line.amount for line in slip.line_ids if line.category == 'DED')
            slip.gross_amount = gross
            slip.tax_amount = abs(tax)
            slip.net_amount = gross + tax

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('nordic.payslip') or '/'
        return super().create(vals_list)

    def compute_sheet(self):
        for slip in self:
            slip.line_ids.unlink()
            lines = []
            
            # Use a proper dictionary for rules to avoid type inference issues
            rules_dict = {}
            
            # Setup the calculation context
            eval_context = {
                'employee': slip.employee_id,
                'payslip': slip,
                'result': 0.0,
                'rules': rules_dict,
            }

            if slip.struct_id:
                # Sort rules by sequence to allow dependency
                for rule in slip.struct_id.rule_ids:
                    amount = 0.0
                    
                    if rule.amount_select == 'fix':
                        amount = rule.amount_fix
                    elif rule.amount_select == 'percentage':
                        # Example: BASIC * 0.25 
                        base = rules_dict.get('BASIC', 0.0)
                        amount = base * (rule.amount_percentage / 100.0)
                    elif rule.amount_select == 'python':
                        # Execute custom Python code
                        local_context = eval_context.copy()
                        safe_eval(rule.amount_python_compute, local_context, mode='exec')
                        amount = local_context.get('result', 0.0)

                    # Store for future rules
                    rules_dict[rule.code] = amount
                    
                    lines.append((0, 0, {
                        'name': rule.name,
                        'code': rule.code,
                        'category': rule.category,
                        'amount': amount,
                        'sequence': rule.sequence,
                    }))
            
            slip.write({'line_ids': lines})

class PayslipLine(models.Model):
    _name = 'nordic.payslip.line'
    _description = 'Payslip Line'
    _order = 'sequence'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    slip_id = fields.Many2one('nordic.payslip', string='Payslip', ondelete='cascade')
    sequence = fields.Integer(default=10)
    category = fields.Selection([
        ('BASIC', 'Basic Pay'),
        ('ALW', 'Allowance'),
        ('DED', 'Deduction'),
        ('NET', 'Net Pay'),
    ], default='BASIC')
    amount = fields.Float()
