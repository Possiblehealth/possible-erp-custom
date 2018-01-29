# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class stock_production_lot(osv.osv):

    _name = 'stock.production.lot'
    _inherit = 'stock.production.lot'

    _columns = {
        'x_supplier_category':fields.many2one('x.product.supplier.category',required='True',
                                              string ='Supplier Category'),
        'partner_id': fields.many2one('res.partner', string='Supplier Name')
    }


stock_production_lot()