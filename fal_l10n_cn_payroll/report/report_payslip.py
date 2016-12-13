#-*- coding:utf-8 -*-

from openerp.report import report_sxw
from openerp.tools import amount_to_text_en

class payslip_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(payslip_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_payslip_lines': self.get_payslip_lines,
        })

    def get_payslip_lines(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].appears_on_payslip == True:
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

report_sxw.report_sxw('report.fal_payslip', 'hr.payslip', 'fal_l10n_cn_payroll/report/report_payslip.rml', parser=payslip_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
