# -*- coding: utf-8 -*-

import ast

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class Payslip(models.Model):
    _name = 'nordic.payslip'
    _description = 'Employee Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char(string='Reference', required=True, readonly=True, default='/')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True, store=True)
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

    # Norwegian Lønnslipp Metadata
    run_number = fields.Integer(string='Run Number (Kjørenr)', default=1)
    payment_date = fields.Date(string='Payment Date (Dato)', default=fields.Date.context_today)

    # Computed fields for Dashboard/Reporting
    gross_amount = fields.Float(string='Gross Pay', compute='_compute_totals', store=True)
    tax_amount = fields.Float(string='Income Tax', compute='_compute_totals', store=True)
    net_amount = fields.Float(string='Net Pay', compute='_compute_totals', store=True)
    total_employer_cost = fields.Float(string='Total Employer Cost', compute='_compute_totals', store=True)

    _allowed_state_transitions = {
        'draft': {'verify', 'cancel'},
        'verify': {'done', 'cancel', 'draft'},
        'done': {'cancel'},
        'cancel': {'draft'},
    }

    @api.depends('line_ids.amount')
    def _compute_totals(self):
        for slip in self:
            gross = sum(line.amount for line in slip.line_ids if line.category in ['BASIC', 'ALW'])
            tax = sum(line.amount for line in slip.line_ids if line.code == 'TAX')
            ded = sum(line.amount for line in slip.line_ids if line.category == 'DED')
            comp = sum(line.amount for line in slip.line_ids if line.category == 'COMP')
            slip.gross_amount = gross
            slip.tax_amount = abs(tax)
            slip.net_amount = gross + ded # Net pay is Gross - all Deductions
            slip.total_employer_cost = gross + comp

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('nordic.payslip') or '/'
        return super().create(vals_list)

    def compute_sheet(self):
        for slip in self:
            slip._check_production_structure_approval()
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
                        'tax_code': rule.tax_code,
                        'is_vacation_base': rule.is_vacation_base,
                    }))
            
            slip.write({'line_ids': lines})

    def write(self, vals):
        if 'state' in vals and not self.env.context.get('allow_state_transition'):
            raise UserError(_(
                'Use the payslip workflow actions to change status instead of writing the state directly.'
            ))
        result = super().write(vals)
        if {'struct_id', 'state'}.intersection(vals):
            self._check_production_structure_approval()
        return result

    def action_submit_for_verification(self):
        for slip in self:
            if not slip.line_ids:
                slip.compute_sheet()
            slip._transition_state('verify')
        return True

    def action_mark_done(self):
        for slip in self:
            if not slip.line_ids:
                raise UserError(_('Compute the payslip before marking it as done.'))
            slip._transition_state('done')
        return True

    def action_reset_to_draft(self):
        self._transition_state('draft')
        return True

    def action_cancel(self):
        self._transition_state('cancel')
        return True

    def _transition_state(self, target_state):
        for slip in self:
            source_state = slip.state
            if target_state not in self._allowed_state_transitions.get(slip.state, set()):
                raise UserError(_(
                    'Cannot move payslip %(payslip)s from %(source)s to %(target)s.'
                ) % {
                    'payslip': slip.display_name,
                    'source': slip.state,
                    'target': target_state,
                })
            if target_state in {'verify', 'done'}:
                slip._check_production_structure_approval()
            slip.with_context(allow_state_transition=True).write({'state': target_state})
            slip.message_post(
                body=_('Payslip workflow audit: status changed from %(source)s to %(target)s.') % {
                    'source': source_state,
                    'target': target_state,
                },
                subtype_xmlid='mail.mt_note',
            )

    def _check_production_structure_approval(self):
        for slip in self:
            if not slip.struct_id:
                continue
            if slip.state not in {'verify', 'done'} and not self.env.context.get('force_production_structure_approval'):
                continue
            if not slip.struct_id.approved_for_production:
                raise UserError(_(
                    'Payroll structure %(structure)s must be approved for production before it can be used on non-draft payslips.'
                ) % {'structure': slip.struct_id.display_name})

    def get_a_melding_report_lines(self):
        self.ensure_one()
        mapping_model = self.env['nordic.a.melding.code.map']
        mappings = {
            mapping.internal_code: mapping
            for mapping in mapping_model.search([('active', '=', True)])
        }
        unsupported_lines = self.line_ids.filtered(
            lambda line: line.amount and line.code not in mappings
        )
        if unsupported_lines:
            raise UserError(_(
                "Unsupported payslip lines for A-melding: %s"
            ) % ', '.join(sorted(set(unsupported_lines.mapped('code')))))

        report_lines = []
        for line in self.line_ids.filtered(lambda current_line: current_line.amount and current_line.code in mappings):
            mapping = mappings[line.code]
            if line.category != mapping.expected_category:
                raise UserError(_(
                    'A-melding line %(code)s must use category %(category)s.'
                ) % {
                    'code': line.code,
                    'category': mapping.expected_category,
                })
            if mapping.sign_expectation == 'positive' and line.amount <= 0:
                raise UserError(_(
                    'A-melding line %(code)s must be positive.'
                ) % {'code': line.code})
            if mapping.sign_expectation == 'negative' and line.amount >= 0:
                raise UserError(_(
                    'A-melding line %(code)s must be negative before deduction normalization.'
                ) % {'code': line.code})
            report_lines.append({
                'internal_code': line.code,
                'edag_code': mapping.edag_code,
                'official_name': mapping.official_name,
                'amount': round(abs(line.amount), 2),
                'kind': mapping.line_kind,
                'category': line.category,
                'source_url': mapping.source_url,
            })

        return report_lines

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
        ('COMP', 'Employer Contribution'),
        ('NET', 'Net Pay'),
    ], default='BASIC')
    amount = fields.Float()
    tax_code = fields.Char(string='Tax Code')
    is_vacation_base = fields.Boolean(string='Vacation Base (FP)')

