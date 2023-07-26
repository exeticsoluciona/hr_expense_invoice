# -*- encoding: utf-8 -*-

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

import logging

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    factura_id = fields.Many2one('account.move', string="Factura", domain="[('state','=','posted'), ('invoice_date', '!=', False)]", readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, check_company=True)

    @api.onchange('factura_id')
    def _onchange_factura_id(self):
        if self.factura_id:
            self.quantity = 1
            self.unit_amount = self.factura_id.amount_total
            self.total_amount = self.factura_id.amount_total
            self.reference = self.factura_id.name
            self.tax_ids = [(5, False, False)]
            self.currency_id = self.factura_id.currency_id

    def _get_account_move_line_values(self):
        result = super(HrExpense, self)._get_account_move_line_values()
        for k in result.keys():
            expense = self.browse(k)
            if expense.factura_id:
                for line in result[k]:
                    if 'date_maturity' not in line:
                        line['partner_id'] = expense.factura_id.partner_id.id
        return result
    
class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'
    
    def es_pagable(self, cuenta):
        if 'user_type_id' in cuenta.fields_get():
            return True if cuenta.user_type_id.type == 'payable' else False
        else:
            return True if cuenta.account_type == 'liability_payable' else False
    
    # Evitar que se marque como pagado cuando se concilia la factura
    def set_to_paid(self):
        pendientes = self.account_move_id.line_ids.filtered(lambda r: self.es_pagable(r.account_id) and not r.reconciled)
        if len(pendientes) == 0:
            self.write({'state': 'done'})

    def action_sheet_move_create(self):
        res = super(HrExpenseSheet, self).action_sheet_move_create()
        rounding = self.company_id.currency_id.rounding
        
        lineas_por_pagar = self.expense_line_ids.factura_id.line_ids.filtered(lambda r: self.es_pagable(r.account_id) and not r.reconciled)
        gastos = self.expense_line_ids

        lineas = []
        for p in lineas_por_pagar:
            lineas.append(Command.create({
                'name': p.name,
                'ref': p.ref,
                'partner_id': p.partner_id.id,
                'debit': p.credit,
                'credit': 0,
                'account_id': p.account_id.id,
            }))

        for g in gastos:
            lineas.append(Command.create({
                'name': g.name,
                'ref': g.reference,
                'partner_id': g.employee_id.sudo().address_home_id.commercial_partner_id.id,
                'debit': 0,
                'credit': g.total_amount,
                'account_id': g.account_id.id,
            }))

        diario = self.env['account.journal'].search([('type','=','general')])
        movimiento = self.env['account.move'].create({
            'journal_id': diario[0].id,
            'date': self.accounting_date,
            'ref': 'Conciliacion manual: '+self.name,
            'move_type': 'entry',
            'line_ids': lineas
        })
        movimiento._post()
        
        i = 0
        for l in lineas_por_pagar:
            (l | movimiento.line_ids[i]).reconcile()
            i += 1

        return res

