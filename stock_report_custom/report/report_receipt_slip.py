# -*- coding: utf-8 -*-
from openerp.report import report_sxw
from dateutil.tz import tzlocal,tzutc
from datetime import datetime

class picking(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_product_desc':self.get_product_desc,
            'get_formatted_date':self.get_formatted_date,
            'get_total': self.get_total
        })

    def get_formatted_date(self, date):
        utcdate = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').replace(tzinfo=tzutc())
        localdate = utcdate.astimezone(tzlocal()).strftime('%m/%d/%Y %H:%M:%S')
        return localdate

    def get_product_desc(self,move_line):
        desc = move_line.product_id.name
        if move_line.product_id.default_code:
            desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        return desc
    
    def get_total(self, picking):
        amount_total = 0.0
        amount_untaxed = 0.0
        amount_taxed = 0.0
        move_line_product_ids  = [l.product_id.id for l in picking.move_lines]
        prd_wise_qty = {} # dictionary to maintain quantities by product_id
        for ln in picking.move_lines:
            if not ln.product_id in prd_wise_qty.keys():
                prd_wise_qty.update({ln.product_id.id: ln.product_qty})
            else:
                qty = prd_wise_qty.get(ln.product_id.id)
                prd_wise_qty.update({ln.product_id.id: qty+ln.product_qty})
        if picking.purchase_id:
            for p_line in picking.purchase_id.order_line:
                if p_line.product_id.id in move_line_product_ids:
                    product_tax_amount = 0.0
                    prd_qty = prd_wise_qty.get(p_line.product_id.id)
                    for c in self.pool.get('account.tax').compute_all(self.cr, self.uid, p_line.taxes_id, p_line.price_unit, 
                                                                      prd_qty, p_line.product_id, p_line.order_id.partner_id)['taxes']:
                        product_tax_amount += c.get('amount')
                        amount_taxed += c.get('amount')
                    amount_untaxed += p_line.price_unit * prd_qty
                    amount_total += (p_line.price_unit * prd_qty) + product_tax_amount
        else:
            for line in picking.move_lines:
                amount_total += line.price_unit
        return {'amount_total': amount_total,
                'amount_taxed': amount_taxed,
                'amount_untaxed': amount_untaxed}


report_sxw.report_sxw('report.stock.picking.receipt_slip','stock.picking',
                      'addons/bahmni_internal_stock_move/report/picking_ext.rml',parser=picking)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: