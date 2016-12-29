#-*- coding:utf-8 -*-
from datetime import datetime

from openerp import netsvc
from openerp import api, fields, models, _
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class hr_payslip(models.Model):
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'

    # overide real method
    @api.model
    def get_payslip_lines(self, contract_ids, payslip_id):
        results = super(hr_payslip, self).get_payslip_lines(
                    contract_ids, payslip_id)

        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict,
                                                      category.parent_id,
                                                      amount)
            localdict['categories'].dict[category.code] =\
                category.code in localdict['categories'].dict and\
                localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute(
                    """
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute(
                    """
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

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
                    to_date = fields.Date.today()
                self.env.cr.execute(
                            """
                            SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                            FROM hr_payslip as hp, hr_payslip_line as pl
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                            (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten by another rule with the same code
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        # blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)
        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days, 'inputs': inputs}
        # get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            localdict['result'] = None
            localdict['result_qty'] = 1.0
            for rule in sorted_rules:
                if rule.fal_is_insurance:
                    for result in results:
                        if result['code'] == rule.code:
                            amount, qty, rate = rule.fal_rule_child_employee_id.compute_rule(localdict)
                            if not amount:
                                rate = 0.00
                            localdict['result'] = None
                            localdict['result_qty'] = 1.0
                            amount2, qty2, rate2 = rule.fal_rule_child_employeer_id.compute_rule(localdict)
                            result['amount'] = max(amount, amount2)
                            result['rate'] = rate
                            result['fal_rate_er'] = rate2
        return results

    def cancel_sheet(self):
        move_obj = self.env['account.move']
        for payslip in self:
            if payslip.move_id:
                move_obj.button_cancel([payslip.move_id.id])
        return super(hr_payslip, self).cancel_sheet()

# end of hr_payslip()


class hr_payslip_line(models.Model):
    '''
    Payslip Line
    '''
    _name = 'hr.payslip.line'
    _inherit = 'hr.payslip.line'

    @api.depends('quantity', 'amount', 'fal_rate_er')
    def _calculate_total2(self):
        for line in self:
            line.fal_total_er =\
                float(line.quantity) * line.amount * line.fal_rate_er / 100

    amount = fields.Float(
                    'Base Amount',
                    digits_compute=dp.get_precision('Payroll'))
    fal_rate_er = fields.Float(
                    'Employeer Rate (%)',
                    digits_compute=dp.get_precision('Payroll Rate'))
    fal_total_er = fields.Float(
                    compute='_calculate_total2',
                    string='Employeer Total',
                    digits_compute=dp.get_precision('Payroll'),
                    store=True)

# end of hr_payslip_line()


class hr_salary_rule(models.Model):

    _name = 'hr.salary.rule'
    _inherit = 'hr.salary.rule'

    fal_is_insurance = fields.Boolean('Is Insurance')
    fal_rule_child_employee_id = fields.Many2one(
                                    'hr.salary.rule',
                                    'Rule Child for Employee')
    fal_rule_child_employeer_id = fields.Many2one(
                                    'hr.salary.rule',
                                    'Rule Child for Employeer')
    fal_highlight_on_payslip = fields.Boolean(
                                    'Highlight on payslip',
                                    help="Highlight on the payslip")

# end of hr_salary_rule()


class hr_contract(models.Model):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    fal_fixed_allowance = fields.Float(
                                'Job Allowance',
                                digits=(16, 2),
                                required=True,
                                help="Job Allowance of the employee")
    fal_house_allowance = fields.Float(
                            'House Allowance',
                            digits=(16, 2),
                            help="House Allowance of the employee")
    fal_haf_base = fields.Float(
                            'HAF Base',
                            digits=(16, 2),
                            required=True,
                            help="Based for House Allowance of the employee")
    fal_si_base = fields.Float(
                        'SI Base',
                        digits=(16, 2),
                        required=True,
                        help="Based for Social Insurance of the employee")

# end of hr_contract()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
