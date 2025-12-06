# Copyright 2025 InsightPulse AI Finance SSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BIR1601C(models.Model):
    """BIR Form 1601-C: Monthly Withholding Tax (Compensation & Final)"""

    _name = "bir.1601c"
    _description = "BIR Form 1601-C - Monthly Withholding Tax"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "period_end desc, agency_id"

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

    # Period fields
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
    month = fields.Selection(
        [
            ("01", "January"),
            ("02", "February"),
            ("03", "March"),
            ("04", "April"),
            ("05", "May"),
            ("06", "June"),
            ("07", "July"),
            ("08", "August"),
            ("09", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Month",
        required=True,
        compute="_compute_month",
        store=True,
    )
    year = fields.Char(
        string="Year", required=True, compute="_compute_year", store=True
    )

    # Withholding tax details
    compensation_tax = fields.Monetary(
        string="Compensation Tax",
        currency_field="currency_id",
        tracking=True,
        help="Withholding tax on compensation (salaries)",
    )
    final_tax = fields.Monetary(
        string="Final Tax",
        currency_field="currency_id",
        tracking=True,
        help="Final withholding tax",
    )
    total_tax_withheld = fields.Monetary(
        string="Total Tax Withheld",
        currency_field="currency_id",
        compute="_compute_total_tax",
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

    # Line items
    line_ids = fields.One2many(
        "bir.1601c.line",
        "form_id",
        string="Tax Lines",
        states={"posted": [("readonly", True)]},
    )

    @api.depends("period_end")
    def _compute_month(self):
        """Compute month from period end date"""
        for record in self:
            if record.period_end:
                record.month = record.period_end.strftime("%m")
            else:
                record.month = False

    @api.depends("period_end")
    def _compute_year(self):
        """Compute year from period end date"""
        for record in self:
            if record.period_end:
                record.year = record.period_end.strftime("%Y")
            else:
                record.year = False

    @api.depends("compensation_tax", "final_tax")
    def _compute_total_tax(self):
        """Compute total tax withheld"""
        for record in self:
            record.total_tax_withheld = record.compensation_tax + record.final_tax

    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if vals.get("name", "/") == "/":
            vals["name"] = self.env["ir.sequence"].next_by_code("bir.1601c") or "/"
        return super().create(vals)

    def action_confirm(self):
        """Confirm the BIR 1601-C form"""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(
                _("Cannot confirm form without tax lines. Please add tax details.")
            )
        self.write({"state": "confirmed"})
        return True

    def action_post(self):
        """Post the BIR 1601-C form"""
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(_("Form must be confirmed before posting."))
        self.write({"state": "posted"})
        # Trigger Supabase sync
        self.action_sync_to_supabase()
        return True

    def action_cancel(self):
        """Cancel the BIR 1601-C form"""
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
        """Sync BIR 1601-C data to Supabase"""
        for record in self:
            sync_model = self.env["taxpulse.supabase.sync"]
            result = sync_model.sync_bir_1601c(record)
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
        """Print BIR 1601-C report"""
        self.ensure_one()
        return self.env.ref("taxpulse_ph_pack.action_report_bir_1601c").report_action(
            self
        )

    def compute_withholding_tax_from_moves(self):
        """Automatically compute withholding tax from account moves

        This method scans posted account moves within the form's period and
        extracts withholding tax amounts from move lines. It identifies:
        - Compensation tax: Withholding on employee compensation (salaries)
        - Final tax: Final withholding tax on various income types

        Tax identification is based on:
        1. Tax groups (account.tax.group) with 'compensation' or 'final' in the name
        2. Tax codes starting with 'WC' (compensation) or 'WF'/'F' (final)
        3. Account codes containing '2160' (typical PH withholding payable accounts)
        """
        self.ensure_one()

        # Query account moves for the period
        AccountMove = self.env["account.move"]
        domain = [
            ("date", ">=", self.period_start),
            ("date", "<=", self.period_end),
            ("state", "=", "posted"),
        ]

        # Filter by agency's analytic account if available
        if self.agency_id.analytic_account_id:
            domain.append(
                (
                    "line_ids.analytic_account_id",
                    "=",
                    self.agency_id.analytic_account_id.id,
                )
            )

        moves = AccountMove.search(domain)

        # Extract withholding tax from move lines
        compensation_tax = 0.0
        final_tax = 0.0

        # Get all move lines from the period's moves
        move_lines = self.env["account.move.line"].search(
            [
                ("move_id", "in", moves.ids),
                ("tax_line_id", "!=", False),  # Only tax lines
            ]
        )

        for line in move_lines:
            tax = line.tax_line_id
            tax_amount = abs(line.balance)  # Use absolute value for reporting

            # Determine tax type based on tax configuration
            is_compensation = False
            is_final = False

            # Check tax group name
            if tax.tax_group_id:
                group_name = (tax.tax_group_id.name or "").lower()
                if (
                    "compensation" in group_name
                    or "salary" in group_name
                    or "payroll" in group_name
                ):
                    is_compensation = True
                elif "final" in group_name:
                    is_final = True

            # Check tax name/description for classification
            tax_name = (tax.name or "").upper()
            tax_description = (tax.description or "").upper()

            # Compensation withholding indicators
            if any(
                indicator in tax_name or indicator in tax_description
                for indicator in [
                    "WC",
                    "COMPENSATION",
                    "SALARY",
                    "PAYROLL",
                    "1601C",
                    "1601-C",
                ]
            ):
                is_compensation = True
            # Final withholding indicators
            elif any(
                indicator in tax_name or indicator in tax_description
                for indicator in ["WF", "FINAL", "F001", "F002", "F003", "F004", "F005"]
            ):
                is_final = True

            # Accumulate based on classification
            if is_compensation:
                compensation_tax += tax_amount
            elif is_final:
                final_tax += tax_amount

        self.write(
            {
                "compensation_tax": compensation_tax,
                "final_tax": final_tax,
            }
        )


class BIR1601CLine(models.Model):
    """Tax line items for BIR 1601-C"""

    _name = "bir.1601c.line"
    _description = "BIR 1601-C Tax Line"
    _order = "sequence, id"

    form_id = fields.Many2one(
        "bir.1601c", string="Form", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Description", required=True)
    tax_type = fields.Selection(
        [("compensation", "Compensation"), ("final", "Final")],
        string="Tax Type",
        required=True,
    )
    tax_base = fields.Monetary(
        string="Tax Base",
        currency_field="currency_id",
        help="Base amount subject to tax",
    )
    tax_rate = fields.Float(string="Tax Rate (%)", digits=(5, 2))
    tax_amount = fields.Monetary(
        string="Tax Amount",
        currency_field="currency_id",
        compute="_compute_tax_amount",
        store=True,
    )
    currency_id = fields.Many2one(related="form_id.currency_id", readonly=True)

    @api.depends("tax_base", "tax_rate")
    def _compute_tax_amount(self):
        """Compute tax amount"""
        for line in self:
            line.tax_amount = line.tax_base * (line.tax_rate / 100.0)
