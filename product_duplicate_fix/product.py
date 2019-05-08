# -*- encoding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class product_product(osv.osv):
    _inherit = 'product.product'

    def _check_low_stock(self, cr, uid, ids, field_name, arg, context=None):
        result = {}.fromkeys(ids, False)
        for product in self.browse(cr, uid, ids, context=context):
            orderpoints = sorted(product.orderpoint_ids, key=lambda orderpoint: orderpoint.product_min_qty, reverse=True)
            if (len(orderpoints) > 0 and product.virtual_available < orderpoints[0].product_min_qty):
                result[product.id] = True
            else:
                result[product.id] = False
        return result

    def _search_low_stock(self, cr, uid, obj, name, args, context=None):
        ids = set()
        context = context or {}
        location = context.get('location', False)
        location_condition = ""
        if(location):
            location_condition = "where location_id=" + str(location)
        for cond in args:
            cr.execute("select product_id from stock_warehouse_orderpoint " + location_condition)
            product_ids = set(id[0] for id in cr.fetchall())
            for product in self.browse(cr, uid, list(product_ids), context=context):
                orderpoints = sorted(product.orderpoint_ids, key=lambda orderpoint: orderpoint.product_min_qty, reverse=True)
                if (len(orderpoints) > 0 and product.virtual_available < orderpoints[0].product_min_qty):
                    ids.add(product.id)
        if ids:
            return [('id', 'in', tuple(ids))]
        return [('id', '=', '0')]

    _columns = {
        'low_stock': fields.function(_check_low_stock, type="boolean",
                                     string="Low Stock", fnct_search=_search_low_stock),
        }
        
    def create(self, cr, uid, vals, context=None):
        res = super(product_product,self).create(cr, uid, vals, context=context)
        user_obj = self.pool.get('res.users').browse(cr,uid, uid, context)
        if not user_obj.create_product:
            raise osv.except_osv('Error!',"You don't have right to create or duplicate products.Please contact your System Administrator.")      
        return res
        