class SalaryRule(models.Model):
    _name = 'nordic.salary.rule'
    _description = 'Salary Rule'
    _inherit = ['mail.thread']
    _order = 'sequence'
    _governed_fields = {
        'name',
        'code',
        'sequence',
        'category',
        'amount_select',
        'amount_fix',
        'amount_percentage',
        'amount_python_compute',
        'tax_code',
        'is_vacation_base',
    }
    _forbidden_python_call_names = {'__import__', 'compile', 'eval', 'exec', 'open'}
    _forbidden_python_nodes = (
        ast.AsyncFunctionDef,
        ast.AsyncWith,
        ast.ClassDef,
        ast.Delete,
        ast.FunctionDef,
        ast.Global,
        ast.Import,
        ast.ImportFrom,
        ast.Lambda,
        ast.Nonlocal,
        ast.Raise,
        ast.Try,
        ast.With,
    )

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10, tracking=True)
    category = fields.Selection([
        ('BASIC', 'Basic Pay'),
        ('ALW', 'Allowance'),
        ('DED', 'Deduction'),
        ('COMP', 'Employer Contribution'),
    ], default='ALW', tracking=True)
    
    amount_select = fields.Selection([
        ('fix', 'Fixed Amount'),
        ('percentage', 'Percentage (%)'),
        ('python', 'Python Code'),
    ], default='fix', tracking=True)
    
    amount_fix = fields.Float(tracking=True)
    amount_percentage = fields.Float(tracking=True)
    amount_python_compute = fields.Text(
        tracking=True,
        help='Python formulas must assign a value to result and are restricted to a safe subset of Python.',
    )
    
    tax_code = fields.Char(string='Tax Code (Skatt)', tracking=True)
    is_vacation_base = fields.Boolean(string='Vacation Pay Base (FP)', default=False, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        self._check_formula_governance_access(set().union(*(set(vals) for vals in vals_list)))
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            changed_fields = set(vals).intersection(self._governed_fields)
            if changed_fields:
                record._post_governance_audit_log('created', changed_fields)
        return records

    def write(self, vals):
        self._check_formula_governance_access(set(vals))
        changed_fields = set(vals).intersection(self._governed_fields)
        result = super().write(vals)
        if changed_fields:
            for rule in self:
                rule._post_governance_audit_log('updated', changed_fields)
        return result

    def unlink(self):
        self._check_formula_governance_access(self._governed_fields)
        return super().unlink()

    def _check_formula_governance_access(self, changed_fields):
        if not changed_fields.intersection(self._governed_fields):
            return
        if self.env.is_superuser() or self.env.user.has_group('hr.group_hr_manager'):
            return
        raise AccessError(_(
            'Only HR managers can create, update, or delete salary rule definitions.'
        ))

    @api.constrains('amount_select', 'amount_python_compute')
    def _check_python_rule_definition(self):
        for rule in self:
            if rule.amount_select != 'python':
                continue

            source = (rule.amount_python_compute or '').strip()
            if not source:
                raise ValidationError(_('Python salary rules must define Python code.'))

            try:
                expression_tree = ast.parse(source, mode='exec')
            except SyntaxError as exc:
                raise ValidationError(_(
                    'Invalid Python code for salary rule %(rule)s: %(error)s'
                ) % {
                    'rule': rule.display_name,
                    'error': exc.msg,
                }) from exc

            if not any(self._is_result_assignment(node) for node in ast.walk(expression_tree)):
                raise ValidationError(_(
                    'Python salary rule %(rule)s must assign the final amount to result.'
                ) % {'rule': rule.display_name})

            for node in ast.walk(expression_tree):
                if isinstance(node, self._forbidden_python_nodes):
                    raise ValidationError(_(
                        'Python salary rule %(rule)s uses forbidden statement %(statement)s.'
                    ) % {
                        'rule': rule.display_name,
                        'statement': type(node).__name__,
                    })
                if isinstance(node, ast.Call) and self._get_called_name(node.func) in self._forbidden_python_call_names:
                    raise ValidationError(_(
                        'Python salary rule %(rule)s uses forbidden call %(call)s.'
                    ) % {
                        'rule': rule.display_name,
                        'call': self._get_called_name(node.func),
                    })

    def _is_result_assignment(self, node):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        return any(isinstance(target, ast.Name) and target.id == 'result' for target in targets)

    def _get_called_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return False

    def _post_governance_audit_log(self, action, changed_fields):
        self.ensure_one()
        field_labels = []
        for field_name in sorted(changed_fields):
            field = self._fields.get(field_name)
            field_labels.append(field.string if field and field.string else field_name)
        self.message_post(
            body=_('Salary rule governance audit: %(action)s fields %(fields)s.') % {
                'action': action,
                'fields': ', '.join(field_labels),
            },
            subtype_xmlid='mail.mt_note',
        )

class PayrollStructure(models.Model):
    _name = 'nordic.payroll.structure'
    _description = 'Payroll Structure'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True, tracking=True)
    rule_ids = fields.Many2many('nordic.salary.rule', string='Salary Rules', tracking=True)
    approved_for_production = fields.Boolean(string='Approved For Production', default=False, tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, tracking=True)
    approved_on = fields.Datetime(string='Approved On', readonly=True, tracking=True)

    def write(self, vals):
        result = super().write(vals)
        tracked_fields = {'name', 'rule_ids'}.intersection(vals)
        if tracked_fields:
            for structure in self:
                structure._post_structure_audit_log('updated', tracked_fields)
        return result

    def action_approve_for_production(self):
        self._check_structure_governance_access()
        approval_time = fields.Datetime.now()
        for structure in self:
            structure.write({
                'approved_for_production': True,
                'approved_by': self.env.user.id,
                'approved_on': approval_time,
            })
            structure._post_structure_audit_log('approved', {'approved_for_production'})

    def action_revoke_production_approval(self):
        self._check_structure_governance_access()
        for structure in self:
            structure.write({
                'approved_for_production': False,
                'approved_by': False,
                'approved_on': False,
            })
            structure._post_structure_audit_log('revoked', {'approved_for_production'})

    def _check_structure_governance_access(self):
        if self.env.is_superuser() or self.env.user.has_group('hr.group_hr_manager'):
            return
        raise AccessError(_(
            'Only HR managers can approve or revoke payroll structures for production.'
        ))

    def _post_structure_audit_log(self, action, changed_fields):
        self.ensure_one()
        field_labels = []
        for field_name in sorted(changed_fields):
            field = self._fields.get(field_name)
            field_labels.append(field.string if field and field.string else field_name)
        self.message_post(
            body=_('Payroll structure governance audit: %(action)s fields %(fields)s.') % {
                'action': action,
                'fields': ', '.join(field_labels),
            },
            subtype_xmlid='mail.mt_note',
        )

    @api.model
    def cleanup_seed_data(self):
        ir_model_data = self.env['ir.model.data'].sudo()
        salary_rule_model = self.env['nordic.salary.rule'].sudo()

        canonical_rules = {
            'rule_basic_pay': {
                'name': 'Basic Salary',
                'code': 'BASIC',
                'sequence': 1,
                'category': 'BASIC',
                'tax_code': 'Tab.',
                'is_vacation_base': True,
                'amount_select': 'python',
                'amount_python_compute': 'result = employee.nordic_wage',
            },
            'rule_pension_otp': {
                'name': 'Pension (OTP/Deduction)',
                'code': 'PENSION',
                'sequence': 50,
                'category': 'DED',
                'tax_code': 'Tab.',
                'is_vacation_base': False,
                'amount_select': 'python',
                'amount_python_compute': "basic = rules.get('BASIC', 0.0)\nrate = employee.pension_percentage or 2.0\nresult = - (basic * (rate / 100.0))",
            },
            'rule_income_tax': {
                'name': 'Income Tax (Skatt)',
                'code': 'TAX',
                'sequence': 100,
                'category': 'DED',
                'tax_code': 'Tab.',
                'is_vacation_base': False,
                'amount_select': 'python',
                'amount_python_compute': "gross = rules.get('BASIC', 0.0)\npension = rules.get('PENSION', 0.0)\ntaxable = gross + pension\nresult = - (taxable * 0.25)",
            },
            'rule_aga_zone1': {
                'name': 'Employer Contribution (AGA)',
                'code': 'AGA',
                'sequence': 200,
                'category': 'COMP',
                'tax_code': False,
                'is_vacation_base': False,
                'amount_select': 'python',
                'amount_python_compute': "rate = employee.get_employer_contribution_rate(payslip.company_id)\nresult = rules.get('BASIC', 0.0) * (rate / 100.0)",
            },
        }
        canonical_rule_ids = []
        for xmlid_name, values in canonical_rules.items():
            xmlid = ir_model_data.search([
                ('module', '=', 'nordic_payroll'),
                ('name', '=', xmlid_name),
                ('model', '=', 'nordic.salary.rule'),
            ], limit=1)
            rule = salary_rule_model.browse(xmlid.res_id).exists() if xmlid else salary_rule_model
            if rule:
                rule.write(values)
                canonical_rule_ids.append(rule.id)

        base_structure = self.env.ref('nordic_payroll.structure_nordic_base', raise_if_not_found=False)
        if base_structure:
            base_structure.sudo().write({
                'name': 'Nordic Base Structure (Standard)',
                'rule_ids': [(6, 0, canonical_rule_ids)],
                'approved_for_production': True,
            })

        obsolete_xmlids = ir_model_data.search([
            ('module', '=', 'nordic_payroll'),
            ('name', 'in', ['rule_basic', 'rule_pension_ded']),
            ('model', '=', 'nordic.salary.rule'),
        ])
        obsolete_rules = salary_rule_model.browse(obsolete_xmlids.mapped('res_id')).exists()
        if obsolete_rules:
            obsolete_rules.unlink()
        if obsolete_xmlids:
            obsolete_xmlids.unlink()
