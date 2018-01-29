# -*- coding: utf-8 -*-
{
    'name' : 'Custom Stock Reports',
    'version' : '1.0',
    'author' : '',
    'category' : 'Inventory',
    'description' : """
Custom Stock Reports.
====================================
Custom Incoming Shipment Report:
--------------------------------------------
    * Includes Price Unit in move lines
    * Includes Taxes and Total amount in report, where taxes are referred from PO linked to it.
""",
    'website': '',
    'images' : [],
    'depends' : ['bahmni_internal_stock_move'],
    'data': ['stock_reports.xml'],
    'js': [],
    'qweb' : [],
    'css':[],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: