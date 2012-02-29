# -*- coding: utf-8 -*-
#########################################################################
#                                                                       #
# Copyright (C) 2011   Charles McCreary                                 #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

import time

from osv import fields, osv
import netsvc
from tools.translate import _
import decimal_precision as dp

class account_easy_bank_reconcile(osv.osv):
    logger = netsvc.Logger()
    _name = "account.easy.bank.reconcile"

    def populate_candidate_lines(self, cr, uid, context=None):
        self.logger.notifyChannel('addons.'+self._name+'.view_init', netsvc.LOG_DEBUG,
                                  'context:%s'%context)
        if context is None:
            context = {}
        # Populate account_easy_bank_reconcile_candidate_line with unreconciled moves
        journal_pool = self.pool.get('account.journal')
        journal_type = context.get('journal_type', False)
        journal_id = False
        account_easy_bank_reconcile_candidate_line = self.pool.get('account.easy.bank.reconcile.candidate.line')
        if journal_type:
            ids = journal_pool.search(cr, uid, [('type', '=', journal_type)])
            for _id in ids:
                journal = journal_pool.browse(cr, uid, _id, context = context)
                self.logger.notifyChannel('addons.'+self._name+'.view_init', netsvc.LOG_DEBUG,
                                          'journal.default_credit_account_id:%s'%journal.default_credit_account_id.id)
                '''
                If this query f***s up and generates dupes, the following will list the originals and the dupes:
                SELECT * 
                FROM account_easy_bank_reconcile_candidate_line candidate_line JOIN (
                    SELECT move_line_id, MIN(id) AS minid FROM account_easy_bank_reconcile_candidate_line 
                    GROUP BY move_line_id
                    HAVING ( COUNT(move_line_id) > 1 )
                ) AS dupmoves
                ON candidate_line.move_line_id = dupmoves.move_line_id
                ORDER BY id DESC

                And to delete these dupes:

                DELETE FROM account_easy_bank_reconcile_candidate_line WHERE id in 
                (SELECT id
                FROM account_easy_bank_reconcile_candidate_line candidate_line JOIN (
                    SELECT move_line_id, MIN(id) AS minid FROM account_easy_bank_reconcile_candidate_line 
                    GROUP BY move_line_id
                    HAVING ( COUNT(move_line_id) > 1 )
                ) AS dupmoves
                ON candidate_line.move_line_id = dupmoves.move_line_id
                WHERE candidate_line.id <> minid)
                '''
                sql = '''SELECT b.id, b.date, b.ref, b.credit, b.debit 
                         FROM account_move_line b
                         WHERE NOT EXISTS (
                             SELECT a.move_line_id FROM account_easy_bank_reconcile_candidate_line a
                             WHERE a.move_line_id = b.id AND reconcile_journal_id = %d)
                         AND b.account_id = %d''' % (journal.id,journal.default_credit_account_id.id)
                self.logger.notifyChannel('addons.'+self._name+'.view_init', netsvc.LOG_DEBUG,
                                          'sql:%s'%sql)
                cr.execute(sql)
                for record in cr.fetchall():
                    for val in record:
                        self.logger.notifyChannel('addons.'+self._name+'.view_init', netsvc.LOG_DEBUG,
                                                  'val:%s'%val)
                    name_parts = [str(record[1]),
                                  str(record[2]),
                                  str(record[3] or '0.00'),
                                  str(record[4] or '0.00')]
                    values = {'move_line_id': record[0], 
                              'reconcile_journal_id':journal.id,
                              'name':' '.join(name_parts)}
                    self.logger.notifyChannel('addons.'+self._name+'.view_init', netsvc.LOG_DEBUG,
                                              'values:%s'%values)
                    account_easy_bank_reconcile_candidate_line.create(cr, uid, values, context=context)


    def create(self, cr, uid, vals, context=None):
        self.logger.notifyChannel('addons.'+self._name+'.create', netsvc.LOG_DEBUG,
                                  'vals:%s'%vals)
        self.logger.notifyChannel('addons.'+self._name+'.create', netsvc.LOG_DEBUG,
                                  'context:%s'%context)
        seq = 0
        if 'line_ids' in vals:
            for line in vals['line_ids']:
                seq += 1
                line[2]['sequence'] = seq
                vals[seq - 1] = line
        return super(account_easy_bank_reconcile, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        self.logger.notifyChannel('addons.'+self._name+'.write', netsvc.LOG_DEBUG,
                                  'ids:%s'%ids)
        self.logger.notifyChannel('addons.'+self._name+'.write', netsvc.LOG_DEBUG,
                                  'vals:%s'%vals)
        res = super(account_easy_bank_reconcile, self).write(cr, uid, ids, vals, context=context)
        return res

    def _default_journal_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal_pool = self.pool.get('account.journal')
        journal_type = context.get('journal_type', False)
        journal_id = False
        if journal_type:
            ids = journal_pool.search(cr, uid, [('type', '=', journal_type)])
            if ids:
                journal_id = ids[0]
        return journal_id

    def _default_balance_start(self, cr, uid, context=None):
        cr.execute('select id from account_easy_bank_reconcile where journal_id=%s order by date desc limit 1', (1,))
        res = cr.fetchone()
        if res:
            return self.browse(cr, uid, res[0], context=context).balance_end
        return 0.0

    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')
        res = {}

        company_currency_id = res_users_obj.browse(cursor, 
                                                   user, 
                                                   user,
                                                   context=context).company_id.currency_id.id

        statements = self.browse(cursor, user, ids, context=context)
        for statement in statements:
            res[statement.id] = statement.balance_start
            msg = 'res[statement.id]:%s' % res[statement.id]
            self.logger.notifyChannel(self._name+'._end_balance', netsvc.LOG_DEBUG, msg)
            currency_id = statement.currency.id
            msg = 'statement.report_type:%s' % statement.report_type
            self.logger.notifyChannel(self._name+'._end_balance', netsvc.LOG_DEBUG, msg)
            meaning = 1.0
            if statement.report_type == 'liability':
                meaning = -1.0
            for line in statement.line_ids:
                msg = 'line.debit:%s' % line.debit
                self.logger.notifyChannel(self._name+'._end_balance', netsvc.LOG_DEBUG, msg)
                msg = 'line.credit:%s' % line.credit
                self.logger.notifyChannel(self._name+'._end_balance', netsvc.LOG_DEBUG, msg)
                if line.debit > 0:
                    res[statement.id] += res_currency_obj.compute(cursor,
                                                                  user, 
                                                                  company_currency_id, 
                                                                  currency_id,
                                                                  line.debit, 
                                                                  context=context)*meaning
                else:
                    res[statement.id] -= res_currency_obj.compute(cursor,
                                                                  user, 
                                                                  company_currency_id, 
                                                                  currency_id,
                                                                  line.credit, 
                                                                  context=context)*meaning
            msg = 'res[statement.id]:%s' % res[statement.id]
            self.logger.notifyChannel(self._name+'._end_balance', netsvc.LOG_DEBUG, msg)
        for r in res:
            res[r] = round(res[r], 2)
        return res

    def _get_period(self, cr, uid, context=None):
        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        return False

    def _currency(self, cursor, user, ids, name, args, context=None):
        res = {}
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')
        default_currency = res_users_obj.browse(cursor, 
                                                user, 
                                                user, 
                                                context=context).company_id.currency_id
        for statement in self.browse(cursor, user, ids, context=context):
            currency = statement.journal_id.currency
            if not currency:
                currency = default_currency
            res[statement.id] = currency.id
        currency_names = {}
        for currency_id, currency_name in res_currency_obj.name_get(cursor,
                user, [x for x in res.values()], context=context):
            currency_names[currency_id] = currency_name
        for statement_id in res.keys():
            currency_id = res[statement_id]
            res[statement_id] = (currency_id, currency_names[currency_id])
        return res

    _order = "date desc, id desc"
    _description = "Bank Reconciliation Statement"
    _columns = {
        'name': fields.char('Name', 
                            size=64, 
                            required=True, 
                            help='if you give the Name other then /, its created Accounting Entries Move will be with same name as statement name. This allows the statement entries to have the same references than the statement itself', 
                            states={'confirm': [('readonly', True)]}),
        'date': fields.date('Date', 
                            required=True, 
                            states={'confirm': [('readonly', True)]}),
        'journal_id': fields.many2one('account.journal', 
                                      'Journal', 
                                      required=True,
                                      readonly=True, 
                                      states={'draft':[('readonly',False)]}),
        'period_id': fields.many2one('account.period', 
                                     'Period', 
                                     required=True,
                                     states={'confirm':[('readonly', True)]}),
        'balance_start': fields.float('Starting Balance', 
                                      digits_compute=dp.get_precision('Account'),
                                      states={'confirm':[('readonly',True)]}),
        'balance_end_real': fields.float('Ending Balance', 
                                         digits_compute=dp.get_precision('Account'),
                                         states={'confirm':[('readonly', True)]}),
        'balance_end': fields.function(_end_balance, 
                                       string='Balance'),
        'company_id': fields.related('journal_id', 
                                     'company_id', 
                                     type='many2one', 
                                     relation='res.company', 
                                     string='Company', 
                                     store=True, 
                                     readonly=True),
        'line_ids': fields.one2many('account.easy.bank.reconcile.line',
                                    'statement_id', 
                                    'Statement lines',
                                    states={'confirm':[('readonly', True)]}),
        'state': fields.selection([('draft', 'Draft'),('confirm', 'Confirmed')],
                                  'State', 
                                  required=True,
                                  states={'confirm': [('readonly', True)]}, 
                                  readonly="1",
                                  help='When new statement is created the state will be \'Draft\'. \n* And after getting confirmation from the bank it will be in \'Confirmed\' state.'),
        'currency': fields.function(_currency, string='Currency',
                                    type='many2one', 
                                    relation='res.currency'),
        'account_id': fields.related('journal_id', 
                                     'default_credit_account_id', 
                                     type='many2one', 
                                     relation='account.account', 
                                     string='Account used in this journal', 
                                     readonly=True, 
                                     help='used in statement reconciliation domain, but shouldn\'t be used elswhere.'),
        'report_type': fields.related('account_id', 
                                      'user_type', 
                                      'report_type', 
                                      type='char', 
                                      size=16, 
                                      string='Account Type', 
                                      readonly=True, 
                                      store=False),
    }

    _defaults = {
        'name': "/",
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': 'draft',
        'balance_start': _default_balance_start,
        'journal_id': _default_journal_id,
        'period_id': _get_period,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.bank.statement',context=c),
    }

    def onchange_date(self, cr, user, ids, date, context=None):
        """
        Returns a dict that contains new values and context
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        res = {}
        period_pool = self.pool.get('account.period')

        if context is None:
            context = {}

        pids = period_pool.search(cr, user, [('date_start','<=',date), ('date_stop','>=',date)])
        if pids:
            res.update({
                'period_id':pids[0]
            })
            context.update({
                'period_id':pids[0]
            })

        return {
            'value':res,
            'context':context,
        }

    def button_dummy(self, cr, uid, ids, context=None):
        msg = 'context:%s' % context
        self.logger.notifyChannel(self._name+'.button_dummy', netsvc.LOG_DEBUG, msg)
        self.populate_candidate_lines(cr, uid, context)
        return self.write(cr, uid, ids, {}, context=context)

    def get_next_st_line_number(self, cr, uid, st_number, st_line, context=None):
        return st_number + '/' + str(st_line.sequence)

    def balance_check(self, cr, uid, st_id, journal_type='bank', context=None):
        self.logger.notifyChannel('addons.'+self._name+'.balance_check', netsvc.LOG_DEBUG,
                                  'st_id:%s'%st_id)
        self.logger.notifyChannel('addons.'+self._name+'.balance_check', netsvc.LOG_DEBUG,
                                  'journal_type:%s'%journal_type)
        self.logger.notifyChannel('addons.'+self._name+'.balance_check', netsvc.LOG_DEBUG,
                                  'context:%s'%context)
        st = self.browse(cr, uid, st_id, context=context)
        self.logger.notifyChannel('addons.'+self._name+'.balance_check', netsvc.LOG_DEBUG,
                                  'st.balance_end:%s'%st.balance_end)
        self.logger.notifyChannel('addons.'+self._name+'.balance_check', netsvc.LOG_DEBUG,
                                  'st.balance_end_real:%s'%st.balance_end_real)
        if not (abs((st.balance_end or 0.0) - st.balance_end_real) < 0.0001):
            raise osv.except_osv('Error !',
                    'The statement balance is incorrect !\nThe expected balance (%.2f) is different than the computed one. (%.2f)' % (st.balance_end_real, st.balance_end))
        return True

    def statement_close(self, cr, uid, ids, journal_type='bank', context=None):
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

    def check_status_condition(self, cr, uid, state, journal_type='bank'):
        return state=='draft'

    def button_confirm_bank(self, cr, uid, ids, context=None):
        self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                  'context: %s'%context)
        self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                  'ids: %s'%ids)
        obj_seq = self.pool.get('ir.sequence')
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                      'j_type: %s'%j_type)
            self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                      'st.state: %s'%st.state)
            company_currency_id = st.journal_id.company_id.currency_id.id
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                          'state != "draft"')
                continue
            else:
                self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                          'state == "draft"')

            self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                      'Calling balance_check')
            self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                      'st.id: %s'%st.id)
            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                      'balance_check ok')
            self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                      'st.journal_id.default_credit_account_id:%s'%st.journal_id.default_credit_account_id)
            self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,
                                      'st.journal_id.default_debit_account_id:%s'%st.journal_id.default_debit_account_id)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv('Configuration Error !',
                        'Please verify that an account is defined in the journal.')

            if not st.name == '/':
                st_number = st.name
            else:
                if st.journal_id.sequence_id:
                    c = {'fiscalyear_id': st.period_id.fiscalyear_id.id}
                    st_number = obj_seq.get_id(cr, uid, st.journal_id.sequence_id.id, context=c)
                else:
                    st_number = obj_seq.get(cr, uid, 'account.easy.bank.reconcile')
                    
            account_easy_bank_reconcile_line_pool = self.pool.get('account.easy.bank.reconcile.line')
            account_easy_bank_reconcile_candidate_line_pool = self.pool.get('account.easy.bank.reconcile.candidate.line')
            
            seq = 0
            for line in st.line_ids:
                seq += 1
                line = account_easy_bank_reconcile_line_pool.browse(cr, uid, line.id, context=context)
                msg = 'line.candidate_move_line_id.id:%s' % line.candidate_move_line_id.id
                self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,msg)
                candidate_line = account_easy_bank_reconcile_candidate_line_pool.browse(cr, uid, line.candidate_move_line_id.id, context=context)
                msg = 'candidate_line.id:%s' % candidate_line.id
                self.logger.notifyChannel('addons.'+self._name+'.button_confirm_bank', netsvc.LOG_DEBUG,msg)
                candidate_line.write({'state':'reconciled'})
                line.write({'sequence':seq})

            self.write(cr, uid, [st.id], {'name': st_number}, context=context)
            self.log(cr, uid, st.id, 'Statement %s is confirmed, journal items are created.' % (st_number,))
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        done = []
        return self.write(cr, uid, done, {'state':'draft'}, context=context)

    def onchange_journal_id(self, cr, uid, statement_id, journal_id, context=None):
        self.logger.notifyChannel('addons.'+self._name+'.onchange_journal_id', netsvc.LOG_DEBUG,
                                  'context:%s'%context)
        if context is None:
            context = {}
        cr.execute('SELECT balance_end_real \
                FROM account_easy_bank_reconcile \
                WHERE journal_id = %s AND NOT state = %s \
                ORDER BY date DESC,id DESC LIMIT 1', (journal_id, 'draft'))
        res = cr.fetchone()
        balance_start = res and res[0] or 0.0
        account_id = self.pool.get('account.journal').read(cr, uid, journal_id, 
                                   ['default_credit_account_id'], 
                                   context=context)['default_credit_account_id']
        context.update({'account_id': account_id})
        return {'value': {'balance_start': balance_start, 'account_id': account_id}}

    def unlink(self, cr, uid, ids, context=None):
        msg = 'ids:%s' % ids
        self.logger.notifyChannel('addons.'+self._name+'.unlink', netsvc.LOG_DEBUG,msg)
        stat = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for t in stat:
            msg = 't:%s' % t
            self.logger.notifyChannel('addons.'+self._name+'.unlink', netsvc.LOG_DEBUG,msg)
            if t['state'] in ('draft'):
                unlink_ids.append(t['id'])
                st = self.browse(cr, uid, t['id'], context=context)
                msg = 'st:%s' % st
                self.logger.notifyChannel('addons.'+self._name+'.unlink', netsvc.LOG_DEBUG,msg)
                msg = 'st.line_ids:%s' % st.line_ids
                self.logger.notifyChannel('addons.'+self._name+'.unlink', netsvc.LOG_DEBUG,msg)
                # Reset all of the candidate lines to draft
                for line in st.line_ids:
                    msg = 'line.candidate_move_line_id.id:%s' % line.candidate_move_line_id.id
                    self.logger.notifyChannel('addons.'+self._name+'.unlink', netsvc.LOG_DEBUG,msg)
                    line.candidate_move_line_id.write({'state':'draft'})
            else:
                raise osv.except_osv('Invalid action !', 'Cannot delete bank statement(s) which are already confirmed !')
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        msg = 'id:%s' % id
        self.logger.notifyChannel('addons.'+self._name+'.copy', netsvc.LOG_DEBUG,msg)
        if default is None:
            default = {}
        if context is None:
            context = {}
        default = default.copy()
        return super(account_easy_bank_reconcile, self).copy(cr, uid, id, default, context=context)

account_easy_bank_reconcile()

class account_easy_bank_reconcile_candidate_line(osv.osv):
    logger = netsvc.Logger()

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        msg = 'args:%s' % args
        self.logger.notifyChannel(self._name+'.search', netsvc.LOG_DEBUG,msg)
        msg = 'offset:%s' % offset
        self.logger.notifyChannel(self._name+'.search', netsvc.LOG_DEBUG,msg)
        msg = 'limit:%s' % limit
        self.logger.notifyChannel(self._name+'.search', netsvc.LOG_DEBUG,msg)
        msg = 'order:%s' % order
        self.logger.notifyChannel(self._name+'.search', netsvc.LOG_DEBUG,msg)
        msg = 'count:%s' % count
        self.logger.notifyChannel(self._name+'.search', netsvc.LOG_DEBUG,msg)
        q = []
        for arg in args:
            if arg[0] == 'state':
                q.append('candidate_line.state' + ' ' + str(arg[1]) + ' ' + "'%s'"%str(arg[2]))
            elif arg[0] == 'reconcile_journal_id':
                q.append('candidate_line.reconcile_journal_id' + ' ' + str(arg[1]) + ' ' + "'%s'"%str(arg[2]))
            else:
                q.append('move_line.%s'%str(arg[0]) + ' ' + str(arg[1]) + ' ' + str(arg[2]))
        sql = '''select candidate_line.id from account_move_line move_line 
                 inner join account_easy_bank_reconcile_candidate_line candidate_line 
                 on move_line.id = candidate_line.move_line_id WHERE %s order by move_line.date''' % ' AND '.join(q)
        if limit is not None:
            sql = sql + ' LIMIT %d' % limit
        if offset:
            sql = sql + ' OFFSET %d' % offset
        msg = 'sql:%s' % sql
        self.logger.notifyChannel(self._name+'.search', netsvc.LOG_DEBUG,msg)
        cr.execute(sql)
        ids = [(r[0]) for r in cr.fetchall()]
        msg = 'ids:%s' % ids
        self.logger.notifyChannel(self._name+'.search', netsvc.LOG_DEBUG,msg)
        return ids

    _name = "account.easy.bank.reconcile.candidate.line"
    _description = "Bank Reconciliation Candidate Statement Line"
    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'move_line_id': fields.many2one('account.move.line', 
                                        'Journal Item',
                                        required=True,
                                        ondelete='cascade',
                                        help="The move of this entry line."),
        'journal_id': fields.related('move_line_id',
                                     'journal_id', 
                                     type='many2one', 
                                     string='Journal ID', 
                                     readonly=True, 
                                     store=False),
        'account_id': fields.related('move_line_id',
                                     'account_id', 
                                     type='many2one', 
                                     string='Account ID', 
                                     readonly=True, 
                                     store=False),
        'date': fields.related('move_line_id',
                               'date', 
                               type='date', 
                               string='Date', 
                               readonly=True, 
                               store=False),
        'reference': fields.related('move_line_id',
                                    'ref', 
                                    type='char', 
                                    size=64, 
                                    string='Reference', 
                                    readonly=True, 
                                    store=False),
        'credit': fields.related('move_line_id',
                                 'credit', 
                                 type='float', 
                                 string='Credit', 
                                 readonly=True, 
                                 store=False),
        'debit': fields.related('move_line_id',
                                'debit', 
                                type='float', 
                                string='Debit', 
                                readonly=True, 
                                store=False),
        'state': fields.selection((('draft','Unposted'), ('pending','Pending'), ('reconciled','Reconciled')), 
                                  'State', 
                                  required=True,
                                  help='Select if on bank statement'),
        'reconcile_journal_id': fields.many2one('account.journal', 
                                                'Reconcile Journal', 
                                                required=True,
                                                readonly=True),
    }
    _defaults = {
        'state': 'draft',
    }

account_easy_bank_reconcile_candidate_line()

class account_easy_bank_reconcile_line(osv.osv):
    _name = "account.easy.bank.reconcile.line"
    logger = netsvc.Logger()

    def onchange_move_line_id(self, cr, uid, line_id, candidate_move_line_id, journal_id, account_id, context = None):
        res = {}
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  'context: %s'%context)
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  'line_id: %s'%line_id)
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  'candidate_move_line_id: %s'%candidate_move_line_id)
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  'journal_id: %s'%journal_id)
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  'account_id: %s'%account_id)

        if not candidate_move_line_id:
            return {}
        candidate_move_line = self.pool.get('account.easy.bank.reconcile.candidate.line').browse(cr, uid, candidate_move_line_id, context=context)

        credit = candidate_move_line.credit
        debit = candidate_move_line.debit
        reference = candidate_move_line.reference
        _date = candidate_move_line.date
        res.update({
            'debit':debit,
            'credit':credit,
            'reference':reference,
            'date': _date,
        })
        # Mark candidate lines as pending
        candidate_move_line.write({'state':'pending'})

        return {'value':res,}

    def post(self, cr, uid, ids, context=None):
        msg = 'ids:%s' % ids
        self.logger.notifyChannel('addons.'+self._name+'.post', netsvc.LOG_DEBUG,msg)
        return True

    def unlink(self, cr, uid, ids, context=None):
        msg = 'ids:%s' % ids
        self.logger.notifyChannel('addons.'+self._name+'.unlink', netsvc.LOG_DEBUG,msg)
        # Mark candidate lines as pending
        #account_easy_bank_reconcile_candidate_line_pool = self.pool.get('account.easy.bank.reconcile.candidate.line')
        for id in ids:
            statement_line = self.browse(cr, uid, id, context=context)
            candidate_line = statement_line.candidate_move_line_id
            msg = 'candidate_line.id:%s' % candidate_line.id
            self.logger.notifyChannel('addons.'+self._name+'.unlink', netsvc.LOG_DEBUG,msg)
            candidate_line.write({'state':'draft'})
        osv.osv.unlink(self, cr, uid, ids, context=context)
        return True

    def button_validate(self, cursor, user, ids, context=None):
        self.logger.notifyChannel('addons.'+self._name+'.button_validate', netsvc.LOG_DEBUG,
                                  'context: %s'%context)
        self.logger.notifyChannel('addons.'+self._name+'.button_validate', netsvc.LOG_DEBUG,
                                  'ids: %s'%ids)

        return self.post(cursor, user, ids, context=context)

    _order = "statement_id desc, sequence"
    _description = "Bank Reconciliation Statement Line"
    _columns = {
        'statement_id': fields.many2one('account.easy.bank.reconcile', 
                                        'Statement',
                                        select=True, 
                                        required=False, 
                                        ondelete='cascade'),
        'sequence': fields.integer('Sequence', 
                                   help="Gives the sequence order when displaying a list of bank statement lines."),
        'candidate_move_line_id': fields.many2one('account.easy.bank.reconcile.candidate.line', 
                                                  'Journal Item',
                                                  required=True,
                                                  help="The move of this entry line."),
        'date': fields.related('candidate_move_line_id',
                               'move_line_id',
                               'date', 
                               type='date', 
                               string='Date', 
                               readonly=True, 
                               store=False),
        'reference': fields.related('candidate_move_line_id',
                                    'move_line_id',
                                    'ref', 
                                    type='char', 
                                    size=64, 
                                    string='Reference', 
                                    readonly=True, 
                                    store=False),
        'credit': fields.related('candidate_move_line_id',
                                 'move_line_id',
                                 'credit', 
                                 type='float', 
                                 string='Credit', 
                                 readonly=True, 
                                 store=False),
        'debit': fields.related('candidate_move_line_id',
                                'move_line_id',
                                'debit', 
                                dtype='float', 
                                string='Debit', 
                                readonly=True, 
                                store=False),
    }

account_easy_bank_reconcile_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
