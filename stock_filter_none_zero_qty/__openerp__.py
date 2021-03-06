# -*- coding: utf-8 -*-
##############################################################################
#
#    Stock Filter for Zero Quantity for Bahmni OpenERP
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
{
    'name' : 'Filter products in stock',
    'description' : '''
       · Adds a "Stock" button to product's search view to show
         stockable products with and without stock availability
       · By default, only products with stock are shown (i.e.
         button is enabled)
    ''',
    'version' : '1.0',
    'depends' : [
        "stock",
        "product",
    ],
    'category': 'Warehouse',
    'author' : 'Ajeenckya Gadewar',
    'website': 'https://www.satvix.com',
    'demo': [],
    'data': [
        'product_view.xml',
    ],
    'installable' : True,
    'active' : False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

