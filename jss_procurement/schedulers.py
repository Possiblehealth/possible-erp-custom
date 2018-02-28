# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import netsvc
from openerp import pooler
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import tools
from psycopg2 import OperationalError
import logging

logger = logging.getLogger(__name__)


class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    
    def _procure_confirm(self, cr, uid, ids=None, use_new_cursor=False, context=None):
        '''
        Call the scheduler to check the procurement order

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param use_new_cursor: False or the dbname
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        '''
        if context is None:
            context = {}
        try:
            if use_new_cursor:
                cr = pooler.get_db(use_new_cursor).cursor()
            wf_service = netsvc.LocalService("workflow")

            procurement_obj = self.pool.get('procurement.order')
            if not ids:
                ids = procurement_obj.search(cr, uid, [('state', '=', 'exception')], order="date_planned")
            for id in ids:
                wf_service.trg_validate(uid, 'procurement.order', id, 'button_restart', cr)
            if use_new_cursor:
                cr.commit()
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            maxdate = (datetime.today() + relativedelta(days=company.schedule_range)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
            start_date = fields.datetime.now()
            offset = 0
            prev_ids = []
            while True:
                ids = procurement_obj.search(cr, uid, [('state', '=', 'confirmed'),
                                                       ('procure_method', '=', 'make_to_order'),
                                                       ('date_planned', '<', maxdate)],
                                            offset=offset, limit=500, order='priority, date_planned',
                                            context=context)
                for proc in procurement_obj.browse(cr, uid, ids, context=context):
                    logger.info("proc jss make_to_order ===> %d"%(proc.id,))
                    try:
                        wf_service.trg_validate(uid, 'procurement.order', proc.id, 'button_check', cr)
                        if use_new_cursor:
                            cr.commit()
                    except OperationalError:
                        if use_new_cursor:
                            cr.rollback()
                            continue
                        else:
                            raise
                if not ids or prev_ids == ids:
                    break
                else:
                    prev_ids = ids
            ids = []
            prev_ids = []
            while True:
                ids = procurement_obj.search(cr, uid, [('state', '=', 'confirmed'), 
                                                       ('procure_method', '=', 'make_to_stock'), 
                                                       ('date_planned', '<', maxdate)],
                                             offset=offset, limit=500)
                for proc in procurement_obj.browse(cr, uid, ids):
                    logger.info("proc jss make_to_stock ===> %d"%(proc.id,))
                    try:
                        wf_service.trg_validate(uid, 'procurement.order', proc.id, 'button_check', cr)

                        if use_new_cursor:
                            cr.commit()
                    except OperationalError:
                        if use_new_cursor:
                            cr.rollback()
                            continue
                        else:
                            raise
                if not ids or prev_ids == ids:
                    break
                else:
                    prev_ids = ids

            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        return {}

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: