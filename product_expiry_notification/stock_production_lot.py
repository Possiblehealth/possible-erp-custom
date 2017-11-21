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
"""inherits from stock.production.lot adds functionally for warn prodlot expiration"""

from osv import osv, fields
from datetime import datetime, timedelta
from tools.translate import _

class stock_production_lot(osv.osv):
    """inherits from stock.production.lot adds functionally for warn prodlot expiration"""
    _inherit = 'stock.production.lot'

    def _get_if_expired(self, cr, uid, ids, field_name, arg, context=None):
        """get if prodlots is expired based on life_date"""
        if context is None: context = {}
        res = {}
        for obj_prodlot_id in self.browse(cr, uid, ids):
            if obj_prodlot_id.life_date:
                value = False
                #check if prodlot is expired
                if datetime.strptime(obj_prodlot_id.life_date, "%Y-%m-%d %H:%M:%S") < datetime.now():
                    value = True
                res[obj_prodlot_id.id] = value
            else:
                res[obj_prodlot_id.id] = False
        return res

    def _get_if_expiring_in_30_days(self, cr, uid, ids, field_name, arg, context=None):
        """get if prodlots is expired based on life_date"""
        if context is None: context = {}
        res = {}
        for obj_prodlot_id in self.browse(cr, uid, ids):
            if obj_prodlot_id.life_date:
                value = False
                #check if prodlot is expired
                if (datetime.strptime(obj_prodlot_id.life_date, "%Y-%m-%d %H:%M:%S") > datetime.now()
                    and datetime.strptime(obj_prodlot_id.life_date, "%Y-%m-%d %H:%M:%S") < (datetime.now()+timedelta(days=30))):
                    value = True
                res[obj_prodlot_id.id] = value
            else:
                res[obj_prodlot_id.id] = False
        return res

    def _get_if_expiring_in_60_days(self, cr, uid, ids, field_name, arg, context=None):
        """get if prodlots is expired based on life_date"""
        if context is None: context = {}
        res = {}
        for obj_prodlot_id in self.browse(cr, uid, ids):
            if obj_prodlot_id.life_date:
                value = False
                #check if prodlot is expired
                if (datetime.strptime(obj_prodlot_id.life_date, "%Y-%m-%d %H:%M:%S") >= (datetime.now()+timedelta(days=30))
                    and datetime.strptime(obj_prodlot_id.life_date, "%Y-%m-%d %H:%M:%S") < (datetime.now()+timedelta(days=60))):
                    value = True
                res[obj_prodlot_id.id] = value
            else:
                res[obj_prodlot_id.id] = False
        return res

    def _get_if_expiring_in_90_days(self, cr, uid, ids, field_name, arg, context=None):
        """get if prodlots is expired based on life_date"""
        if context is None: context = {}
        res = {}
        for obj_prodlot_id in self.browse(cr, uid, ids):
            if obj_prodlot_id.life_date:
                value = False
                #check if prodlot is expired
                if (datetime.strptime(obj_prodlot_id.life_date, "%Y-%m-%d %H:%M:%S") >= (datetime.now()+timedelta(days=60))
                    and datetime.strptime(obj_prodlot_id.life_date, "%Y-%m-%d %H:%M:%S") < (datetime.now()+timedelta(days=90))):
                    value = True
                res[obj_prodlot_id.id] = value
            else:
                res[obj_prodlot_id.id] = False
        return res

    _columns = {
        'expired': fields.function(_get_if_expired, method=True, type="boolean", string="Expired",
            store={'stock.production.lot': (lambda self, cr, uid, ids, c={}: ids, None, 20)}),
        'expire_30': fields.function(_get_if_expiring_in_30_days, method=True, type="boolean", string="Expiring in 30 days",
            store={'stock.production.lot': (lambda self, cr, uid, ids, c={}: ids, None, 20)}),
        'expire_30_60': fields.function(_get_if_expiring_in_60_days, method=True, type="boolean", string="Expiring in 30 to 60 days",
            store={'stock.production.lot': (lambda self, cr, uid, ids, c={}: ids, None, 20)}),
        'expire_60_90': fields.function(_get_if_expiring_in_90_days, method=True, type="boolean", string="Expiring in 60 to 90 days",
            store={'stock.production.lot': (lambda self, cr, uid, ids, c={}: ids, None, 20)})
    }

    #pylint: disable-msg=W0613
    def searchfor_expired_prodlots(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        """cron that search for expired prodlots and mark its with expired everyday, send a notification too"""
        if context is None: context = {}
        today = datetime.now().strftime('%Y-%m-%d 00:00:00')

        ids = self.search(cr, uid, [('life_date', '<', today), ('expired', '=', False)])

        if ids:
            self.write(cr, uid, ids, {})

            group_id = self.pool.get('res.groups').search(cr, uid, [('name', '=', 'Production Lots / Expiration Notifications')])

            if group_id:
                group_id = group_id[0]

                cr.execute("select uid from res_groups_users_rel where gid = %s" % (group_id,))

                res = cr.fetchall()

                #get a string coma list from object case prodlots collection
                # pylint: disable-msg=W0141
                expired_lots_names = u','.join(map(str, map(lambda x:x.name, self.browse(cr, uid, ids))))

                message = _("New production lots expired. Now you should not use these prodlots. n\nLots names: %s\n\n") % (expired_lots_names,)

                for (user_id,) in res:
                    self.pool.get('res.request').create(cr, uid, {
                            'name': _("Production Lots Expired"),
                            'body': message,
                            'state': 'waiting',
                            'act_from': uid,
                            'act_to': user_id,
                            'priority': '0'
                        })

        return True

stock_production_lot()