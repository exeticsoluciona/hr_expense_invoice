# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    factura_id = fields.Many2one('account.move', string="Factura", domain="[('state','=','posted'), ('type','in',['in_invoice'])]", readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, check_company=True)

    @api.onchange('factura_id')
    def _onchange_factura_id(self):
        if self.factura_id:
            self.account_id = self.factura_id.partner_id.property_account_payable_id
            self.quantity = 1
            self.unit_amount = self.factura_id.amount_total
            self.reference = self.factura_id.name

    def _get_account_move_line_values(self):
        result = super(HrExpense, self)._get_account_move_line_values()
        for k in result.keys():
            expense = self.browse(k)
            if expense.factura_id:
                for line in result[k]:
                    if 'date_maturity' not in line:
                        line['partner_id'] = expense.factura_id.partner_id.id
        return result

class HrExpenseSheetRegisterPaymentWizard(models.TransientModel):
    _inherit = 'hr.expense.sheet.register.payment.wizard'

    def expense_post_payment(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        sheet = self.env['hr.expense.sheet'].browse(active_ids)

        for linea_gasto in sheet.account_move_id.line_ids.filtered(lambda r: r.account_id.user_type_id.type == 'payable' and not r.reconciled):
            for linea_factura in sheet.expense_line_ids.factura_id.line_ids.filtered(lambda r: r.account_id.user_type_id.type == 'payable' and not r.reconciled):
                if linea_gasto.partner_id.id == linea_factura.partner_id.id and ( linea_gasto.debit == linea_factura.credit or linea_gasto.credit - linea_factura.debit ):
                    (linea_gasto | linea_factura).reconcile()

        return super(HrExpenseSheetRegisterPaymentWizard, self).expense_post_payment()
