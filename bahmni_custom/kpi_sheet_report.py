from __future__ import division
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists
from datetime import datetime,timedelta
import logging

_logger = logging.getLogger(__name__)

class kpi_sheet_report(osv.osv):
    _name = 'kpi_sheet.report'
    _description = 'KPI Sheet report for specific location'
    _auto = False
    _date_format = "%Y-%m-%d"
    _date_time_format = '%Y-%m-%d %H:%M:%S'
    _columns={
        'name':fields.text('Name',readonly=True),
        'date_order':fields.date('Order Date',readonly=True),
        'quantity':fields.float('Quantity',readonly=True),
        'id':fields.integer('Product ID',readonly=True),
    }
    def create_KPI_Sheet_View(self,cr,location_id,view_name):

        drop_view_if_exists(cr,view_name)
        cr.execute("""
        create or replace view {view_name} AS(select row_number() OVER (order by sm.date) as id,pp.name_template as name,
       pp.id as product_id,sm.product_qty as quantity,sm.date as date_order,
  sm.location_dest_id, sm.location_id,sm.prodlot_id,
  CASE WHEN sm.location_dest_id ={location_id} THEN '+'
  WHEN sm.location_id = {location_id}  THEN '-'
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
  spl.sale_price as lot_sp,
  spl.name as batch_number,
  pp.physic_medicine,pp.insurance_medicine,pp.vertical_program,pp.dental_item
from
  stock_move sm inner join product_product pp
    on sm.product_id=pp.id
       and sm.state='done' AND (sm.location_dest_id={location_id} or sm.location_id={location_id})
    LEFT JOIN stock_warehouse_orderpoint swo on swo.product_id=sm.product_id and swo.location_id = {location_id}
    LEFT JOIN product_template pt on pt.id = pp.product_tmpl_id
    LEFT JOIN stock_production_lot spl on spl.id=sm.prodlot_id
    LEFT JOIN product_category pc on pt.categ_id= pc.id
    LEFT JOIN sale_order_line sol on sol.id=sm.sale_line_id
  LEFT JOIN purchase_order_line pol on pol.id=sm.purchase_line_id
  LEFT JOIN purchase_order_taxe pot on pot.ord_id = pol.id
  LEFT JOIN account_tax at on at.id = pot.tax_id
  LEFT JOIN res_partner rp on rp.id=pol.partner_id
  LEFT JOIN x_product_supplier_category xpsc on xpsc.id=rp.x_supplier_category
  LEFT JOIN purchase_order po on pol.order_id = po.id
  LEFT JOIN stock_location dstloc on dstloc.id = sm.location_dest_id
  LEFT JOIN stock_location srcloc on srcloc.id = sm.location_id
ORDER BY pp.id , date_order)
        """.format(location_id=location_id,view_name=view_name))

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

    def export_header(self, cr, uid, start_date, end_date):
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
        header.append("Physic Medicine")
        header.append("Insurance Medicine")
        header.append("Vertical Program")
        header.append("Dental Item")
        header.append("Running total")
        header.append("Hit/Mis")
        header.append("Stockout duration")
        header.append("Batch Number")
        return header;
    def export_data(self, cr, uid, start_date, end_date, location_id, view_name, context=None):

        self.create_KPI_Sheet_View(cr, location_id, view_name)
        if not start_date:
            raise osv.except_osv(('Error'), ('Please choose a start date to show the graph'))
        if not end_date:
            raise osv.except_osv(('Error'), ('Please choose a end date to show the graph'))
        productsIds = self.pool.get('stock.location').search(cr, uid, [('id', '=', location_id)],limit=10, context=context)

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
                LEFT JOIN """+view_name+""" sm on sm.product_id= pp.id and
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
            sm.x_bare_minimum,sm.amtwithtax,sm.medicine_item,poname,sm.lot_sp,sm.batch_number,sm.physic_medicine,sm.insurance_medicine,sm.vertical_program,sm.dental_item
            from """+view_name+""" sm
            where
            (location_dest_id="""+str(productsIds[0])+" or location_id="+str(productsIds[0])+") and date_order>='"+start_date+"' and date_order<='"+end_date+"""'
            ORDER BY product_id,sm.date_order asc""")
        out = []
        rows = cr.fetchall()
        # fill hash of hash here
        last_prod_id=-1
        runningTotal=0.0
        stockout_duration=0.0
        last_date=start_date+" 00:00:00"
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
            if row[27]:
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
            min = row[22]
            prodID=row[0]
            line.append(row[14])
            line.append(row[15])
            line.append(row[16])
            line.append(row[17])
            line.append(row[28])
            line.append(row[29])
            line.append(row[30])
            line.append(row[31])
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
                last_date=start_date+" 00:00:00"
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
            line.append(row[27])

            last_date=row[3]
            out.append(line)
        return out

    def getAllLocations(self, cr, uid, usage, context):
        def getLocation(locationId):
            return self._getLocation(cr, uid, locationId, context=context)

        locationIds = self.pool.get('stock.location').search(cr, uid, [('usage', '=', usage), ('active', '=', True)],
                                                             context=context)
        return map(getLocation, locationIds or [])

    def _getLocation(self, cr, uid, locationId, context=None):
        location = self.pool.get('stock.location').browse(cr, uid, locationId, context=context)
        return {'name': location.name, 'id': location.id}

kpi_sheet_report()

