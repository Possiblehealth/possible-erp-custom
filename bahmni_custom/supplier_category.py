from openerp.osv import fields, osv
import logging


_logger = logging.getLogger(__name__)
class supplier_category(osv.osv):
    _name = "x.product.supplier.category"
    _description = "Supplier Categories for Batch Numbers"
    _columns = {
        'x_name': fields.char('Supplier Category', required=True),
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            _logger.error("Sandeep");
            _logger.error(record);
            name = record.x_name
            res.append((record.id,name))
        return res


supplier_category()


class stock_production_lot(osv.osv):

    _name = 'stock.production.lot'
    _inherit = 'stock.production.lot'

    _columns = {
        'x_supplier_category':fields.many2one('x.product.supplier.category',required='True',string ='Supplier Category')
    }


stock_production_lot()
