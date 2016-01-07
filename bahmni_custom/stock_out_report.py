from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists
from datetime import datetime,timedelta
import logging
import collections
import time

_logger = logging.getLogger(__name__)

class stock_out_report(osv.osv):
    _name = 'stock_out.report'
    _description = 'Stock Out Report'
    _auto = False
    _date_format = "%Y-%m-%d"
    _columns={
        'name':fields.text('Name',readonly=True),
        'date_order':fields.date('Order Date',readonly=True),
        'quantity':fields.float('Quantity',readonly=True),
        'id':fields.integer('Product ID',readonly=True),
            }
    def init(self,cr):
        drop_view_if_exists(cr,'stock_out_report')
        cr.execute("""
        create or replace view stock_out_report AS(select row_number() OVER (order by sm.write_date) as id,pp.name_template as name,
  pp.id as product_id,sum(sm.product_qty) as quantity,sm.write_date::timestamp::date as date_order,
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
        _logger.error("unprocessed_order count is %s", searchText)
        productsIds = self.pool.get('product.product').search(cr, uid, [('name_template', 'ilike', searchText)],limit=10, context=context)
        res = [];
        if(productsIds):
            for product in productsIds:
                line=self.pool.get('product.product').browse(cr, uid,product ,context=context)
                res.append({'name':line.name,'id':line.name})
        return res;

    def addNameToDictionary(self,d, tup):
        if tup[0] not in d:
            d[tup[0]] = {}
        if tup[2] is None:
            tup[2] = 0
        d[tup[0]][tup[1]] = tup[2]
    def normalizeDict(self,timeProdQtyHash,date_list,daybeforestr):
        lastDay = datetime.strptime(daybeforestr, self._date_format)
        lastDayProdQtyMap = timeProdQtyHash[daybeforestr]
        for date in date_list:
            currentDay = datetime.strftime(date, self._date_format)
            if currentDay not in timeProdQtyHash:
                timeProdQtyHash[currentDay] = {}
            currDayProdQtyMap = timeProdQtyHash[currentDay]
            for prodID, v in lastDayProdQtyMap.iteritems():
                if prodID not in currDayProdQtyMap:
                    currDayProdQtyMap[prodID]=0
                prdQty = currDayProdQtyMap[prodID];
                currDayProdQtyMap[prodID]=prdQty+v
            lastDayProdQtyMap=timeProdQtyHash[currentDay]

    def chart_d3_get_data(self, cr, uid, xaxis, yaxis, domain, group_by, options,
        product, start_date, end_date, context=None):
        # if not product:
        #     raise osv.except_osv(('Error'), ('Please choose a product to show the graph'))
        if not start_date:
            raise osv.except_osv(('Error'), ('Please choose a start date to show the graph'))
        if not end_date:
            raise osv.except_osv(('Error'), ('Please choose a end date to show the graph'))
        _logger.error("ssss executing query")
        productsIds = self.pool.get('stock.location').search(cr, uid, [('name', '=', 'BPH Storeroom')],limit=10, context=context)

        a = datetime.strptime(start_date, self._date_format)
        b = datetime.strptime(end_date, self._date_format)
        delta = b - a
        # print delta.days
        daybefore= a - timedelta(days=1)
        daybeforestr=datetime.strftime(daybefore,self._date_format)
        date_list = [a + timedelta(days=x) for x in range(0, delta.days)]
        timeProdQtyHash={}
        cr.execute("select pp.id,pp.name_template,sum(CASE WHEN sm.location_dest_id = "+str(productsIds[0])+""" THEN 1*quantity
                ELSE -1*quantity
                END) as qty
                from product_product pp
                LEFT JOIN stock_out_report sm on sm.product_id= pp.id and
                (location_dest_id="""+str(productsIds[0])+" or location_id="+str(productsIds[0])+") and date_order<'"+start_date+"""'
                GROUP BY pp.name_template,pp.id""")
        rows = cr.fetchall()
        for row in rows:
            arg=[daybeforestr,row[0],row[2]]
            self.addNameToDictionary(timeProdQtyHash,arg)

#         cr.execute("select pp.id,pp.name_template,sum(CASE WHEN sm.location_dest_id =  "+str(productsIds[0])+""" THEN 1*quantity
#         ELSE -1*quantity
#             END) as way,sm.date_order from product_product pp
# LEFT JOIN stock_move_inventory_report sm on sm.product_id= pp.id
# and (location_dest_id="""+str(productsIds[0])+" or location_id="+str(productsIds[0])+") and date_order>='"+start_date+"' and date_order<='"+end_date+"""'
#             GROUP BY pp.name_template,pp.id,sm.date_order ORDER BY sm.date_order asc""")
        cr.execute("SELECT product_id,name,sum(CASE WHEN sm.location_dest_id = "+str(productsIds[0])+""" THEN 1*quantity
        ELSE -1*quantity
            END) as way,sm.date_order
            from stock_out_report sm
            where
            (location_dest_id="""+str(productsIds[0])+" or location_id="+str(productsIds[0])+") and date_order>='"+start_date+"' and date_order<='"+end_date+"""'
            GROUP BY sm.name,sm.date_order,sm.product_id ORDER BY sm.date_order asc""")

        rows = cr.fetchall()
# fill hash of hash here
        for row in rows:
            _logger.error("ssss %s",row)
            _logger.error("Sandeep is %s = %s = %s", row[0],row[1],row[2])
            arg=(row[3],row[0],row[2])
            self.addNameToDictionary(timeProdQtyHash,arg)
        _logger.error("dictionary")
        _logger.error(timeProdQtyHash)
        self.normalizeDict(timeProdQtyHash,date_list,daybeforestr)
        res = [];
        dataset={}
        for dateStr, prdQty in timeProdQtyHash.iteritems():

            noOfSO = 0;
            for id, qty in prdQty.iteritems():
                if qty<1 :
                    noOfSO += 1
            xdate = datetime.strptime(dateStr, self._date_format)
            ts = time.mktime(xdate.timetuple())*1000
            dataset.update({ts: {'x':ts,'y':noOfSO} })
        dataset = collections.OrderedDict(sorted(dataset.items()))
        res.append({
            'values': dataset.values(),
            'key': "No of Stock Outs",
            'color': "#ff7f0e",
            })
        return res,options;


stock_out_report()

