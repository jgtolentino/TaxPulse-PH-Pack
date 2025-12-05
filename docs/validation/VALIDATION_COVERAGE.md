# TaxPulse-PH-Pack Validation Coverage

> Last updated: 2025-12-05

This document describes the validation rules implemented in TaxPulse-PH-Pack, their integration with the tax computation architecture, and identified gaps for future implementation.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Transaction-Level Validations](#transaction-level-validations)
3. [Aggregate-Level Validations](#aggregate-level-validations)
4. [Validation Workflow](#validation-workflow)
5. [Implementation Gaps](#implementation-gaps)
6. [References](#references)

---

## Architecture Overview

Validations in TaxPulse-PH-Pack operate as a **two-tier quality gate** within the tax computation pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────┘

[Source Transactions]
        │
        ▼
┌───────────────────────┐
│  TIER 1: Transaction  │ ← V_TXN_001 through V_TXN_009
│  Level Validation     │   Runs per-transaction before computation
│  (9 rules)            │   Blocking errors stop processing
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Rules Engine         │ ← JSONLogic evaluation
│  Tax Computation      │   Bucket accumulation
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  TIER 2: Aggregate    │ ← V_AGG_001 through V_AGG_009
│  Level Validation     │   Runs after computation, before form generation
│  (9 rules)            │   Warnings flag for review, errors block posting
└───────────┬───────────┘
            │
            ▼
[BIR Form Generation]
```

### Key Principles

1. **Fail Fast**: Transaction-level errors block computation immediately
2. **Audit Trail**: All validation results logged with timestamp and rule ID
3. **Severity Tiers**: `error` (blocking) > `warning` (review required) > `info` (advisory)
4. **Deterministic**: Same inputs always produce same validation results

### Configuration Location

All validation rules are defined in:
```
packs/ph/validations/core_validations.yaml
```

---

## Transaction-Level Validations

These validations run **per-transaction** before tax computation begins. Blocking errors (`severity: error`) prevent the transaction from entering the rules engine.

| Rule ID | Name | Description | Severity | JSONLogic Condition |
|---------|------|-------------|----------|---------------------|
| **V_TXN_001** | TIN Format | Validates Philippine TIN format: `NNN-NNN-NNN` (9-digit) or `NNN-NNN-NNN-NNN` (12-digit with branch) | `error` | Regex: `^\d{3}-\d{3}-\d{3}(-\d{3})?$` |
| **V_TXN_002** | Positive Amount | Gross amount must be greater than zero | `error` | `{">" : [{"var": "gross_amount"}, 0]}` |
| **V_TXN_003** | ATC Required for EWT | Transactions with EWT tax codes must have an ATC code | `error` | `{"if": [{"in": [{"var": "tax_code"}, ["EWT", "EWT_PROF", ...]]}, {"!=": [{"var": "atc_code"}, null]}, true]}` |
| **V_TXN_004** | Fiscal Year Bounds | Transaction date must fall within the declared fiscal year | `error` | Date range check against `fiscal_year_start` and `fiscal_year_end` |
| **V_TXN_005** | Currency PHP | Currency should be PHP; foreign currency flagged for review | `warning` | `{"==": [{"var": "currency"}, "PHP"]}` |
| **V_TXN_006** | Valid Document Type | Document type must be one of: `invoice`, `bill`, `credit_note`, `debit_note`, `payment` | `error` | Enum membership check |
| **V_TXN_007** | Partner Name | Partner/vendor name should not be empty | `warning` | `{"!=": [{"var": "partner_name"}, ""]}` |
| **V_TXN_008** | Description Present | Transaction description recommended for audit trail | `info` | `{"!=": [{"var": "description"}, ""]}` |
| **V_TXN_009** | Duplicate Check | Flags potential duplicate based on (partner, amount, date, doc_type) | `warning` | Hash-based duplicate detection |

### Error Handling

```python
# Example validation result structure
{
    "transaction_id": "TXN001",
    "validation_results": [
        {"rule_id": "V_TXN_001", "passed": True},
        {"rule_id": "V_TXN_002", "passed": False, "severity": "error",
         "message": "Gross amount must be positive, got: -5000.00"}
    ],
    "can_proceed": False,  # Blocked due to V_TXN_002 error
    "blocking_errors": ["V_TXN_002"],
    "warnings": []
}
```

---

## Aggregate-Level Validations

These validations run **after tax computation** on the accumulated bucket values and computed form lines. They catch logical inconsistencies and anomalies before form generation.

| Rule ID | Name | Description | Severity | Threshold/Logic |
|---------|------|-------------|----------|-----------------|
| **V_AGG_001** | VAT Payable Reasonableness | VAT payable should fall within expected bounds | `warning` | `-500,000 ≤ VAT_PAYABLE ≤ 5,000,000` |
| **V_AGG_002** | Input/Output VAT Ratio | Input VAT should not exceed Output VAT by unreasonable margin (except CAPEX periods) | `warning` | `INPUT_VAT / OUTPUT_VAT ≤ 1.5` or flagged for review |
| **V_AGG_003** | No Negative Buckets | Accumulated bucket values should not be negative | `error` | `all(bucket >= 0 for bucket in buckets)` |
| **V_AGG_004** | Zero-Rated Documentation | Zero-rated sales require supporting export documentation reference | `warning` | If `VAT_OUTPUT_ZERO > 0`, check `export_docs_ref` populated |
| **V_AGG_005** | EWT Concentration | Warns if single ATC code exceeds 30% of total EWT | `info` | `max(atc_bucket) / EWT_TOTAL ≤ 0.30` |
| **V_AGG_006** | Period Variance | Flags if current period varies >50% from prior period | `warning` | `abs(current - prior) / prior ≤ 0.50` |
| **V_AGG_007** | Form Line Reconciliation | Computed form line totals must reconcile to source buckets | `error` | `sum(mapped_lines) == bucket_total` |
| **V_AGG_008** | Required Lines Populated | All mandatory BIR form lines must have values (can be zero) | `error` | Check against form schema required fields |
| **V_AGG_009** | Override Variance | Flags manual overrides that differ significantly from computed values | `warning` | `abs(override - computed) / computed ≤ 0.10` |

### Aggregate Validation Output

```python
# Example aggregate validation result
{
    "period": "2025-Q1",
    "agency_id": "TBWA",
    "form_type": "2550Q",
    "validation_results": [
        {"rule_id": "V_AGG_001", "passed": True,
         "details": {"vat_payable": 125000.00, "within_bounds": True}},
        {"rule_id": "V_AGG_005", "passed": False, "severity": "info",
         "message": "W010 (Professional Fees) represents 45% of total EWT",
         "details": {"atc": "W010", "concentration": 0.45}}
    ],
    "can_post": True,  # No blocking errors
    "requires_review": True,  # Has warnings
    "review_items": ["V_AGG_005"]
}
```

---

## Validation Workflow

### Integration with Form Lifecycle

```
┌──────────────────────────────────────────────────────────────────────┐
│                      FORM LIFECYCLE + VALIDATION                     │
└──────────────────────────────────────────────────────────────────────┘

[DRAFT]                    [PENDING REVIEW]              [CONFIRMED]
   │                              │                           │
   │  Create form                 │  Tier 1 + Tier 2         │  Manager
   │  from transactions           │  validations pass         │  approval
   │                              │                           │
   ▼                              ▼                           ▼
┌─────────┐    Validate    ┌─────────────┐   Review    ┌──────────┐
│  Draft  │───────────────▶│  Validated  │────────────▶│ Confirmed│
└─────────┘                └─────────────┘             └──────────┘
     │                           │                          │
     │ Errors                    │ Warnings                 │
     ▼                           ▼                          ▼
┌─────────┐               ┌─────────────┐             ┌──────────┐
│ Blocked │               │ Review Queue│             │  Posted  │──▶ Supabase
└─────────┘               └─────────────┘             └──────────┘
```

### Maker-Checker Enforcement

| Role | Can Create Draft | Can Confirm | Can Post | Can Override Warning |
|------|------------------|-------------|----------|----------------------|
| Tax Preparer | ✅ | ❌ | ❌ | ❌ |
| Tax Manager | ✅ | ✅ | ✅ | ✅ (with justification) |
| System Admin | ❌ | ❌ | ❌ | ❌ |

---

## Implementation Gaps

The following validation capabilities are **not yet implemented** and are tracked as enhancement tickets:

| Gap | Priority | Ticket | Description |
|-----|----------|--------|-------------|
| **AI-Powered Anomaly Detection** | P1 | [TICKET-001](../tickets/TICKET-001-ai-anomaly-detection.md) | Machine learning models to detect unusual patterns beyond rule-based thresholds |
| **Real-Time Validation API** | P1 | [TICKET-002](../tickets/TICKET-002-realtime-validation-api.md) | REST endpoint for on-demand validation without full form creation |
| **Cross-Tenant Validation (SSC)** | P2 | [TICKET-003](../tickets/TICKET-003-cross-tenant-validation.md) | Validate intercompany transactions across multiple agencies |
| **BIR TIN Registry Lookup** | P2 | [TICKET-004](../tickets/TICKET-004-bir-tin-registry.md) | Verify TIN against BIR's actual registry (not just format) |
| **ATC Code Suggestion/Validation** | P2 | [TICKET-005](../tickets/TICKET-005-atc-suggestion.md) | AI-assisted ATC code recommendation based on transaction description |
| **CFO Risk Posture Deck** | P3 | [TICKET-006](../tickets/TICKET-006-cfo-validation-deck.md) | Executive presentation on validation coverage and risk posture |

### Gap Impact Assessment

| Gap | Risk if Unaddressed | Workaround |
|-----|---------------------|------------|
| AI Anomaly Detection | Novel fraud/error patterns missed | Manual review of V_AGG_005/006 warnings |
| Real-Time API | No pre-submission validation; errors caught late | Run full computation for validation |
| Cross-Tenant | Intercompany discrepancies undetected | Manual reconciliation spreadsheets |
| BIR TIN Registry | Invalid TINs accepted (format-valid but unregistered) | Manual BIR portal lookup |
| ATC Suggestion | Mis-coded transactions at source | Tax team training on ATC selection |

---

## References

- **Validation Rules File**: `packs/ph/validations/core_validations.yaml`
- **Rules Engine**: `engine/rules_engine/evaluator.py`
- **Form Models**: `models/bir_*.py`
- **PRD**: `specs/001-taxpulse-engine.prd.md`
- **Test Fixtures**: `packs/ph/tests/fixtures/`

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2025-12-05 | Claude | Initial documentation |
