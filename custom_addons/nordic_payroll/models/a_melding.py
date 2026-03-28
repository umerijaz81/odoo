# -*- coding: utf-8 -*-

import base64
import json
import logging
import uuid
from datetime import timedelta
from xml.etree import ElementTree

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AMeldingCodeMap(models.Model):
    _name = 'nordic.a.melding.code.map'
    _description = 'A-melding EDAG Code Mapping'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    internal_code = fields.Char(required=True)
    edag_code = fields.Char(required=True)
    official_name = fields.Char(required=True)
    line_kind = fields.Selection([
        ('income', 'Income'),
        ('deduction', 'Deduction'),
        ('employer_contribution', 'Employer Contribution'),
    ], required=True)
    expected_category = fields.Selection([
        ('BASIC', 'Basic Pay'),
        ('ALW', 'Allowance'),
        ('DED', 'Deduction'),
        ('COMP', 'Employer Contribution'),
    ], required=True)
    sign_expectation = fields.Selection([
        ('positive', 'Positive'),
        ('negative', 'Negative'),
    ], required=True)
    source_url = fields.Char(required=True)
    active = fields.Boolean(default=True)


class AMeldingFeedbackLine(models.Model):
    _name = 'nordic.a.melding.feedback.line'
    _description = 'A-melding Feedback Line'
    _order = 'sequence, id'

    report_id = fields.Many2one('nordic.a.melding', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    severity = fields.Selection([
        ('rejection', 'Rejection'),
        ('immediate', 'Immediate'),
        ('guideline', 'Guideline'),
        ('info', 'Info'),
    ], required=True)
    code = fields.Char(required=True)
    location = fields.Char()
    description = fields.Text(required=True)
    requires_correction = fields.Boolean(default=False)


class AMeldingPaymentLine(models.Model):
    _name = 'nordic.a.melding.payment.line'
    _description = 'A-melding Feedback Payment Line'
    _order = 'sequence, id'

    report_id = fields.Many2one('nordic.a.melding', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    payment_type = fields.Selection([
        ('withholding_tax', 'Withholding Tax'),
        ('employer_contribution', "Employer's National Insurance Contributions"),
        ('financial_activity_tax', 'Financial Activity Tax'),
        ('attachment_of_earnings', 'Attachment Of Earnings'),
        ('other', 'Other'),
    ], required=True)
    amount = fields.Float(required=True)
    account_number = fields.Char()
    kid = fields.Char()
    description = fields.Char()


class ResCompany(models.Model):
    _inherit = 'res.company'

    altinn_transport_enabled = fields.Boolean(string='Enable Altinn A02 Transport')
    a_melding_transport_profile = fields.Selection([
        ('maskinporten_dialogporten', 'Skatteetaten Maskinporten/Dialogporten'),
        ('generic_legacy', 'Generic Legacy Adapter'),
    ], string='A-melding Transport Profile', default='maskinporten_dialogporten')
    altinn_environment = fields.Selection([
        ('sandbox', 'Sandbox'),
        ('production', 'Production'),
    ], string='Altinn Environment', default='sandbox')
    altinn_api_base_url = fields.Char(string='Altinn API Base URL')
    altinn_token_url = fields.Char(string='Altinn Token URL')
    altinn_client_id = fields.Char(string='Altinn Client ID')
    altinn_client_secret = fields.Char(string='Altinn Client Secret')
    altinn_scope = fields.Char(string='Altinn OAuth Scope', default='altinn:serviceowner/api')
    altinn_subscription_key = fields.Char(string='Altinn Subscription Key')
    altinn_a02_submission_path = fields.Char(string='A02 Submission Path', default='/a-melding/a02/submissions')
    altinn_receipt_path_template = fields.Char(
        string='Receipt Polling Path Template',
        default='/a-melding/a03/receipts/{submission_id}',
        help='Use {submission_id} to interpolate the external submission identifier into the receipt URL.',
    )
    maskinporten_token_url = fields.Char(string='Maskinporten Token URL')
    maskinporten_client_id = fields.Char(string='Maskinporten Client ID')
    maskinporten_scope = fields.Char(string='Maskinporten Scope', default='skatteetaten:innrapporteringamelding')
    maskinporten_issuer = fields.Char(string='Maskinporten Issuer')
    maskinporten_private_key_id = fields.Char(string='Maskinporten Key ID')
    maskinporten_private_key = fields.Text(string='Maskinporten Private Key')
    skatteetaten_api_base_url = fields.Char(string='Skatteetaten API Base URL')
    skatteetaten_rest_submission_path = fields.Char(string='Skatteetaten REST Submission Path')
    dialogporten_api_base_url = fields.Char(string='Dialogporten API Base URL')
    dialogporten_feedback_path_template = fields.Char(
        string='Dialogporten Feedback Path Template',
        default='/api/v1/serviceowner/dialogs/{dialog_id}/messages/{message_id}',
        help='Use {dialog_id} and {message_id} placeholders from Dialogporten feedback events.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    altinn_transport_enabled = fields.Boolean(related='company_id.altinn_transport_enabled', readonly=False)
    a_melding_transport_profile = fields.Selection(related='company_id.a_melding_transport_profile', readonly=False)
    altinn_environment = fields.Selection(related='company_id.altinn_environment', readonly=False)
    altinn_api_base_url = fields.Char(related='company_id.altinn_api_base_url', readonly=False)
    altinn_token_url = fields.Char(related='company_id.altinn_token_url', readonly=False)
    altinn_client_id = fields.Char(related='company_id.altinn_client_id', readonly=False)
    altinn_client_secret = fields.Char(related='company_id.altinn_client_secret', readonly=False)
    altinn_scope = fields.Char(related='company_id.altinn_scope', readonly=False)
    altinn_subscription_key = fields.Char(related='company_id.altinn_subscription_key', readonly=False)
    altinn_a02_submission_path = fields.Char(related='company_id.altinn_a02_submission_path', readonly=False)
    altinn_receipt_path_template = fields.Char(related='company_id.altinn_receipt_path_template', readonly=False)
    maskinporten_token_url = fields.Char(related='company_id.maskinporten_token_url', readonly=False)
    maskinporten_client_id = fields.Char(related='company_id.maskinporten_client_id', readonly=False)
    maskinporten_scope = fields.Char(related='company_id.maskinporten_scope', readonly=False)
    maskinporten_issuer = fields.Char(related='company_id.maskinporten_issuer', readonly=False)
    maskinporten_private_key_id = fields.Char(related='company_id.maskinporten_private_key_id', readonly=False)
    maskinporten_private_key = fields.Text(related='company_id.maskinporten_private_key', readonly=False)
    skatteetaten_api_base_url = fields.Char(related='company_id.skatteetaten_api_base_url', readonly=False)
    skatteetaten_rest_submission_path = fields.Char(related='company_id.skatteetaten_rest_submission_path', readonly=False)
    dialogporten_api_base_url = fields.Char(related='company_id.dialogporten_api_base_url', readonly=False)
    dialogporten_feedback_path_template = fields.Char(related='company_id.dialogporten_feedback_path_template', readonly=False)

class AMelding(models.Model):
    _name = 'nordic.a.melding'
    _description = 'Norwegian A-melding Reporting'
    _inherit = ['mail.thread']
    _edag_namespace = 'http://www.skatteetaten.no/xsd/edag/v2'
    _allowed_state_transitions = {
        'draft': {'generated'},
        'generated': {'sent', 'draft'},
        'sent': {'accepted', 'rejected'},
        'accepted': set(),
        'rejected': {'draft'},
    }

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('sent', 'Sent to Altinn'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    xml_file = fields.Binary(string='A-melding XML')
    xml_filename = fields.Char(string='XML Filename')
    altinn_transport_ready = fields.Boolean(compute='_compute_altinn_transport_ready')
    transport_contract_status = fields.Selection([
        ('not_configured', 'Not Configured'),
        ('incomplete', 'Incomplete'),
        ('validated', 'Validated Against Official Contract'),
        ('legacy', 'Legacy Adapter'),
    ], compute='_compute_transport_contract_status')
    transport_contract_notes = fields.Text(compute='_compute_transport_contract_status')
    submission_type = fields.Selection([
        ('ordinary', 'Ordinary'),
        ('replacement', 'Replacement'),
        ('correction', 'Correction'),
    ], string='Submission Type', default='ordinary', tracking=True)
    amends_report_id = fields.Many2one('nordic.a.melding', string='Amends Report', readonly=True, copy=False, tracking=True)
    amended_report_ids = fields.One2many('nordic.a.melding', 'amends_report_id', string='Amendments')
    replacement_for_reference = fields.Char(string='Replacement For Submission', tracking=True)
    correction_for_reference = fields.Char(string='Correction For Submission', tracking=True)
    late_submission_reason = fields.Char(string='Late Submission Reason', tracking=True)
    submission_deadline = fields.Date(string='Submission Deadline', compute='_compute_submission_deadline', store=True)
    is_late_submission = fields.Boolean(string='Late Submission', compute='_compute_is_late_submission')
    generated_on = fields.Datetime(string='Generated On', readonly=True, tracking=True)
    sent_on = fields.Datetime(string='Sent On', readonly=True, tracking=True)
    receipt_polled_on = fields.Datetime(string='Receipt Polled On', readonly=True, tracking=True)
    feedback_processed_on = fields.Datetime(string='Feedback Processed On', readonly=True, tracking=True)
    idempotency_key = fields.Char(string='Idempotency Key', readonly=True, copy=False, tracking=True)
    external_submission_id = fields.Char(string='External Submission ID', readonly=True, tracking=True)
    altinn_receipt_reference = fields.Char(string='Altinn Receipt Reference', readonly=True, tracking=True)
    dialogporten_dialog_id = fields.Char(string='Dialogporten Dialog ID', readonly=True, tracking=True)
    dialogporten_message_id = fields.Char(string='Dialogporten Message ID', readonly=True, tracking=True)
    receipt_status = fields.Selection([
        ('not_requested', 'Not Requested'),
        ('pending', 'Pending'),
        ('available', 'Available'),
        ('processed', 'Processed'),
        ('error', 'Error'),
    ], string='Receipt Status', default='not_requested', tracking=True)
    transport_message = fields.Text(string='Transport Message', readonly=True, tracking=True)
    feedback_reference = fields.Char(string='Altinn Feedback Reference', tracking=True)
    feedback_notes = fields.Text(string='Feedback Notes', tracking=True)
    feedback_xml_file = fields.Binary(string='Altinn Feedback XML')
    feedback_xml_filename = fields.Char(string='Feedback XML Filename')
    receipt_xml_file = fields.Binary(string='Receipt XML')
    receipt_xml_filename = fields.Char(string='Receipt XML Filename')
    feedback_line_ids = fields.One2many('nordic.a.melding.feedback.line', 'report_id', string='Feedback Messages', readonly=True)
    payment_line_ids = fields.One2many('nordic.a.melding.payment.line', 'report_id', string='Payment Lines', readonly=True)

    @api.depends(
        'company_id.altinn_transport_enabled',
        'company_id.a_melding_transport_profile',
        'company_id.altinn_api_base_url',
        'company_id.altinn_token_url',
        'company_id.altinn_client_id',
        'company_id.altinn_client_secret',
        'company_id.maskinporten_token_url',
        'company_id.maskinporten_client_id',
        'company_id.maskinporten_scope',
        'company_id.maskinporten_issuer',
        'company_id.maskinporten_private_key_id',
        'company_id.maskinporten_private_key',
        'company_id.skatteetaten_api_base_url',
        'company_id.skatteetaten_rest_submission_path',
        'company_id.dialogporten_api_base_url',
        'company_id.dialogporten_feedback_path_template',
    )
    def _compute_altinn_transport_ready(self):
        for report in self:
            company = report.company_id
            if not company.altinn_transport_enabled:
                report.altinn_transport_ready = False
                continue
            if company.a_melding_transport_profile == 'generic_legacy':
                report.altinn_transport_ready = all([
                    company.altinn_api_base_url,
                    company.altinn_token_url,
                    company.altinn_client_id,
                    company.altinn_client_secret,
                ])
                continue
            report.altinn_transport_ready = all([
                company.maskinporten_token_url,
                company.maskinporten_client_id,
                company.maskinporten_scope,
                company.maskinporten_issuer,
                company.maskinporten_private_key_id,
                company.maskinporten_private_key,
                company.skatteetaten_api_base_url,
                company.skatteetaten_rest_submission_path,
                company.dialogporten_api_base_url,
                company.dialogporten_feedback_path_template,
            ])

    @api.depends(
        'company_id.altinn_transport_enabled',
        'company_id.a_melding_transport_profile',
        'company_id.maskinporten_scope',
        'company_id.altinn_api_base_url',
        'company_id.dialogporten_api_base_url',
        'altinn_transport_ready',
    )
    def _compute_transport_contract_status(self):
        for report in self:
            company = report.company_id
            if not company.altinn_transport_enabled:
                report.transport_contract_status = 'not_configured'
                report.transport_contract_notes = _('Transport is disabled for this company.')
                continue
            if company.a_melding_transport_profile == 'generic_legacy':
                report.transport_contract_status = 'legacy'
                report.transport_contract_notes = _(
                    'Legacy generic Altinn-style POST/GET transport is enabled. Official Skatteetaten integration requires Maskinporten scope skatteetaten:innrapporteringamelding, application/json request bodies, idempotency keys, and Dialogporten-based feedback retrieval.'
                )
                continue
            if not report.altinn_transport_ready:
                report.transport_contract_status = 'incomplete'
                report.transport_contract_notes = _(
                    'Official contract selected, but required Maskinporten or Dialogporten settings are missing. Configure Maskinporten token/client/key settings plus Skatteetaten REST and Dialogporten endpoints.'
                )
                continue
            report.transport_contract_status = 'validated'
            report.transport_contract_notes = _(
                'Official transport profile configured: Maskinporten authentication with scope skatteetaten:innrapporteringamelding, Skatteetaten REST/file upload submission, mandatory idempotency keys, and Dialogporten feedback flow.'
            )

    @api.depends('date_to')
    def _compute_submission_deadline(self):
        for report in self:
            if not report.date_to:
                report.submission_deadline = False
                continue
            following_month = report.date_to.replace(day=28) + timedelta(days=4)
            first_of_next_month = following_month.replace(day=1)
            deadline = first_of_next_month.replace(day=5)
            while deadline.weekday() >= 5:
                deadline += timedelta(days=1)
            report.submission_deadline = deadline

    @api.depends('submission_deadline')
    def _compute_is_late_submission(self):
        today = fields.Date.context_today(self)
        for report in self:
            report.is_late_submission = bool(report.submission_deadline and report.submission_deadline < today)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('nordic.a.melding') or 'AM/' + fields.Date.today().strftime('%Y/%m')
            vals.setdefault('company_id', self.env.company.id)
        reports = super().create(vals_list)
        reports._sync_amendment_chain()
        return reports

    def write(self, vals):
        if 'state' in vals and not self.env.context.get('allow_state_transition'):
            raise UserError(_(
                'Use the A-melding workflow actions to change status instead of writing the state directly.'
            ))
        result = super().write(vals)
        if not self.env.context.get('skip_amendment_sync') and {'submission_type', 'date_from', 'date_to', 'company_id', 'replacement_for_reference', 'correction_for_reference'}.intersection(vals):
            self._sync_amendment_chain()
        return result

    def _sync_amendment_chain(self):
        for report in self:
            values = {}
            if report.submission_type == 'ordinary':
                values = {
                    'amends_report_id': False,
                    'replacement_for_reference': False,
                    'correction_for_reference': False,
                }
            else:
                target_report = report._find_amendment_target()
                reference_value = target_report._get_submission_reference_value() if target_report else False
                if report.submission_type == 'replacement':
                    values['correction_for_reference'] = False
                    values['amends_report_id'] = target_report.id if target_report else False
                    if target_report and not report.replacement_for_reference:
                        values['replacement_for_reference'] = reference_value
                elif report.submission_type == 'correction':
                    values['replacement_for_reference'] = False
                    values['amends_report_id'] = target_report.id if target_report else False
                    if target_report and not report.correction_for_reference:
                        values['correction_for_reference'] = reference_value
            changed_values = {
                key: value
                for key, value in values.items()
                if (
                    report[key].id if key == 'amends_report_id' else report[key]
                ) != value
            }
            if changed_values:
                report.with_context(skip_amendment_sync=True).write(changed_values)

    def _find_amendment_target(self):
        self.ensure_one()
        if self.submission_type == 'ordinary':
            return self.env['nordic.a.melding']
        return self.search([
            ('id', '!=', self.id),
            ('company_id', '=', self.company_id.id),
            ('date_from', '=', self.date_from),
            ('date_to', '=', self.date_to),
            ('state', 'in', ['generated', 'sent', 'accepted', 'rejected']),
        ], order='sent_on desc, generated_on desc, id desc', limit=1)

    def _get_submission_reference_value(self):
        self.ensure_one()
        return self.external_submission_id or self.altinn_receipt_reference or self.feedback_reference or self.name

    def _ensure_idempotency_key(self):
        self.ensure_one()
        if not self.idempotency_key:
            self.write({'idempotency_key': str(uuid.uuid4())})
        return self.idempotency_key

    def _get_reportable_payslips(self):
        self.ensure_one()
        return self.env['nordic.payslip'].search([
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ])

    def _validate_reporting_prerequisites(self, payslips):
        self.ensure_one()
        if not payslips:
            raise UserError(_('No completed payslips found for the selected period.'))
        if not self.company_id.company_registry:
            raise UserError(_('Set the company organization number before generating A-melding.'))
        if self.date_from.strftime('%Y-%m') != self.date_to.strftime('%Y-%m'):
            raise UserError(_('A-melding periods must start and end within the same calendar month.'))

        missing_ssn_employees = payslips.filtered(lambda slip: not slip.employee_id.nordic_ssn).mapped('employee_id.name')
        if missing_ssn_employees:
            raise UserError(_(
                'Employees missing SSN for A-melding: %s'
            ) % ', '.join(sorted(set(missing_ssn_employees))))

        employees_with_multiple_slips = []
        for employee in payslips.mapped('employee_id'):
            if len(payslips.filtered(lambda slip: slip.employee_id == employee)) > 1:
                employees_with_multiple_slips.append(employee.name)
        if employees_with_multiple_slips:
            raise UserError(_(
                'A-melding requires exactly one completed payslip per employee in the selected month: %s'
            ) % ', '.join(sorted(set(employees_with_multiple_slips))))

        missing_employment_details = []
        for employee in payslips.mapped('employee_id'):
            if not employee.employment_start_date or not employee.position_percentage or not employee.weekly_hours:
                missing_employment_details.append(employee.name)
        if missing_employment_details:
            raise UserError(_(
                'Employees missing employment reporting data for A-melding: %s'
            ) % ', '.join(sorted(set(missing_employment_details))))
        self._validate_submission_controls()

    def _validate_submission_controls(self):
        self.ensure_one()
        self._sync_amendment_chain()
        today = fields.Date.context_today(self)
        reporting_month = self.date_from.replace(day=1)
        current_month = today.replace(day=1)
        max_future_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        max_future_month = (max_future_month.replace(day=28) + timedelta(days=4)).replace(day=1)

        if reporting_month > current_month and (reporting_month > max_future_month or reporting_month.year != today.year):
            raise UserError(_(
                'A-melding can only be submitted for the current month and up to two months ahead within the current calendar year.'
            ))
        if self.is_late_submission and not self.late_submission_reason:
            raise UserError(_(
                'Late A-melding submissions require a documented late submission reason before XML generation or Altinn submission.'
            ))
        if self.submission_type == 'replacement' and not self.replacement_for_reference:
            raise UserError(_('Replacement submissions require a reference to the submission being replaced.'))
        if self.submission_type == 'correction' and not self.correction_for_reference:
            raise UserError(_('Correction submissions require a reference to the submission being corrected.'))

    def _build_a_melding_xml(self, payslips):
        self.ensure_one()
        ElementTree.register_namespace('', self._edag_namespace)
        root = ElementTree.Element(f'{{{self._edag_namespace}}}EDAG-M')
        delivery = ElementTree.SubElement(root, f'{{{self._edag_namespace}}}Leveranse')
        ElementTree.SubElement(delivery, f'{{{self._edag_namespace}}}LeveranseId').text = self.name
        ElementTree.SubElement(delivery, f'{{{self._edag_namespace}}}Maaned').text = self.date_from.strftime('%Y-%m')
        ElementTree.SubElement(delivery, f'{{{self._edag_namespace}}}Orgnummer').text = self.company_id.company_registry
        ElementTree.SubElement(delivery, f'{{{self._edag_namespace}}}Innsendingstype').text = self.submission_type
        if self.replacement_for_reference:
            ElementTree.SubElement(delivery, f'{{{self._edag_namespace}}}ErstatterLeveranseId').text = self.replacement_for_reference
        if self.correction_for_reference:
            ElementTree.SubElement(delivery, f'{{{self._edag_namespace}}}KorrigererLeveranseId').text = self.correction_for_reference

        for slip in payslips:
            assignment = ElementTree.SubElement(delivery, f'{{{self._edag_namespace}}}Oppgave')
            ElementTree.SubElement(assignment, f'{{{self._edag_namespace}}}Fodselsnummer').text = slip.employee_id.nordic_ssn
            employment = slip.employee_id.get_a_melding_employment_data(self.date_to)
            employment_node = ElementTree.SubElement(assignment, f'{{{self._edag_namespace}}}Arbeidsforhold')
            ElementTree.SubElement(employment_node, f'{{{self._edag_namespace}}}AnsettelsesId').text = employment['employment_identifier']
            ElementTree.SubElement(employment_node, f'{{{self._edag_namespace}}}Startdato').text = employment['start_date'].strftime('%Y-%m-%d')
            if employment['end_date']:
                ElementTree.SubElement(employment_node, f'{{{self._edag_namespace}}}Sluttdato').text = employment['end_date'].strftime('%Y-%m-%d')
            ElementTree.SubElement(employment_node, f'{{{self._edag_namespace}}}Stillingsprosent').text = str(employment['position_percentage'])
            ElementTree.SubElement(employment_node, f'{{{self._edag_namespace}}}AvtaltUkentligArbeidstid').text = str(employment['weekly_hours'])
            ElementTree.SubElement(employment_node, f'{{{self._edag_namespace}}}Arbeidstidsordning').text = employment['working_hours_scheme']
            if employment['job_title']:
                ElementTree.SubElement(employment_node, f'{{{self._edag_namespace}}}Yrkestittel').text = employment['job_title']
            for line in slip.get_a_melding_report_lines():
                line_tag = {
                    'income': 'Inntektslinje',
                    'deduction': 'TrekkLinje',
                    'employer_contribution': 'ArbeidsgiveravgiftLinje',
                }[line['kind']]
                xml_line = ElementTree.SubElement(assignment, f'{{{self._edag_namespace}}}{line_tag}')
                ElementTree.SubElement(xml_line, f'{{{self._edag_namespace}}}Type').text = line['edag_code']
                ElementTree.SubElement(xml_line, f'{{{self._edag_namespace}}}Beskrivelse').text = line['official_name']
                ElementTree.SubElement(xml_line, f'{{{self._edag_namespace}}}Belop').text = str(line['amount'])

        return ElementTree.tostring(root, encoding='utf-8', xml_declaration=True)

    def action_generate_xml(self):
        """Aggregate reportable payslips and generate validated A-melding XML."""
        self.ensure_one()
        payslips = self._get_reportable_payslips()
        self._validate_reporting_prerequisites(payslips)
        xml_content = self._build_a_melding_xml(payslips)
        self._transition_state('generated', {
            'xml_file': base64.b64encode(xml_content),
            'xml_filename': f"a-melding-{self.date_from.strftime('%Y-%m')}.xml",
            'generated_on': fields.Datetime.now(),
        })
        return True

    def action_mark_sent(self):
        self.ensure_one()
        if not self.xml_file:
            raise UserError(_('Generate XML before marking the A-melding as sent.'))
        self._transition_state('sent', {
            'sent_on': fields.Datetime.now(),
            'receipt_status': 'pending',
        })
        return True

    def action_submit_to_altinn(self):
        self.ensure_one()
        if self.state != 'generated':
            raise UserError(_('Only generated A-meldings can be submitted to Altinn.'))
        if not self.altinn_transport_ready:
            raise UserError(_('Configure Altinn A02 transport settings for the company before submitting.'))
        if not self.xml_file:
            raise UserError(_('Generate XML before submitting the A-melding to Altinn.'))

        if self.company_id.a_melding_transport_profile == 'maskinporten_dialogporten':
            raise UserError(_(
                'Official contract validation succeeded, but direct submission remains blocked until the request body is rebuilt against Skatteetaten\'s published application/json REST or file-upload schema. Feedback retrieval must also be driven from Dialogporten event identifiers rather than the legacy receipt polling path.'
            ))

        response_payload = self._submit_to_altinn(base64.b64decode(self.xml_file))
        self._transition_state('sent', {
            'sent_on': fields.Datetime.now(),
            'idempotency_key': self.idempotency_key,
            'external_submission_id': response_payload['submission_id'],
            'altinn_receipt_reference': response_payload['receipt_reference'],
            'receipt_status': response_payload['receipt_status'],
            'transport_message': response_payload['message'],
        })
        return True

    def action_reset_to_draft(self):
        self.ensure_one()
        self._transition_state('draft', {
            'external_submission_id': False,
            'altinn_receipt_reference': False,
            'receipt_status': 'not_requested',
            'receipt_polled_on': False,
            'transport_message': False,
            'feedback_processed_on': False,
            'sent_on': False,
            'idempotency_key': False,
            'feedback_reference': False,
            'feedback_notes': False,
            'feedback_xml_file': False,
            'feedback_xml_filename': False,
            'receipt_xml_file': False,
            'receipt_xml_filename': False,
            'dialogporten_dialog_id': False,
            'dialogporten_message_id': False,
        })
        return True

    def action_poll_altinn_receipt(self):
        self.ensure_one()
        if self.state != 'sent':
            raise UserError(_('Altinn receipts can only be polled after submission.'))
        if not self.external_submission_id:
            raise UserError(_('No external submission identifier is stored for this A-melding.'))
        if not self.altinn_transport_ready:
            raise UserError(_('Configure Altinn A02 transport settings for the company before polling receipts.'))

        receipt = self._poll_altinn_receipt()
        self.write({
            'receipt_polled_on': fields.Datetime.now(),
            'receipt_status': receipt['receipt_status'],
            'transport_message': receipt['message'],
            'altinn_receipt_reference': receipt['receipt_reference'] or self.altinn_receipt_reference,
        })
        if receipt['receipt_xml']:
            encoded_receipt_xml = base64.b64encode(receipt['receipt_xml'].encode('utf-8'))
            self.write({
                'receipt_xml_file': encoded_receipt_xml,
                'receipt_xml_filename': receipt['receipt_filename'],
                'feedback_xml_file': encoded_receipt_xml,
                'feedback_xml_filename': receipt['receipt_filename'],
            })
            self.action_process_feedback_xml()
            self.write({'receipt_status': 'processed'})
        return True

    def action_process_feedback_xml(self):
        self.ensure_one()
        if self.state != 'sent':
            raise UserError(_('Feedback can only be processed after the A-melding has been marked as sent.'))
        if not self.feedback_xml_file:
            raise UserError(_('Upload the Altinn feedback XML before processing feedback.'))

        feedback_payload = base64.b64decode(self.feedback_xml_file)
        parsed_feedback = self._parse_feedback_xml(feedback_payload)
        target_state = 'rejected' if parsed_feedback['has_rejection'] else 'accepted'
        feedback_line_commands = [(5, 0, 0)] + [
            (0, 0, line_values)
            for line_values in parsed_feedback['feedback_lines']
        ]
        payment_line_commands = [(5, 0, 0)] + [
            (0, 0, payment_values)
            for payment_values in parsed_feedback['payment_lines']
        ]
        self._transition_state(target_state, {
            'feedback_reference': parsed_feedback['reference'],
            'feedback_notes': parsed_feedback['summary'],
            'feedback_processed_on': fields.Datetime.now(),
            'receipt_status': 'processed',
            'feedback_line_ids': feedback_line_commands,
            'payment_line_ids': payment_line_commands,
        })
        return True

    def _submit_to_altinn(self, xml_payload):
        self.ensure_one()
        config = self._get_altinn_transport_config()
        idempotency_key = self._ensure_idempotency_key()
        token = self._get_altinn_access_token(config)
        headers = self._build_altinn_headers(token, idempotency_key=idempotency_key)
        headers['Content-Type'] = 'application/xml'
        response = requests.post(
            self._build_altinn_url(config['api_base_url'], config['submission_path']),
            headers=headers,
            data=xml_payload,
            timeout=60,
        )
        response.raise_for_status()
        payload = self._coerce_http_payload(response)
        submission_id = self._extract_nested_value(payload, ['submissionId', 'submission_id', 'id', 'reference'])
        receipt_reference = self._extract_nested_value(payload, ['receiptId', 'receipt_id', 'receiptReference', 'receipt_reference', 'reference']) or submission_id
        message = self._extract_nested_value(payload, ['message', 'statusMessage', 'description']) or _('Submitted to Altinn A02 transport endpoint.')
        return {
            'submission_id': submission_id or self.name,
            'receipt_reference': receipt_reference,
            'receipt_status': self._normalize_receipt_status(self._extract_nested_value(payload, ['receiptStatus', 'status', 'state']) or 'pending'),
            'message': message,
        }

    def _poll_altinn_receipt(self):
        self.ensure_one()
        config = self._get_altinn_transport_config()
        token = self._get_altinn_access_token(config)
        headers = self._build_altinn_headers(token, idempotency_key=self._ensure_idempotency_key())
        receipt_path = config['receipt_path_template'].format(submission_id=self.external_submission_id)
        response = requests.get(
            self._build_altinn_url(config['api_base_url'], receipt_path),
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        payload = self._coerce_http_payload(response)
        receipt_xml = self._extract_receipt_xml(response, payload)
        receipt_status = self._normalize_receipt_status(self._extract_nested_value(payload, ['receiptStatus', 'status', 'state']) or ('available' if receipt_xml else 'pending'))
        message = self._extract_nested_value(payload, ['message', 'statusMessage', 'description']) or _('Polled Altinn receipt endpoint.')
        return {
            'receipt_status': receipt_status,
            'receipt_reference': self._extract_nested_value(payload, ['receiptId', 'receipt_id', 'receiptReference', 'receipt_reference', 'reference']),
            'receipt_xml': receipt_xml,
            'receipt_filename': f'a03-receipt-{self.name}.xml',
            'message': message,
        }

    def _get_altinn_transport_config(self):
        self.ensure_one()
        company = self.company_id
        if not company.altinn_transport_enabled:
            raise UserError(_('Altinn transport is not enabled for the selected company.'))
        if company.a_melding_transport_profile != 'generic_legacy':
            raise UserError(_(
                'Legacy generic transport configuration is no longer the active contract for this company. Use the official Maskinporten/Dialogporten profile or switch the company to the generic legacy adapter for mocked compatibility testing.'
            ))
        required_values = {
            'api_base_url': company.altinn_api_base_url,
            'token_url': company.altinn_token_url,
            'client_id': company.altinn_client_id,
            'client_secret': company.altinn_client_secret,
            'submission_path': company.altinn_a02_submission_path,
            'receipt_path_template': company.altinn_receipt_path_template,
        }
        missing_keys = [label for label, value in required_values.items() if not value]
        if missing_keys:
            raise UserError(_('Missing Altinn company settings: %s') % ', '.join(sorted(missing_keys)))
        required_values['scope'] = company.altinn_scope
        required_values['subscription_key'] = company.altinn_subscription_key
        return required_values

    def _get_altinn_access_token(self, config):
        token_response = requests.post(
            config['token_url'],
            data={
                'grant_type': 'client_credentials',
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'scope': config['scope'],
            },
            timeout=30,
        )
        token_response.raise_for_status()
        payload = self._coerce_http_payload(token_response)
        token = self._extract_nested_value(payload, ['access_token', 'accessToken', 'token'])
        if not token:
            raise UserError(_('Altinn token response did not include an access token.'))
        return token

    def _build_altinn_headers(self, access_token, idempotency_key=False):
        self.ensure_one()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json, application/xml',
        }
        if idempotency_key:
            headers['idempotencyKey'] = idempotency_key
        if self.company_id.altinn_subscription_key:
            headers['Ocp-Apim-Subscription-Key'] = self.company_id.altinn_subscription_key
        return headers

    def _build_altinn_url(self, base_url, path):
        return '%s/%s' % (base_url.rstrip('/'), path.lstrip('/'))

    def _coerce_http_payload(self, response):
        content_type = (response.headers.get('Content-Type') or '').lower()
        text = response.text or ''
        if 'json' in content_type:
            return response.json()
        stripped = text.strip()
        if stripped.startswith('{') or stripped.startswith('['):
            return json.loads(stripped)
        if stripped.startswith('<'):
            return {'xml': stripped}
        return {'text': stripped}

    def _extract_receipt_xml(self, response, payload):
        xml_payload = self._extract_nested_value(payload, ['feedbackXml', 'feedback_xml', 'receiptXml', 'receipt_xml', 'xml', 'content'])
        if xml_payload:
            decoded_payload = self._decode_base64_text(xml_payload)
            return decoded_payload if decoded_payload.lstrip().startswith('<') else xml_payload
        content_type = (response.headers.get('Content-Type') or '').lower()
        if 'xml' in content_type and response.text:
            return response.text
        return False

    def _extract_nested_value(self, payload, keys):
        if isinstance(payload, dict):
            for key, value in payload.items():
                if key in keys:
                    return value
                nested_value = self._extract_nested_value(value, keys)
                if nested_value not in (False, None, '', []):
                    return nested_value
        elif isinstance(payload, list):
            for item in payload:
                nested_value = self._extract_nested_value(item, keys)
                if nested_value not in (False, None, '', []):
                    return nested_value
        return False

    def _decode_base64_text(self, payload):
        if not isinstance(payload, str):
            return payload
        try:
            decoded = base64.b64decode(payload).decode('utf-8')
        except Exception:
            return payload
        return decoded

    def _normalize_receipt_status(self, status):
        normalized = (status or '').strip().lower()
        if normalized in {'processed', 'accepted', 'rejected'}:
            return 'processed'
        if normalized in {'available', 'ready', 'complete'}:
            return 'available'
        if normalized in {'error', 'failed'}:
            return 'error'
        if normalized in {'pending', 'submitted', 'sent', 'processing'}:
            return 'pending'
        return 'not_requested'

    def _transition_state(self, target_state, extra_vals=None):
        extra_vals = extra_vals or {}
        for report in self:
            source_state = report.state
            if target_state not in self._allowed_state_transitions.get(report.state, set()):
                raise UserError(_(
                    'Cannot move A-melding %(report)s from %(source)s to %(target)s.'
                ) % {
                    'report': report.display_name,
                    'source': source_state,
                    'target': target_state,
                })
            values = {'state': target_state}
            values.update(extra_vals)
            report.with_context(allow_state_transition=True).write(values)
            report.message_post(
                body=_('A-melding workflow audit: status changed from %(source)s to %(target)s.') % {
                    'source': source_state,
                    'target': target_state,
                },
                subtype_xmlid='mail.mt_note',
            )

    def _parse_feedback_xml(self, payload):
        root = ElementTree.fromstring(payload)
        reference = self._find_first_text(root, {'Reference', 'Tilbakemeldingsreferanse', 'MeldingsId', 'Referanse'})
        feedback_lines = self._extract_feedback_lines(root)
        payment_lines = self._extract_payment_lines(root)
        has_rejection = any(line['severity'] == 'rejection' for line in feedback_lines)
        summary = _('%(count)s feedback messages, %(payments)s payment lines parsed from A03 feedback.') % {
            'count': len(feedback_lines),
            'payments': len(payment_lines),
        }
        return {
            'reference': reference,
            'feedback_lines': feedback_lines,
            'payment_lines': payment_lines,
            'has_rejection': has_rejection,
            'summary': summary,
        }

    def _extract_feedback_lines(self, root):
        feedback_lines = []
        message_tags = {'Message', 'Melding', 'Error', 'Issue', 'Tilbakemelding', 'Avvik'}
        for element in root.iter():
            if self._local_name(element.tag) not in message_tags:
                continue
            severity = self._normalize_severity(self._find_first_text(element, {'Severity', 'Alvorlighetsgrad', 'Level'}))
            code = self._find_first_text(element, {'Code', 'Kode', 'Rule'}) or 'UNKNOWN'
            location = self._find_first_text(element, {'Location', 'Sted', 'Path'})
            description = self._find_first_text(element, {'Description', 'Beskrivelse', 'MessageText', 'Text'}) or ''
            if not description:
                continue
            feedback_lines.append({
                'severity': severity,
                'code': code,
                'location': location,
                'description': description,
                'requires_correction': severity in {'rejection', 'immediate'},
            })
        return feedback_lines

    def _extract_payment_lines(self, root):
        payment_lines = []
        payment_tags = {'Payment', 'Betaling', 'Krav'}
        for element in root.iter():
            if self._local_name(element.tag) not in payment_tags:
                continue
            payment_type_text = self._find_first_text(element, {'Type', 'PaymentType', 'Kategori'}) or element.attrib.get('type') or 'other'
            amount_text = self._find_first_text(element, {'Amount', 'Belop', 'Sum'})
            if not amount_text:
                continue
            try:
                amount = float(amount_text)
            except ValueError:
                continue
            payment_lines.append({
                'payment_type': self._normalize_payment_type(payment_type_text),
                'amount': amount,
                'account_number': self._find_first_text(element, {'AccountNumber', 'Kontonummer'}),
                'kid': self._find_first_text(element, {'KID', 'Kid'}),
                'description': self._find_first_text(element, {'Description', 'Beskrivelse'}),
            })
        return payment_lines

    def _find_first_text(self, element, tag_names):
        for child in element.iter():
            if self._local_name(child.tag) in tag_names and (child.text or '').strip():
                return child.text.strip()
        return False

    def _local_name(self, tag):
        return tag.split('}', 1)[-1]

    def _normalize_severity(self, severity):
        normalized = (severity or '').strip().lower()
        if 'rejection' in normalized or 'avvis' in normalized:
            return 'rejection'
        if 'immediate' in normalized:
            return 'immediate'
        if 'guideline' in normalized:
            return 'guideline'
        return 'info'

    def _normalize_payment_type(self, payment_type):
        normalized = (payment_type or '').strip().lower().replace(' ', '_')
        mapping = {
            'withholding_tax': 'withholding_tax',
            'forskuddstrekk': 'withholding_tax',
            'employer_contribution': 'employer_contribution',
            'employers_national_insurance_contributions': 'employer_contribution',
            'arbeidsgiveravgift': 'employer_contribution',
            'financial_activity_tax': 'financial_activity_tax',
            'finansskatt': 'financial_activity_tax',
            'attachment_of_earnings': 'attachment_of_earnings',
            'utleggstrekk': 'attachment_of_earnings',
        }
        return mapping.get(normalized, 'other')
