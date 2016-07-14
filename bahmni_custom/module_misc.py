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

class stock_warehouse_orderpoint(osv.osv):
    _name = 'stock.warehouse.orderpoint'
    _inherit = 'stock.warehouse.orderpoint'

    _columns={
        'x_bare_minimum':fields.integer('Bare Minimum')
    }
stock_warehouse_orderpoint()

class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'

    _columns={
        'x_formulary':fields.boolean('Formulary'),
        'x_govt':fields.boolean('Govt Supply'),
        'x_low_cost_eq':fields.boolean('MOHP Essential Medicine')
        }
    _default={
        'x_formulary':False,
        'x_govt':False,
        'x_low_cost_eq':False
    }
product_template()

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
        'lab_item':fields.boolean('Lab Item'),
        'medical_item':fields.boolean('Medical Item'),
        'other_item':fields.boolean('Other Item'),
        'medicine_item':fields.boolean('Medicine')
        }
    _default={
        'antibiotic':False,
        'lab_item':False,
        'medical_item':False,
        'other_item':False,
        'medicine_item':False
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
            x_prod_supcat_cnt = self.pool.get("x_product_supplier_category").search(cr,uid,[('id' , '=', suppliercat.id)])
            if len(x_prod_supcat_cnt) > 0:
                x_prod_supcat = self.pool.get("x_product_supplier_category").browse(cr,uid,suppliercat.id)
                res[stock_move.id] = x_prod_supcat.x_name
            else:
                res[stock_move.id] = ""
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


class stock_move_split_lines_exten(osv.osv_memory):
    _name = "stock.move.split.lines"
    _description = "Stock move Split lines"
    _inherit = "stock.move.split.lines"

    def _get_product_mrp(self, cr, uid, context=None):
        context = context or {}
        tax_amount = 0
        stock_move_id = context.get('stock_move', None)
        stock_move = stock_move_id and self.pool.get('stock.move').browse(cr, uid, stock_move_id, context=context)
        return (stock_move and stock_move.purchase_line_id and stock_move.purchase_line_id.mrp) or 0.0

    def onchange_cost_price(self, cr, uid, ids, cost_price, context=None):
        cost_price = cost_price or 0.0
        product_uom = self._get_product_uom(cr, uid, context=context)
        mrp = self._get_product_mrp(cr, uid, context=context)
        return {'value': {'sale_price': self._calculate_sale_price(cr,uid,cost_price, product_uom,mrp)}}

    def _calculate_sale_price(self, cr,uid,cost_price, product_uom, mrp):
        cost_price = cost_price or 0.0
        return cost_price

    def _calculate_default_sale_price(self, cr, uid, context=None):
        cost_price = self._get_default_cost_price(cr, uid, context=context) or 0.0
        product_uom = self._get_product_uom(cr, uid, context=context)
        mrp = self._get_product_mrp(cr, uid, context=context)
        return self._calculate_sale_price(cr,uid,cost_price, product_uom,mrp)

    def _get_default_cost_price(self, cr, uid, context=None):
        context = context or {}
        tax_amount = 0
        stock_move_id = context.get('stock_move', None)
        stock_move = stock_move_id and self.pool.get('stock.move').browse(cr, uid, stock_move_id, context=context)
        if (stock_move and stock_move.purchase_line_id):
            for tax in stock_move.purchase_line_id.taxes_id:
                tax_amount = tax_amount + tax.amount

        return (stock_move and (stock_move.price_unit + (stock_move.price_unit * tax_amount))) or 0.0


    _defaults = {
        'mrp': _get_product_mrp,
        'cost_price': _get_default_cost_price,
        'sale_price': _calculate_default_sale_price
    }

stock_move_split_lines_exten()

class stock_production_lot(osv.osv):

    _name = 'stock.production.lot'
    _inherit = 'stock.production.lot'

    _columns = {
        'x_supplier_category':fields.many2one('x.product.supplier.category',required='True',string ='Supplier Category')
    }


stock_production_lot()