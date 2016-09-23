from __future__ import division
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists
from datetime import datetime,timedelta
import logging
import collections
import time


_logger = logging.getLogger(__name__)

class min_max_report(osv.osv):
    _name = 'min_max.report'
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
    def init(self,cr):
        drop_view_if_exists(cr,'kpi_data_store')
        cr.execute("""
        create or replace view kpi_data_store AS(select row_number() OVER (order by sm.write_date) as id,pp.name_template as name,
       pp.id as product_id,sm.product_qty as quantity,sm.write_date as date_order,
  sm.location_dest_id, sm.location_id,sm.prodlot_id,
  CASE WHEN sm.location_dest_id =27 THEN '+'
  WHEN sm.location_id =27 THEN '-'
  ELSE '*'
  END as way,
  srcloc.name as fromloc,
  dstloc.name as toloc,
  pp.default_code as itemreference,
  swo.product_min_qty,swo.product_max_qty,swo.x_bare_minimum,
  pt.x_formulary,
  pt.x_govt,
  pt.x_low_cost_eq,
  pp.antibiotic,pp.other_item,pp.medical_item,pp.lab_item,
  pp.medicine_item,
  xpsc.x_name as supplier_category,
  pt.list_price,po.name as poname,
  pc.name as product_category,
  rp.name as supplier,
  pol.price_unit as purchase_price,at.amount as ptax,
  (pol.price_unit+(pol.price_unit*coalesce(at.amount,0))) as amtwithtax,
  spl.sale_price as lot_sp
from
  stock_move sm inner join product_product pp
    on sm.product_id=pp.id
       and sm.state='done' AND (sm.location_dest_id=27 or sm.location_id=27)
    LEFT JOIN stock_warehouse_orderpoint swo on swo.product_id=sm.product_id and swo.location_id = (SELECT id FROM stock_location where name = 'BPH Storeroom')
    LEFT JOIN product_template pt on pt.id = pp.product_tmpl_id
    LEFT JOIN stock_production_lot spl on spl.id=sm.prodlot_id
    LEFT JOIN x_product_supplier_category xpsc on xpsc.id=spl.x_supplier_category
    LEFT JOIN product_category pc on pt.categ_id= pc.id
  LEFT JOIN purchase_order_line pol on pol.id=sm.purchase_line_id
  LEFT JOIN purchase_order_taxe pot on pot.ord_id = pol.id
  LEFT JOIN account_tax at on at.id = pot.tax_id
  LEFT JOIN res_partner rp on rp.id=pol.partner_id
  LEFT JOIN purchase_order po on pol.order_id = po.id
  LEFT JOIN stock_location dstloc on dstloc.id = sm.location_dest_id
  LEFT JOIN stock_location srcloc on srcloc.id = sm.location_id
ORDER BY pp.id , date_order)
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
    def export_header(self, cr, uid, start_date, end_date):
        # if not product:
        #     raise osv.except_osv(('Error'), ('Please choose a product to show the graph'))
        if not start_date:
            raise osv.except_osv(('Error'), ('Please choose a start date to show the graph'))
        if not end_date:
            raise osv.except_osv(('Error'), ('Please choose a end date to show the graph'))
        header = []
        header.append("Product Name")
        header.append("Product Category")
        header.append("Supplier Category")
        header.append("Move date")
        header.append("Way")
        header.append("Supplier Name")
        header.append("PO Name")
        header.append("Supplier Unit Price")
        header.append("Purchase Unit Price With Tax")
        header.append("Quantity")
        header.append("Sales Price")
        header.append("From")
        header.append("To")
        header.append("Product reference")
        header.append("Essential")
        header.append("Government")
        header.append("Formulary")
        header.append("Medicine")
        header.append("Bare Min")
        header.append("Min")
        header.append("Max level")
        header.append("Antibiotic")
        header.append("Lab Item")
        header.append("Medical Item")
        header.append("Other Item")
        header.append("Running total")
        header.append("Hit/Mis")
        header.append("Stockout duration")
        return header;
    def export_data(self, cr, uid, start_date, end_date,context=None):
        # if not product:
        #     raise osv.except_osv(('Error'), ('Please choose a product to show the graph'))
        if not start_date:
            raise osv.except_osv(('Error'), ('Please choose a start date to show the graph'))
        if not end_date:
            raise osv.except_osv(('Error'), ('Please choose a end date to show the graph'))
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
                LEFT JOIN kpi_data_store sm on sm.product_id= pp.id and
                (location_dest_id="""+str(productsIds[0])+" or location_id="+str(productsIds[0])+") and date_order<'"+start_date+"""'
                GROUP BY pp.name_template,pp.id""")
        rows = cr.fetchall()
        for row in rows:
            timeProdQtyHash[row[0]] = row[2]
        cr.execute("SELECT product_id,name,(CASE WHEN sm.location_dest_id = "+str(productsIds[0])+""" THEN 1*quantity
        ELSE -1*quantity
            END) as qty,sm.date_order, sm.way,sm.itemreference,sm.x_low_cost_eq,sm.x_govt,sm.x_formulary,
            sm.product_min_qty,sm.product_max_qty,sm.product_category,sm.supplier_category,sm.supplier,
            sm.antibiotic,sm.lab_item,sm.medical_item,sm.other_item,sm.list_price,sm.fromloc,sm.toloc,sm.purchase_price,
            sm.x_bare_minimum,sm.amtwithtax,sm.medicine_item,poname,sm.lot_sp
            from kpi_data_store sm
            where
            (location_dest_id="""+str(productsIds[0])+" or location_id="+str(productsIds[0])+") and date_order>='"+start_date+"' and date_order<='"+end_date+"""'
            ORDER BY product_id,sm.date_order asc""")
        out = []
        rows = cr.fetchall()
        # fill hash of hash here
        last_prod_id=-1
        runningTotal=0.0
        stockout_duration=0.0
        last_date=start_date+" 00:00:00.000000"
        sum_stock_out=0
        for row in rows:
            line = []
            line.append(row[1])
            line.append(row[11])
            line.append(row[12])
            line.append(row[3])
            line.append(row[4])
            line.append(row[13])
            line.append(row[25])
            line.append(row[21])
            line.append(row[23])    #header.append("Purchase Unit Price With Tax")
            line.append(row[2])
            if row[25]:
                line.append(row[26])    #header.append("Sales Price")
            else:
                line.append(row[18])    #header.append("Sales Price")
            line.append(row[19])
            line.append(row[20])
            line.append(row[5])
            line.append(row[6])
            line.append(row[7])
            line.append(row[8])
            line.append(row[24])     #header.append("Medicine")
            line.append(row[22])     #header.append("Bare Min")
            line.append(row[9])
            line.append(row[10])
            max = row[10]
            min = row[9]
            prodID=row[0]
            line.append(row[14])
            line.append(row[15])
            line.append(row[16])
            line.append(row[17])
            if last_prod_id != prodID :
                if prodID not in timeProdQtyHash:
                    timeProdQtyHash[prodID]=0.0
                if not timeProdQtyHash[prodID]:
                    runningTotal = 0
                else:
                    runningTotal = timeProdQtyHash[prodID]
                #Needed if stocked out from day 1
                if runningTotal<1 :
                    sum_stock_out=1
                else:
                    sum_stock_out=0
                last_prod_id = prodID
                stockout_duration=0.0
                last_date=start_date+" 00:00:00.000000"
            if not row[2]:
                runningTotal = runningTotal + 0
            else:
                runningTotal = runningTotal + row[2]
            line.append(runningTotal)
            if runningTotal<=0 :
                line.append("Stockout")
            elif runningTotal <min:
                line.append("B Min")
            elif runningTotal >max :
                line.append("A Max")
            else:
                line.append("Hit")
            if sum_stock_out==1:
                lday = datetime.strptime(last_date, self._date_time_format)
                cday = datetime.strptime(row[3], self._date_time_format)
                delta = cday - lday
                stockout_duration += stockout_duration + delta.days
            else:
                stockout_duration=0
            if runningTotal<1 :
                sum_stock_out=1
            else:
                sum_stock_out=0
            line.append(stockout_duration)
            last_date=row[3]
            out.append(line)
        return out

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
            arg=(row[3],row[0],row[2])
            self.addNameToDictionary(timeProdQtyHash,arg)
        self.normalizeDict(timeProdQtyHash,date_list,daybeforestr)
        cr.execute("""select pp.id,pp.name_template,product_min_qty,product_max_qty  from product_product pp
        LEFT JOIN stock_warehouse_orderpoint swo on swo.product_id= pp.id and location_id="""+str(productsIds[0]))
        order_points = {}
        rows = cr.fetchall()
        # fill hash of hash here
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

