# Copyright 2025 InsightPulse AI Finance SSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BIR1702RT(models.Model):
    """BIR Form 1702-RT: Annual Income Tax Return"""

    _name = "bir.1702rt"
    _description = "BIR Form 1702-RT - Annual Income Tax"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "fiscal_year desc, agency_id"

    name = fields.Char(
        string="Form Number", required=True, copy=False, readonly=True, default="/"
    )
    agency_id = fields.Many2one(
        "taxpulse.agency",
        string="Agency",
        required=True,
        tracking=True,
        states={"posted": [("readonly", True)]},
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    tin = fields.Char(string="TIN", related="agency_id.tin", readonly=True)
    rdo_code = fields.Char(
        string="RDO Code", related="agency_id.rdo_code", readonly=True
    )

    # Fiscal year fields
    fiscal_year = fields.Char(
        string="Fiscal Year",
        required=True,
        tracking=True,
        states={"posted": [("readonly", True)]},
    )
    period_start = fields.Date(
        string="Period Start",
        required=True,
        tracking=True,
        states={"posted": [("readonly", True)]},
    )
    period_end = fields.Date(
        string="Period End",
        required=True,
        tracking=True,
        states={"posted": [("readonly", True)]},
    )

    # Income and tax details
    gross_income = fields.Monetary(
        string="Gross Income",
        currency_field="currency_id",
        tracking=True,
    )
    deductions = fields.Monetary(
        string="Deductions",
        currency_field="currency_id",
        tracking=True,
    )
    taxable_income = fields.Monetary(
        string="Taxable Income",
        currency_field="currency_id",
        compute="_compute_taxable_income",
        store=True,
        tracking=True,
    )
    income_tax_due = fields.Monetary(
        string="Income Tax Due",
        currency_field="currency_id",
        tracking=True,
    )
    tax_credits = fields.Monetary(
        string="Tax Credits",
        currency_field="currency_id",
        tracking=True,
    )
    net_tax_payable = fields.Monetary(
        string="Net Tax Payable",
        currency_field="currency_id",
        compute="_compute_net_tax",
        store=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )

    # Status fields
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    # Supabase sync
    supabase_synced = fields.Boolean(string="Synced to Supabase", default=False)
    supabase_id = fields.Char(string="Supabase ID", readonly=True)
    last_sync_date = fields.Datetime(string="Last Sync Date", readonly=True)

    @api.depends("gross_income", "deductions")
    def _compute_taxable_income(self):
        """Compute taxable income"""
        for record in self:
            record.taxable_income = record.gross_income - record.deductions

    @api.depends("income_tax_due", "tax_credits")
    def _compute_net_tax(self):
        """Compute net tax payable"""
        for record in self:
            record.net_tax_payable = record.income_tax_due - record.tax_credits

    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if vals.get("name", "/") == "/":
            vals["name"] = self.env["ir.sequence"].next_by_code("bir.1702rt") or "/"
        return super().create(vals)

    def action_confirm(self):
        """Confirm the BIR 1702-RT form"""
        self.ensure_one()
        self.write({"state": "confirmed"})
        return True

    def action_post(self):
        """Post the BIR 1702-RT form"""
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(_("Form must be confirmed before posting."))
        self.write({"state": "posted"})
        # Trigger Supabase sync
        self.action_sync_to_supabase()
        return True

    def action_cancel(self):
        """Cancel the BIR 1702-RT form"""
        self.ensure_one()
        if self.state == "posted":
            raise UserError(
                _("Cannot cancel a posted form. Create a corrective entry instead.")
            )
        self.write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        """Reset form to draft"""
        self.ensure_one()
        self.write({"state": "draft"})
        return True

    def action_sync_to_supabase(self):
        """Sync BIR 1702-RT data to Supabase"""
        for record in self:
            sync_model = self.env["taxpulse.supabase.sync"]
            result = sync_model.sync_bir_1702rt(record)
            if result.get("success"):
                record.write(
                    {
                        "supabase_synced": True,
                        "supabase_id": result.get("supabase_id"),
                        "last_sync_date": fields.Datetime.now(),
                    }
                )
        return True

    def action_print_report(self):
        """Print BIR 1702-RT report"""
        self.ensure_one()
        return self.env.ref("taxpulse_ph_pack.action_report_bir_1702rt").report_action(
            self
        )
