# -*- coding: utf-8 -*-
from osv import osv


class product_product(osv.osv):
    _inherit = 'product.product'
    
    
    def get_product_available_category_wise(self, cr, uid, ids, categ_id, context=None):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """
        if context is None:
            context = {}

        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        shop_obj = self.pool.get('sale.shop')
        
        states = context.get('states',[])
        what = context.get('what',())
        if not ids:
            ids = self.search(cr, uid, [])
        res = {}.fromkeys([categ_id], 0.0)
        if not ids:
            return res
        
        #currently this code is not getting used, as shop is not passed though context
        if context.get('shop', False):
            warehouse_ids = shop_obj.read(cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id']
            warehouse_id = None;
            if(warehouse_ids and len(warehouse_ids) > 0):
                warehouse_id = shop_obj.read(cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id'][0]
            if warehouse_id:
                context['warehouse'] = warehouse_id

        if context.get('warehouse', False):
            lot_id = warehouse_obj.read(cr, uid, int(context['warehouse']), ['lot_stock_id'])['lot_stock_id'][0]
            if lot_id:
                context['location'] = lot_id

        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = location_obj.search(cr, uid, [('name','ilike', context['location'])], context=context)
            else:
                location_ids = context['location']
        else:
            location_ids = []
            wids = warehouse_obj.search(cr, uid, [], context=context)
            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.lot_stock_id.id)
            
        #this code is also unused, as compute_child flag is not passed through context        
        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            if location_ids:
                child_location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', location_ids)])
                location_ids = child_location_ids or location_ids

        # this will be a dictionary of the product UoM by product id
        product2uom = {}
        uom_ids = []
        for product in self.read(cr, uid, ids, ['uom_id'], context=context):
            product2uom[product['id']] = product['uom_id'][0]
            uom_ids.append(product['uom_id'][0])
        # this will be a dictionary of the UoM resources we need for conversion purposes, by UoM id
        uoms_o = {}
        for uom in self.pool.get('product.uom').browse(cr, uid, uom_ids, context=context):
            uoms_o[uom.id] = uom

        results = []
        results2 = []

        from_date = context.get('from_date',False)
        to_date = context.get('to_date',False)
        date_str = False
        date_values = False
        where = []
        if location_ids:
            where.extend([tuple(location_ids),tuple(location_ids)])
        if ids:
            where.append(tuple(ids))
        if states:
            where.append(tuple(states))
            
        #where = [tuple(location_ids),tuple(location_ids),tuple(ids),tuple(states)]
        if from_date and to_date:
            date_str = "sm.date>=%s and sm.date<=%s"
            where.append(from_date)
            where.append(to_date)
        elif from_date:
            date_str = "sm.date>=%s"
            date_values = from_date
        elif to_date:
#             date_str = "sm.date<=%s"
            date_str = "sm.date<%s" # changed it to consider opening balance on start date, which should exclude start date.
            date_values = to_date
        if date_values:
            where.append(date_values)

        prodlot_id = context.get('prodlot_id', False)
        prodlot_clause = ' and (spl.life_date is null or spl.life_date > now()) '
        if prodlot_id:
            prodlot_clause = ' and prodlot_id = %s '
            where += [prodlot_id]

        # TODO: perhaps merge in one query.
        if 'in' in what:
            # all moves from a location out of the set to a location in the set
            sql_query = 'select COALESCE(round(sum(sm.product_qty * pt.standard_price * pu.factor/u.factor), 4), 0), '\
                        'sm.product_id, sm.product_uom '\
                        'from stock_move sm '\
                        'left join product_product pp on pp.id=sm.product_id '\
                        'left join product_template pt on pt.id=pp.product_tmpl_id '\
                        'left join product_uom pu on pu.id=sm.product_uom '\
                        'left join product_uom u on u.id=pt.uom_id '\
                        'left outer join stock_production_lot spl on sm.prodlot_id = spl.id '\
                        'where '
                
            if location_ids:
                sql_query += 'sm.location_dest_id  IN %s '\
                                'and sm.location_id NOT IN %s '
                if ids:
                    sql_query += ' and sm.product_id IN %s '
                if states:
                    sql_query += ' and sm.state IN %s '
            elif ids:
                sql_query += 'sm.product_id IN %s '
                if states:
                    sql_query += 'and sm.state IN %s '
            elif states:
                sql_query += ' sm.state IN %s '
                    
            sql_query += (date_str and 'and '+date_str+' ' or '') +' '\
                         + prodlot_clause +\
                         'group by sm.product_id, sm.product_uom'\
               
            cr.execute(sql_query, tuple(where))

            results = cr.fetchall()
        if 'out' in what:
            # all moves from a location in the set to a location out of the set
            sql_query = 'select COALESCE(round(sum(sm.product_qty * pt.standard_price * pu.factor/u.factor), 4), 0), '\
                        'sm.product_id, sm.product_uom '\
                        'from stock_move sm '\
                        'left join product_product pp on pp.id=sm.product_id '\
                        'left join product_template pt on pt.id=pp.product_tmpl_id '\
                        'left join product_uom pu on pu.id=sm.product_uom '\
                        'left join product_uom u on u.id=pt.uom_id '\
                        'left outer join stock_production_lot spl on sm.prodlot_id = spl.id '\
                        'where '
                
            if location_ids:
                sql_query += 'sm.location_id IN %s '\
                'and sm.location_dest_id NOT IN %s '
                if ids:
                    sql_query += 'and sm.product_id  IN %s '
                if states:
                    sql_query += 'and sm.state  IN %s '
            elif ids:
                sql_query += 'sm.product_id  IN %s '
                if states:
                    sql_query += 'and sm.state in %s '
            elif states:
                sql_query += 'sm.state in %s '
            sql_query += (date_str and 'and '+date_str+' ' or '') + ' '\
                         + prodlot_clause +\
                        'group by sm.product_id,sm.product_uom'
                           
            cr.execute(sql_query, tuple(where))
            results2 = cr.fetchall()
            
        # Get the missing UoM resources
        uom_obj = self.pool.get('product.uom')
        uoms = map(lambda x: x[2], results) + map(lambda x: x[2], results2)
        if context.get('uom', False):
            uoms += [context['uom']]
        uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
        if uoms:
            uoms = uom_obj.browse(cr, uid, list(set(uoms)), context=context)
            for o in uoms:
                uoms_o[o.id] = o

        #TOCHECK: before change uom of product, stock move line are in old uom.
        context.update({'raise-exception': False})
        
        # Count the incoming quantities
        for amount, prod_id, prod_uom in results:
#             amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
#                      uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
#             res[prod_id] += amount
            res[categ_id] += amount
        # Count the outgoing quantities
        for amount, prod_id, prod_uom in results2:
#             amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
#                     uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
#             res[prod_id] -= amount
            res[categ_id] += amount
        res[categ_id] = round(res[categ_id], 4)
        return res
