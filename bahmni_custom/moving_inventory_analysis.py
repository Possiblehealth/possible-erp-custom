from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class stock_move_inventory_report(osv.osv):
    _name = 'stock_move_inventory.report'
    _description = 'Stock Move Inventory'
    _auto = False
    _columns={
        'name':fields.text('Name',readonly=True),
        'date_order':fields.date('Order Date',readonly=True),
        'quantity':fields.float('Quantity',readonly=True),
        'id':fields.integer('Product ID',readonly=True),
            }
    _mainLocationId=None
    def init(self,cr):
        cr.execute("SELECT value FROM custom_report_props WHERE name='mainLocationId'")
        self._mainLocationId = cr.fetchall()[0][0]
        drop_view_if_exists(cr,'stock_move_inventory_report')
        cr.execute("""
        create or replace view stock_move_inventory_report AS(select row_number() OVER (order by sm.write_date) as id,pp.name_template as name,
  sum(sm.product_qty) as quantity,sm.write_date::timestamp::date as date_order,
sm.location_dest_id, sm.location_id
from
  stock_move sm inner join product_product pp
    on sm.product_id=pp.id
       and sm.state='done'
GROUP BY sm.write_date,pp.name_template,pp.id,sm.location_dest_id,sm.location_id ORDER BY pp.id , date_order)
        """)

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

    def autocomplete_data(self, cr, uid, model, searchText,
        context=None):
        productsIds = self.pool.get('product.product').search(cr, uid, [('name_template', 'ilike', searchText)],limit=10, context=context)
        res = [];
        if(productsIds):
            for product in productsIds:
                line=self.pool.get('product.product').browse(cr, uid,product ,context=context)
                res.append({'name':line.name,'id':line.name})
        return res;

    def chart_d3_get_data(self, cr, uid, xaxis, yaxis, domain, group_by, options,
        product, start_date, end_date, context=None):
        if not product:
            raise osv.except_osv(('Error'), ('Please choose a product to show the graph'))
        if not start_date:
            raise osv.except_osv(('Error'), ('Please choose a start date to show the graph'))
        if not end_date:
            raise osv.except_osv(('Error'), ('Please choose a end date to show the graph'))

        cr.execute("SELECT name,sum(CASE WHEN sm.location_dest_id = " + self._mainLocationId  + """ THEN 1*quantity
            ELSE -1*quantity
            END) as qty
            from stock_move_inventory_report sm
            where name = '""" + product +"""' and
            (location_dest_id=""" + self._mainLocationId  + " or location_id=" + self._mainLocationId  + ") and date_order<'" + start_date + """'
            GROUP BY sm.name""")
        rows = cr.fetchall()
        startingQty=0;
        for row in rows:
            startingQty=row[1]
        cr.execute("select product_min_qty,product_max_qty from stock_warehouse_orderpoint where product_id=(select id from product_product where name_template='" + product +"') and location_id=" + self._mainLocationId  + " limit 1")
        rows = cr.fetchall()
        min=0
        max=0
        for row in rows:
            min = row[0]
            max = row[1];
        cr.execute("select name,quantity,EXTRACT(EPOCH FROM date_trunc('second', date_order) AT TIME ZONE 'UTC')*1000 from stock_move_inventory_report where name='"+product+"' and date_order>'"+start_date+"' and date_order<'"+end_date+"'")
        cr.execute("SELECT name,sum(CASE WHEN sm.location_dest_id = " + self._mainLocationId  + """ THEN 1*quantity
        ELSE -1*quantity
            END) as way,EXTRACT(EPOCH FROM date_trunc('second', date_order) AT TIME ZONE 'UTC')*1000
            from stock_move_inventory_report sm
            where name = '""" + product +"""' and
            (location_dest_id=""" + self._mainLocationId  + " or location_id=" + self._mainLocationId  + ") and date_order>='" + start_date + "' and date_order<='" + end_date + """'
            GROUP BY sm.name,sm.date_order ORDER BY sm.date_order asc""")
        rows = cr.fetchall()
        dataset = []
        maxset = []
        minset = []
        datasetXaxis=[]
        for row in rows:
            dataset.append({'x':row[2],'y':row[1]+startingQty})
            datasetXaxis.append({'x':row[2],'y':0})
            startingQty = startingQty + row[1]
            if max:
                maxset.append({'x':row[2],'y':max})
                minset.append({'x':row[2],'y':min})
        res = [];
        res.append({
            'values': dataset,
            'key': product,
            'color': "#ff7f0e",
            })
        res.append({
            'values': maxset,
            'key': "Max Level",
            'color': "#2ca02c",
            'strokeWidth': 3,
            })
        res.append({
            'values': minset,
            'key': "Min Level",
            'color': "#22202c",
            'strokeWidth': 3,
            })

        res.append({
            'values': datasetXaxis,
            'key': "",
            'color': "#ff202c",
            'strokeWidth': 5,
            })
        return res,options;

stock_move_inventory_report()

