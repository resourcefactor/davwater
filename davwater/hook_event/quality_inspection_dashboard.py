from __future__ import unicode_literals
from frappe import _

def get_data(data):
    return {
        'fieldname': 'quality_inspection',
        'transactions': [
            {
                'label': _('Stock Entry'),
                'items': ['Stock Entry']
            },
        ]
    }
