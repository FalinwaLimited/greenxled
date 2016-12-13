#-*- coding:utf-8 -*-
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from openerp import netsvc
from openerp.osv import fields, orm
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval

class hr_payslip(orm.Model):
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'
    #overide real method
    def get_payslip_lines(self, cr, uid, contract_ids, payslip_id, context):
        results = super(hr_payslip, self).get_payslip_lines(cr, uid, contract_ids, payslip_id, context=context)

        class BrowsableObject(object):
            def __init__(self, pool, cr, uid, employee_id, dict):
                self.pool = pool
                self.cr = cr
                self.uid = uid
                self.employee_id = employee_id
                self.dict = dict

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                result = 0.0
                self.cr.execute("SELECT sum(amount) as sum\
                            FROM hr_payslip as hp, hr_payslip_input as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done' \
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                           (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()[0]
                return res or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                result = 0.0
                self.cr.execute("SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours\
                            FROM hr_payslip as hp, hr_payslip_worked_days as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done'\
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                           (self.employee_id, from_date, to_date, code))
                return self.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)\
                            FROM hr_payslip as hp, hr_payslip_line as pl \
                            WHERE hp.employee_id = %s AND hp.state = 'done' \
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s",
                            (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()
                return res and res[0] or 0.0

        payslip_obj = self.pool.get('hr.payslip')
        payslip = payslip_obj.browse(cr, uid, payslip_id, context=context)
        inputs_obj = self.pool.get('hr.payslip.worked_days')
        input_obj = InputLine(self.pool, cr, uid, payslip.employee_id.id, {})
        worked_days_obj = WorkedDays(self.pool, cr, uid, payslip.employee_id.id, {})
        obj_rule = self.pool.get('hr.salary.rule')       
        categories_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, {})
        payslip_obj = Payslips(self.pool, cr, uid, payslip.employee_id.id, payslip)
        rules_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, {})
        localdict = {'categories': categories_obj, 'rules': rules_obj, 'payslip': payslip_obj, 'worked_days': worked_days_obj, 'inputs': input_obj}
        #get the ids of the structures on the contracts and their parent id as well
        structure_ids = self.pool.get('hr.contract').get_all_structures(cr, uid, contract_ids, context=context)
        #get the rules of the structure and thier children
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
        #run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            employee = contract.employee_id
            localdict.update({'employee': employee, 'contract': contract})
            localdict['result'] = None
            localdict['result_qty'] = 1.0
            for rule in obj_rule.browse(cr, uid, sorted_rule_ids, context=context):
                if rule.fal_is_insurance:
                    for result in results:
                        if result['code'] == rule.code :
                            amount, qty, rate = obj_rule.compute_rule(cr, uid, rule.fal_rule_child_employee_id.id, localdict, context=context)
                            if not amount:
                                rate = 0.00
                            localdict['result'] = None
                            localdict['result_qty'] = 1.0
                            amount2, qty2, rate2 = obj_rule.compute_rule(cr, uid, rule.fal_rule_child_employeer_id.id, localdict, context=context)
                            result['amount'] = max(amount, amount2)
                            result['rate'] = rate
                            result['fal_rate_er'] = rate2
        return results
    
    def cancel_sheet(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('account.move')
        for payslip in self.browse(cr, uid, ids):
            if payslip.move_id:
                move_obj.button_cancel(cr, uid, [payslip.move_id.id], context)
        return super(hr_payslip, self).cancel_sheet(cr, uid, ids, context)
        
#end of hr_payslip()


class hr_payslip_line(orm.Model):
    '''
    Payslip Line
    '''
    _name = 'hr.payslip.line'
    _inherit = 'hr.payslip.line'
    
    def _calculate_total2(self, cr, uid, ids, name, args, context):
        if not ids: return {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = float(line.quantity) * line.amount * line.fal_rate_er / 100
        return res
        
    _columns = {
        'amount': fields.float('Base Amount', digits_compute=dp.get_precision('Payroll')),
        'fal_rate_er': fields.float('Employeer Rate (%)', digits_compute=dp.get_precision('Payroll Rate')),
        'fal_total_er': fields.function(_calculate_total2, method=True, type='float', string='Employeer Total', digits_compute=dp.get_precision('Payroll'),store=True ),
    }
        
#end of hr_payslip_line()

class hr_salary_rule(orm.Model):

    _name = 'hr.salary.rule'
    _inherit = 'hr.salary.rule'
    _columns = {
        'fal_is_insurance' : fields.boolean('Is Insurance'),
        'fal_rule_child_employee_id':fields.many2one('hr.salary.rule', 'Rule Child for Employee'),
        'fal_rule_child_employeer_id':fields.many2one('hr.salary.rule', 'Rule Child for Employeer'),
        'fal_highlight_on_payslip' : fields.boolean('Highlight on payslip', help="Highlight on the payslip"),
    }
    
#end of hr_salary_rule()

class hr_contract(orm.Model):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    _columns = {
        'fal_fixed_allowance': fields.float('Job Allowance', digits=(16,2), required=True, help="Job Allowance of the employee"),
        'fal_house_allowance': fields.float('House Allowance', digits=(16,2), help="House Allowance of the employee"),
        'fal_haf_base': fields.float('HAF Base', digits=(16,2), required=True, help="Based for House Allowance of the employee"),
        'fal_si_base': fields.float('SI Base', digits=(16,2), required=True, help="Based for Social Insurance of the employee"),
    }

#end of hr_contract()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
