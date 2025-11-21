# Copyright 2025 InsightPulse AI Finance SSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BIR2550Q(models.Model):
    """BIR Form 2550Q: Quarterly VAT Return"""

    _name = "bir.2550q"
    _description = "BIR Form 2550Q - Quarterly VAT"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "quarter_end desc, agency_id"

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
    rdo_code = fields.Char(string="RDO Code", related="agency_id.rdo_code", readonly=True)

    # Quarter fields
    quarter_start = fields.Date(
        string="Quarter Start",
        required=True,
        tracking=True,
        states={"posted": [("readonly", True)]},
    )
    quarter_end = fields.Date(
        string="Quarter End",
        required=True,
        tracking=True,
        states={"posted": [("readonly", True)]},
    )
    quarter = fields.Selection(
        [("Q1", "Q1"), ("Q2", "Q2"), ("Q3", "Q3"), ("Q4", "Q4")],
        string="Quarter",
        required=True,
        compute="_compute_quarter",
        store=True,
    )
    year = fields.Char(string="Year", required=True, compute="_compute_year", store=True)

    # VAT details
    output_vat = fields.Monetary(
        string="Output VAT",
        currency_field="currency_id",
        tracking=True,
        help="VAT on sales",
    )
    input_vat = fields.Monetary(
        string="Input VAT",
        currency_field="currency_id",
        tracking=True,
        help="VAT on purchases",
    )
    vat_payable = fields.Monetary(
        string="VAT Payable",
        currency_field="currency_id",
        compute="_compute_vat_payable",
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

    @api.depends("quarter_end")
    def _compute_quarter(self):
        """Compute quarter from quarter end date"""
        for record in self:
            if record.quarter_end:
                month = int(record.quarter_end.strftime("%m"))
                if month <= 3:
                    record.quarter = "Q1"
                elif month <= 6:
                    record.quarter = "Q2"
                elif month <= 9:
                    record.quarter = "Q3"
                else:
                    record.quarter = "Q4"
            else:
                record.quarter = False

    @api.depends("quarter_end")
    def _compute_year(self):
        """Compute year from quarter end date"""
        for record in self:
            if record.quarter_end:
                record.year = record.quarter_end.strftime("%Y")
            else:
                record.year = False

    @api.depends("output_vat", "input_vat")
    def _compute_vat_payable(self):
        """Compute VAT payable"""
        for record in self:
            record.vat_payable = record.output_vat - record.input_vat

    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if vals.get("name", "/") == "/":
            vals["name"] = self.env["ir.sequence"].next_by_code("bir.2550q") or "/"
        return super().create(vals)

    def action_confirm(self):
        """Confirm the BIR 2550Q form"""
        self.ensure_one()
        self.write({"state": "confirmed"})
        return True

    def action_post(self):
        """Post the BIR 2550Q form"""
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(_("Form must be confirmed before posting."))
        self.write({"state": "posted"})
        # Trigger Supabase sync
        self.action_sync_to_supabase()
        return True

    def action_cancel(self):
        """Cancel the BIR 2550Q form"""
        self.ensure_one()
        if self.state == "posted":
            raise UserError(_("Cannot cancel a posted form. Create a corrective entry instead."))
        self.write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        """Reset form to draft"""
        self.ensure_one()
        self.write({"state": "draft"})
        return True

    def action_sync_to_supabase(self):
        """Sync BIR 2550Q data to Supabase"""
        for record in self:
            sync_model = self.env["taxpulse.supabase.sync"]
            result = sync_model.sync_bir_2550q(record)
            if result.get("success"):
                record.write({
                    "supabase_synced": True,
                    "supabase_id": result.get("supabase_id"),
                    "last_sync_date": fields.Datetime.now(),
                })
        return True

    def action_print_report(self):
        """Print BIR 2550Q report"""
        self.ensure_one()
        return self.env.ref("taxpulse_ph_pack.action_report_bir_2550q").report_action(self)
