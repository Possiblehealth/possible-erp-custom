from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists
import logging

class stock_move_inventory_report(osv.osv):
    _name = 'stock_move_inventory.report'
    _description = 'Stock Move Inventory'
    _auto = False
    _columns={
        'name_template':fields.text('Name',readonly=True),
        'date_order':fields.date('Order Date',readonly=True),
        'quantity':fields.float('Quantity',readonly=True),
            }
    def init(self,cr):
        drop_view_if_exists(cr,'stock_move_inventory_report')
        cr.execute("""
        create or replace view stock_move_inventory_report AS
  (select row_number() OVER (order by sm.write_date) as id,pp.name_template,sum(sm.product_qty) as quantity,sm.write_date as date_order from
    stock_move sm inner join product_product pp
      on sm.product_id=pp.id and sm.location_id in (select id from stock_location where name like '%BPH%')
         and sm.state='done'
  GROUP BY date_order,pp.name_template,pp.id ORDER BY pp.id , date_order)
        """)

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))
stock_move_inventory_report()

