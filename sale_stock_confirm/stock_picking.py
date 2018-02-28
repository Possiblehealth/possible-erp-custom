# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp.tools import float_compare



class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def draft_force_assign(self, cr, uid, ids, *args):
        """ Confirms picking directly from draft state.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            context = args and args[0] if args else {}
            context.update({'location': pick.location_id.id})
            unavailable_products = []   # list to store product name, for which quantity on hand is less than qty in move line
            for move in pick.move_lines:
                available_qty = self.pool.get('product.product').browse(cr, uid, move.product_id.id, context=context).virtual_available
                # check for unavailable products
                if (int(float_compare(available_qty, move.product_qty, precision_rounding=move.product_uom.rounding))==-1) \
                    and move.product_id.type=='product' and move.product_id.procure_method=='make_to_stock':
                    unavailable_products.append(move.product_id.name + ' | Available Qty : %.2f %s'%(available_qty if available_qty>=0 else 0, move.product_uom.name))
                    
            unavailable_products = [str(i)+'. '+x for i, x in enumerate(unavailable_products, 1)]
            if unavailable_products:
                warn_msg = _('Quantities you are trying to transfer are not available at location : %s\n%s'%(pick.location_id.name, '\n'.join(unavailable_products),))
                raise osv.except_osv(_("Not enough stock !"), warn_msg)
            else: 
                if not pick.move_lines:
                    raise osv.except_osv(_('Error!'),_('You cannot process picking without stock moves.'))
                wf_service.trg_validate(uid, 'stock.picking', pick.id,
                    'button_confirm', cr)
        return True
    
    def onchange_location(self, cr, uid, ids, location_id, location_dest_id, move_lines, context=None):
        warning = {}
        unavailable_prds = []
        context = context.copy() if context else {}
        context.update({'location_id': location_id})
        for move_line in move_lines:
            move_line_vals = move_line[2] if len(move_line)==3 else {}
            if move_line_vals:
                move_line[2] = move_line[2] if move_line[2] else {}
                move_line[2]['location_id'] = location_id
                move_line[2]['location_dest_id'] = location_dest_id
                product_id = move_line_vals.get('product_id')
                product_brw = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
                available_qty = product_brw.virtual_available
                product_uom_brw = self.pool.get('product.uom').browse(cr, uid, move_line_vals.get('product_uom'))
                if (int(float_compare(available_qty, move_line_vals.get('product_qty'), precision_rounding=product_uom_brw.rounding))==-1) \
                    and product_brw.type=='product' and product_brw.procure_method=='make_to_stock':
                    unavailable_prds.append(product_brw.name + ' | Available Qty : %.2f %s'%(available_qty if available_qty>=0 else 0, product_uom_brw.name))
        unavailable_prds = [str(i)+ '. '+x for i,x in enumerate(unavailable_prds,1)]
        if unavailable_prds:
            warn_msg = _('Quantities selected by you, are not available at selected source location: \n%s'%('\n'.join(unavailable_prds),))
            warning = {'title': _("Not enough stock ! : "),
                       'message': warn_msg}
        return {'value': {'move_lines': move_lines},
                'warning': warning}
    