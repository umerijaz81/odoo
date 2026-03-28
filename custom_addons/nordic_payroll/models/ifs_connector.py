# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class IfsConnector(models.AbstractModel):
    _name = 'nordic.ifs.connector'
    _description = 'IFS Cloud REST API Connector'

    def _get_ifs_config(self):
        # Ideally stored in ir.config_parameter or a concrete settings model
        return {
            'base_url': self.env['ir.config_parameter'].sudo().get_param('nordic.ifs.base_url', 'https://ifs-test.eidsiva.no/main/ifsapplications/projection/v1'),
            'client_id': self.env['ir.config_parameter'].sudo().get_param('nordic.ifs.client_id'),
            'client_secret': self.env['ir.config_parameter'].sudo().get_param('nordic.ifs.client_secret'),
        }

    def call_ifs_api(self, endpoint, method='GET', data=None):
        config = self._get_ifs_config()
        url = f"{config['base_url']}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            # Add OAuth2 token logic here
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            else:
                response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            _logger.error(f"IFS API Error at {endpoint}: {str(e)}")
            return False

    def sync_employees(self):
        # ... (implementation from previous turn)
        return True

    def post_expenses_to_ifs(self, expense_ids):
        """Epic-02: Push approved expenses to IFS for reimbursement."""
        endpoint = "ExpenseHandling.svc/PostClaims"
        expenses = self.env['hr.expense'].browse(expense_ids)
        data = {
            'Claims': [{
                'EmployeeID': exp.employee_id.nordic_ssn,
                'Amount': exp.total_amount,
                'Currency': exp.currency_id.name,
                'Description': exp.name,
            } for exp in expenses]
        }
        return self.call_ifs_api(endpoint, method='POST', data=data)

    def post_journal_to_ifs(self, move_id):
        """Epic-02: Push finalized payroll accounting entries to IFS."""
        endpoint = "Financials.svc/PostJournalEntry"
        move = self.env['account.move'].browse(move_id)
        data = {
            'VoucherDate': move.date.strftime('%Y-%m-%d'),
            'VoucherType': 'PAY',
            'Lines': [{
                'Account': line.account_id.code,
                'Debit': line.debit,
                'Credit': line.credit,
                'Text': line.name,
            } for line in move.line_ids]
        }
        return self.call_ifs_api(endpoint, method='POST', data=data)
