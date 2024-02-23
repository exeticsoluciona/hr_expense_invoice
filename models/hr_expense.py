# -*- encoding: utf-8 -*-

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

import logging

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    factura_id = fields.Many2one('account.move', string="Factura", domain="[('state','=','posted'), ('move_type', '=', 'in_invoice')]", check_company=True)

    @api.onchange('factura_id')
    def _onchange_factura_id(self):
        if self.factura_id:
            if not self.product_has_cost:
                self.tax_ids = [Command.clear()]
                self.currency_id = self.factura_id.currency_id
                self.total_amount_currency = self.factura_id.amount_total
                self.currency_rate = 1 / self.factura_id.invoice_line_ids.currency_rate 
            else:
                self.factura_id = False
                return {
                    'warning': {'title': 'Producto con costo', 'message': 'No se pueden relacionar facturas cuando el producto de gasto tiene un costo. El campo de factura se ha dejado vacío.'},
                }
            
    @api.onchange('product_has_cost')
    def _onchange_product_has_cost(self):
        if self.product_has_cost:
            self.factura_id = False
            return {
                    'warning': {'title': 'Producto con costo', 'message': 'No se pueden relacionar facturas cuando el producto de gasto tiene un costo. El campo de factura se ha dejado vacío.'},
                }

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'
    
    def action_sheet_move_create(self):
        res = super(HrExpenseSheet, self).action_sheet_move_create()
        rounding = self.company_id.currency_id.rounding
        
        lineas_por_pagar = self.expense_line_ids.factura_id.line_ids.filtered(lambda l: l.account_type == 'liability_payable' and not l.reconciled)
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
                'ref': g.name,
                'partner_id': g.employee_id.sudo().work_contact_id.id,
                'debit': 0,
                'credit': g.total_amount,
                'account_id': g.account_id.id,
            }))

        diarios = self.env['account.journal'].search([('type','=','general')])
        misc = diarios.filtered(lambda r: r.code == 'MISC')
        
        diario = diarios[0]
        if len(misc) > 0:
            diario = misc[0]
            
        movimiento = self.env['account.move'].create({
            'journal_id': diario.id,
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

