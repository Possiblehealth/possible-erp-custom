from __future__ import division
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime,timedelta
import logging
import collections
import time

_logger = logging.getLogger(__name__)

class min_max_report(osv.osv):
    _name = 'min_max.report'
    _description = 'Min Max Report'
    _auto = False
    _date_format = "%Y-%m-%d"
    _date_time_format = '%Y-%m-%d %H:%M:%S.%f'
    _columns={
        'name':fields.text('Name',readonly=True),
        'date_order':fields.date('Order Date',readonly=True),
        'quantity':fields.float('Quantity',readonly=True),
        'id':fields.integer('Product ID',readonly=True),
    }
    _hospitalLocationId = None

    def init(self,cr):
        cr.execute("SELECT value FROM custom_report_props WHERE name='hospitalLocationId'")
        self._hospitalLocationId = cr.fetchall()[0][0]

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
        cr.execute("""select pp.id,pp.name_template,sum(CASE WHEN sm.location_dest_id = {hospitalLocationId} THEN 1*quantity
                ELSE -1*quantity
                END) as qty
                from product_product pp
                LEFT JOIN stock_out_report sm on sm.product_id= pp.id and
                (location_dest_id={hospitalLocationId} or location_id={hospitalLocationId}) and date_order<'{start_date}'
                GROUP BY pp.name_template,pp.id""".format(hospitalLocationId=self._hospitalLocationId,start_date=start_date))
        rows = cr.fetchall()
        for row in rows:
            self.addNameToDictionary(timeProdQtyHash,daybeforestr,row[0],row[2])
        cr.execute("""SELECT product_id,name,sum(CASE WHEN sm.location_dest_id = {hospitalLocationId} THEN 1*quantity
        ELSE -1*quantity
            END) as way,sm.date_order
            from stock_out_report sm
            where
            (location_dest_id= {hospitalLocationId} or location_id= {hospitalLocationId}) and date_order>='{start_date}' and date_order<='{end_date}'
            GROUP BY sm.name,sm.date_order,sm.product_id ORDER BY sm.date_order asc"""
                   .format(hospitalLocationId=self._hospitalLocationId,start_date=start_date,end_date=end_date))

        rows = cr.fetchall()
        for row in rows:
            self.addNameToDictionary(timeProdQtyHash,row[3],row[0],row[2])
        self.normalizeDict(timeProdQtyHash,date_list,daybeforestr)
        cr.execute("""select pp.id,pp.name_template,product_min_qty,product_max_qty  from product_product pp
        LEFT JOIN stock_warehouse_orderpoint swo on swo.product_id= pp.id and location_id="""+self._hospitalLocationId)
        order_points = {}
        rows = cr.fetchall()
        for row in rows:
            order_points.update({row[0]: {'min':row[2],'max':row[3]}})
        res = [];
        dataset={}
        datasetMin={}
        datasetMax={}
        datasetXaxis={}
        for dateStr, prdQty in timeProdQtyHash.iteritems():
            noOfAboveMax = 0;
            noOfBelowMin = 0;
            noOfWithRange = 0;
            for id, qty in prdQty.iteritems():
                max = order_points[id]['max']
                min = order_points[id]['min']
                if qty<min :
                    noOfBelowMin += 1
                elif qty>max :
                    noOfAboveMax += 1
                else:
                    noOfWithRange += 1
            xdate = datetime.strptime(dateStr, self._date_format)
            ts = time.mktime(xdate.timetuple())*1000
            dataset.update({ts: {'x':ts,'y':round((noOfWithRange/len(order_points))*100, 2)} })
            datasetMax.update({ts: {'x':ts,'y':round((noOfAboveMax/len(order_points))*100, 2)} })
            datasetMin.update({ts: {'x':ts,'y':round((noOfBelowMin/len(order_points))*100, 2)} })
            datasetXaxis.update({ts: {'x':ts,'y':0} })

        dataset = collections.OrderedDict(sorted(dataset.items()))
        datasetMax = collections.OrderedDict(sorted(datasetMax.items()))
        datasetMin = collections.OrderedDict(sorted(datasetMin.items()))
        datasetXaxis = collections.OrderedDict(sorted(datasetXaxis.items()))
        res.append({
            'values': dataset.values(),
            'key': "Percent In Range",
            'color': "#ff7f0e",
            })
        res.append({
            'values': datasetMax.values(),
            'key': "Percent Above Max",
            'color': "#2ca02c",
            'strokeWidth': 3,
            })
        res.append({
            'values': datasetMin.values(),
            'key': "Percent Below Min",
            'color': "#22202c",
            'strokeWidth': 3,
            })

        res.append({
            'values': datasetXaxis.values(),
            'key': "",
            'color': "#ff202c",
            'strokeWidth': 5,
            })
        return res,options;

min_max_report()

