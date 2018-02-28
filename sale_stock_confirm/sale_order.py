# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools import float_compare
from openerp.tools.translate import _

    
class sale_order(osv.osv):
    _inherit = 'sale.order'
        
    def action_wait(self, cr, uid, ids, context=None):
        context = context or {}
        lang = context.get('lang',False)
        for o in self.browse(cr, uid, ids):
            if o.partner_id:
                lang = o.partner_id.lang
            context.update({'lang': lang, 'partner_id': o.partner_id.id})
            context.update({'shop': o.shop_id.id if o.shop_id else False,
                            'pricelist': o.pricelist_id.id if o.pricelist_id else False})
            prds_not_available = []
            for o_line in o.order_line:
                available_qty = self.pool.get('product.product').browse(cr, uid, o_line.product_id.id, context=context).virtual_available
                 #check for unavailable products
                if (int(float_compare(available_qty, o_line.product_uom_qty, precision_rounding=o_line.product_uom.rounding))==-1)\
                    and o_line.product_id.type=='product' and o_line.product_id.procure_method=='make_to_stock':
                    prds_not_available.append(o_line.product_id.name+' | Available Qty : %.2f %s'%(available_qty if available_qty>=0 else 0, o_line.product_uom.name)) 
           
            prds_not_available = [str(i)+ '. '+x for i,x in enumerate(prds_not_available,1)]
            if prds_not_available:
                warn_msg = _('You can not confirm this order, '
                             'as following products are not available in stock\n%s'%('\n'.join(prds_not_available),))
                raise osv.except_osv(_("Not enough stock ! : "), warn_msg)
            else:
                if not o.order_line:
                    raise osv.except_osv(_('Error!'),_('You cannot confirm a sales order which has no line.'))
                noprod = self.test_no_product(cr, uid, o, context)
                if (o.order_policy == 'manual') or noprod:
                    self.write(cr, uid, [o.id], {'state': 'manual', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
                else:
                    self.write(cr, uid, [o.id], {'state': 'progress', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
                self.pool.get('sale.order.line').button_confirm(cr, uid, [x.id for x in o.order_line])
        return True
