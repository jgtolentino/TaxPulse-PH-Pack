# Copyright 2025 InsightPulse AI Finance SSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Post-installation hook to setup agencies and tax configurations"""
    _logger.info("Running TaxPulse PH Pack post-installation hook...")

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Create default agencies if not exists
        agencies = [
            {"code": "RIM", "name": "RIM Agency"},
            {"code": "CKVC", "name": "CKVC Agency"},
            {"code": "BOM", "name": "BOM Agency"},
            {"code": "JPAL", "name": "JPAL Agency"},
            {"code": "JLI", "name": "JLI Agency"},
            {"code": "JAP", "name": "JAP Agency"},
            {"code": "LAS", "name": "LAS Agency"},
            {"code": "RMQB", "name": "RMQB Agency"},
        ]

        Agency = env["taxpulse.agency"]
        for agency_data in agencies:
            existing = Agency.search([("code", "=", agency_data["code"])], limit=1)
            if not existing:
                Agency.create(agency_data)
                _logger.info(f"Created agency: {agency_data['code']}")

        _logger.info("TaxPulse PH Pack post-installation hook completed successfully")
