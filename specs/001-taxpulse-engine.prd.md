# TaxPulse Engine – PH Tax Rules & Validation Layer (SpectraTax Engine)

**Status:** Draft v1.0
**Product Name:** TaxPulse Engine (TBWA instance: *SpectraTax Engine*)
**Owner:** Finance/Tax Platform Team (TBWA SMP × InsightPulse AI)
**Last Updated:** 2025-11-19

---

## 1. Problem & Context

TBWA\SMP currently uses **Spectra** as the core accounting system. Tax computations for PH (VAT, withholding, income tax) are still heavily:

* Exported from Spectra into **Excel**
* Massaged via **manual formulas** and templates
* Reviewed by internal finance and external firms (SGV / P&A Grant Thornton / R.G. Manabat)

This leads to:

* **High error risk**
  * Copy–paste mistakes, broken Excel links, outdated templates
* **Opaque logic**
  * Tax rules live in people's heads and hidden spreadsheets
* **Slow closing**
  * Month-end crunch and stressful cutoffs, especially for VAT and withholding
* **Weak auditability**
  * Difficult to explain "exactly how this BIR number was computed"

**We need:**

A **deterministic, versioned PH tax rules engine** that sits between Spectra (or any ERP) and BIR filing tools, producing **BIR-ready numbers and auditor-grade workpapers**, with strong validation, reconciliations, and maker–checker controls.

AI agents should *review and explain* outputs, not silently change tax math.

---

## 2. Goals & Non-Goals

### 2.1 Goals

1. **Deterministic PH tax computation**
   * All VAT, withholding, and income tax computations driven by **versioned rules** and rate tables.
   * Same inputs + same rules → **same outputs every time**.

2. **Centralized rule & rate management**
   * PH tax rates, rules, conditions, and mappings to BIR forms stored in **database tables**, not spreadsheets.

3. **Strong validation & reconciliation**
   * Automatic checks for:
     * Missing data (TIN, ATC, tax codes, etc.)
     * Rate/ATC mismatches
     * GL vs tax return totals
     * Subledger vs tax return
     * Period vs period variances

4. **Maker–checker workflow**
   * Controlled lifecycle for each tax return:
     * `Draft → ForReview → Approved → Filed`
   * All approvals and overrides logged.

5. **Parallel-run confidence**
   * Engine validated against **historical months**:
     * Compare against legacy Excel outputs
     * Classify differences and track resolution

6. **AI as "virtual tax senior"**
   * AI agents:
     * Explain numbers, variances, and reconciliations
     * Highlight anomalies or suspicious patterns
   * AI **cannot** modify rules or results directly; human approval required.

### 2.2 Non-Goals (v1)

* Replacing Spectra as the system of record.
* Direct eBIRForms / eFPS filing (v1 outputs are **BIR-ready** schedules + workpapers; e-filing can be added later).
* Handling all exotic PH tax edge cases:
  * Focus is on **recurring core taxes**:
    * VAT (Forms 2550M/2550Q, as applicable)
    * Expanded and final withholding (0619-E/F, 1601-EQ/FQ)
    * Compensation withholding support (1601-C workpapers, not full payroll engine)
    * Quarterly income tax *support* (1702Q workpapers)

---

## 3. Users & Use Cases

### 3.1 Users

* **Finance Tax Preparer (Maker)**
  * Imports data from Spectra.
  * Resolves validation errors and exceptions.
  * Runs computations and generates draft returns.

* **Finance Manager / Tax Reviewer (Checker)**
  * Reviews summaries, reconciliations, exceptions.
  * Approves or rejects returns.
  * Owns final "filed" state.

* **External Auditors / Tax Advisors**
  * Consume engine outputs as **structured workpapers**.
  * Validate methodology and completeness.

* **AI Tax Agents ("Virtual Seniors")**
  * Read-only access into rules, results, and reconciliations.
  * Provide narratives, explanations, and checklists.

### 3.2 Core Use Cases

1. **Compute monthly/quarterly VAT** from Spectra transactions.
2. **Compute expanded and final withholding taxes** from AP and payment data.
3. **Generate BIR-style summaries & attachments** (e.g., ATC-based EWT schedules).
4. **Run validations** and block filing when critical errors exist.
5. **Run reconciliations** (GL vs return, subledger vs return).
6. **Parallel-run historical months** to validate engine vs legacy Excel.
7. **Allow AI assistants to explain and review** but not alter tax math.

---

## 4. Scope (v1)

### In Scope

* TaxPulse Engine core:
  * **Rule/rate tables**
  * **Rules evaluation engine** (JSONLogic-style)
  * **Mapping to BIR forms** via `output_bucket → form/line`
