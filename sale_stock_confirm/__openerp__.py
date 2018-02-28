# -*- coding: utf-8 -*-
{
    "name":"Sale Stock Confirm",
    "version":"1.0",
    "author":"Satvix Informatics",
    "category":"PossibleCustom",
    "description":
    """
Check availability of product, before confirmation of SO / Internal move
========================================================================
* This module fixes the issue of sale order, as due to bahmni_internal_stock_move warning \
    for products which are not available in the system was not getting raised.
* Also will raise warning on confirm of Sales Order / Internal Move, when quantity on hand for product is zero.
    """,
    "depends": ["bahmni_stock_batch_sale_price", "bahmni_internal_stock_move"],
    'data':['stock_move_view.xml'],
    'demo':[],
    'auto_install':False,
    'application':True,
    'installable':True,
}