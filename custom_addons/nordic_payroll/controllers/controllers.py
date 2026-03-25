# from odoo import http


# class NordicPayroll(http.Controller):
#     @http.route('/nordic_payroll/nordic_payroll', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/nordic_payroll/nordic_payroll/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('nordic_payroll.listing', {
#             'root': '/nordic_payroll/nordic_payroll',
#             'objects': http.request.env['nordic_payroll.nordic_payroll'].search([]),
#         })

#     @http.route('/nordic_payroll/nordic_payroll/objects/<model("nordic_payroll.nordic_payroll"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('nordic_payroll.object', {
#             'object': obj
#         })

