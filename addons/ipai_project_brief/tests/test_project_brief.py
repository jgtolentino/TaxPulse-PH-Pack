# ipai_project_brief/tests/test_project_brief.py
from odoo.tests import TransactionCase
from odoo import fields
from odoo.exceptions import ValidationError


class TestProjectBrief(TransactionCase):

    def setUp(self):
        super().setUp()
        self.ProjectBrief = self.env["project.brief"]
        self.project = self.env["project.project"].create(
            {
                "name": "Test Project",
            }
        )
        self.client = self.env["res.partner"].create(
            {
                "name": "Test Client",
                "is_company": True,
            }
        )

    def test_create_brief_basic(self):
        brief = self.ProjectBrief.create(
            {
                "name": "Test Brief",
                "project_id": self.project.id,
                "client_id": self.client.id,
                "deadline": fields.Date.today(),
            }
        )
        self.assertEqual(brief.status, "draft")
        self.assertEqual(brief.project_id, self.project)
        self.assertEqual(brief.client_id, self.client)

    def test_deadline_cannot_be_past(self):
        with self.assertRaises(ValidationError):
            self.ProjectBrief.create(
                {
                    "name": "Past Brief",
                    "project_id": self.project.id,
                    "client_id": self.client.id,
                    "deadline": "2000-01-01",
                }
            )

    def test_approve_locks_brief(self):
        brief = self.ProjectBrief.create(
            {
                "name": "Lock Test",
                "project_id": self.project.id,
                "client_id": self.client.id,
            }
        )
        brief.action_mark_in_review()
        self.assertEqual(brief.status, "in_review")
        brief.action_approve()
        self.assertEqual(brief.status, "approved")
        self.assertTrue(brief.is_locked)

        # Simulate non-admin user trying to write (simplified check)
        with self.assertRaises(ValidationError):
            brief.with_user(self.env.ref("base.user_demo")).write({"name": "Changed"})
