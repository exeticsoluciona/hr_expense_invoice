# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging

class AccountMove(models.Model):
    _inherit = 'account.move'

    def crear_gasto(self):
        Expense = self.env['hr.expense']
        
        for f in self:
            anteriores = Expense.search([('factura_id','=',f.id)])
            
            if len(anteriores) == 0:
                raise ValidationError('La factura {} ya fue utilizada en otro gasto, no se puede utilizar en otro gasto.'.format(f.name))
                
            if not f.invoice_user_id.employee_id:
                raise ValidationError('Su usuario no tiene un empleado asignado; sin empleado, no se puede crear un gasto.')
            
            if f.state == 'posted' and f.invoice_date:
                productos = self.env['product.product'].search([('can_be_expensed', '=', True), '|', ('company_id', '=', False), ('company_id', '=', f.company_id.id)])
                
                values = {
                    'name': f.name,
                    'date': f.invoice_date,
                    'employee_id': f.invoice_user_id.employee_id.id,
                    'factura_id': f.id,
                    'product_id': productos[0].id,
                    'unit_amount': 0,
                    'product_uom_id': self.env['uom.uom'].search([], limit=1, order='id').id,
                };
                
                exp = Expense.create(values);
                exp._onchange_factura_id()

            
