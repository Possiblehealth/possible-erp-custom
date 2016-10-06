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
    _date_time_format = '%Y-%m-%d %H:%M:%S.%f'
    _columns={
        'name':fields.text('Name',readonly=True),
        'date_order':fields.date('Order Date',readonly=True),
        'quantity':fields.float('Quantity',readonly=True),
        'id':fields.integer('Product ID',readonly=True),
            }
    _hospitalLocationId=None
    _stockTransferLocations=None
    def init(self,cr):
        cr.execute("SELECT value FROM custom_report_props WHERE name='hospitalLocationId'")
        self._hospitalLocationId = cr.fetchall()[0][0]
        cr.execute("select value from custom_report_props where name='stockTransferLocationIds'")
        self._stockTransferLocations = cr.fetchall()[0][0]

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

    def addNameToDictionary(self,dictionary, date, productId, quantity):
        if date not in dictionary:
            dictionary[date] = {}
        dictionary[date][productId] = quantity or 0

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
        if not start_date:
            raise osv.except_osv(('Error'), ('Please choose a start date to show the graph'))
        if not end_date:
            raise osv.except_osv(('Error'), ('Please choose a end date to show the graph'))

        a = datetime.strptime(start_date, self._date_format)
        b = datetime.strptime(end_date, self._date_format)
        delta = b - a
        # print delta.days
        daybefore= a - timedelta(days=1)
        daybeforestr=datetime.strftime(daybefore,self._date_format)
        date_list = [a + timedelta(days=x) for x in range(0, delta.days)]
        timeProdQtyHash={}
        cr.execute("""select pp.id,pp.name_template,sum(CASE WHEN sm.location_dest_id in ({stockTransferLocations}) THEN -1*quantity
                ELSE 1*quantity
                END) as qty
                from product_product pp
                INNER JOIN product_template pt ON pp.id = pt.id AND pt.x_formulary IS TRUE
                LEFT JOIN stock_out_report sm on sm.product_id= pp.id and
                (location_dest_id in ({stockTransferLocations}) or location_id in ({stockTransferLocations})) and date_order<'{start_date}'
                GROUP BY pp.name_template,pp.id""".format(start_date=start_date,stockTransferLocations=self._stockTransferLocations))
        rows = cr.fetchall()
        for row in rows:
            self.addNameToDictionary(timeProdQtyHash,daybeforestr,row[0],row[2])

        cr.execute("""SELECT sm.product_id,sm.name,sum(CASE WHEN sm.location_dest_id in ({stockTransferLocations}) THEN -1*quantity
            ELSE 1*quantity
            END) as way,sm.date_order
            from stock_out_report sm
            INNER JOIN product_template pt ON sm.product_id = pt.id AND pt.x_formulary IS TRUE
            where
            (location_dest_id in ({stockTransferLocations}) or location_id in ({stockTransferLocations}))
            and date_order>='{start_date}' and date_order<='{end_date}'
            GROUP BY sm.name,sm.date_order,sm.product_id
            ORDER BY sm.date_order asc""".format(start_date=start_date,end_date=end_date,stockTransferLocations=self._stockTransferLocations))

        rows = cr.fetchall()
# fill hash of hash here
        for row in rows:
            self.addNameToDictionary(timeProdQtyHash,row[3],row[0],row[2])
        self.normalizeDict(timeProdQtyHash,date_list,daybeforestr)
        res = [];
        dataset={}
        datasetxaxis={}
        for dateStr, prdQty in timeProdQtyHash.iteritems():

            noOfSO = 0;
            for id, qty in prdQty.iteritems():
                if qty<1 :
                    noOfSO += 1
            xdate = datetime.strptime(dateStr, self._date_format)
            ts = time.mktime(xdate.timetuple())*1000
            dataset.update({ts: {'x':ts,'y':noOfSO} })
            datasetxaxis.update({ts: {'x':ts,'y':0} })
        dataset = collections.OrderedDict(sorted(dataset.items()))
        res.append({
            'values': dataset.values(),
            'key': "No of Stock Outs",
            'color': "#ff7f0e",
            })
        res.append({
            'values': datasetxaxis.values(),
            'key': "",
            'color': "#227f0e",
            })
        return res,options;
stock_out_report()

