# -*- coding: utf-8 -*-
# © 2017 Satvix Informatics (https://www.satvix.com)


{
    'name': 'OpenERP Report',
    'version': '7.0.1.0.0',
    'category': 'custom',
    'sequence': 1,
    'summary': 'OpenERP Report',
    'description': """
        Custom Reports:
        python lib dependancy : xlsxwriter, zipfile
         * Purchase Order
         * RFQ
         * Picking
         * Move Report ()
    """,
    'author': 'Satvix Informatics',
    'website': 'https://www.satvix.com',
    'images' : [],
    'depends': ['stock_with_cost','product_stock_type'],
    'data': [        
        'stock_move_report/stock_move_report_view.xml',
        'security/ir.model.access.csv',
    ],
    'test': [
        
    ],
    'demo': [
       
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