* PH-specific logic:
  * VAT (12%, zero-rated, exempt)
  * Expanded & final withholding (ATC-based)
  * Support for compensation withholding data (summary/integration; payroll remains external)
* Validation engine for data and aggregate checks.
* Reconciliation engine:
  * GL vs Return
  * Subledger vs Return
  * Period vs Period
* Maker–checker workflow and audit logs.
* Test suite and golden datasets.
* Parallel-run tooling for historical months (shadow mode).

### Out of Scope (v1)

* Direct integration into BIR eFPS/eBIRForms APIs or eTSP accreditation.
* Full payroll calculation engine (we assume payroll system already generates correct withholding totals).
* Non-PH tax jurisdictions.

---

## 5. Functional Requirements

### 5.1 Data Ingestion & Canonical Schema

**FR-1** – Data Ingestion Sources

* Support the following input modes:
  * Direct DB read from Spectra views (preferred, read-only).
  * CSV/Excel export from Spectra or other ERPs.

**FR-2** – Canonical Transaction Schema
Normalize ingested data into a canonical schema per transaction line (e.g. `tx_source` view or table) with fields like:

* Core IDs:
  * `txn_id`
  * `company_code`
  * `doc_type` (invoice, bill, CN, DN, etc.)
  * `doc_number`
* Dates:
  * `date` (posting/invoice date)
  * `due_date` (optional)
* Partner data:
  * `partner_id`
  * `partner_name`
  * `partner_type` (customer/vendor/employee)
  * `vendor_type` (e.g., PROFESSIONAL, SUPPLIER, INDIVIDUAL, FOREIGN)
  * `tin` (taxpayer identification number)
* Amounts:
  * `gross_amount`
  * `net_of_vat`
  * `vat_amount`
  * `withholding_base` (optional; else derived)
* Tax labeling:
  * `tax_code` (e.g., VAT_12_SALES, VAT_EXEMPT_PURCH, EWT_PROF_W010)
  * `tax_type` (VAT/EWT/FWT/INCOME)
  * `atc_code` (for WHT)
  * `type_tax_use` (`sale` / `purchase` / `payment`)
* Accounting:
  * `gl_account`
  * `cost_center`
  * `project_code` (for agencies / jobs)
* Meta:
  * `source_system` (e.g., SPECTRA)
  * `import_batch_id`

**FR-3** – Import Logging
Every ingestion run must log:

* `source_system`, `company_code`, `period_start`, `period_end`
* `record_count`
* `source_ref` (filename or DB view name)
* `checksum` of the source file (for traceability)

Stored in `import_log`.

---

### 5.2 Rules & Rates Model

**FR-4** – Tax Rate Table (`tax_rate`)
Store PH tax rates as versioned records:

* `code` (e.g., VAT_12_SALES, EWT_PROF_W010)
* `description`
* `rate` (e.g., 0.12, 0.10)
* `valid_from`, `valid_to`
* `is_active`

**FR-5** – Tax Rules Table (`tax_rule`)
Store tax computation logic as data, not code:

* `code` (e.g., VAT_OUTPUT_STD_12, EWT_PROF_W010_10)
* `tax_type` (`VAT`, `EWT`, `FWT`, `INCOME`)
* `scope` (`transaction` or `aggregate`)
* `condition_json` (JSONLogic condition, e.g. vendor type, tax code, amount > 0)
* `formula` (expression like `"base * rate"`)
* `base_source` (`gross_amount`, `net_of_vat`, or other numeric field)
* `rate_code` (FK to `tax_rate.code`)
* `output_bucket` (e.g., `VAT_OUTPUT_12`, `EWT_BUCKET_W010`)
* `priority` (integer; lower means evaluated earlier)
* `valid_from`, `valid_to`, `is_active`

**FR-6** – Rule Evaluation Engine
The engine must:

* Evaluate `condition_json` using a safe JSONLogic interpreter.
* For each applicable `tax_rule`:
  * Resolve `rate` from `tax_rate`
  * Resolve `base` from transaction data via `base_source`
  * Compute `tax_amount` via `formula` with only `base` and `rate` as inputs.
* Sum results into **output buckets** per transaction and per return.

---

### 5.3 Mapping to BIR Forms (`tax_mapping`)

**FR-7** – Mapping Table
Store mapping between output buckets and BIR forms:

* `output_bucket` (e.g., `VAT_OUTPUT_12`)
* `bir_form` (e.g., `2550Q`, `1601EQ`)
* `bir_line_code` (internal code like `ITEM_12A` or `SCH1_W010`)
* `bir_line_label` (human-friendly line description)

**FR-8** – BIR Line Aggregator
Given a dictionary `{output_bucket → amount}`, the engine must:

* Produce totals per `(bir_form, bir_line_code)`
* Output structured lines:
  * `bir_form`, `bir_line_code`, `bir_line_label`, `amount`

