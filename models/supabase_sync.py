# Copyright 2025 InsightPulse AI Finance SSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import os
import logging
import json

_logger = logging.getLogger(__name__)


class TaxPulseSupabaseSync(models.Model):
    """Supabase synchronization handler for TaxPulse"""

    _name = "taxpulse.supabase.sync"
    _description = "Supabase Sync Handler"

    def _get_supabase_config(self):
        """Get Supabase configuration from environment"""
        config = {
            "url": os.environ.get("SUPABASE_URL", "https://xkxyvboeubffxxbebsll.supabase.co"),
            "service_role_key": os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        }

        if not config["service_role_key"]:
            raise UserError(
                _("Supabase service role key not configured. Please set SUPABASE_SERVICE_ROLE_KEY environment variable.")
            )

        return config

    def _make_supabase_request(self, endpoint, method="POST", data=None):
        """Make authenticated request to Supabase RPC endpoint"""
        config = self._get_supabase_config()
        url = f"{config['url']}/rest/v1/rpc/{endpoint}"

        headers = {
            "apikey": config["service_role_key"],
            "Authorization": f"Bearer {config['service_role_key']}",
            "Content-Type": "application/json",
        }

        try:
            if method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=20)
            elif method == "GET":
                response = requests.get(url, headers=headers, params=data, timeout=20)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return {"success": True, "data": response.json()}

        except requests.exceptions.HTTPError as e:
            _logger.error(f"Supabase HTTP error: {e.response.text}")
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except requests.exceptions.RequestException as e:
            _logger.error(f"Supabase request error: {str(e)}")
            return {"success": False, "error": str(e)}

    def sync_bir_1601c(self, record):
        """Sync BIR 1601-C form to Supabase"""
        if not record:
            return {"success": False, "error": "No record provided"}

        data = {
            "p_odoo_id": record.id,
            "p_agency_code": record.agency_id.code,
            "p_agency_name": record.agency_id.name,
            "p_form_number": record.name,
            "p_period_start": record.period_start.isoformat() if record.period_start else None,
            "p_period_end": record.period_end.isoformat() if record.period_end else None,
            "p_month": record.month,
            "p_year": record.year,
            "p_compensation_tax": float(record.compensation_tax),
            "p_final_tax": float(record.final_tax),
            "p_total_tax_withheld": float(record.total_tax_withheld),
            "p_state": record.state,
            "p_tin": record.tin or "",
            "p_rdo_code": record.rdo_code or "",
        }

        result = self._make_supabase_request("upsert_bir_1601c", data=data)

        if result.get("success"):
            result["supabase_id"] = result.get("data", {}).get("id")
            _logger.info(f"Successfully synced BIR 1601-C {record.name} to Supabase")
        else:
            _logger.error(f"Failed to sync BIR 1601-C {record.name}: {result.get('error')}")

        return result

    def sync_bir_2550q(self, record):
        """Sync BIR 2550Q form to Supabase"""
        if not record:
            return {"success": False, "error": "No record provided"}

        data = {
            "p_odoo_id": record.id,
            "p_agency_code": record.agency_id.code,
            "p_agency_name": record.agency_id.name,
            "p_form_number": record.name,
            "p_quarter_start": record.quarter_start.isoformat() if record.quarter_start else None,
            "p_quarter_end": record.quarter_end.isoformat() if record.quarter_end else None,
            "p_quarter": record.quarter,
            "p_year": record.year,
            "p_output_vat": float(record.output_vat),
            "p_input_vat": float(record.input_vat),
            "p_vat_payable": float(record.vat_payable),
            "p_state": record.state,
            "p_tin": record.tin or "",
            "p_rdo_code": record.rdo_code or "",
        }

        result = self._make_supabase_request("upsert_bir_2550q", data=data)

        if result.get("success"):
            result["supabase_id"] = result.get("data", {}).get("id")
            _logger.info(f"Successfully synced BIR 2550Q {record.name} to Supabase")
        else:
            _logger.error(f"Failed to sync BIR 2550Q {record.name}: {result.get('error')}")

        return result

    def sync_bir_1702rt(self, record):
        """Sync BIR 1702-RT form to Supabase"""
        if not record:
            return {"success": False, "error": "No record provided"}

        data = {
            "p_odoo_id": record.id,
            "p_agency_code": record.agency_id.code,
            "p_agency_name": record.agency_id.name,
            "p_form_number": record.name,
            "p_fiscal_year": record.fiscal_year,
            "p_period_start": record.period_start.isoformat() if record.period_start else None,
            "p_period_end": record.period_end.isoformat() if record.period_end else None,
            "p_gross_income": float(record.gross_income),
            "p_deductions": float(record.deductions),
            "p_taxable_income": float(record.taxable_income),
            "p_income_tax_due": float(record.income_tax_due),
            "p_tax_credits": float(record.tax_credits),
            "p_net_tax_payable": float(record.net_tax_payable),
            "p_state": record.state,
            "p_tin": record.tin or "",
            "p_rdo_code": record.rdo_code or "",
        }

        result = self._make_supabase_request("upsert_bir_1702rt", data=data)

        if result.get("success"):
            result["supabase_id"] = result.get("data", {}).get("id")
            _logger.info(f"Successfully synced BIR 1702-RT {record.name} to Supabase")
        else:
            _logger.error(f"Failed to sync BIR 1702-RT {record.name}: {result.get('error')}")

        return result

    def bulk_sync_all(self):
        """Bulk sync all BIR forms to Supabase"""
        results = {
            "bir_1601c": {"success": 0, "failed": 0},
            "bir_2550q": {"success": 0, "failed": 0},
            "bir_1702rt": {"success": 0, "failed": 0},
        }

        # Sync all BIR 1601-C forms
        forms_1601c = self.env["bir.1601c"].search([("state", "=", "posted")])
        for form in forms_1601c:
            result = self.sync_bir_1601c(form)
            if result.get("success"):
                results["bir_1601c"]["success"] += 1
            else:
                results["bir_1601c"]["failed"] += 1

        # Sync all BIR 2550Q forms
        forms_2550q = self.env["bir.2550q"].search([("state", "=", "posted")])
        for form in forms_2550q:
            result = self.sync_bir_2550q(form)
            if result.get("success"):
                results["bir_2550q"]["success"] += 1
            else:
                results["bir_2550q"]["failed"] += 1

        # Sync all BIR 1702-RT forms
        forms_1702rt = self.env["bir.1702rt"].search([("state", "=", "posted")])
        for form in forms_1702rt:
            result = self.sync_bir_1702rt(form)
            if result.get("success"):
                results["bir_1702rt"]["success"] += 1
            else:
                results["bir_1702rt"]["failed"] += 1

        _logger.info(f"Bulk sync completed: {json.dumps(results)}")
        return results
