# ipai_project_brief/__manifest__.py
{
    "name": "IPAI Project Brief",
    "summary": "Adds structured project briefs for creative/agency projects.",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "author": "InsightPulseAI",
    "website": "https://insightpulseai.net",
    "category": "Project",
    "depends": [
        "project",
        "contacts",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/project_menu.xml",
        "views/project_brief_views.xml",
        "data/project_brief_demo.xml",
    ],
    "application": False,
    "installable": True,
}
