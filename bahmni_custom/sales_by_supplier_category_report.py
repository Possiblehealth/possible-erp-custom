from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists
import logging

class sales_by_supplier_category_report(osv.osv):
    _name = 'sale_supplier_category.report'
    _description = 'Sale Supplier Category Name'
    _auto = False
    _order = 'id desc'
    _columns={
        'name_template':fields.text('Name',readonly=True),
        'date_order':fields.date('Order Date',readonly=True),
        'product_uom_qty':fields.float('Quantity',readonly=True),
        'amount_total':fields.float('Total Amount',readonly=True),
        'x_name':fields.text('Supplier Category',readonly=True)
    }

    def init(self,cr):
        drop_view_if_exists(cr,'sale_supplier_category_report')
        cr.execute("""
        create or replace view sale_supplier_category_report AS
        (select row_number() OVER (order by sm.write_date) as id,pp.name_template,
  sm.product_qty as product_uom_qty,sm.create_date as date_order,
  pt.list_price*sm.product_qty as amount_total,spl.name,xpsc.x_name
from stock_move sm inner join product_product pp
    on sm.product_id=pp.id and sm.state='done' AND (sm.location_id=27)
LEFT JOIN
product_template pt on pt.id = pp.product_tmpl_id
  LEFT JOIN
  stock_production_lot spl on spl.id = sm.prodlot_id
  LEFT JOIN
  x_product_supplier_category xpsc on xpsc.id = spl.x_supplier_category)
        """)
    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))
sales_by_supplier_category_report()
