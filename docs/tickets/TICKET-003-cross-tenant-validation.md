# TICKET-003: Cross-Tenant Validation for SSCs

> **Priority**: P2
> **Type**: Enhancement
> **Component**: Validation / Multi-Tenant
> **Status**: Open
> **Created**: 2025-12-05

---

## Problem Statement

Shared Service Centers (SSCs) manage tax compliance for **multiple agencies/entities** within a single TaxPulse deployment. Current validation operates in **isolation per agency**, missing:

1. **Intercompany transaction mismatches**: Agency A records a sale to Agency B, but Agency B's purchase doesn't match (amount, date, or tax treatment)
2. **Duplicate cross-agency transactions**: Same invoice recorded by multiple agencies
3. **Transfer pricing anomalies**: Related-party transactions with unusual margins
4. **Consolidated limit breaches**: Individual agencies pass validation, but consolidated position triggers regulatory thresholds

**Business Impact**: SSCs discover intercompany discrepancies during consolidation or external audit, causing delays and restatements.

---

## Scope & Constraints

### In Scope

- **Intercompany matching**: Detect mismatches between related agencies
- **Cross-agency duplicate detection**: Flag same transaction appearing in multiple agencies
- **Consolidated threshold validation**: Validate aggregate position across all managed agencies
- **Related-party flagging**: Identify and flag transactions between entities under common control

### Out of Scope (This Ticket)

- Automated intercompany elimination entries
- Transfer pricing compliance (complex regulatory area)
- Cross-tenant validation across different SSC customers (different tenants)

### Constraints

- **Performance**: Cross-tenant queries must complete in <10 seconds for SSC with 10 agencies
- **Data Isolation**: Only validate across agencies within same SSC/tenant; never cross tenant boundaries
- **Privacy**: Detailed transaction data stays within agency; only matching keys shared for comparison

---

## Acceptance Criteria

### Functional

- [ ] System identifies intercompany transaction pairs based on matching keys (partner TIN + amount + date ± tolerance)
- [ ] Mismatched pairs flagged with discrepancy details (amount diff, date diff, tax code diff)
- [ ] Duplicate detection across agencies using transaction hash
- [ ] Consolidated VAT position calculated and validated against thresholds
- [ ] Cross-agency validation report generated per period

### Non-Functional

- [ ] Query performance: <10 seconds for 10 agencies, 50K transactions total
- [ ] No data leakage: Agency A cannot see Agency B's transaction details (only match/mismatch status)
- [ ] Audit trail: All cross-agency validations logged

### Testing

- [ ] Test case: Matched intercompany pair (Agency A sale = Agency B purchase)
- [ ] Test case: Mismatched amounts (Agency A: ₱100K, Agency B: ₱95K)
- [ ] Test case: Missing counterparty (Agency A records sale, Agency B has no matching purchase)
- [ ] Test case: Duplicate transaction across 3 agencies

---

## Technical Approach

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│               CROSS-TENANT VALIDATION ARCHITECTURE              │
└─────────────────────────────────────────────────────────────────┘

[Agency A Transactions]  [Agency B Transactions]  [Agency C Transactions]
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Transaction Key       │
                    │  Extraction            │
                    │  (TIN, Amount, Date)   │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  Cross-Agency Matcher  │
                    │  - Fuzzy date match    │
                    │  - Amount tolerance    │
                    │  - TIN normalization   │
                    └───────────┬────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        ┌──────────┐     ┌──────────────┐  ┌──────────────┐
        │ Matched  │     │ Mismatched   │  │ Orphaned     │
        │ Pairs    │     │ Pairs        │  │ (No Counter) │
        └──────────┘     └──────────────┘  └──────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  V_CROSS_* Validation  │
                    │  Rules                 │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  Cross-Agency Report   │
                    └────────────────────────┘
```

### Matching Algorithm

```python
# Intercompany matching keys
def generate_matching_key(txn: Transaction) -> str:
    """
    Generate a normalized key for intercompany matching.
    Key: normalized_counterparty_tin | normalized_amount | date_bucket
    """
    # Normalize TIN (remove dashes, standardize format)
    tin = normalize_tin(txn.partner_tin)

    # Round amount to nearest 100 for fuzzy matching
    amount_bucket = round(txn.gross_amount, -2)

    # Date bucket: allow ±3 day tolerance
    date_bucket = txn.doc_date.strftime("%Y-%m")  # Month-level bucket

    return f"{tin}|{amount_bucket}|{date_bucket}"


