# -*- coding: utf-8 -*-
# © 2017 Satvix Informatics (https://www.satvix.com)

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import time
from datetime import datetime
import pytz
import os,glob
import csv,xlwt
from xlsxwriter.workbook import Workbook
import shutil 
import base64
from tools.translate import _
from pathlib import Path
import logging
from pprint import pprint
_logger = logging.getLogger(__name__)

import sys
import zipfile
reload(sys) 
sys.setdefaultencoding('utf-8')


class stock_move_report_wizard(osv.osv_memory):
    _name = 'stock.move.report.wizard'
    _description = 'OpenERP Report Wizard'

    _columns = {
        'start_date':   fields.datetime('Start Date'),
        'end_date':     fields.datetime('End Date'),
        'type':         fields.selection([('in','In'),('out','Out'),('internal','Internal'),('scrap','Scrap'),('consumption','Consumption'),('production','production'),('all','all')],string='Type',required=True),
    }

    _defaults = {
        'start_date': lambda *a: time.strftime('%Y-%m-%d 16:00:00'),
        'end_date': lambda *a: time.strftime('%Y-%m-%d 15:59:59'),
        'type': 'all',
    }
    
    def generate_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]        
        context['start_date'] = data.start_date
        context['end_date'] = data.end_date
        context['type'] = data.type
        
        pi_obj = self.pool.get('stock.move.report')
        pi_obj.generate_report(cr, uid, context)

        mod_obj = self.pool.get('ir.model.data')

        res = mod_obj.get_object_reference(cr, uid, 'move_reports', 'view_move_report_tree')
        res_id = res and res[1] or False,

        return {
            'name': _('OpenERP Report'),
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': res_id,
            'res_model': 'stock.move.report',
            'context': "{}",
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': False,
        }
stock_move_report_wizard()


