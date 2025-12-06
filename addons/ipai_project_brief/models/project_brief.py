# ipai_project_brief/models/project_brief.py
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProjectBrief(models.Model):
    _name = "project.brief"
    _description = "Project Brief"
    _order = "create_date desc"

    name = fields.Char(
        string="Brief Title",
        required=True,
        help="Short internal title for this brief.",
    )

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        help="Linked project in Odoo.",
    )

    client_id = fields.Many2one(
        "res.partner",
        string="Client",
        required=True,
        domain=[("is_company", "=", True)],
        help="Client company for this brief.",
    )

    brand_name = fields.Char(
        string="Brand",
        help="Brand involved in this brief.",
    )

    objective = fields.Text(
        string="Objective",
        help="Business/communication objective of the project.",
    )

    target_audience = fields.Text(
        string="Target Audience",
    )

    key_message = fields.Text(
        string="Key Message",
    )

    deliverables = fields.Text(
        string="Deliverables",
    )

    budget = fields.Monetary(
        string="Estimated Budget",
        currency_field="company_currency_id",
    )

    deadline = fields.Date(
        string="Deadline",
    )

    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("approved", "Approved"),
            ("on_hold", "On Hold"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    company_currency_id = fields.Many2one(
        "res.currency",
        string="Company Currency",
        related="company_id.currency_id",
        readonly=True,
    )

    is_locked = fields.Boolean(
        string="Locked",
        help="Locked briefs can no longer be edited, only read.",
        default=False,
    )

    @api.constrains("deadline")
    def _check_deadline(self):
        for rec in self:
            if rec.deadline and rec.deadline < fields.Date.today():
                raise ValidationError(_("Deadline cannot be in the past."))

    def action_mark_in_review(self):
        for rec in self:
            rec.status = "in_review"

    def action_approve(self):
        for rec in self:
            rec.status = "approved"
            rec.is_locked = True

    def action_hold(self):
        for rec in self:
            rec.status = "on_hold"

    def action_cancel(self):
        for rec in self:
            rec.status = "cancelled"

    def write(self, vals):
        """
        Protect locked briefs from being edited except by superuser.
        """
        for rec in self:
            if rec.is_locked and rec.env.uid != self.env.ref("base.user_admin").id:
                raise ValidationError(
                    _(
                        "You cannot edit a locked brief. Please contact an administrator."
                    )
                )
        return super().write(vals)
