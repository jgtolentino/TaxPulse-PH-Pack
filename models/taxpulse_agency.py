# Copyright 2025 InsightPulse AI Finance SSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TaxPulseAgency(models.Model):
    """Agency management for multi-agency Finance SSC operations"""

    _name = "taxpulse.agency"
    _description = "TaxPulse Agency"
    _order = "code"

    name = fields.Char(string="Agency Name", required=True)
    code = fields.Char(string="Agency Code", required=True, size=10, index=True)
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        help="Analytic account for tracking agency expenses",
    )
    tin = fields.Char(string="TIN", help="Tax Identification Number")
    rdo_code = fields.Char(string="RDO Code", help="Revenue District Office code")
    line_of_business = fields.Char(string="Line of Business")
    address = fields.Text(string="Address")
    active = fields.Boolean(string="Active", default=True)

    # BIR Form counters
    bir_1601c_count = fields.Integer(
        string="1601-C Forms", compute="_compute_bir_form_counts"
    )
    bir_2550q_count = fields.Integer(
        string="2550Q Forms", compute="_compute_bir_form_counts"
    )
    bir_1702rt_count = fields.Integer(
        string="1702-RT Forms", compute="_compute_bir_form_counts"
    )

    _sql_constraints = [("code_unique", "UNIQUE(code)", "Agency code must be unique!")]

    @api.depends("code")
    def _compute_bir_form_counts(self):
        """Compute count of BIR forms for each agency"""
        for agency in self:
            agency.bir_1601c_count = self.env["bir.1601c"].search_count(
                [("agency_id", "=", agency.id)]
            )
            agency.bir_2550q_count = self.env["bir.2550q"].search_count(
                [("agency_id", "=", agency.id)]
            )
            agency.bir_1702rt_count = self.env["bir.1702rt"].search_count(
                [("agency_id", "=", agency.id)]
            )

    def action_view_bir_1601c(self):
        """View 1601-C forms for this agency"""
        self.ensure_one()
        return {
            "name": f"BIR 1601-C Forms - {self.code}",
            "type": "ir.actions.act_window",
            "res_model": "bir.1601c",
            "view_mode": "tree,form",
            "domain": [("agency_id", "=", self.id)],
            "context": {"default_agency_id": self.id},
        }

    def action_view_bir_2550q(self):
        """View 2550Q forms for this agency"""
        self.ensure_one()
        return {
            "name": f"BIR 2550Q Forms - {self.code}",
            "type": "ir.actions.act_window",
            "res_model": "bir.2550q",
            "view_mode": "tree,form",
            "domain": [("agency_id", "=", self.id)],
            "context": {"default_agency_id": self.id},
        }

    def action_view_bir_1702rt(self):
        """View 1702-RT forms for this agency"""
        self.ensure_one()
        return {
            "name": f"BIR 1702-RT Forms - {self.code}",
            "type": "ir.actions.act_window",
            "res_model": "bir.1702rt",
            "view_mode": "tree,form",
            "domain": [("agency_id", "=", self.id)],
            "context": {"default_agency_id": self.id},
        }
