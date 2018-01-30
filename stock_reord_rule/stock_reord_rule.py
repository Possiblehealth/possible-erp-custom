# -*- encoding: utf-8 -*-
##############################################################################
#
#    Smart reordering rules for Bahmni OpenERP
#    Copyright (C) 2017 Ajeenckya Gadewar (<https://www.satvix.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, fields
import math


class stock_warehouse_orderpoint(orm.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _qty_orderpoint_days(self, cr, uid, ids, context=None):
        """Calculate quantity to create warehouse stock for n days of sales.
        Qty sold in days_stats * (1+forecast_gap)
                 / days_stats * days_warehouse)
        """

        obj_product = self.pool.get('product.product')
        product_ids = tuple(obj_product.search(cr, uid, [('days_stats','>',0)], context=context))
        sql = """
         SELECT sm.product_id AS product_id,
               round(sum(product_qty) / pp.days_stats *
                   (1 + 1 / 100) * pp.days_warehouse)
               AS quantity
        FROM stock_move sm
        JOIN stock_location sl ON sl.id = sm.location_id
        JOIN stock_picking sp ON sp.id = sm.picking_id
        JOIN product_product pp ON pp.id = sm.product_id
        JOIN product_template pt ON pt.id = pp.product_tmpl_id
        WHERE sl.name like '\%Storeroom'
        AND sp.type in ('internal','out')
        AND sm.product_id IN %s AND sm.date > (date(now()) - pp.days_stats)
        GROUP BY sm.product_id,
                 pp.days_stats,
                 pp.forecast_gap,
                 pp.days_warehouse;
        """
        cr.execute(sql, (product_ids,))
        sql_res = cr.fetchall()

        if sql_res:
            for val in sql_res:
                if val:
                    domain = [('product_id', '=', val[0])]
                    reord_rules_ids = self.search(cr, uid,
                                                  domain,
                                                  context=context)
                    if reord_rules_ids:
                        self.write(cr, uid,
                                   reord_rules_ids,
                                   {'product_min_qty': val[1],'product_max_qty': val[1]},
                                   context=context)
            # template = self.pool.get('ir.model.data').get_object(cr, uid, 'stock_reord_rule', 'email_template_customer_auto')
            # mail_id = self.pool.get('email.template').send_mail(cr, uid, template.id, res , force_send=True)
        return True


class product_product(orm.Model):
    _inherit = "product.product"

    _columns = {
        'days_warehouse': fields.integer('Days of needed warehouse stock'),
        'days_stats': fields.integer('Days of sale statistics'),
        'forecast_gap': fields.integer('Expected sales variation (percent +/-)')
        }
