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
        drop_view_if_exists(cr,'kpi_data_hospital')
        cr.execute("""
        create or replace view kpi_data_hospital AS(select row_number() OVER (order by sm.write_date) as id,pp.name_template as name,
       pp.id as product_id,sm.product_qty as quantity,sm.write_date as date_order,
  sm.location_dest_id, sm.location_id,sm.prodlot_id,
       CASE WHEN sm.location_dest_id in (
         select id from stock_location where name='Inventory loss' or
                                             name='Customers' or
                                             name='Suppliers' or
                                             name='Scrapped' or
                                             name='BPH Expired' or
                                             name='BPH Scrap'
       ) THEN '+'
       WHEN sm.location_id in (
         select id from stock_location where name='Inventory loss' or
                                             name='Customers' or
                                             name='Suppliers' or
                                             name='Scrapped' or
                                             name='BPH Expired' or
                                             name='BPH Scrap'
       ) THEN '-'
       ELSE '*'
       END as way,
       pp.default_code as itemreference,
  swo.product_min_qty,swo.product_max_qty,swo.x_bare_minimum,
  pt.x_formulary,
  pt.x_govt,
  pt.x_low_cost_eq,
       xpsc.x_name as supplier_category,
  pt.list_price,
       pc.name as product_category,
       rp.name as supplier
from
  stock_move sm inner join product_product pp
    on sm.product_id=pp.id
       and sm.state='done' AND (sm.location_dest_id in (
    select id from stock_location where name='Inventory loss' or
                                        name='Customers' or
                                        name='Suppliers' or
                                        name='Scrapped' or
                                        name='BPH Expired' or
                                        name='BPH Scrap'
  )
                                or sm.location_id in (
    select id from stock_location where name='Inventory loss' or
                                        name='Customers' or
                                        name='Suppliers' or
                                        name='Scrapped' or
                                        name='BPH Expired' or
                                        name='BPH Scrap'
  ))
  LEFT JOIN stock_warehouse_orderpoint swo on swo.product_id=sm.product_id and swo.location_id = (SELECT id FROM stock_location where name = 'BPH Storeroom')
  LEFT JOIN product_template pt on pt.id = pp.product_tmpl_id
  LEFT JOIN stock_production_lot spl on spl.id=sm.prodlot_id
  LEFT JOIN x_product_supplier_category xpsc on xpsc.id=spl.x_supplier_category
  LEFT JOIN product_category pc on pt.categ_id= pc.id
  LEFT JOIN purchase_order_line pol on pol.id=sm.purchase_line_id
  LEFT JOIN res_partner rp on rp.id=pol.partner_id
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
        header.append("Quantity")
        header.append("Product reference")
        header.append("Essential")
        header.append("Government")
        header.append("Formulary")
        header.append("Min")
        header.append("Max level")
        header.append("Running total")
        header.append("Hit/Mis")
        header.append("Stockout duration")
        return header
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
        cr.execute("""select pp.id,pp.name_template,sum(CASE WHEN sm.location_dest_id  in (
    select id from stock_location where name='Inventory loss' or
                                        name='Customers' or
                                        name='Suppliers' or
                                        name='Scrapped' or
                                        name='BPH Expired' or
                                        name='BPH Scrap'
  ) THEN -1*quantity
                    ELSE 1*quantity
                    END) as qty
                    from product_product pp
                    LEFT JOIN kpi_data_hospital sm on sm.product_id= pp.id and
                    (location_dest_id in (
    select id from stock_location where name='Inventory loss' or
                                        name='Customers' or
                                        name='Suppliers' or
                                        name='Scrapped' or
                                        name='BPH Expired' or
                                        name='BPH Scrap'
  )
                     or location_id in (
    select id from stock_location where name='Inventory loss' or
                                        name='Customers' or
                                        name='Suppliers' or
                                        name='Scrapped' or
                                        name='BPH Expired' or
                                        name='BPH Scrap'
  )) and date_order<'"""+start_date+"""' GROUP BY pp.name_template,pp.id""")

        rows = cr.fetchall()
        for row in rows:
            timeProdQtyHash[row[0]] = row[2]
        cr.execute("""SELECT product_id,name,(CASE WHEN sm.location_dest_id in (
    select id from stock_location where name='Inventory loss' or
                                        name='Customers' or
                                        name='Suppliers' or
                                        name='Scrapped' or
                                        name='BPH Expired' or
                                        name='BPH Scrap'
  )
                    THEN -1*quantity
            ELSE 1*quantity
                END) as qty,sm.date_order, sm.way,sm.itemreference,sm.x_low_cost_eq,sm.x_govt,sm.x_formulary,
                sm.product_min_qty,sm.product_max_qty,sm.product_category,sm.supplier_category,sm.supplier
                from kpi_data_hospital sm
                where
                (location_dest_id in (
    select id from stock_location where name='Inventory loss' or
                                        name='Customers' or
                                        name='Suppliers' or
                                        name='Scrapped' or
                                        name='BPH Expired' or
                                        name='BPH Scrap'
  ) or location_id in (
    select id from stock_location where name='Inventory loss' or
                                        name='Customers' or
                                        name='Suppliers' or
                                        name='Scrapped' or
                                        name='BPH Expired' or
                                        name='BPH Scrap'
  )) and date_order>='"""+start_date+"' and date_order<='"+end_date+"' ORDER BY product_id,sm.date_order asc")
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
            line.append(row[2])
            line.append(row[5])
            line.append(row[6])
            line.append(row[7])
            line.append(row[8])
            line.append(row[9])
            line.append(row[10])
            max = row[10]
            min = row[9]
            prodID=row[0]
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

