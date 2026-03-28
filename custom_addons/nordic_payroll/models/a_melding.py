# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
import logging

_logger = logging.getLogger(__name__)

class AMelding(models.Model):
    _name = 'nordic.a.melding'
    _description = 'Norwegian A-melding Reporting'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('sent', 'Sent to Altinn'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft')

    xml_file = fields.Binary(string='A-melding XML')
    xml_filename = fields.Char(string='XML Filename')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('nordic.a.melding') or 'AM/' + fields.Date.today().strftime('%Y/%m')
        return super().create(vals_list)

    def action_generate_xml(self):
        """Aggregate Payslips and generate A-melding XML."""
        self.ensure_one()
        Payslips = self.env['nordic.payslip'].search([
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done')
        ])
        
        if not Payslips:
            return False
            
        # Basic XML aggregation logic
        xml_lines = []
        xml_lines.append("<?xml version='1.0' encoding='UTF-8'?>")
        xml_lines.append("<EDAG-M xmlns='http://www.skatteetaten.no/xsd/edag/v2'>")
        xml_lines.append(f"<Leveranse><Maaned>{self.date_from.strftime('%Y-%m')}</Maaned>")
        
        for slip in Payslips:
            xml_lines.append(f"<Oppgave><Fodselsnummer>{slip.employee_id.nordic_ssn or ''}</Fodselsnummer>")
            for line in slip.line_ids:
                if line.amount != 0:
                    xml_lines.append(f"<Inntektslinje><Type>{line.code}</Type><Belop>{line.amount}</Belop></Inntektslinje>")
            xml_lines.append("</Oppgave>")
            
        xml_lines.append("</Leveranse></EDAG-M>")
        
        xml_content = "\n".join(xml_lines)
        self.write({
            'xml_file': base64.b64encode(xml_content.encode('utf-8')),
            'xml_filename': f"a-melding-{self.date_from.strftime('%Y-%m')}.xml",
            'state': 'generated'
        })
        return True
