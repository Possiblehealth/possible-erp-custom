from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists
import logging

class supplier_category_report(osv.osv):
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
        (select srl.id,pp.name_template,srl.product_uom_qty,so.create_date as date_order,so.amount_total,spl.name,xpsc.x_name from stock_move sm
        INNER JOIN
        sale_order_line srl on sm.purchase_line_id=srl.id
                             and sm.state='done' and sm.purchase_line_id is not null
                             AND sm.prodlot_id is not NULL
        LEFT JOIN
        stock_production_lot spl on spl.id = sm.prodlot_id
        LEFT JOIN
        x_product_supplier_category xpsc on xpsc.id = spl.x_supplier_category
        LEFT JOIN
        sale_order so on srl.order_id=so.id
        LEFT JOIN
        product_product pp on pp.id = sm.product_id)
        """)
    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))
supplier_category_report()
