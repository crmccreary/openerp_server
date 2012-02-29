# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from osv import osv
from osv import fields

class account_account_type(osv.osv):
    _inherit = "account.account.type"
    
    _columns = {
        'pl_income_type':fields.selection([
            ('gross','Total Sales/Cost of goods sold'),
            ('operating','Operating Income/Expense'),
            ('other','Other Income/Expense'),
        ],'P&L Income/Expense Category', select=True, help="According value related accounts will be used to to have different total on income statement report",),
        }

account_account_type()
