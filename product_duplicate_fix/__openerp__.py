# -*- encoding: utf-8 -*-
{
    'name' : 'Fix Product Duplication issue',
    'version' : '1.0',
    'category' : 'Products',
    'author'  : 'Satvix Informatics',
    'license' : 'AGPL-3',
    'depends' : ['product', 'base'],
    'data': ["users_view.xml"],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': '''
*   Fix the Product Duplication issue.
*   Also restrict the user to create product based on the configuration in users profile
    '''
}