---

### 5.4 Tax Return Model & Lifecycle

**FR-9** – Tax Return & Lines
Represent each return as:

* `tax_return`:
  * `company_code`
  * `period_start`, `period_end`
  * `tax_type` (VAT/EWT/FWT/INCOME)
  * `status` (`Draft`, `ForReview`, `Approved`, `Filed`)
* `tax_return_line`:
  * `tax_return_id`
  * `output_bucket`
  * `amount`
  * `bir_form`, `bir_line_code`

**FR-10** – Return Lifecycle
Enforce state transitions:

* `Draft → ForReview` (Preparer)
* `ForReview → Approved` (Reviewer)
* `Approved → Filed` (with `filed_date` & optional reference)

All transitions must be logged in `approval_log`:

* `tax_return_id`, `previous_status`, `new_status`, `actor`, `comment`, `timestamp`

Validation errors (see below) must **block** transition from `Draft → ForReview`.

---

### 5.5 Validation Engine & Violations

**FR-11** – Validation Rules Table (`validation_rule`)

* `code` (e.g., `PH_WHT_PARTNER_TIN_REQUIRED`)
* `description`
* `level` (`error` or `warning`)
* `scope` (`transaction` or `aggregate`)
* `condition_json` (JSONLogic condition that **triggers** a violation)
* `message_template` (with templated placeholders like `%{partner_name}`)
* `valid_from`, `valid_to`, `is_active`

**FR-12** – Execution of Validation Rules
The validation engine must:

* Run through all relevant rules for each transaction (scope `transaction`)
* Run aggregate checks (scope `aggregate`) on summarized data
* Record violations as `validation_violation` rows:
  * `tax_return_id`
  * `validation_rule_code`
  * `level`
  * `scope`
  * `context_json` (e.g., `{"txn_id": 12345}`)
  * `message`

**FR-13** – Enforcement of Levels

* **Error**:
  * Blocks status change from `Draft → ForReview`.
* **Warning**:
  * Allows transition, but:
    * Reviewer must explicitly acknowledge warnings (comment required).

Example validation rules:

* Vendor has WHT but `tin` is null → `error`.
* ATC W010 used for a non-professional vendor → `warning`.
* Period-to-period variance > configured threshold → `warning`.

---

### 5.6 Reconciliations

**FR-14** – GL vs Return Reconciliation

* For each tax return, compute:
  * `gl_total`: sum of relevant tax-related GL accounts for the period.
  * `return_total`: sum of all tax return line amounts for that tax type.
* Compare and classify:
  * `pass` if difference ≤ threshold (e.g., 0.01)
  * `fail` otherwise
* Log result in `reconciliation_log` with `recon_type = 'GL_vs_Return'`.

**FR-15** – Subledger vs Return

* Compare tax computed at transaction level (sum of VAT/EWT buckets) vs the aggregated BIR line totals.
* Similar classification as GL vs Return.

**FR-16** – Period vs Period

* Compare current period totals vs prior period:
  * Amounts
  * Percent changes
* Flag large variances as warnings in `reconciliation_log`.

---

### 5.7 AI Agent Integration (Read-Only on Math)

**FR-17** – Exposed Data to AI Agents

Provide API or DB views for AI agents (read-only):

* `tax_return` + `tax_return_line`
* `validation_violation`
* `reconciliation_log`
* `tax_rule`, `tax_rate`, `tax_mapping`, `validation_rule` metadata
* Selected transaction data (anonymized where needed)

**FR-18** – Prohibited Actions

* AI agents must not:
  * Modify `tax_rate`, `tax_rule`, `tax_mapping`, `validation_rule`.
  * Change `tax_return.status`.
* Any suggestions must be surfaced as **"proposed changes"** for human review.

---

## 6. Non-Functional Requirements

**NFR-1 – Accuracy**

* Golden dataset tests must show **exact match** (to centavo) against reference outputs for supported scenarios.
* Parallel-run implementation must show:
  * ≥ 95% of historical lines classified as `MATCH` or `ENGINE_FIX`.
  * 0 unresolved `UNKNOWN` differences in forms targeted for go-live.

**NFR-2 – Determinism**

* Identical inputs and rule versions must always produce identical outputs.
* No randomization in rule evaluation order or computations.

**NFR-3 – Performance**

* For typical TBWA data volume (tens of thousands of transactions):
  * Single tax return computation (including validations + reconciliations) should complete in **≤ 2 minutes**.

**NFR-4 – Security**

* Read-only integration to Spectra DB.
* Role-based access control:
  * Distinct permissions for:
    * Rule administration
    * Return preparation
    * Approval/filing
* Sensitive data (TINs, partner details) protected according to internal policies.

