from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class NordicPensionScheme(models.Model):
    _name = 'nordic.pension.scheme'
    _description = 'Nordic Pension Scheme'

    name = fields.Char(required=True)
    code = fields.Char()
    contribution_percentage = fields.Float(string='Contribution (%)', default=2.0)
    active = fields.Boolean(default=True)


class NordicAgaRate(models.Model):
    _name = 'nordic.aga.rate'
    _description = 'Nordic Employer Contribution Rate'
    _order = 'company_id, zone'

    company_id = fields.Many2one('res.company', string='Company')
    zone = fields.Selection([
        ('1', 'Zone 1'),
        ('1a', 'Zone 1a'),
        ('2', 'Zone 2'),
        ('3', 'Zone 3'),
        ('4', 'Zone 4'),
        ('5', 'Zone 5'),
    ], required=True)
    rate = fields.Float(string='Rate (%)', required=True)
    active = fields.Boolean(default=True)

    @api.constrains('company_id', 'zone')
    def _check_company_zone_uniqueness(self):
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id),
                ('zone', '=', record.zone),
            ], limit=1)
            if duplicate:
                raise ValidationError(_('Only one AGA rate per company and zone is allowed.'))


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    _default_aga_rate_map = {
        '1': 14.1,
        '1a': 10.6,
        '2': 10.6,
        '3': 6.4,
        '4': 5.1,
        '5': 0.0,
    }

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
    wage_type = fields.Selection([
        ('monthly', 'Monthly Salary'),
        ('hourly', 'Hourly Wage'),
    ], string='Wage Type', default='monthly', groups="hr.group_hr_user", tracking=True)
    pension_scheme_id = fields.Many2one('nordic.pension.scheme', string='Pension Scheme', groups="hr.group_hr_user")
    deduction_rules_ids = fields.Many2many(
        'nordic.salary.rule',
        'nordic_employee_deduction_rule_rel',
        'employee_id',
        'rule_id',
        string='Deduction Rules',
        domain=[('category', '=', 'DED')],
        groups="hr.group_hr_user",
    )

    overtime_pct = fields.Float(string='Overtime Multiplier (%)', default=150.0)
    employment_identifier = fields.Char(string='Employment Identifier', groups="hr.group_hr_user", tracking=True)
    employment_start_date = fields.Date(string='Employment Start Date', groups="hr.group_hr_user", tracking=True)
    employment_end_date = fields.Date(string='Employment End Date', groups="hr.group_hr_user", tracking=True)
    position_percentage = fields.Float(string='Position Percentage', default=100.0, groups="hr.group_hr_user", tracking=True)
    weekly_hours = fields.Float(string='Weekly Hours', default=37.5, groups="hr.group_hr_user", tracking=True)
    working_hours_scheme = fields.Selection([
        ('ordinary', 'Ordinary Hours'),
        ('shift365', 'Shift 36.5 Hours'),
        ('offshore336', 'Offshore 33.6 Hours'),
        ('fullycontinuousShiftAndOtherSchemes', 'Fully Continuous Shift / Other Schemes'),
        ('24-hourcontinuousShiftAndRotation355', '24-hour Continuous Shift And Rotation 35.5 Hours'),
    ], string='Working Hours Scheme', default='ordinary', groups="hr.group_hr_user", tracking=True)

    # Lønnslipp specific fields
    bank_account = fields.Char(string='Bank Account (IBAN/Lønnskonto)', groups="hr.group_hr_user", tracking=True)
    vacation_days_used = fields.Float(string='Vacation Days Used (F.d.brukt)', default=0.0)
    vacation_days_available = fields.Float(string='Vacation Days Remaining (F.d.tilgode)', default=25.0)

    def get_a_melding_employment_data(self, report_date):
        self.ensure_one()
        return {
            'employment_identifier': self.employment_identifier or f'EMP-{self.id}',
            'start_date': self.employment_start_date,
            'end_date': self.employment_end_date,
            'position_percentage': round(self.position_percentage or 0.0, 2),
            'weekly_hours': round(self.weekly_hours or 0.0, 2),
            'working_hours_scheme': self.working_hours_scheme or 'ordinary',
            'job_title': self.job_title or (self.job_id.name if self.job_id else False),
            'report_date': report_date,
        }

    def get_employer_contribution_rate(self, company=None):
        self.ensure_one()
        zone = self.tax_zone or '1'
        target_company = company or self.company_id or self.env.company
        rate_model = self.env['nordic.aga.rate']
        rate = rate_model.search([
            ('active', '=', True),
            ('zone', '=', zone),
            ('company_id', '=', target_company.id),
        ], limit=1)
        if not rate:
            rate = rate_model.search([
                ('active', '=', True),
                ('zone', '=', zone),
                ('company_id', '=', False),
            ], limit=1)
        if rate:
            return rate.rate
        return self._default_aga_rate_map.get(zone, 0.0)
