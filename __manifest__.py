# Copyright 2025 InsightPulse AI Finance SSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "TaxPulse PH Pack",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Philippine BIR Tax Compliance & Multi-Agency Finance Automation",
    "author": "InsightPulse AI, Jake Tolentino",
    "website": "https://github.com/jgtolentino/TaxPulse-PH-Pack",
    "license": "AGPL-3",
    "depends": [
        "account",
        "account_reports",
        "l10n_ph",
        "analytic",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/bir_form_templates.xml",
        "data/agency_data.xml",
        "views/bir_1601c_views.xml",
        "views/bir_2550q_views.xml",
        "views/bir_1702rt_views.xml",
        "views/taxpulse_agency_views.xml",
        "views/taxpulse_menu.xml",
        "reports/bir_1601c_report.xml",
        "reports/bir_2550q_report.xml",
        "reports/bir_1702rt_report.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "external_dependencies": {
        "python": ["requests", "psycopg2"],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}
