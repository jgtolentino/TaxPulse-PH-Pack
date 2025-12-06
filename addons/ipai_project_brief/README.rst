==================
IPAI Project Brief
==================

Purpose
-------

This module adds a simple, structured "Project Brief" object to Odoo 18 CE,
designed for creative/agency workflows. It allows project teams to capture
objectives, audience, key message, deliverables, budget, and deadline in one
place, linked to a standard Odoo project.

Features
--------

* New model: ``project.brief`` with:
  - Title, project, client, brand
  - Objective, target audience, key message, deliverables
  - Budget (monetary), deadline, status, lock flag
* Status flow: Draft → In Review → Approved / On Hold / Cancelled
* Automatic lock of approved briefs (non-admin users cannot edit)
* Menu and tree/form/search views under Project
* Basic demo data example for quick testing
* Tests:
  - Creating a brief
  - Deadline constraint
  - Approval and lock behaviour

Dependencies
------------

* Project
* Contacts

Usage
-----

* Go to **Project → Project Briefs**.
* Create a new brief and link it to a project and client.
* Use the status buttons to move the brief through review and approval.
* Once approved, the brief is locked for editing by non-admins.

License
-------

LGPL-3
