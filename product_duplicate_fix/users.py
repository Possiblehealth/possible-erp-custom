# -*- encoding: utf-8 -*-
from openerp.osv import osv, fields


class res_users(osv.osv):
    _inherit = 'res.users'


    _columns = {
        'create_product': fields.boolean("Create/Duplicate Product"),
        }
    
    
