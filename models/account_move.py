# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def crear_gasto(self, empleado_id):
        Expense = self.env['hr.expense']
        resultado = self.env['hr.expense']
        
        for f in self:
            if f.state == 'posted' and f.invoice_date:
                anteriores = Expense.search([('factura_id','=',f.id)])
            
                if len(anteriores) > 0:
                    raise ValidationError('La factura {} ya fue utilizada en otro gasto, no puede ser utilizada dos veces.'.format(f.name))
                
                productos = self.env['product.product'].search([('can_be_expensed', '=', True), '|', ('company_id', '=', False), ('company_id', '=', f.company_id.id)])
                
                if len(productos) == 0:
                    raise ValidationError('No existe productos para gastos.')
                
                values = {
                    'name': f.name,
                    'date': f.invoice_date,
                    'employee_id': empleado_id,
                    'factura_id': f.id,
                    'product_id': productos[0].id,
                };
                
                exp = Expense.create(values);
                exp._onchange_factura_id()
                resultado |= exp

        return resultado

            
class HRExpenseInvoiceCrearGasto(models.TransientModel):
    _name = 'hr.expense.invoice.crear_gasto'
    _description = 'Crear gastos desde factura'
    
    empleado_id = fields.Many2one('hr.employee', required=True)
    
    def action_crear_gasto(self):
        active_ids = self.env.context.get('active_ids')

        facturas = self.env['account.move'].browse(active_ids)
        gastos = facturas.crear_gasto(self.empleado_id.id)

        return {
            'name': _('Gasto'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'context': {'create': False},
            'view_mode': 'list,form',
            'domain': [('id', 'in', gastos.ids)],
        }