class stock_move_report(osv.osv):
    _name = 'stock.move.report'
    _description = 'OpenERP Report'
    _rec_name = "move_id"
    _order = 'date desc'
    
    
    _create_sql = """
                INSERT INTO stock_move_report
                    (
                        create_uid,
                        write_uid,
                        create_date,
                        write_date,
                        move_id,
                        date,
                        date_expected,
                        origin,
                        invoice_name,
                        picking_id,
                        picking_name,
                        type,
                        pick_return,
                        partner_ref,
                        partner_id,
                        partner_category,
                        partner_name,
                        stock_type_id,
                        stock_type_name,
                        category_id,
                        category_name,
                        product_sku,
                        product_id,
                        product_name,
                        move_qty,
                        product_qty,
                        uom_id,
                        uom_name,
                        product_uom_name,
                        uom_factor,
                        product_price,
                        price_unit,
                        cost_total,
                        po_price,
                        amount_total,
                        loc_name,
                        loc_dest_name,
                        return_reason
                    )
                SELECT %d, %d, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                        m.id as move_id, m.date, m.date_expected, m.origin,
                        am.name as invoice_name,
                        p.id as picking_id, p.name as picking_name, 
                        p.type as type, p.return as pick_return,
                        rp.ref as partner_ref, rp.id as partner_id, 
                        xpsc.x_name as partner_category,
                        rp.name as partner_name,
                        st.id as stock_type_id , st.name as stock_type_name,
                        c.id as category_id, cp.name || ' / ' || c.name as category_name,
                        m.product_code as product_sku, pp.id as product_id, pt.name as product_name,
                        m.product_qty as move_qty, m.product_qty * pu.factor / u.factor as product_qty,
                        u.id as uom_id, u.name as uom_name, pu.name as product_uom_name, pu.factor / u.factor as uom_facotr,
                        m.price_unit / pu.factor * u.factor as product_price, m.price_unit as price_unit, round(m.product_qty * pu.factor / u.factor*m.price_unit, 4) as cost_total,
                        m.po_price as po_price, m.amount_total as amount_total,
                        sl.complete_name as location_name,
                        sld.complete_name as location_dest_name,
                        srr.code as return_reason
                    from stock_move m
                        left join stock_picking p on p.id = m.picking_id
                        left join product_product pp on pp.id = m.product_id
                        left join product_template pt on pt.id = pp.product_tmpl_id
                        left join product_category c on c.id = pt.categ_id
                        left join product_category cp on cp.id = c.parent_id
                        left join product_stock_type st on st.id = pt.stock_type_id
                        left join product_uom u on u.id = m.product_uom
                        left join product_uom pu on pu.id = pt.uom_id
                        left join res_partner rp on rp.id = m.partner_id
                        left join x_product_supplier_category xpsc on xpsc.id=rp.x_supplier_category
                        left join stock_location sl on sl.id = m.location_id
                        left join stock_location sld on sld.id = m.location_dest_id
                        left join stock_return_reason srr on srr.id = m.return_reason_id
                        left join account_move am on am.ref=m.origin
                    where  %s 
                    order by m.id
                    """#uid,uid,domain
    _reverse_sql = """
                INSERT INTO stock_move_report
                    (
                        create_uid,
                        write_uid,
                        create_date,
                        write_date,
                        move_id,
                        date,
                        date_expected,
                        origin,
                        invoice_name,
                        picking_id,
                        picking_name,
                        type,
                        pick_return,
                        partner_ref,
                        partner_id,
                        partner_category,
                        partner_name,
                        stock_type_id,
                        stock_type_name,
                        category_id,
                        category_name,
                        product_sku,
                        product_id,
                        product_name,
                        move_qty,
                        product_qty,
                        uom_id,
                        uom_name,
                        product_uom_name,
                        uom_factor,
                        product_price,
                        price_unit,
                        cost_total,
                        po_price,
                        amount_total,
                        loc_name,
                        loc_dest_name,
                        return_reason
                    )
                SELECT %d, %d, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                        m.id as move_id, m.date, m.date_expected, m.origin,
                        am.name as invoice_name,
                        p.id as picking_id, p.name as picking_name, 
                        p.type as type, p.return as pick_return,
                        rp.ref as partner_ref, rp.id as partner_id, 
                        xpsc.x_name as partner_category, rp.name as partner_name,
                        st.id as stock_type_id , st.name as stock_type_name,
                        c.id as category_id, cp.name || ' / ' || c.name as category_name,
                        m.product_code as product_sku, pp.id as product_id, pt.name as product_name,
                        -m.product_qty as product_qty, -m.product_qty * pu.factor / u.factor,
                        u.id as uom_id, u.name as uom_name, pu.name as product_uom_name, pu.factor / u.factor as uom_facotr,
                        m.price_unit / pu.factor * u.factor as product_price, m.price_unit as price_unit, round(-m.product_qty * pu.factor / u.factor *m.price_unit,4) as cost_total,
                        m.po_price as po_price, m.amount_total as amount_total,
                        sl.complete_name as location_name,
                        sld.complete_name as location_dest_name,
                        srr.code as return_reason
                    from stock_move m
                        left join stock_picking p on p.id = m.picking_id
                        left join product_product pp on pp.id = m.product_id
                        left join product_template pt on pt.id = pp.product_tmpl_id
                        left join product_category c on c.id = pt.categ_id
                        left join product_category cp on cp.id = c.parent_id
                        left join product_stock_type st on st.id = pt.stock_type_id
                        left join product_uom u on u.id = m.product_uom
                        left join product_uom pu ON (pt.uom_id=pu.id)
                        left join res_partner rp on rp.id = m.partner_id
                        left join x_product_supplier_category xpsc on xpsc.id=rp.x_supplier_category
                        left join stock_location sl on sl.id = m.location_id
                        left join stock_location sld on sld.id = m.location_dest_id
                        left join stock_return_reason srr on srr.id = m.return_reason_id
                        left join account_move am on am.ref=m.origin
                    WHERE  %s 
                    ORDER BY m.id;
                    """#uid,uid,domain
    _in_header = " date, origin, invoice_name, picking_name, type, pick_return, partner_ref, partner_name, partner_category, stock_type_name, category_name, product_sku, product_id, product_name, move_qty, product_qty, uom_name, product_uom_name, product_price, po_price, amount_total, loc_name, loc_dest_name, return_reason"
    _out_header = " date, origin, invoice_name, picking_name, type, pick_return, partner_ref, partner_name, partner_category, stock_type_name, category_name, product_sku, product_id, product_name, move_qty, product_qty, uom_name, product_uom_name, uom_factor, product_price, price_unit, cost_total, loc_name, loc_dest_name, return_reason"
    _read_header = " date, origin, invoice_name, picking_name, type, pick_return, partner_ref, partner_name, partner_category, stock_type_name, category_name, product_sku, product_id, product_name, move_qty, product_qty, uom_name, product_uom_name, uom_factor, product_price, price_unit, cost_total, loc_name, loc_dest_name, return_reason"
    _read_sql = """
        SELECT %s FROM stock_move_report;
        """
    
    def _get_table_data(self, cr, uid, type, context=None):
        #print "==============#LY %s"% self._read_sql
        if type == "in":
            header = self._in_header
        elif type== "out":
            header = self._out_header
        else:
            header = self._read_header
        
        sql = self._read_sql%header
        cr.execute(sql)
        content = cr.fetchall()
        header = header.split(',')
        return header, content
    
    def _get_warehouse_group(self, cr, uid, name="Warehouse"):
        group_ids = self.pool.get('mail.group').search(cr, uid, [('name', 'ilike', name)])
        return group_ids and group_ids[0] or False
    
    def _prepare_filter(self, cr, uid, context=None):
        if not context:
            context={}
        
        start_date = context.get('start_date','2013-03-31 16:00:00') #timezone 'CST' to 'UTC'
        end_date = context.get('end_date','2013-04-30 15:59:59')# timezone 'CST' to 'UTC'
        type = context.get('type','in')
        res="""
            m.date >= '%s'
                        and m.date <= '%s'
                        and m.state = 'done'
            """%(start_date, end_date)
        if type == 'in':
            res += """AND (p.type = 'in' and p.return='none')
                    """
        elif type == 'out':
            res += """AND (p.type = 'out' and p.return='none')
                    """
        elif type == 'internal':
            res += """and p.type = 'internal'
                    """
        elif type == 'scrap':
            res += """AND m.location_id IN (SELECT id FROM stock_location WHERE usage='inventory')
                        AND m.location_dest_id NOT IN (SELECT id FROM stock_location WHERE usage='inventory')
                    """
        elif type == 'consumption':
            res += """AND m.production_id IS NULL
                        AND m.location_id NOT IN (SELECT id FROM stock_location WHERE usage='production')
                        AND m.location_dest_id IN (SELECT id FROM stock_location WHERE usage='production')
                    """
        elif type == 'production':
            res += """AND m.production_id IS NOT NULL
                        AND m.location_id IN (SELECT id FROM stock_location WHERE usage='production')
                        AND m.location_dest_id NOT IN (SELECT id FROM stock_location WHERE usage='production')
                    """
        return res
    
    def _reverse_filter(self, cr, uid, context=None):
        if not context:
            context={}
        
        start_date = context.get('start_date','2013-03-31 16:00:00') #timezone 'CST' to 'UTC'
        end_date = context.get('end_date','2013-04-30 15:59:59')# timezone 'CST' to 'UTC'
        type = context.get('type','in')
        res="""
            m.date >= '%s'
                        AND m.date <= '%s'
                        AND m.state = 'done'
            """%(start_date, end_date)
        
        if type == 'in':
            res += """AND (p.type = 'out' AND p.return='supplier')
                    """
        elif type == 'out':
            res += """AND (p.type = 'in' AND p.return='customer')
                    """
        elif type == 'scrap':
            res += """AND m.location_id NOT IN (SELECT id FROM stock_location WHERE usage='inventory')
                        AND m.location_dest_id IN (SELECT id FROM stock_location WHERE usage='inventory')
                    """
