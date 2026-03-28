import base64
from datetime import date, timedelta
from unittest.mock import Mock, patch
from xml.etree import ElementTree

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestNordicPayroll(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user_group = cls.env.ref('hr.group_hr_user')
        cls.hr_manager_group = cls.env.ref('hr.group_hr_manager')
        cls.company = cls.env.company
        cls.company.write({'company_registry': '123456789'})
        cls.other_company = cls.env['res.company'].create({
            'name': 'Nordic Payroll Test Company 2',
            'company_registry': '987654321',
        })
        cls.reporting_company = cls.env['res.company'].create({
            'name': 'Nordic Payroll Reporting Company',
            'company_registry': '192837465',
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Nordic Payroll Test Employee',
            'nordic_ssn': '12345678901',
            'nordic_wage': 50000.0,
            'pension_percentage': 2.0,
            'tax_table': '7100',
            'tax_zone': '1',
            'employment_identifier': 'EMP-100',
            'employment_start_date': '2025-01-01',
            'position_percentage': 100.0,
            'weekly_hours': 37.5,
            'working_hours_scheme': 'ordinary',
        })
        cls.reporting_employee = cls.env['hr.employee'].create({
            'name': 'Nordic Payroll Reporting Employee',
            'company_id': cls.reporting_company.id,
            'nordic_ssn': '10987654321',
            'nordic_wage': 52000.0,
            'pension_percentage': 2.0,
            'tax_table': '7100',
            'tax_zone': '1',
            'employment_identifier': 'EMP-200',
            'employment_start_date': '2025-01-01',
            'position_percentage': 100.0,
            'weekly_hours': 37.5,
            'working_hours_scheme': 'ordinary',
        })
        cls.structure = cls.env['nordic.payroll.structure'].create({
            'name': 'Nordic Payroll Test Structure',
            'rule_ids': [
                (0, 0, {
                    'name': 'Basic Salary',
                    'code': 'BASIC',
                    'sequence': 10,
                    'category': 'BASIC',
                    'amount_select': 'python',
                    'amount_python_compute': 'result = employee.nordic_wage',
                }),
                (0, 0, {
                    'name': 'Pension Deduction',
                    'code': 'PENSION',
                    'sequence': 20,
                    'category': 'DED',
                    'amount_select': 'python',
                    'amount_python_compute': (
                        "basic = rules.get('BASIC', 0.0)\n"
                        "rate = employee.pension_percentage or 0.0\n"
                        "result = -(basic * (rate / 100.0))"
                    ),
                }),
                (0, 0, {
                    'name': 'Income Tax',
                    'code': 'TAX',
                    'sequence': 30,
                    'category': 'DED',
                    'amount_select': 'python',
                    'amount_python_compute': (
                        "taxable = rules.get('BASIC', 0.0) + rules.get('PENSION', 0.0)\n"
                        "result = -(taxable * 0.25)"
                    ),
                }),
                (0, 0, {
                    'name': 'Employer Contribution',
                    'code': 'AGA',
                    'sequence': 40,
                    'category': 'COMP',
                    'amount_select': 'python',
                    'amount_python_compute': (
                        "rate = employee.get_employer_contribution_rate(payslip.company_id)\n"
                        "result = rules.get('BASIC', 0.0) * (rate / 100.0)"
                    ),
                }),
            ],
        })
        cls.structure.action_approve_for_production()
        cls.hr_limited_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Nordic Payroll HR User',
            'login': 'nordic_payroll_hr_user',
            'email': 'nordic_payroll_hr_user@example.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.hr_user_group.id])],
        })

    @classmethod
    def _add_months(cls, source_date, offset):
        month_index = source_date.month - 1 + offset
        year = source_date.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, 1)

    @classmethod
    def _month_range(cls, offset=0):
        month_start = cls._add_months(date.today().replace(day=1), offset)
        next_month_start = cls._add_months(month_start, 1)
        month_end = next_month_start - timedelta(days=1)
        return month_start.isoformat(), month_end.isoformat()

    def _create_a_melding(self, company=None, date_from=None, date_to=None, **extra_vals):
        vals = {
            'company_id': (company or self.reporting_company).id,
            'date_from': date_from,
            'date_to': date_to,
        }
        vals.update(extra_vals)
        return self.env['nordic.a.melding'].create(vals)

    def _create_payslip(self, date_from=None, date_to=None, payment_date=None, employee=None, company=None):
        default_from, default_to = self._month_range(0)
        return self.env['nordic.payslip'].create({
            'company_id': (company or self.reporting_company).id,
            'employee_id': (employee or self.reporting_employee).id,
            'struct_id': self.structure.id,
            'date_from': date_from or default_from,
            'date_to': date_to or default_to,
            'payment_date': payment_date or date_to or default_to,
            'run_number': 1,
        })

    def _create_company_scoped_payslip(self, company, date_from, date_to):
        return self.env['nordic.payslip'].create({
            'company_id': company.id,
            'employee_id': self.employee.id,
            'struct_id': self.structure.id,
            'date_from': date_from,
            'date_to': date_to,
            'payment_date': date_to,
            'run_number': 1,
        })

    def _finalize_payslip(self, payslip):
        payslip.action_submit_for_verification()
        payslip.action_mark_done()
        return payslip

    def _mock_response(self, json_payload=None, text='', content_type='application/json'):
        response = Mock()
        response.headers = {'Content-Type': content_type}
        response.text = text
        response.raise_for_status = Mock()
        if json_payload is not None:
            response.json = Mock(return_value=json_payload)
        else:
            response.json = Mock(side_effect=ValueError('No JSON body'))
        return response

    def _configure_altinn_company(self):
        self.reporting_company.write({
            'altinn_transport_enabled': True,
            'a_melding_transport_profile': 'generic_legacy',
            'altinn_api_base_url': 'https://altinn.example.test/api',
            'altinn_token_url': 'https://altinn.example.test/oauth/token',
            'altinn_client_id': 'client-id',
            'altinn_client_secret': 'client-secret',
            'altinn_scope': 'altinn:test',
            'altinn_a02_submission_path': '/a02/submissions',
            'altinn_receipt_path_template': '/a03/receipts/{submission_id}',
        })

    def _configure_official_transport_company(self):
        self.reporting_company.write({
            'altinn_transport_enabled': True,
            'a_melding_transport_profile': 'maskinporten_dialogporten',
            'maskinporten_token_url': 'https://maskinporten.example.test/token',
            'maskinporten_client_id': 'maskinporten-client-id',
            'maskinporten_scope': 'skatteetaten:innrapporteringamelding',
            'maskinporten_issuer': '123456789',
            'maskinporten_private_key_id': 'kid-001',
            'maskinporten_private_key': '-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----',
            'skatteetaten_api_base_url': 'https://api.skatteetaten-test.no',
            'skatteetaten_rest_submission_path': '/amelding/rest',
            'dialogporten_api_base_url': 'https://dialogporten.example.test',
            'dialogporten_feedback_path_template': '/dialogs/{dialog_id}/messages/{message_id}',
        })

    def test_compute_sheet_generates_expected_lines_and_totals(self):
        payslip = self._create_payslip()

        payslip.compute_sheet()

        lines_by_code = {line.code: line for line in payslip.line_ids}
        self.assertEqual(set(lines_by_code), {'BASIC', 'PENSION', 'TAX', 'AGA'})
        self.assertEqual(lines_by_code['BASIC'].amount, 50000.0)
        self.assertEqual(lines_by_code['PENSION'].amount, -1000.0)
        self.assertEqual(lines_by_code['TAX'].amount, -12250.0)
        self.assertAlmostEqual(lines_by_code['AGA'].amount, 7050.0, places=2)

        self.assertEqual(payslip.gross_amount, 50000.0)
        self.assertEqual(payslip.tax_amount, 12250.0)
        self.assertEqual(payslip.net_amount, 36750.0)
        self.assertAlmostEqual(payslip.total_employer_cost, 57050.0, places=2)
        self.assertNotEqual(payslip.name, '/')

    def test_a_melding_generation_creates_xml_file(self):
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)

        self.assertTrue(report.action_generate_xml())
        self.assertEqual(report.state, 'generated')
        self.assertTrue(report.xml_file)

        xml_root = ElementTree.fromstring(base64.b64decode(report.xml_file))
        namespace = {'edag': 'http://www.skatteetaten.no/xsd/edag/v2'}
        self.assertEqual(xml_root.tag, '{http://www.skatteetaten.no/xsd/edag/v2}EDAG-M')
        self.assertEqual(xml_root.findtext('edag:Leveranse/edag:LeveranseId', namespaces=namespace), report.name)
        self.assertEqual(xml_root.findtext('edag:Leveranse/edag:Orgnummer', namespaces=namespace), self.reporting_company.company_registry)
        self.assertEqual(xml_root.findtext('edag:Leveranse/edag:Innsendingstype', namespaces=namespace), 'ordinary')
        self.assertEqual(
            xml_root.findtext('edag:Leveranse/edag:Oppgave/edag:Arbeidsforhold/edag:AnsettelsesId', namespaces=namespace),
            self.reporting_employee.employment_identifier,
        )

        income_lines = xml_root.findall('edag:Leveranse/edag:Oppgave/edag:Inntektslinje', namespace)
        deduction_lines = xml_root.findall('edag:Leveranse/edag:Oppgave/edag:TrekkLinje', namespace)
        employer_lines = xml_root.findall('edag:Leveranse/edag:Oppgave/edag:ArbeidsgiveravgiftLinje', namespace)
        self.assertEqual(len(income_lines), 1)
        self.assertEqual(len(deduction_lines), 2)
        self.assertEqual(len(employer_lines), 1)
        self.assertEqual({line.findtext('edag:Type', namespaces=namespace) for line in income_lines}, {'fixedSalary'})
        self.assertEqual({line.findtext('edag:Type', namespaces=namespace) for line in deduction_lines}, {'pensionContribution', 'withholdingTax'})
        self.assertEqual({line.findtext('edag:Type', namespaces=namespace) for line in employer_lines}, {'employersNationalInsuranceContribution'})

    def test_a_melding_generation_rejects_missing_employee_ssn(self):
        date_from, date_to = self._month_range(2)
        original_ssn = self.reporting_employee.nordic_ssn
        self.reporting_employee.nordic_ssn = False
        try:
            payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
            report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)

            with self.assertRaises(UserError):
                report.action_generate_xml()
        finally:
            self.reporting_employee.nordic_ssn = original_ssn

    def test_a_melding_generation_rejects_missing_employment_data(self):
        date_from, date_to = self._month_range(2)
        original_start_date = self.reporting_employee.employment_start_date
        self.reporting_employee.employment_start_date = False
        try:
            payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
            report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)

            with self.assertRaises(UserError):
                report.action_generate_xml()
        finally:
            self.reporting_employee.employment_start_date = original_start_date

    def test_a_melding_generation_rejects_unsupported_line_codes(self):
        date_from, date_to = self._month_range(2)
        payslip = self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to)
        payslip.action_submit_for_verification()
        self.env['nordic.payslip.line'].create({
            'slip_id': payslip.id,
            'name': 'Unsupported Allowance',
            'code': 'UNSUPPORTED',
            'sequence': 99,
            'category': 'ALW',
            'amount': 500.0,
        })
        payslip.action_mark_done()
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)

        with self.assertRaises(UserError):
            report.action_generate_xml()

    def test_a_melding_supports_extended_edag_mapping_catalog(self):
        date_from, date_to = self._month_range(2)
        payslip = self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to)
        payslip.compute_sheet()
        extra_lines = [
            ('OVERTIME', 'Overtime payment', 'ALW', 4000.0),
            ('HOLIDAYPAY', 'Holiday pay', 'ALW', 7500.0),
            ('BONUS', 'Bonus', 'ALW', 2500.0),
            ('EXP_PERDIEM', 'Per diem allowance', 'ALW', 850.0),
            ('EXP_MILEAGE', 'Mileage allowance', 'ALW', 1200.0),
            ('EXP_REIMB', 'Expense reimbursement', 'ALW', 650.0),
        ]
        for code, name, category, amount in extra_lines:
            self.env['nordic.payslip.line'].create({
                'slip_id': payslip.id,
                'name': name,
                'code': code,
                'sequence': 100,
                'category': category,
                'amount': amount,
            })

        mapped_codes = {line['edag_code'] for line in payslip.get_a_melding_report_lines()}

        self.assertTrue({'overtimePay', 'holidayPay', 'bonus', 'perDiemAllowance', 'mileageAllowance', 'expenseReimbursement'}.issubset(mapped_codes))

    def test_a_melding_supports_leave_benefit_and_sector_specific_mappings(self):
        date_from, date_to = self._month_range(2)
        payslip = self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to)
        payslip.compute_sheet()
        extra_lines = [
            ('SICKPAY', 'Sick pay', 'ALW', 3200.0),
            ('PARENTALPAY', 'Parental pay', 'ALW', 4200.0),
            ('CAREPAY', 'Care pay', 'ALW', 1800.0),
            ('SHIFTADD', 'Shift allowance', 'ALW', 900.0),
            ('OFFSHOREADD', 'Offshore allowance', 'ALW', 1400.0),
            ('CARBENEFIT', 'Company car benefit', 'ALW', 2500.0),
            ('EKOMBENEFIT', 'Electronic communication benefit', 'ALW', 450.0),
        ]
        for code, name, category, amount in extra_lines:
            self.env['nordic.payslip.line'].create({
                'slip_id': payslip.id,
                'name': name,
                'code': code,
                'sequence': 110,
                'category': category,
                'amount': amount,
            })

        mapped_codes = {line['edag_code'] for line in payslip.get_a_melding_report_lines()}

        self.assertTrue({
            'sickPay',
            'parentalPay',
            'carePay',
            'shiftAllowance',
            'offshoreAllowance',
            'companyCarBenefit',
            'electronicCommunicationBenefit',
        }.issubset(mapped_codes))

    def test_hr_user_only_sees_records_in_allowed_companies(self):
        date_from_one, date_to_one = self._month_range(0)
        date_from_two, date_to_two = self._month_range(1)
        company_one_payslip = self._create_company_scoped_payslip(self.company, date_from_one, date_to_one)
        company_two_payslip = self._create_company_scoped_payslip(self.other_company, date_from_two, date_to_two)
        company_one_a_melding = self._create_a_melding(self.company, date_from_one, date_to_one)
        company_two_a_melding = self._create_a_melding(self.other_company, date_from_two, date_to_two)

        visible_payslips = self.env['nordic.payslip'].with_user(self.hr_limited_user).search([])
        visible_a_meldings = self.env['nordic.a.melding'].with_user(self.hr_limited_user).search([])

        self.assertIn(company_one_payslip, visible_payslips)
        self.assertNotIn(company_two_payslip, visible_payslips)
        self.assertIn(company_one_a_melding, visible_a_meldings)
        self.assertNotIn(company_two_a_melding, visible_a_meldings)

    def test_compute_sheet_uses_company_specific_aga_rate_override(self):
        self.env['nordic.aga.rate'].create({
            'company_id': self.reporting_company.id,
            'zone': '1',
            'rate': 10.0,
        })
        payslip = self._create_payslip()
        payslip.compute_sheet()

        lines_by_code = {line.code: line for line in payslip.line_ids}
        self.assertAlmostEqual(lines_by_code['AGA'].amount, 5000.0, places=2)
        self.assertAlmostEqual(payslip.total_employer_cost, 55000.0, places=2)

    def test_payslip_state_must_change_via_actions(self):
        payslip = self._create_payslip()

        with self.assertRaises(UserError):
            payslip.write({'state': 'verify'})

        payslip.action_submit_for_verification()
        self.assertEqual(payslip.state, 'verify')
        payslip.action_mark_done()
        self.assertEqual(payslip.state, 'done')
        payslip.action_cancel()
        self.assertEqual(payslip.state, 'cancel')
        payslip.action_reset_to_draft()
        self.assertEqual(payslip.state, 'draft')

    def test_payslip_workflow_actions_are_audited(self):
        payslip = self._create_payslip()
        mail_message = self.env['mail.message']
        initial_message_count = mail_message.search_count([
            ('model', '=', 'nordic.payslip'),
            ('res_id', '=', payslip.id),
        ])

        payslip.action_submit_for_verification()

        self.assertGreater(mail_message.search_count([
            ('model', '=', 'nordic.payslip'),
            ('res_id', '=', payslip.id),
        ]), initial_message_count)

    def test_payslip_done_requires_verification_first(self):
        payslip = self._create_payslip()

        with self.assertRaises(UserError):
            payslip.action_mark_done()

    def test_a_melding_generation_rejects_multiple_payslips_for_same_employee(self):
        date_from, date_to = self._month_range(2)
        first_payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        second_payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, first_payslip.date_from, first_payslip.date_to)

        with self.assertRaises(UserError):
            report.action_generate_xml()

    def test_a_melding_generation_rejects_invalid_line_semantics(self):
        date_from, date_to = self._month_range(2)
        payslip = self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to)
        payslip.action_submit_for_verification()
        payslip.line_ids.filtered(lambda line: line.code == 'TAX').write({'amount': 12250.0})
        payslip.action_mark_done()
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)

        with self.assertRaises(UserError):
            report.action_generate_xml()

    def test_a_melding_state_must_change_via_actions(self):
        date_from, date_to = self._month_range(2)
        report = self._create_a_melding(self.reporting_company, date_from, date_to)

        with self.assertRaises(UserError):
            report.write({'state': 'sent'})

    def test_a_melding_feedback_processing_sets_structured_state_and_lines(self):
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)
        mail_message = self.env['mail.message']

        report.action_generate_xml()
        generated_message_count = mail_message.search_count([
            ('model', '=', 'nordic.a.melding'),
            ('res_id', '=', report.id),
        ])

        report.action_mark_sent()
        report.feedback_xml_file = base64.b64encode(b'''<?xml version="1.0" encoding="UTF-8"?>
<A03Feedback>
  <Reference>A03-TEST-001</Reference>
  <Messages>
    <Message>
      <Severity>Guideline</Severity>
      <Code>MAGNET-001</Code>
      <Location>Oppgave[1]</Location>
      <Description>Check fixed salary mapping.</Description>
    </Message>
  </Messages>
  <Payments>
    <Payment type="withholding_tax">
      <Amount>12250.0</Amount>
      <AccountNumber>76940524802</AccountNumber>
      <KID>123456789</KID>
      <Description>Withholding tax payment</Description>
    </Payment>
  </Payments>
</A03Feedback>''')
        report.feedback_xml_filename = 'a03-feedback.xml'
        report.action_process_feedback_xml()

        self.assertEqual(report.state, 'accepted')
        self.assertTrue(report.feedback_processed_on)
        self.assertEqual(report.feedback_reference, 'A03-TEST-001')
        self.assertEqual(len(report.feedback_line_ids), 1)
        self.assertEqual(report.feedback_line_ids.severity, 'guideline')
        self.assertEqual(len(report.payment_line_ids), 1)
        self.assertEqual(report.payment_line_ids.payment_type, 'withholding_tax')
        self.assertGreater(mail_message.search_count([
            ('model', '=', 'nordic.a.melding'),
            ('res_id', '=', report.id),
        ]), generated_message_count)

    def test_a_melding_feedback_processing_can_reject_submission(self):
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)
        report.action_generate_xml()
        report.action_mark_sent()
        report.feedback_xml_file = base64.b64encode(b'''<?xml version="1.0" encoding="UTF-8"?>
<A03Feedback>
  <Reference>A03-TEST-002</Reference>
  <Messages>
    <Message>
      <Severity>Rejection</Severity>
      <Code>EDAG-400</Code>
      <Location>Oppgave[1]</Location>
      <Description>Rejected by business rule.</Description>
    </Message>
  </Messages>
</A03Feedback>''')
        report.feedback_xml_filename = 'a03-rejection.xml'

        report.action_process_feedback_xml()

        self.assertEqual(report.state, 'rejected')
        self.assertEqual(report.feedback_line_ids.severity, 'rejection')

    def test_a_melding_feedback_processing_requires_sent_state_first(self):
        date_from, date_to = self._month_range(2)
        report = self._create_a_melding(self.reporting_company, date_from, date_to)
        report.feedback_xml_file = base64.b64encode(b'<A03Feedback/>')
        report.feedback_xml_filename = 'feedback.xml'

        with self.assertRaises(UserError):
            report.action_process_feedback_xml()

    def test_a_melding_replacement_submission_requires_reference(self):
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to, submission_type='replacement')

        with self.assertRaises(UserError):
            report.action_generate_xml()

    def test_a_melding_replacement_submission_auto_links_latest_prior_submission(self):
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        baseline = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)
        baseline.action_generate_xml()
        baseline.with_context(allow_state_transition=True).write({
            'state': 'sent',
            'sent_on': fields.Datetime.now(),
            'external_submission_id': 'SUB-BASE-001',
        })

        amendment = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to, submission_type='replacement')

        self.assertEqual(amendment.amends_report_id, baseline)
        self.assertEqual(amendment.replacement_for_reference, 'SUB-BASE-001')
        amendment.action_generate_xml()
        self.assertEqual(amendment.state, 'generated')

    def test_a_melding_correction_submission_auto_links_using_report_reference(self):
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        baseline = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)
        baseline.action_generate_xml()
        baseline.with_context(allow_state_transition=True).write({
            'state': 'accepted',
            'feedback_reference': 'A03-BASE-001',
        })

        amendment = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to, submission_type='correction')

        self.assertEqual(amendment.amends_report_id, baseline)
        self.assertEqual(amendment.correction_for_reference, 'A03-BASE-001')

    def test_a_melding_switching_back_to_ordinary_clears_amendment_chain(self):
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        baseline = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)
        baseline.action_generate_xml()
        baseline.with_context(allow_state_transition=True).write({
            'state': 'sent',
            'external_submission_id': 'SUB-BASE-002',
        })
        amendment = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to, submission_type='replacement')

        amendment.write({'submission_type': 'ordinary'})

        self.assertFalse(amendment.amends_report_id)
        self.assertFalse(amendment.replacement_for_reference)
        self.assertFalse(amendment.correction_for_reference)

    def test_a_melding_rejects_future_period_beyond_two_months(self):
        date_from, date_to = self._month_range(3)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)

        with self.assertRaises(UserError):
            report.action_generate_xml()

    def test_a_melding_late_submission_requires_reason(self):
        date_from, date_to = self._month_range(-1)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)

        with self.assertRaises(UserError):
            report.action_generate_xml()

        report.late_submission_reason = 'Recovered corrected payroll input after deadline.'
        report.action_generate_xml()
        self.assertEqual(report.state, 'generated')

    def test_a_melding_submit_to_altinn_uses_configured_transport(self):
        self._configure_altinn_company()
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)
        report.action_generate_xml()

        token_response = self._mock_response({'access_token': 'token-123'})
        submit_response = self._mock_response({'submissionId': 'SUB-001', 'receiptId': 'REC-001', 'status': 'pending', 'message': 'Submitted'})
        with patch('odoo.addons.nordic_payroll.models.a_melding.requests.post', side_effect=[token_response, submit_response]) as mocked_post:
            report.action_submit_to_altinn()

        self.assertEqual(report.state, 'sent')
        self.assertEqual(report.external_submission_id, 'SUB-001')
        self.assertEqual(report.altinn_receipt_reference, 'REC-001')
        self.assertEqual(report.receipt_status, 'pending')
        self.assertEqual(mocked_post.call_count, 2)
        submit_call = mocked_post.call_args_list[1]
        self.assertEqual(submit_call.kwargs['headers']['Authorization'], 'Bearer token-123')
        self.assertTrue(report.idempotency_key)
        self.assertEqual(submit_call.kwargs['headers']['idempotencyKey'], report.idempotency_key)

    def test_a_melding_official_transport_profile_blocks_legacy_xml_submission(self):
        self._configure_official_transport_company()
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)
        report.action_generate_xml()

        self.assertEqual(report.transport_contract_status, 'validated')
        with self.assertRaises(UserError):
            report.action_submit_to_altinn()

    def test_a_melding_receipt_polling_processes_feedback_xml(self):
        self._configure_altinn_company()
        date_from, date_to = self._month_range(2)
        payslip = self._finalize_payslip(self._create_payslip(date_from=date_from, date_to=date_to, payment_date=date_to))
        report = self._create_a_melding(self.reporting_company, payslip.date_from, payslip.date_to)
        report.action_generate_xml()
        report.action_mark_sent()
        report.write({'external_submission_id': 'SUB-002'})

        token_response = self._mock_response({'access_token': 'token-123'})
        receipt_response = self._mock_response({
            'receiptStatus': 'available',
            'receiptId': 'REC-002',
            'feedbackXml': base64.b64encode(b'''<?xml version="1.0" encoding="UTF-8"?>
<A03Feedback>
  <Reference>A03-TEST-003</Reference>
  <Messages>
    <Message>
      <Severity>Guideline</Severity>
      <Code>MAGNET-003</Code>
      <Location>Oppgave[1]</Location>
      <Description>Receipt downloaded.</Description>
    </Message>
  </Messages>
</A03Feedback>''').decode('ascii'),
            'message': 'Receipt ready',
        })
        with patch('odoo.addons.nordic_payroll.models.a_melding.requests.post', return_value=token_response), patch('odoo.addons.nordic_payroll.models.a_melding.requests.get', return_value=receipt_response):
            report.action_poll_altinn_receipt()

        self.assertEqual(report.state, 'accepted')
        self.assertEqual(report.receipt_status, 'processed')
        self.assertEqual(report.feedback_reference, 'A03-TEST-003')
        self.assertTrue(report.receipt_xml_file)

    def test_unapproved_structure_cannot_be_used_for_non_draft_payslip(self):
        unapproved_structure = self.env['nordic.payroll.structure'].create({
            'name': 'Unapproved Test Structure',
            'rule_ids': [(6, 0, self.structure.rule_ids.ids)],
        })
        date_from, date_to = self._month_range(0)
        payslip = self.env['nordic.payslip'].create({
            'employee_id': self.employee.id,
            'struct_id': unapproved_structure.id,
            'date_from': date_from,
            'date_to': date_to,
            'payment_date': date_to,
            'run_number': 1,
        })

        with self.assertRaises(UserError):
            payslip.with_context(force_production_structure_approval=True).compute_sheet()

        with self.assertRaises(UserError):
            payslip.action_submit_for_verification()

    def test_payroll_structure_approval_is_tracked(self):
        structure = self.env['nordic.payroll.structure'].create({
            'name': 'Approval Audit Structure',
            'rule_ids': [(6, 0, self.structure.rule_ids.ids)],
        })
        mail_message = self.env['mail.message']
        initial_message_count = mail_message.search_count([
            ('model', '=', 'nordic.payroll.structure'),
            ('res_id', '=', structure.id),
        ])

        structure.action_approve_for_production()

        self.assertTrue(structure.approved_for_production)
        self.assertEqual(structure.approved_by, self.env.user)
        self.assertGreater(mail_message.search_count([
            ('model', '=', 'nordic.payroll.structure'),
            ('res_id', '=', structure.id),
        ]), initial_message_count)

    def test_hr_user_cannot_approve_payroll_structure(self):
        structure = self.env['nordic.payroll.structure'].create({
            'name': 'Restricted Approval Structure',
            'rule_ids': [(6, 0, self.structure.rule_ids.ids)],
        })

        with self.assertRaises(AccessError):
            structure.with_user(self.hr_limited_user).action_approve_for_production()

    def test_salary_rule_rejects_invalid_python_code(self):
        with self.assertRaises(ValidationError):
            self.env['nordic.salary.rule'].create({
                'name': 'Broken Python Rule',
                'code': 'BROKEN',
                'category': 'ALW',
                'amount_select': 'python',
                'amount_python_compute': 'result = (',
            })

    def test_salary_rule_rejects_python_without_result_assignment(self):
        with self.assertRaises(ValidationError):
            self.env['nordic.salary.rule'].create({
                'name': 'Missing Result Rule',
                'code': 'MISS_RESULT',
                'category': 'ALW',
                'amount_select': 'python',
                'amount_python_compute': "basic = rules.get('BASIC', 0.0)",
            })

    def test_hr_user_cannot_modify_salary_rule_definitions(self):
        rule = self.structure.rule_ids.filtered(lambda current_rule: current_rule.code == 'BASIC')[:1]

        with self.assertRaises(AccessError):
            rule.with_user(self.hr_limited_user).write({'amount_python_compute': 'result = employee.nordic_wage * 1.1'})

    def test_salary_rule_formula_edits_are_tracked(self):
        rule = self.structure.rule_ids.filtered(lambda current_rule: current_rule.code == 'BASIC')[:1]
        mail_message = self.env['mail.message']
        initial_message_count = mail_message.search_count([
            ('model', '=', 'nordic.salary.rule'),
            ('res_id', '=', rule.id),
        ])

        rule.write({'amount_python_compute': 'result = employee.nordic_wage + 100.0'})

        self.assertGreater(mail_message.search_count([
            ('model', '=', 'nordic.salary.rule'),
            ('res_id', '=', rule.id),
        ]), initial_message_count)
