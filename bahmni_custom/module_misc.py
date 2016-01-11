import logging
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class account_invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"
    _order = "id"
    def _get_supplier_ref(self, cr, uid, ids, name, args, context=None):
        res = {}
        for account_invoice in self.browse(cr, uid, ids):
            res[account_invoice.id]=account_invoice.partner_id.supplier_reference
        return res

    _columns={
        'supplier_reference': fields.function(_get_supplier_ref, type='char', string='Supplier-Reference(Internal)',),
        }
account_invoice()

class purchase_order(osv.osv):

    _name = "purchase.order"
    _inherit = "purchase.order"
    _order = "id"

    def _get_supplier_ref(self, cr, uid, ids, name, args, context=None):
        res = {}
        for purchase_order in self.browse(cr, uid, ids):
            res[purchase_order.id]=purchase_order.partner_id.supplier_reference
        return res

    _columns={
        'supplier_reference': fields.function(_get_supplier_ref, type='char', string='Supplier-Reference(Internal)',),
        }
purchase_order()

class res_partner(osv.osv):
    _name = "res.partner"
    _inherit = "res.partner"
    _order = "id"
    _columns={
        'supplier_reference':fields.char('Supplier-Reference(Internal)'),
        }
res_partner()

class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'
    def _get_product_min_max_qty(self, cr, uid, ids, name, args, context=None):
        res={}
        context = context or {}
        location = context.get('location', False)
        for product in self.browse(cr, uid, ids, context=context):
            orderpoints={}
            if (location>0):
                ops = product.orderpoint_ids
                for op in ops:
                    if (op.location_id == location):
                        orderpoints = op
                if not orderpoints:
                    orderpoints = sorted(product.orderpoint_ids, key=lambda orderpoint: orderpoint.product_min_qty, reverse=True)
            else:
                orderpoints = sorted(product.orderpoint_ids, key=lambda orderpoint: orderpoint.product_min_qty, reverse=True)
            if (len(orderpoints) > 0):
                res[product.id] = "Min - "+str(orderpoints[0].product_min_qty)+" Max - "+str(orderpoints[0].product_max_qty)
            else:
                res[product.id] = "Not Defined"
        return res
    _columns={
        'product_min_max': fields.function(_get_product_min_max_qty, type='char', string='Product Min - Max Quantity',),
        'antibiotic':fields.boolean('Antibiotic'),
        }
    _default={
        'antibiotic':False
    }
product_product()

class stock_move(osv.osv):
    _name = "stock.move"
    _inherit = "stock.move"
    _order = "id"

    def _get_suppliercat_id(self, cr, uid, ids, name, args, context=None):
        res = {}
        for stock_move in self.browse(cr, uid, ids):
            supplier_obj=self.pool.get("stock.production.lot")
            suppliercat=supplier_obj.browse(cr,uid,stock_move.prodlot_id.id)
            category=self.pool.get("x_product_supplier_category").browse(cr,uid,suppliercat.x_supplier_category)
            res[stock_move.id] = suppliercat.x_supplier_category.x_name
        return res

    def _get_prod_internal_reference(self, cr, uid, ids, name, args, context=None):
        res = {}
        for stock_move in self.browse(cr, uid, ids):
            internal_obj=self.pool.get("product.product")
            internal_ref=internal_obj.browse(cr,uid,stock_move.product_id.id)
            res[stock_move.id] = internal_ref.default_code
        return res
    _columns={
        'suppliercat_name': fields.function(_get_suppliercat_id, type='char', string='Supplier Category',),
        'prod_internal_reference': fields.function(_get_prod_internal_reference, type='char', string='Internal Reference',),
        }
stock_move()

