# -*- coding: utf-8 -*-
from openerp import api, fields, models

class account_analytic_chart(models.TransientModel):
    _inherit = 'account.analytic.chart'

    @api.v7
    def analytic_account_chart_open_window(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result_context = {}
        if context is None:
            context = {}
        result = mod_obj.get_object_reference(cr, uid, 'fal_parent_account', 'action_account_analytic_account_tree2')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        data = self.read(cr, uid, ids, [])[0]
        if data['from_date']:
            result_context.update({'from_date': data['from_date']})
        if data['to_date']:
            result_context.update({'to_date': data['to_date']})
        result['context'] = str(result_context)
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
