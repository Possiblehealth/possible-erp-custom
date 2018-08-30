# -*- coding: utf-8 -*-
import math
from datetime import datetime
import re
from openerp.osv import osv, fields
from openerp import tools


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
                            if not prd_ids:
                                product_found = True
                            else:
                                visited_products.append(prd_ids[0])
                        prod_obj = self.pool.get('product.product').browse(cr, uid, visited_products[-1])
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
                product_uom_qty = prod_lot.future_stock_forecast

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

            sale_order_line_obj.create(cr, uid, sale_order_line, context=context)

            sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order.id, context=context)
            if common and prod_obj.volume:
                if product_uom_qty and product_uom_qty * prod_obj.volume < order['quantity']:
                    order['quantity'] = order['quantity'] - product_uom_qty * prod_obj.volume
                    self._create_sale_order_line_function(cr, uid, name, sale_order, order, context=context)
            else:
                if product_uom_qty < order['quantity']:
                    order['quantity'] = order['quantity'] - product_uom_qty
                    self._create_sale_order_line_function(cr, uid, name, sale_order, order, context=context)