**NFR-5 – Observability**

* Structured logs for:
  * Rule evaluation errors
  * Validation hits
  * Reconciliation failures
  * Parallel-run differences
* Optionally exportable to TBWA logging/monitoring stack.

---

## 7. Testing & Validation Strategy

### 7.1 Unit Tests

* JSONLogic evaluator:
  * Operators: `and`, `or`, `!`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `in`.
  * Edge cases: missing fields, `null`, type mismatches.
* Formula evaluator:
  * Correct handling of `base * rate`, sign logic (CR/DR, credit notes), rounding.
  * Restrict evaluation to safe variables (`base`, `rate`).
* Rule selection:
  * Priority order is respected.
  * Non-matching rules are ignored.
  * Overlapping rules behave as intended (no unintended double-taxing).
* Validation rules:
  * Each rule has at least one positive ("should trigger") and negative ("should not trigger") test.

---

### 7.2 Golden Datasets

Build **fixture-based tests** for each tax type:

* `fixtures/vat_basic_transactions.csv`
* `fixtures/vat_basic_expected_lines.csv`
* `fixtures/ewt_prof_transactions.csv`
* `fixtures/ewt_prof_expected_lines.csv`
* etc.

Tests must:

* Ingest fixture transactions.
* Run full rules engine pipeline (rules + mapping).
* Compare outputs with expected BIR line totals and reconciliation results.

Any discrepancy → test failure.

---

### 7.3 Regression & Snapshot Testing

* For each fixture scenario, store a **snapshot** of:
  * Tax rules configuration.
  * Generated return lines.
  * Reconciliation and validation summaries.
* When rules change, require:
  * Explicit snapshot update.
  * Reviewer approval acknowledging changes in behavior.

---

### 7.4 Parallel-Run Testing (Historical Months)

* Select at least **6 months** of historical data (already filed).
* For each month:
  * Ingest Spectra data as of that period.
  * Run TaxPulse Engine.
  * Compare engine outputs vs legacy Excel/BIR numbers.

Classify each difference as:

* `MATCH` – same result as legacy.
* `ENGINE_FIX` – engine identifies and corrects a historical manual error.
* `LEGACY_INTENTIONAL` – existing policy choice requires engine configuration update.
* `UNKNOWN` – unexplained difference requiring investigation.

Go-live gate:

* ≥ 95% lines are `MATCH` or `ENGINE_FIX`.
* All `UNKNOWN` entries resolved or accepted with documented rationale.

---

### 7.5 AI Behaviour Testing (Manual & Prompt-Level)

* Confirm AI cannot mutate:
  * Rule tables
  * Return statuses
* Confirm AI can:
  * Explain a specific BIR line using underlying transactions/rules.
  * Generate plain-language reconciliation summaries.

---

## 8. Rollout Plan

**Phase 0 – Prototype VAT-only**

* Implement minimal rules engine for:
  * VAT 12% output
  * VAT zero-rated
  * VAT exempt
* Create synthetic fixtures and run golden tests.

**Phase 1 – Extend to EWT/FWT**

* Implement EWT rules per ATC (professional fees, rentals, services).
* Implement FWT basics (if needed).
* Add validation rules (TIN presence, ATC/vendor-type consistency).

**Phase 2 – Historical Parallel Run**

* Run engine for chosen historical months.
* Classify and resolve differences.
* Refine rules and mappings.

**Phase 3 – Shadow Mode (Read-Only)**

* For current periods, run engine in parallel:
  * Finance still files using current process.
  * Compare outputs and refine.

**Phase 4 – Primary Computation Source**

* Officially adopt TaxPulse Engine as:
  * Primary source of tax computation.
  * Primary workpaper generator.
* Legacy Excel kept as fallback only.

**Phase 5 – Enhancements**

* Additional edge-case rules.
* Deeper reporting (drilldowns, dashboards).
* Optionally explore integration with eBIRForms/eFPS or eTSP route.

---

## 9. Risks & Mitigations

* **Risk:** Misconfigured rules cause wrong tax computation.
  **Mitigation:**
  * Golden datasets
  * Parallel-runs
  * Maker–checker
  * Audits by external advisors

* **Risk:** Finance team bypasses system and returns to Excel.
  **Mitigation:**
  * Ensure the engine is easier and faster than existing workflow.
  * Demonstrate stronger control & audit benefits.

* **Risk:** AI "hallucinated" tax recommendations confuse users.
  **Mitigation:**
  * RAG-based AI answers with clear citations.
  * Strict read-only access for AI into rules.
  * Human approval for any policy or rule changes.

---

This PRD is ready to go straight into your repo under `specs/001-taxpulse-engine.prd.md` and used as the reference for implementation, tests, and CI gates.
