# -*- coding: utf-8 -*-
from openerp import api, fields, models, _


class account_account(models.Model):
    _inherit = 'account.account'

    def _check_recursion(self):
        for account in self:
            visited_branch = set()
            visited_node = set()
            res = self._check_cycle(visited_branch, visited_node)
            if not res:
                return False

        return True

    def _check_cycle(self, visited_branch, visited_node):
        if id in visited_branch:  # Cycle
            return False

        if id in visited_node:  # Already tested don't work one more time for nothing
            return True

        visited_branch.add(id)
        visited_node.add(id)

        # visit child using DFS
        account = self
        for child in account.child_ids:
            res = child._check_cycle(visited_branch, visited_node)
            if not res:
                return False

        visited_branch.remove(id)
        return True

    @api.one
    @api.depends('name', 'parent_id', 'parent_id.name', 'parent_id.complete_name')
    def _compute_get_full_name(self, name=None, args=None):
        self.complete_name = self._get_one_full_name(self)
        cc_ac = []

        def get_ac(ac, cc_ac):
            c_ac = self.search([('parent_id', '=', ac.id)])
            cc_ac.extend(c_ac)
            if c_ac:
                for acc in c_ac:
                    get_ac(acc, cc_ac)
            else:
                return False

        get_ac(self, cc_ac)
        for ac in cc_ac:
            name = ac._get_one_full_name(ac)
            self.env.cr.execute("update account_account set complete_name= %s where id= %s", (name, ac.id))

    def _get_one_full_name(self, elmt, level=99):
        if elmt.parent_id:
            parent_path = self._get_one_full_name(elmt.parent_id, level-1) + " / "
        else:
            parent_path = ''
        return parent_path + str(elmt.name and elmt.name.encode('utf-8', 'ignore'))

    @api.multi
    def _compute_child_compute(self, name=None, arg=None):
        for account in self:
            account.child_complete_ids = map(lambda x: x.id, [child for child in account.child_ids])


    #fields start here
    complete_name = fields.Char(string='Full Name', compute=_compute_get_full_name, store=True)
    account_type = fields.Selection([('view','Account View'), ('normal','Normal Account')], 'Type of Account', required=True, default='normal')
    parent_id = fields.Many2one('account.account', 'Parent Account', domain="[('account_type', '=', 'view')]", ondelete='restrict')
    child_ids = fields.One2many('account.account', 'parent_id', 'Child Accounts', copy=False)
    child_complete_ids = fields.Many2many('account.account', compute=_compute_child_compute, string="Account Hierarchy")
    #end here

    _constraints = [(_check_recursion, _('Error! You cannot create recursive hierarchy'), ['parent_id']),]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if ['account_type', '=', 'view'] not in args:
            args.append(('account_type','!=','view'))
        return super(account_account, self).name_search(name, args, operator)

#end of account_account()


class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'
    _rec_name = 'complete_name'

    def _check_recursion(self):
        for account in self:
            visited_branch = set()
            visited_node = set()
            res = account._check_cycle(visited_branch, visited_node)
            if not res:
                return False

        return True

    def _check_cycle(self, visited_branch, visited_node, context=None):
        if id in visited_branch:  # Cycle
            return False

        if id in visited_node:  # Already tested don't work one more time for nothing
            return True

        visited_branch.add(id)
        visited_node.add(id)

        # visit child using DFS
        account_analytic_account = self
        for child in account_analytic_account.child_ids:
            res = child._check_cycle(visited_branch, visited_node)
            if not res:
                return False

        visited_branch.remove(id)
        return True

    @api.one
    @api.depends('name', 'parent_id', 'parent_id.name', 'parent_id.complete_name')
    def _compute_get_full_name(self, name=None, args=None):
        self.complete_name = self._get_one_full_name(self)
        cc_ac = []

        def get_ac(ac, cc_ac):
            c_ac = self.search([('parent_id', '=', ac.id)])
            cc_ac.extend(c_ac)
            if c_ac:
                for acc in c_ac:
                    get_ac(acc, cc_ac)
            else:
                return False

        get_ac(self, cc_ac)
        for ac in cc_ac:
            name = ac._get_one_full_name(ac)
            self.env.cr.execute("update account_analytic_account set complete_name= %s where id= %s", (name, ac.id))

    def _get_one_full_name(self, elmt, level=99):
        if elmt.parent_id:
            parent_path = self._get_one_full_name(elmt.parent_id, level-1) + " / "
        else:
            parent_path = ''
        return parent_path + str(elmt.name and elmt.name.encode('utf-8', 'ignore'))

    @api.multi
    def _compute_child_compute(self, name=None, arg=None):
        for account in self:
            account.child_complete_ids = map(lambda x: x.id, [child for child in account.child_ids])


    #fields start here
    complete_name = fields.Char(string='Full Name', compute=_compute_get_full_name, store=True)
    account_type = fields.Selection([('view','Analytic View'), ('normal','Analytic Account')], 'Type of Account', required=True,
                                 help="If you select the View Type, it means you won\'t allow to create journal entries using that account.\n"\
                                  "The type 'Analytic account' stands for usual accounts that you only want to use in accounting.", default='normal')
    parent_id = fields.Many2one('account.analytic.account', 'Parent Analytic Account', domain="[('account_type', '=', 'view')]", ondelete='restrict')
    child_ids = fields.One2many('account.analytic.account', 'parent_id', 'Child Accounts', copy=False)
    child_complete_ids = fields.Many2many('account.analytic.account', compute=_compute_child_compute, string="Account Hierarchy")
    #end here

    _constraints = [(_check_recursion, _('Error! You cannot create recursive hierarchy'), ['parent_id']),]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if ['account_type', '=','view'] not in args:
            args.append(('account_type','!=','view'))

        return super(account_analytic_account, self).name_search(name, args, operator)

#end of account_analytic_account()

class AccountAccountTemplate(models.Model):
    _inherit = "account.account.template"

    account_type = fields.Selection([('view','Account View'), ('normal','Normal Account')], 'Type of Account', required=True, default='normal')
    parent_id = fields.Many2one('account.account.template', 'Parent Account', ondelete='restrict')

#end of AccountAccountTemplate()

class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.multi
    def generate_account(self, tax_template_ref, acc_template_ref, code_digits, company):
        self.ensure_one()
        account_obj = self.env['account.account']
        account_tmpl_obj = self.env['account.account.template']
        res = super(AccountChartTemplate, self).generate_account(tax_template_ref, acc_template_ref, code_digits, company)
        for key, value in res.items():
            account_template_id = account_tmpl_obj.browse(key)
            parent_id = account_template_id.parent_id and ((account_template_id.parent_id.id in res) and res[account_template_id.parent_id.id]) or False
            account_obj.browse(value).write({
                'parent_id': parent_id,
                'account_type': account_template_id.account_type,
            })
        return res

#end of AccountAccountTemplate()