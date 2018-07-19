# -*- coding: utf-8 -*-
from openerp.report import report_sxw
from dateutil.tz import tzlocal,tzutc
from datetime import datetime

class picking_slip_ext(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(picking_slip_ext, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_formatted_date':self.get_formatted_date,
            'get_product_desc': self.get_product_desc,
        })

    def get_formatted_date(self, date):
        utcdate = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').replace(tzinfo=tzutc())
        localdate = utcdate.astimezone(tzlocal()).strftime('%m/%d/%Y %H:%M:%S')
        return localdate

    def get_product_desc(self, move_line):
        desc = move_line.product_id.name
        if move_line.product_id.default_code:
            desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        return desc


report_sxw.report_sxw('report.stock.picking.picking_slip1','stock.picking',
                      'stock_report_custom/report/report_picking_slip.rml',parser=picking_slip_ext)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: