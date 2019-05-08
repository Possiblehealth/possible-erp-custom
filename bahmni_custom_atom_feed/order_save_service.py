# -*- coding: utf-8 -*-
import math
from datetime import datetime
import re
from itertools import groupby
from openerp.osv import osv, fields
from openerp import tools

import logging
_logger = logging.getLogger(__name__)

class OrderSaveService(osv.osv):
    _inherit = 'order.save.service'
    
    # this method is overridden to select most feasible product, depending on required volume for liquid products
    def _get_product_ids(self, cr, uid, order, context=None):
        if order['productId']:
            prod_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', order['productId'])], context=context)
        else:
            prod_ids = self.pool.get('product.product').search(cr, uid, [('name_template', '=ilike', order['conceptName'].strip())], context=context)
        return prod_ids
    
    # this method is overridden to set quantity of syrup type products depending on their volume 
    def _create_sale_order_line_function(self, cr, uid, name, sale_order, order, context=None):
        
        stored_prod_ids = self._get_product_ids(cr, uid, order, context=context)
        
        if(stored_prod_ids):
            liquid_drug_categ_names = ['syrup', 'suspension', 'cream']
            # this will split the product name with spaces, they will need to standardize the name format,
            # and accordingly with which character string needs to get split will be decided.
            prod_id = stored_prod_ids[0]
            prod_obj = self.pool.get('product.product').browse(cr, uid, prod_id)
            prod_tmpl_obj = self.pool.get('product.template').browse(cr, uid, prod_id)
            
            prod_categ_obj = self.pool.get('product.category').browse(cr, uid, prod_tmpl_obj.categ_id.id)
            
            product_categ_name = prod_categ_obj.name.lower()
            
            product_concept_name = order['conceptName'] 
            product_concept_name = re.sub(r'[\(\)]', '', product_concept_name)
            product_name_string = product_concept_name.lower().split()

            common = 0
            if(product_categ_name in liquid_drug_categ_names):
                common = 1
            # common = prod_categ_obj.intersection(set(liquid_drug_categ_names))
            
            sale_order_line_obj = self.pool.get('sale.order.line')
            prod_lot = sale_order_line_obj.get_available_batch_details(cr, uid, prod_id, sale_order, context=context)

            actual_quantity = order['quantity']
            comments = " ".join([str(actual_quantity), str(order.get('quantityUnits', None))])

            default_quantity_object = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'bahmni_sale_discount', 'group_default_quantity')[1]
            default_quantity_total = self.pool.get('res.groups').browse(cr, uid, default_quantity_object, context=context)
            default_quantity_value = 1
            if default_quantity_total and len(default_quantity_total.users) > 0:
                default_quantity_value = -1
            order['quantity'] = self._get_order_quantity(cr, uid, order, default_quantity_value)
            product_uom_qty = order['quantity']


            if common and order['productName']:

                # get the product with matching concept name and matching volume with required volume
                existing_products_with_same_name = self.pool.get('product.product').search(cr, uid,
                                                                                           [('name_template', '=ilike', order['productName'].strip())],
                                                                                           order='volume desc')

                if(len(existing_products_with_same_name) >= 1):
                    # loop on all products, check whether there exists a product, whose volume is less that this product's volume, 
                    # but greater than or equal to required volume
                    if existing_products_with_same_name[0] != prod_obj.id:
                        prod_obj = self.pool.get('product.product').browse(cr, uid, existing_products_with_same_name[0])
                        prod_lot = sale_order_line_obj.get_available_batch_details(cr, uid, prod_obj.id, sale_order, context=context)
                        comments = " ".join([str(actual_quantity)+'m(l/g)', str(order.get('quantityUnits', None))])
                        
                    # if there exists only single product with provided conceptname, then no matter only that product will get dispensed
                    if len(existing_products_with_same_name) == 1:
                        # if product belongs to syrup, suspension or cream type and volume is defined in product
                        if common and prod_obj.volume:     
                            product_uom_qty = math.ceil(product_uom_qty / prod_obj.volume)
                       

                    else:
                        product_found = False
                        visited_products = [existing_products_with_same_name[0]]
                        visited_product = self.pool.get('product.product').browse(cr, uid, existing_products_with_same_name[0])
                        while product_found is False:
                            prd_ids = self.pool.get('product.product').search(cr, uid, [('id', 'in', existing_products_with_same_name),
                                                                                        ('id', 'not in', visited_products),
                                                                                        ('volume', '<', visited_product.volume),
                                                                                        ('volume', '>=', order['quantity'])],
                                                                                        order='volume desc')
                            _logger.info("\n\n\n**** searched prd_ids=%s",prd_ids)
                            if not prd_ids:
                                product_found = True
                            else:
                                visited_products.append(prd_ids[0])
                        prod_obj = self.pool.get('product.product').browse(cr, uid, visited_products[-1])
                        prod_lot = sale_order_line_obj.get_available_batch_details(cr, uid, prod_obj.id, sale_order, context=context)
                        # if there exists multiple products with same name, then whatever volume is satisfied by product will get assigned to line
                        if product_uom_qty / prod_obj.volume > 0 and product_uom_qty / prod_obj.volume < 1:
                            product_uom_qty = 1
                        else:
                            product_uom_qty = math.floor(product_uom_qty / prod_obj.volume)
                        actual_quantity = product_uom_qty * prod_obj.volume
                        comments = " ".join([str(actual_quantity), str(order.get('quantityUnits', None))])
                
            # according to me this condition was wrong,
            # which is checking future_forecast qty is less than ordered quantity
            # if(prod_lot != None and order['quantity'] > prod_lot.future_stock_forecast):
            if(prod_lot is not None and order['quantity'] <= prod_lot.future_stock_forecast):
                product_uom_qty = math.floor(actual_quantity / prod_obj.volume)#prod_lot.future_stock_forecast
            if prod_lot is None:#Anand Patel
                prod_lot = sale_order_line_obj.get_available_batch_details(cr, uid, prod_obj.id, sale_order, context=context)

            sale_order_line = {
                'product_id': prod_obj.id,
                'price_unit': prod_obj.list_price,
                'comments': comments,
                'product_uom_qty': product_uom_qty,
                'product_uom': prod_obj.uom_id.id,
                'order_id': sale_order.id,
                'external_id':order['encounterId'],
                'external_order_id':order['orderId'],
                'name': prod_obj.name,
                'type': 'make_to_stock',
                'state': 'draft',
                'dispensed_status': order.get('dispensed', False)

            }

            if prod_lot is not None:
                life_date = prod_lot.life_date and datetime.strptime(prod_lot.life_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
                sale_order_line['price_unit'] = prod_lot.sale_price if prod_lot.sale_price > 0.0 else sale_order_line['price_unit']
                sale_order_line['batch_name'] = prod_lot.name
                sale_order_line['batch_id'] = prod_lot.id
                sale_order_line['expiry_date'] = life_date and life_date.strftime('%d/%m/%Y')

            line_domain = [#Anand Patel
            ('product_id','=', prod_obj.id),
            ('price_unit','=',prod_obj.list_price),
            #('comments','=',comments),
            #('product_uom_qty','=',product_uom_qty),
            ('product_uom','=',prod_obj.uom_id.id),
            ('order_id','=',sale_order.id),
            ('external_id','=',order['encounterId']),
            ('external_order_id','=',order['orderId']),
            ('name','=',prod_obj.name),
            ('type','=','make_to_stock'),
            ('state','=','draft'),
            ('dispensed_status','=',order.get('dispensed', False))
            ]
            existing_line_ids = sale_order_line_obj.search(cr, uid, line_domain, context=context)#Anand Patel
            _logger.info("\n\n*** existing_line_ids=%s",existing_line_ids)
            if existing_line_ids:#Anand Patel
                existing_line = sale_order_line_obj.browse(cr, uid, existing_line_ids[0], context=context)#Anand Patel
                comment_volume,comment_uom = existing_line.comments.split(" ")
                updated_line_qty = existing_line.product_uom_qty + 1
                comment_volume = float(existing_line.product_id.volume) * updated_line_qty
                comments = " ".join([str(comment_volume), str(comment_uom)])
                sale_order_line_obj.write(cr, uid, existing_line.id, {
                                        'product_uom_qty':updated_line_qty,
                                        'comments':comments
                                        }, context=context)#Anand Patel
            else:#Anand Patel
                sale_order_line_obj.create(cr, uid, sale_order_line, context=context)#Anand Patel

            sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order.id, context=context)
            if common and prod_obj.volume:
                if product_uom_qty and product_uom_qty * prod_obj.volume < order['quantity']:
                    order['quantity'] = order['quantity'] - product_uom_qty * prod_obj.volume
                    self._create_sale_order_line_function(cr, uid, name, sale_order, order, context=context)
            else:
                if product_uom_qty < order['quantity']:
                    order['quantity'] = order['quantity'] - product_uom_qty
                    self._create_sale_order_line_function(cr, uid, name, sale_order, order, context=context)
