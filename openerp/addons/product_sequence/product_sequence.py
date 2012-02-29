# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 Sylëam Info Services (http://www.syleam.fr) All rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields, osv

#
# Add a sequence on product when field code is empty 
#
class product_sequence(osv.osv):
    #    _name = 'template.class'
    #_description = 'My template class'
    _inherit = 'product.product'

    def create(self, cr, uid, vals, context={}):
        if not vals['default_code']:
            vals['default_code'] = self.pool.get('ir.sequence').get(cr, uid, 'product.product')
        res = super(product_sequence, self).create(cr, uid, vals, context)
        return res

product_sequence()