# Cross-agency query (pseudo-SQL)
"""
WITH agency_keys AS (
    SELECT
        agency_code,
        transaction_id,
        generate_matching_key(partner_tin, gross_amount, doc_date) as match_key,
        doc_type,
        gross_amount,
        doc_date
    FROM transactions
    WHERE tenant_id = :tenant_id
      AND period = :period
      AND partner_tin IN (SELECT tin FROM tenant_related_parties)
)
SELECT
    a.agency_code as agency_a,
    a.transaction_id as txn_a,
    b.agency_code as agency_b,
    b.transaction_id as txn_b,
    ABS(a.gross_amount - b.gross_amount) as amount_diff,
    ABS(a.doc_date - b.doc_date) as date_diff_days
FROM agency_keys a
JOIN agency_keys b ON a.match_key = b.match_key
WHERE a.agency_code < b.agency_code  -- Avoid duplicate pairs
  AND a.doc_type = 'invoice' AND b.doc_type = 'bill'  -- Sale vs Purchase
"""
```

### New Validation Rules

| Rule ID | Name | Description | Severity |
|---------|------|-------------|----------|
| **V_CROSS_001** | Intercompany Amount Match | Related party sale/purchase amounts must match within ₱100 tolerance | `warning` |
| **V_CROSS_002** | Intercompany Date Match | Related party transactions must be within 5 business days | `warning` |
| **V_CROSS_003** | Intercompany Tax Treatment | Both sides must use consistent VAT treatment | `error` |
| **V_CROSS_004** | Orphan Intercompany | Sale to related party with no matching purchase | `warning` |
| **V_CROSS_005** | Cross-Agency Duplicate | Same transaction hash appears in multiple agencies | `error` |
| **V_CROSS_006** | Consolidated VAT Threshold | Combined VAT payable exceeds ₱10M (requires manager sign-off) | `warning` |

---

## Interface Sketch

### Python SDK

```python
from taxpulse.validation.cross_tenant import CrossAgencyValidator

validator = CrossAgencyValidator(tenant_id="ssc_acme")

# Run cross-agency validation for a period
results = validator.validate_period(
    period="2025-Q1",
    agencies=["AGENCY_A", "AGENCY_B", "AGENCY_C"],
    related_party_tins=["111-222-333", "444-555-666"]
)

# Result structure
# {
#     "matched_pairs": [
#         {
#             "agency_a": "AGENCY_A", "txn_a": "INV-001", "amount_a": 100000,
#             "agency_b": "AGENCY_B", "txn_b": "BILL-042", "amount_b": 100000,
#             "status": "matched",
#             "validations": [{"rule_id": "V_CROSS_001", "passed": True}, ...]
#         }
#     ],
#     "mismatched_pairs": [
#         {
#             "agency_a": "AGENCY_A", "txn_a": "INV-002", "amount_a": 250000,
#             "agency_b": "AGENCY_C", "txn_b": "BILL-088", "amount_b": 245000,
#             "status": "mismatched",
#             "discrepancies": [
#                 {"field": "amount", "diff": 5000, "rule_id": "V_CROSS_001"}
#             ]
#         }
#     ],
#     "orphaned_transactions": [
#         {"agency": "AGENCY_A", "txn": "INV-003", "counterparty_tin": "444-555-666",
#          "status": "orphan", "rule_id": "V_CROSS_004"}
#     ],
#     "consolidated_metrics": {
#         "total_vat_payable": 1250000,
#         "threshold_exceeded": False
#     }
# }
```

### REST API

```
POST /api/v1/validate/cross-agency
Content-Type: application/json
Authorization: Bearer <token>

{
  "period": "2025-Q1",
  "agencies": ["AGENCY_A", "AGENCY_B", "AGENCY_C"],
  "options": {
    "include_matched": false,
    "amount_tolerance": 100,
    "date_tolerance_days": 5
  }
}

Response:
{
  "summary": {
    "total_intercompany_transactions": 45,
    "matched": 38,
    "mismatched": 5,
    "orphaned": 2
  },
  "mismatched_pairs": [...],
  "orphaned_transactions": [...],
  "validation_passed": false,
  "blocking_errors": ["V_CROSS_003", "V_CROSS_005"]
}
```

---

## Data Model

### Related Parties Table

```sql
CREATE TABLE tenant_related_parties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    entity_tin VARCHAR(15) NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(50),  -- 'subsidiary', 'parent', 'affiliate'
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, entity_tin, effective_from)
);
```

---

## Dependencies

- [ ] Multi-tenant architecture (schema-per-tenant) in place
- [ ] Related party registry maintained per tenant
- [ ] Cross-agency query permissions (SSC admin role)

---

## Open Questions

1. How should we handle partial matches (2 of 3 fields match)?
2. Should orphan detection run in real-time or only at period close?
3. What's the notification workflow for mismatches—email, dashboard alert, or both?

---

## References

- BIR RMC on related party transactions
- Transfer pricing documentation requirements (for context, not implementation)