#         elif type == 'consumption':
#             res += """AND m.production_id IS NULL
#                         AND m.location_id NOT IN (SELECT id FROM stock_location WHERE usage='production')
#                         AND m.location_dest_id IN (SELECT id FROM stock_location WHERE usage='production')
#                     """
#         elif type == 'production':
#             res += """AND m.production_id IS NOT NULL
#                         AND m.location_id NOT IN (SELECT id FROM stock_location WHERE usage='production')
#                         AND m.location_dest_id IN (SELECT id FROM stock_location WHERE usage='production')
#                     """
        else:
            res="False"
        return res
    
    def _create_message(self, cr, uid, attachment_ids=None,context=None):
        mess_pool = self.pool.get('mail.message')
        partner_ids = [uid]
        if uid != 1:
            partner_ids.append(1)
        
        tz = pytz.timezone(context.get('tz','Asia/Kolkata'))
        tznow = pytz.utc.localize(datetime.now()).astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
        message_id = mess_pool.create(cr, uid, {
                'type': 'notification',
                'partner_ids': partner_ids,
                'subject': 'Your Move Report has been generated %s'%tznow,
                'body': 'Your Move Report has been generated %s'%tznow,
                'subtype_id': 1,
                'res_id': self._get_warehouse_group(cr, uid),
                'model': 'mail.group',
                'record_name': 'Stock Move Report',
                'attachment_ids': attachment_ids
            })
        mess_pool.set_message_starred(cr, uid, [message_id], True)
        return message_id
    
    _columns = {
        'move_id':          fields.many2one('stock.move', 'Stock Move', required=True),
        'date_expected':    fields.datetime('Date Expected'),
        'date':             fields.datetime('Date'),
        'origin':           fields.char('Origin', size=32),
        'invoice_name':     fields.char('Invoice Name', size=64),
        'picking_id':       fields.many2one('stock.picking', 'Stock Picking'),
        'picking_name':     fields.char('Picking Name', size=64),
        'type':             fields.char('Type', size=16),
        'pick_return':      fields.char('Return', size=16),
        'return_reason':    fields.char('Return Reason', size=16),
        'partner_ref':      fields.char('Partner Ref', size=16),
        'partner_name':     fields.char('Partner Name', size=128),
        'partner_id':       fields.many2one('res.partner', 'Partner'),
        'partner_category': fields.char('Supplier Category', size=128),
        'stock_type_id':    fields.many2one('product.stock_type',string='Stock Type'),
        'stock_type_name':  fields.char('Stock Type Name', size=128),
        'category_id':      fields.many2one('product.category',string='Category'),
        'category_name':    fields.char('Category Name', size=128),
        'product_sku':      fields.char('SKU', size=16),
        'product_name':     fields.char('Product Name', size=1024),
        'product_id':       fields.many2one('product.product', 'Product'),
        'move_qty':         fields.float("Move Quantity", digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_qty':      fields.float("Product Quantity", digits_compute=dp.get_precision('Product Unit of Measure')),
        'uom_id':           fields.many2one('product.uom',string='UoM'),
        'uom_factor':       fields.float('Uom Ratio' ,digits=(12, 12),
                                    help='How much bigger or smaller this unit is compared to the reference Unit of Measure for this category:\n'\
                                        '1 * (reference unit) = ratio * (this unit)'),
        'uom_name':         fields.char('UoM Name', size=32),
        'product_uom_name': fields.char('Product UoM', size=32),
        'loc_name':         fields.char('Source Location Name', size=256),
        'loc_dest_name':    fields.char('Dest Location Name', size=256),
        'po_price':         fields.float("PO Price", digits_compute=dp.get_precision('Account')),
        'product_price':    fields.float("Product Price", digits_compute=dp.get_precision('Account')),
        'price_unit':       fields.float("Price Unit", digits_compute=dp.get_precision('Account')),
        'amount_total':     fields.float("Purchase total", digits_compute=dp.get_precision('Account')),
        'cost_total':       fields.float("Cost Total", digits_compute=dp.get_precision('Account')),
    }
    _defaults = {
    }    
    
    def all_files(self,path):
        for child in Path(path).iterdir():
            yield str(child)
            if child.is_dir():
                for grand_child in all_files(str(child)):
                    yield str(Path(grand_child))


    def generate_report(self, cr, uid, context=None):

        start_date = context.get('start_date','2013-03-31 16:00:00') #timezone 'CST' to 'UTC'
        end_date = context.get('end_date','2013-04-30 15:59:59')# timezone 'CST' to 'UTC'

        cr.execute("""TRUNCATE TABLE stock_move_report""")
        
        filter = self._prepare_filter(cr, uid, context)
        #create sql
        sql = self._create_sql%(uid, uid, filter)
        cr.execute(sql)
        #reverse sql
        type = context.get('type','in')
        if type not in ('consumption','production'):
            filter = self._reverse_filter(cr, uid, context)
            sql = self._reverse_sql%(uid, uid, filter)
            if sql:
                cr.execute(sql)
        #create fold
        if not os.path.exists('/tmp/oe-report/'):
            os.mkdir('/tmp/oe-report')
        filelist = glob.glob("/tmp/oe-report/*.xlsx")
        for f in filelist:
            os.remove(f)
        os.chmod('/tmp/oe-report',0777)#check rights  

        #TODO
        header, content = self._get_table_data(cr, uid, type, context)
        
        csv_file = '/tmp/stock.move.report.csv'
        with open(csv_file, "wb") as f:
            fileWriter = csv.writer(f, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
            fileWriter.writerow(header)
            fileWriter.writerows(content)
        #cr.execute("COPY stock_move_in_report TO '/tmp/oe-report/stock.move.report.csv' WITH CSV HEADER NULL AS '' DELIMITER ';'")
        
        #create message
        message_id = self._create_message(cr, uid,context=context)
        
        attachment_pool = self.pool.get('ir.attachment')
        
        def convert_time(time):
            tz = pytz.timezone('Asia/Kolkata')
            time = pytz.utc.localize(datetime.strptime(time,'%Y-%m-%d %H:%M:%S')).astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
            return time
        period = "%s~%s"%(convert_time(context.get('start_date','2013-03-31 16:00:00')),convert_time(context.get('end_date','2013-03-31 16:00:00')))
        
        xlsfile = '/tmp/oe-report/stock.move.report.%s[%s].xlsx'%(type,period)
        #print xlsfile
        w = Workbook(xlsfile)
        # ws = w.add_worksheet('Stock Moves')
        
        #ufile = open(csv_file,'r')
        # spamreader = csv.reader(ufile, delimiter=',', quotechar='"')
        # #line = 0
        # for rowx, row in enumerate(spamreader):
        #     for colx, cell in enumerate(row):
        #         ws.write(rowx, colx, unicode(cell, 'utf-8'))

        wsu = w.add_worksheet('Summary Report')
        
        reader = csv.DictReader(open(csv_file))

        # Code for Summary sheet
        result = {}
        duplicate = {}
        for row in reader:

            key = row.pop(' category_name')
            opening_location = row.pop(' loc_dest_name')
            partner_category = row.pop(' partner_category')
            invoice_name = row.pop(' invoice_name')
            pick_type = row.pop(' type')
            amount = row.pop(' cost_total')
            loc_name = row.pop(' loc_name')
            product_id = row.pop(' product_id')
            

            # Get quantity of product available on a particular day
            if not key:
                continue

            # Create Hash of Hashes
            if key not in result:
                result[key] = {}

            if product_id not in duplicate:
                if 'opening_stock' not in result[key]:
                    result[key]['opening_stock'] = 0.00
                if 'closing_stock' not in result[key]:
                    result[key]['closing_stock'] = 0.00
                if 'opening_pharmacy' not in result[key]:
                    result[key]['opening_pharmacy'] = 0.00
                if 'closing_pharmacy' not in result[key]:
                    result[key]['closing_pharmacy'] = 0.00

                pp_obj = self.pool['product.product']
                ctx = context.copy()
                ctx['from_date'] = context['start_date']
                ctx['location'] = 'Stock'
                pp_res = pp_obj.get_product_available(cr, uid, [product_id], context=ctx)
                result[key]['opening_stock'] += pp_res[product_id]
                ctx['location'] = 'Pharmacy'
                pp_res = pp_obj.get_product_available(cr, uid, [product_id], context=ctx)
                result[key]['opening_pharmacy'] += pp_res[product_id]
                ctx['to_date'] = context['end_date']
                ctx['location'] = 'Stock'
                pp_res = pp_obj.get_product_available(cr, uid, [product_id], context=ctx)
                result[key]['closing_stock'] += pp_res[product_id]
                ctx['location'] = 'Pharmacy'
                pp_res = pp_obj.get_product_available(cr, uid, [product_id], context=ctx)
                result[key]['closing_pharmacy'] += pp_res[product_id]


            if(pick_type == 'in'):
                if(partner_category):
                    if 'additions' not in result[key]:
                        result[key]['additions'] = {}
                    if partner_category not in result[key]['additions']:
                        result[key]['additions'][partner_category] = {}

                    if not invoice_name:
                        continue

                    if invoice_name not in result[key]['additions'][partner_category]:
                        result[key]['additions'][partner_category][invoice_name] = {}
                        result[key]['additions'][partner_category][invoice_name]['amount'] = 0.00 

                    result[key]['additions'][partner_category][invoice_name]['amount'] += float(amount)

            if(pick_type == 'out'):
                if 'usage' not in result[key]:
                    result[key]['usage'] = {}

                if loc_name not in result[key]['usage']:
                    result[key]["usage"][loc_name] = {}
                    result[key]["usage"][loc_name]['amount'] = 0.00

                if not amount:
                    amount = 0.00
                
                result[key]["usage"][loc_name]['amount'] += float(amount)

        # Add content to workbook
        bold = w.add_format({'bold': True})

        wsu.set_column('A:A', 5)

        merge_format_header = w.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size':16})

        wsu.merge_range('F2:I2', 'OpenERP Report for Finance', merge_format_header)

        wsu.write('D4', "Date", bold)
        wsu.write('E4', time.strftime("%d/%m/%Y"))

        # Create a format for opening balance.
        merge_format_opening = w.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#FCD5B5'})

        wsu.merge_range('D5:E5', 'Opening Balance', merge_format_opening)

        merge_format_additions = w.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#D9D9D9'})

        wsu.merge_range('F5:G5', 'Additions', merge_format_additions)

        
        merge_format_additions_total = w.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#E6E0EC'})

        merge_format_usage_total = w.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#B9CDE5'})

        merge_format_usage = w.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#B7DEE8'})

        wsu.merge_range('H5:I5', 'Usage', merge_format_usage)

        merge_format_closing = w.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#B3B1A9'})

        wsu.merge_range('J5:K5', 'Closing Balance', merge_format_closing)

        # set column widths
        wsu.set_column(3, 3, 18)
        wsu.set_column(5, 5, 25)
        wsu.set_column(7, 7, 20)

        row_counter = 6
        col_counter = 3
       
        total_additions = 0.00
        total_usage = 0.00

        for key in result:
            #Create counters
            opening_counter = row_counter
            additions_counter = row_counter
            usage_counter = row_counter
            closing_counter = row_counter

            # Product Category
            wsu.write(opening_counter, col_counter, key, bold)

            opening_counter += 1
            closing_counter += 1

            # Opening Balances
            wsu.write(opening_counter, col_counter, "Stock", merge_format_opening)
            wsu.write(opening_counter, col_counter+1, result[key]['opening_stock'], bold)
            opening_counter += 1
            wsu.write(opening_counter, col_counter, "Pharmacy", merge_format_opening)
            wsu.write(opening_counter, col_counter+1, result[key]['opening_pharmacy'], bold)
            opening_counter += 1


            if 'additions' in result[key]:
                for category in result[key]['additions']:
                    additions_counter += 1
                    wsu.write(additions_counter, col_counter+2, category, merge_format_additions)
                    additions_counter += 1
                    for invoice in result[key]['additions'][category]:
                        wsu.write(additions_counter, col_counter+2, invoice)
                        wsu.write(additions_counter, col_counter+3, result[key]['additions'][category][invoice]['amount'], merge_format_additions)
                        total_additions += result[key]['additions'][category][invoice]['amount']
                        additions_counter += 1

            # Usages
            if 'usage' in result[key]:
                usage_counter += 1
                for usage_key in result[key]['usage']:
                    wsu.write(usage_counter, col_counter+4, usage_key)
                    wsu.write(usage_counter, col_counter+5, result[key]['usage'][usage_key]['amount'], merge_format_usage)
                    total_usage += result[key]['usage'][usage_key]['amount']
                    usage_counter += 1

            # Closing Balances
            wsu.write(closing_counter, col_counter+6, "Stock", merge_format_closing)
            wsu.write(closing_counter, col_counter+7, (result[key]['closing_stock']), bold)
            closing_counter += 1
            wsu.write(closing_counter, col_counter+6, "Pharmacy", merge_format_closing)
            wsu.write(closing_counter, col_counter+7, result[key]['closing_pharmacy'], bold)
            closing_counter += 1

            max_counter = max(opening_counter,additions_counter,usage_counter,closing_counter)
            row_counter = max_counter + 1

            wsu.write(row_counter, col_counter, "Total OB", merge_format_opening)
            wsu.write(row_counter, col_counter+1, result[key]['opening_stock']+result[key]['opening_pharmacy'], merge_format_opening)
            wsu.write(row_counter, col_counter+2, "Total Addition", merge_format_additions_total)
            wsu.write(row_counter, col_counter+3, total_additions, merge_format_additions_total)
            wsu.write(row_counter, col_counter+4, "Total Usage", merge_format_usage_total)
            wsu.write(row_counter, col_counter+5, total_usage, merge_format_usage_total)
            wsu.write(row_counter, col_counter+6, "Total CB", merge_format_closing)
            wsu.write(row_counter, col_counter+7, result[key]['closing_stock']+result[key]['closing_pharmacy'], merge_format_closing)

            row_counter = row_counter + 2

        w.close()

        zip_filename = '/{0}/{1}_{2}[{3}].zip'.format("tmp", "stock_move_report",type, period)
        zf = zipfile.ZipFile(zip_filename, "w")
        for file in self.all_files("/tmp/oe-report/"):
            zf.write(file)
        zf.close()

        with open(zip_filename, "rb") as f:
            attachment_id = attachment_pool.create(cr, uid, {
               'name': "stock.move.report.%s[%s].zip"%(type,period),
               'datas': base64.encodestring(f.read()),
               'datas_fname': "stock.move.report.%s[%s].zip"%(type,period),
               'res_model': 'mail.message',
               'res_id': message_id,
            })
            cr.execute("""
               INSERT INTO message_attachment_rel(
                   message_id, attachment_id)
                   VALUES (%s, %s);
                   """, (message_id, attachment_id))
                    
        return True

stock_move_report()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