'''                    
    #Override this method to delilver the delivery order for "Dispense" Feature.
    #Actually when user press "D" button from Bahmni then its Confirming the quotatio to Sale Order 
    #Delivery Order is created when confirm the Quotation But client needs that delivery created also needs to be delivered.
    #So that stock will be deducted.                
    def create_orders(self, cr,uid,vals,context):
        customer_id = vals.get("customer_id")
        location_name = vals.get("locationName")
        all_orders = self._get_openerp_orders(vals)

        if(not all_orders):
            return ""

        customer_ids = self.pool.get('res.partner').search(cr, uid, [('ref', '=', customer_id)], context=context)
        if(customer_ids):
            cus_id = customer_ids[0]

            for orderType, ordersGroup in groupby(all_orders, lambda order: order.get('type')):

                orders = list(ordersGroup)
                care_setting = orders[0].get('visitType').lower()
                provider_name = orders[0].get('providerName')
                unprocessed_orders = self._filter_processed_orders(context, cr, orders, uid)

                tup = self._get_shop_and_local_shop_id(cr, uid, orderType, location_name, context)
                shop_id = tup[0]
                local_shop_id = tup[1]

                if(not shop_id):
                    continue

                name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order')
                #Adding both the ids to the unprocessed array of orders, Separating to dispensed and non-dispensed orders
                unprocessed_dispensed_order = []
                unprocessed_non_dispensed_order = []
                for unprocessed_order in unprocessed_orders :
                    unprocessed_order['custom_shop_id'] = shop_id
                    unprocessed_order['custom_local_shop_id'] = local_shop_id
                    if(unprocessed_order.get('dispensed', 'false') == 'true') :
                        unprocessed_dispensed_order.append(unprocessed_order)
                    else :
                        unprocessed_non_dispensed_order.append(unprocessed_order)

                if(len(unprocessed_non_dispensed_order) > 0 ) :
                    sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_non_dispensed_order[0]['custom_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)

                    if(not sale_order_ids):
                        #Non Dispensed New
                        self._create_sale_order(cr, uid, cus_id, name, unprocessed_non_dispensed_order[0]['custom_shop_id'], unprocessed_non_dispensed_order, care_setting, provider_name, context)
                    else:
                        #Non Dispensed Update
                        self._update_sale_order(cr, uid, cus_id, name, unprocessed_non_dispensed_order[0]['custom_shop_id'], care_setting, sale_order_ids[0], unprocessed_non_dispensed_order, provider_name, context)

                    sale_order_ids_for_dispensed = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_non_dispensed_order[0]['custom_local_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)

                    if(len(sale_order_ids_for_dispensed) > 0):
                        if(sale_order_ids_for_dispensed[0]) :
                            sale_order_line_ids_for_dispensed = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order_ids_for_dispensed[0])], context=context)
                            if(len(sale_order_line_ids_for_dispensed) == 0):
                                self.pool.get('sale.order').unlink(cr, uid, sale_order_ids_for_dispensed, context=context)

                if(len(unprocessed_dispensed_order) > 0 and local_shop_id) :
                    sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_dispensed_order[0]['custom_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)

                    sale_order_ids_for_dispensed = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_dispensed_order[0]['custom_local_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)
                    if(not sale_order_ids_for_dispensed):
                        
                        if any(sale_order_ids):
                            #Remove existing sale order line
                            self._remove_existing_sale_order_line(cr,uid,sale_order_ids[0],unprocessed_dispensed_order,context=context)

                            #Removing existing empty sale order
                            sale_order_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order_ids[0])], context=context)

                        if(len(sale_order_line_ids) == 0):
                            self.pool.get('sale.order').unlink(cr, uid, sale_order_ids, context=context)

                        #Dispensed New
                        self._create_sale_order(cr, uid, cus_id, name, unprocessed_dispensed_order[0]['custom_local_shop_id'], unprocessed_dispensed_order, care_setting, provider_name, context)
                        if(self._allow_automatic_convertion_to_saleorder (cr,uid)):
                            sale_order_ids_for_dispensed = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_dispensed_order[0]['custom_local_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)
                            self.pool.get('sale.order').action_button_confirm(cr, uid, sale_order_ids_for_dispensed, context)
                            #Below code is to delivery the delivery order automatically when sale order confirms from "D" button
                            #From Bahmni [Anand Patel]
                            for sale_order_id_for_dispensed in sale_order_ids_for_dispensed:
                                picking_ids = self.pool.get('sale.order').browse(cr, uid, sale_order_id_for_dispensed, context).picking_ids
                                for picking_id in picking_ids:
                                    action_process = picking_id.action_process()
                                    partial_picking_id = self.pool.get('stock.partial.picking').create(cr, uid, {}, action_process.get('context'))
                                    do_partial = self.pool.get('stock.partial.picking').do_partial(cr, uid, [int(partial_picking_id)], action_process.get('context'))

                    else:
                        #Remove existing sale order line
                        self._remove_existing_sale_order_line(cr,uid,sale_order_ids[0],unprocessed_dispensed_order,context=context)

                        #Removing existing empty sale order
                        sale_order_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order_ids[0])], context=context)
                        if(len(sale_order_line_ids) == 0):
                            self.pool.get('sale.order').unlink(cr, uid, sale_order_ids, context=context)

                        #Dispensed Update
                        self._update_sale_order(cr, uid, cus_id, name, unprocessed_dispensed_order[0]['custom_local_shop_id'], care_setting, sale_order_ids_for_dispensed[0], unprocessed_dispensed_order, provider_name, context)
        else:
            raise osv.except_osv(('Error!'), ("Patient Id not found in openerp"))
'''
