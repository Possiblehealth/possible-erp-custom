# -*- coding: utf-8 -*-
# © 2014 Elico Corp (https://www.elico-corp.com)
# Licence AGPL-3.0 or later(http://www.gnu.org/licenses/agpl.html)


{
    'name': 'Stock Extra',
    'version': '7.0.1.0.0',
    'category': 'Stock',
    'sequence': 19,
    'summary': 'Stock Extra',
    'description': 'Stock Extra',
    'author': 'Elico Corp',
    'website': 'https://www.elico-corp.com',
    'images' : [],
    'depends': ['product_stock_type','stock','sale','mrp'],
    'data': [
        'stock_view.xml',
        'security/ir.model.access.csv',
    ],
    'test': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

