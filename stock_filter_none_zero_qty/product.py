# -*- coding: utf-8 -*-
##############################################################################
#
#    Stock Filter for Zero Quantity for Bahmni OpenERP
#    Copyright (C) 2017 Ajeenckya Gadewar (<https://www.satvix.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import fields,orm
from tools.translate import _
import decimal_precision as dp


class product_product(orm.Model):
    _inherit = "product.product"

#    def _get_product_available_func(states, what):
#        def _product_available(self, cr, uid, ids, name, arg, context=None):
#            return {}.fromkeys(ids, 0.0)
#        return _product_available
#    
#    _product_qty_available = _get_product_available_func(('done',), ('in', 'out'))
#    _product_virtual_available = _get_product_available_func(('confirmed','waiting','assigned','done'), ('in', 'out'))

    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        return super(product_product,self)._product_available(cr, uid, ids, field_names=field_names, arg=arg, context=context)

    def _qty_available_search(self, cr, uid, obj, name, args, context=None):
        ops = ['>',]
        prod_ids = ()
        if not len(args):
            return []
        prod_ids = []
        for a in args:
            operator = a[1]
            value = a[2]
            if not operator in ops:
                raise orm.except_orm(_('Error !'), _('Operator %s not suported in searches for qty_available (product.product).' % operator))
            if operator == '>':
                todos = self.search(cr, uid, [], context=context)
                ids = self.read(cr, uid, todos, ['qty_available'], context=context)
                for d in ids:
                    if d['qty_available'] > 0:
                        prod_ids.append(d['id'])
        return [('id','in',tuple(prod_ids))]

    _columns = {
        'qty_available': fields.function(_product_available, fnct_search=_qty_available_search, method=True, 
            multi='qty_available',
            type='float',  digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Quantity On Hand',
            help="Current quantity of products.\n"
                 "In a context with a single Stock Location, this includes "
                 "goods stored at this Location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods stored in the Stock Location of this Warehouse, or any "
                 "of its children.\n"
                 "In a context with a single Shop, this includes goods "
                 "stored in the Stock Location of the Warehouse of this Shop, "
                 "or any of its children.\n"
                 "Otherwise, this includes goods stored in any Stock Location "
                 "with 'internal' type."),
    }
