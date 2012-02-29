##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import time
import pooler
from report import report_sxw
from account.report.common_report_header import common_report_header
from tools.translate import _


# TODO NEED to check code again

class report_multistep_income_statement(report_sxw.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context=None):
        super(report_multistep_income_statement, self).__init__(cr, uid, name, context=context)
        self.result_sum_dr = 0.0
        self.result_sum_cr = 0.0
        self.result_sum_operating_dr = 0.0        
        self.result_sum_other_dr = 0.0
        self.result_sum_other_cr = 0.0
        self.res_pl = {}
        self.result = {}
        self.result_temp = []
        self.localcontext.update( {
            'time': time,
            'get_lines': self.get_lines,
            'get_lines_another': self.get_lines_another,
            'get_currency': self._get_currency,
            'get_data': self.get_data,
            'sum_dr': self.sum_dr,
            'sum_cr': self.sum_cr,
            'sum_other_dr': self.sum_other_dr,
            'sum_operating_dr': self.sum_operating_dr,            
            'sum_other_cr': self.sum_other_cr,
            'final_result': self.final_result,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_sortby': self._get_sortby,
            'get_filter': self._get_filter,
            'get_journal': self._get_journal,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_company':self._get_company,
            'get_target_move': self._get_target_move,
            'check_parent' : self.check_parent,
        })
        self.context = context

    def check_parent(self, account_id):
    
        cr, uid = self.cr, self.uid
        account_obj = self.pool.get('account.account')
        parent_account = account_obj.search(cr, uid, [('parent_id' ,'=',account_id)])
        if parent_account : 
            return ''
        else :
            account = account_obj.browse(cr, uid, account_id)
            if account.balance == 0.0 :
                return account.balance
            return account.balance * account.user_type.sign

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
        return super(report_multistep_income_statement, self).set_context(objects, data, new_ids, report_type=report_type)


    def final_result(self):
        return self.res_pl

    def sum_dr(self):
#        if self.res_pl['type'] == _('Net Profit'):
#            self.result_sum_dr += self.res_pl['balance'] + self.res_pl['gross_profit']
        return self.result_sum_dr

    def sum_cr(self):
#        if self.res_pl['type'] == _('Net Loss'):
#            self.result_sum_cr += self.res_pl['balance'] + self.res_pl['gross_profit']
        return self.result_sum_cr

    def sum_other_dr(self):
#        if self.res_pl['type'] == _('Net Profit'):
#            self.result_sum_other_dr += self.res_pl['balance'] + self.res_pl['gross_profit']
        return self.result_sum_other_dr

    def sum_other_cr(self):
#        if self.res_pl['type'] == _('Net Loss'):
#            self.result_sum_other_cr += self.res_pl['balance'] + self.res_pl['gross_profit']
        return self.result_sum_other_cr

    def sum_operating_dr(self):
#        if self.res_pl['type'] == _('Net Loss'):
#            self.result_sum_other_cr += self.res_pl['balance'] + self.res_pl['gross_profit']
        return self.result_sum_operating_dr
        
    def get_data(self, data):
        cr, uid = self.cr, self.uid
        db_pool = pooler.get_pool(self.cr.dbname)

        account_pool = db_pool.get('account.account')
        currency_pool = db_pool.get('res.currency')

        types = [
            'expense',
            'income',
                ]

        ctx = self.context.copy()
        ctx['fiscalyear'] = data['form'].get('fiscalyear_id', False)

        if data['form']['filter'] == 'filter_period':
            ctx['periods'] =  data['form'].get('periods', False)
        elif data['form']['filter'] == 'filter_date':
            ctx['date_from'] = data['form'].get('date_from', False)
            ctx['date_to'] =  data['form'].get('date_to', False)

        cal_list = {}
        account_id = data['form'].get('chart_account_id', False)
        account_ids = account_pool._get_children_and_consol(cr, uid, account_id, context=ctx)
        accounts = account_pool.browse(cr, uid, account_ids, context=ctx)
        self.result ={'gross_income':[],'gross_expense':[],'operating_expense':[],
                      'other_income':[],'other_expense':[] }
        for typ in types:
        
            for account in accounts:
                income_type = account.user_type.pl_income_type
                if (account.user_type.report_type) and (account.user_type.report_type == typ):
                    currency = account.currency_id and account.currency_id or account.company_id.currency_id
                    if typ == 'expense' and income_type == 'gross' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_dr += abs(account.debit - account.credit)
                    if typ == 'income' and income_type == 'gross' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_cr += abs(account.debit - account.credit)
                    if typ == 'expense' and income_type == 'operating' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_operating_dr += abs(account.debit - account.credit)
                    if typ == 'expense' and income_type == 'other' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_other_dr += abs(account.debit - account.credit)
                    if typ == 'income' and income_type == 'other' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_other_cr += abs(account.debit - account.credit)
                    if data['form']['display_account'] == 'bal_movement':
                        if currency_pool.is_zero(self.cr, self.uid, currency, account.credit) > 0 or currency_pool.is_zero(self.cr, self.uid, currency, account.debit) > 0 or currency_pool.is_zero(self.cr, self.uid, currency, account.balance) != 0:
                            self.result['%s_%s'%(income_type,typ)].append(account)
                    elif data['form']['display_account'] == 'bal_solde':
                        if currency_pool.is_zero(self.cr, self.uid, currency, account.balance) != 0:
                            self.result['%s_%s'%(income_type,typ)].append(account)
                    else:
                        self.result['%s_%s'%(income_type,typ)].append(account)
        gross_income = self.result_sum_cr - self.result_sum_dr

        self.res_pl['gross_type'] =  gross_income > 0 and _('Gross Profit') or _('Gross Loss')
        self.res_pl['gross_balance'] = gross_income

        operating_income = gross_income -  self.result_sum_operating_dr

        self.res_pl['operating_type'] =  'Net Ordinary Income'
        self.res_pl['operating_balance'] = operating_income

        net_income = operating_income - self.result_sum_other_dr + self.result_sum_other_cr
        
        self.res_pl['type'] =  net_income > 0  and _('Net Profit') or _('Net Loss')
        self.res_pl['balance'] = net_income
        return None

    def get_lines(self):
        return self.result

    def get_lines_another(self, group):
        return self.result.get(group, [])

report_sxw.report_sxw('report.multi.income.statement', 'account.account',
    'addons/account_multistep_income_statement/report/account_multistep_income_stmt.rml',parser=report_multistep_income_statement, header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
