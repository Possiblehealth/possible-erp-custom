# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp.tools import float_compare
from openerp.tools.translate import _


class stock_move(osv.osv):
    _inherit = 'stock.move'
    
    # inherited this method to pass location_id while onchange_quantity method is called
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False, context=None):
        """ On change of product id, if finds UoM, UoS, quantity and UoS quantity.
        @param prod_id: Changed Product id
        @param loc_id: Source location id
        @param loc_dest_id: Destination location id
        @param partner_id: Address id of partner
        @return: Dictionary of values
        """
        # print "Location---------------"
        # print loc_id
        # print loc_dest_id

        if not prod_id:
            return {}
        lang = False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
        uos_id  = product.uos_id and product.uos_id.id or False
        qty =0.0
        if(loc_id):
            qty = self._get_stock_for_location(cr, uid, loc_id, prod_id)

        result = {
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            'product_qty': 0.00,
            'product_uos_qty' : self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id, loc_id)['value']['product_uos_qty'],
            'prodlot_id' : False,
            'stock_available':qty
            }
        if not ids:
            result['name'] = product.partner_ref
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}
    
#     product_id, product_qty, product_uom, product_uos, location_id, parent.move_lines, context
    #over ridden this method to raise warning for product when quantity on hand is less than required
    def onchange_quantity(self, cr, uid, ids, product_id, product_qty,
                          product_uom, product_uos, loc_id=False, move_lines=False, context=None, loc_dest_id=False):
        """ On change of product quantity finds UoM and UoS quantities
        @param product_id: Product id
        @param product_qty: Changed Quantity of product
        @param product_uom: Unit of measure of product
        @param product_uos: Unit of sale of product
        @return: Dictionary of values
        """
        result = {
            'product_uos_qty': 0.00
        }

        # print "Location OnChange---------------"
        # print loc_id
        # print loc_dest_id

        warning = {}
        warn_msgs = ''
        if (not product_id) or (product_qty < 0.0):
            result['product_qty'] = 0.0
            return {'value': result}

        product_obj = self.pool.get('product.product')
        uos_coeff = product_obj.read(cr, uid, product_id, ['uos_coeff'])
        
        
        context = context or {}
        context.update({'location': loc_id or context.get('location')})

        product_brw_obj = product_obj.browse(cr, uid, product_id, context)
        virtual_available = product_brw_obj.virtual_available
        qty_available = product_brw_obj.qty_available
        product_uom_brw = self.pool.get('product.uom').browse(cr, uid, product_uom)
        if product_qty:
            if (int(float_compare(virtual_available, product_qty, precision_rounding=product_uom_brw.rounding))==-1)\
                and product_brw_obj.type=='product' and product_brw_obj.procure_method=='make_to_stock':
                warn_msg = _('You plan to move %.2f %s but you only have %.2f %s available !\nThe real stock is %.2f %s. (without reservations)') % \
                        (product_qty, product_uom_brw.name,
                        max(0,virtual_available), product_uom_brw.name,
                        max(0,qty_available), product_uom_brw.name)
                warn_msgs += _("Not enough stock ! :\n ") + warn_msg + "\n\n"
  
        # Warn if the quantity was decreased
        if ids:
            for move in self.read(cr, uid, ids, ['product_qty']):
                if product_qty < move['product_qty']:
                    warn_msgs += _("By changing this quantity here, you accept the "
                                    "new quantity as complete: OpenERP will not "
                                    "automatically generate a back order.")
                    warn_msgs += _("Information :\n ") + warn_msg + "\n\n"
 
                break
 
        factor = 1
        if product_uos and product_uom and (product_uom != product_uos):
            result['product_uos_qty'] = product_qty * uos_coeff['uos_coeff']
        else:
            result['product_uos_qty'] = product_qty
 
        if(product_uom):
            product_uom_brw = self.pool.get('product.uom').browse(cr,uid,product_uom)
            factor = product_uom_brw.factor
 
        qty = 0.0
        if(loc_id):
            qty = self._get_stock_for_location(cr, uid, loc_id, product_id) * factor - product_qty
 
        if(move_lines):
            for move in move_lines:
                move_line = move[2]
                if(move_line and move_line['product_id'] and move_line['product_id'] == product_id):
                    qty -= move_line['product_qty']
            for move in move_lines:
                move_line = move[2]
                if(move_line and move_line['product_id'] and move_line['product_id'] == product_id):
                    move_line['product_qty'] = qty
 
        result['stock_available'] = qty
        result['move_lines'] = move_lines
        if warn_msgs:
            warning = {
                'title': _('Warning!'),
                'message' : warn_msgs
            }

        return {'value': result, 'warning': warning,'stock_available':qty}
    