# TICKET-004: BIR TIN Registry Lookup

> **Priority**: P2
> **Type**: Enhancement
> **Component**: Validation / External Integration
> **Status**: Open
> **Created**: 2025-12-05

---

## Problem Statement

Current TIN validation (`V_TXN_001`) only checks **format correctness** (regex: `^\d{3}-\d{3}-\d{3}(-\d{3})?$`). This catches typos but not:

1. **Fake TINs**: Format-valid but never issued by BIR
2. **Inactive TINs**: TINs that have been cancelled or suspended
3. **TIN-Name mismatches**: TIN belongs to a different entity than stated
4. **Incorrect branch codes**: Valid base TIN with wrong 3-digit branch suffix

**Business Impact**:
- Withholding tax remittances credited to wrong taxpayer
- Disallowed deductions on audit due to invalid supplier TINs
- Potential penalties under RR 11-2018 (TIN validation requirements)

---

## Scope & Constraints

### In Scope

- **TIN existence verification**: Check if TIN exists in BIR registry
- **TIN-Name matching**: Verify registered name matches transaction partner name
- **TIN status check**: Confirm TIN is active (not cancelled/suspended)
- **Caching layer**: Cache verified TINs to reduce external calls
- **Manual verification workflow**: Flag for human review when automated check fails

### Out of Scope (This Ticket)

- BIR TIN registration (users must register TINs via BIR portal)
- Automatic TIN correction
- Integration with BIR eFPS (separate system)

### Constraints

- **BIR API availability**: BIR does not provide a public TIN validation API; alternative approaches needed
- **Rate limiting**: Any external lookup must be throttled to avoid abuse
- **Privacy**: TIN data is sensitive; logging must comply with PDPA
- **Fallback**: System must function when external validation unavailable

---

## Acceptance Criteria

### Functional

- [ ] New validation rule `V_TXN_010` performs TIN registry lookup
- [ ] Lookup returns: `VALID`, `INVALID`, `NOT_FOUND`, `NAME_MISMATCH`, `INACTIVE`, `UNAVAILABLE`
- [ ] Valid TINs cached for 30 days (configurable)
- [ ] Failed lookups trigger manual verification workflow
- [ ] Dashboard shows TIN verification status distribution

### Non-Functional

- [ ] Lookup latency: <500ms p95 (excluding cache miss to external)
- [ ] Cache hit rate: >90% after warm-up period
- [ ] Graceful degradation: If external service unavailable, fall back to format-only validation with `UNAVAILABLE` status
- [ ] Audit logging of all TIN verifications (anonymized for bulk reports)

### Testing

- [ ] Test case: Valid TIN, correct name → `VALID`
- [ ] Test case: Valid TIN, name mismatch → `NAME_MISMATCH`
- [ ] Test case: Format-valid but non-existent TIN → `NOT_FOUND`
- [ ] Test case: Cancelled TIN → `INACTIVE`
- [ ] Test case: External service timeout → `UNAVAILABLE` with fallback

---

## Technical Approach

### Lookup Strategy Options

Since BIR does not provide a public TIN validation API, consider these approaches:

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **SEC/DTI Integration** | Official source for business names | Only covers registered businesses, not individuals | Partial solution |
| **Accumulated Partner Registry** | Fast, no external dependency | Only validates TINs seen before | Use for caching |
| **Third-Party Service** | Real-time validation | Cost, reliability, compliance | Evaluate vendors |
| **BIR Portal Scraping** | Direct source | ToS violation, fragile, rate limited | **Not recommended** |
| **Manual Verification Queue** | Human accuracy | Slow, doesn't scale | Fallback only |

**Recommended Approach**: Hybrid model
1. Check local cache/registry first
2. For new TINs, queue for manual verification
3. Optionally integrate third-party service for automated verification
4. Build internal registry over time from verified TINs

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   TIN VERIFICATION ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────────┘

[Transaction with TIN]
        │
        ▼
┌───────────────────────┐
│  V_TXN_001: Format    │ ← Regex check (existing)
│  Validation           │
└───────────┬───────────┘
            │ Format OK
            ▼
┌───────────────────────┐
│  V_TXN_010: Registry  │
│  Lookup               │
└───────────┬───────────┘
            │
    ┌───────┴───────┐
    ▼               ▼
┌─────────┐   ┌─────────────┐
│ Cache   │   │ Cache Miss  │
│ Hit     │   │             │
└────┬────┘   └──────┬──────┘
     │               │
     │               ▼
     │        ┌─────────────┐     ┌─────────────┐
     │        │ External    │────▶│ Third-Party │
     │        │ Lookup      │     │ API (opt)   │
     │        └──────┬──────┘     └─────────────┘
     │               │
     │        ┌──────┴──────┐
     │        ▼             ▼
     │  ┌──────────┐  ┌──────────────┐
     │  │ Verified │  │ Manual Queue │
     │  │ (cache)  │  │ (review)     │
     │  └──────────┘  └──────────────┘
     │        │
     └────────┴───────────┐
                          ▼
              ┌─────────────────────┐
              │ Verification Result │
              │ VALID | INVALID |   │
              │ NOT_FOUND | etc.    │
              └─────────────────────┘
```

### Data Model

```sql
-- TIN Registry (accumulated verified TINs)
CREATE TABLE tin_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tin VARCHAR(15) NOT NULL UNIQUE,
    registered_name VARCHAR(255) NOT NULL,
    registered_name_normalized VARCHAR(255) NOT NULL,  -- For fuzzy matching
    entity_type VARCHAR(20),  -- 'individual', 'corporation', 'partnership'
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active', 'inactive', 'suspended'
    verification_source VARCHAR(50),  -- 'manual', 'sec', 'third_party'
    verified_at TIMESTAMP NOT NULL,
    verified_by UUID REFERENCES users(id),
    expires_at TIMESTAMP,  -- For re-verification
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tin_registry_tin ON tin_registry(tin);
CREATE INDEX idx_tin_registry_name ON tin_registry USING gin(registered_name_normalized gin_trgm_ops);

-- Verification Queue (pending manual review)
CREATE TABLE tin_verification_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tin VARCHAR(15) NOT NULL,
    submitted_name VARCHAR(255) NOT NULL,
    source_transaction_id VARCHAR(50),
    source_agency_code VARCHAR(10),
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'verified', 'rejected'
    priority INTEGER DEFAULT 0,
    assigned_to UUID REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolved_by UUID REFERENCES users(id)
);

-- Verification Audit Log
CREATE TABLE tin_verification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tin_hash VARCHAR(64) NOT NULL,  -- SHA-256 of TIN for privacy
    verification_result VARCHAR(20) NOT NULL,
    verification_source VARCHAR(50) NOT NULL,
    latency_ms INTEGER,
    cache_hit BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Name Matching Algorithm

```python
from rapidfuzz import fuzz

def verify_tin_name_match(
    submitted_name: str,
    registered_name: str,
    threshold: float = 0.85
) -> tuple[bool, float]:
    """
    Fuzzy match submitted partner name against registered name.

    Returns:
        (is_match, similarity_score)
    """
    # Normalize both names
    submitted_norm = normalize_business_name(submitted_name)
    registered_norm = normalize_business_name(registered_name)

    # Calculate similarity using token set ratio (handles word order differences)
    score = fuzz.token_set_ratio(submitted_norm, registered_norm) / 100.0

    return (score >= threshold, score)


def normalize_business_name(name: str) -> str:
    """
    Normalize business name for comparison:
    - Uppercase
    - Remove punctuation
    - Expand common abbreviations (Inc. → Incorporated, Corp. → Corporation)
    - Remove common suffixes for comparison
    """
    name = name.upper().strip()

    # Expand abbreviations
    expansions = {
        r'\bINC\.?\b': 'INCORPORATED',
        r'\bCORP\.?\b': 'CORPORATION',
        r'\bLTD\.?\b': 'LIMITED',
        r'\bLLC\.?\b': 'LIMITED LIABILITY COMPANY',
        r'\bCO\.?\b': 'COMPANY',
    }
    for pattern, expansion in expansions.items():
        name = re.sub(pattern, expansion, name)

    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)

    # Collapse whitespace
    name = ' '.join(name.split())

    return name
```

---

## Interface Sketch

### Python SDK

```python
from taxpulse.validation.tin import TINVerifier

verifier = TINVerifier(
    cache_ttl_days=30,
    external_provider="taxpulse_registry",  # or "third_party_xyz"
    fallback_to_format_only=True
)

# Verify single TIN
result = verifier.verify(
    tin="123-456-789-000",
    submitted_name="ABC Corporation Inc."
)

# Result structure
# {
#     "tin": "123-456-789-000",
#     "status": "NAME_MISMATCH",
#     "registered_name": "ABC CORPORATION",
#     "submitted_name": "ABC Corporation Inc.",
#     "name_similarity": 0.78,
#     "verification_source": "cache",
#     "cache_hit": True,
#     "latency_ms": 12,
#     "message": "Name similarity (78%) below threshold (85%)"
# }

# Bulk verification
results = verifier.verify_batch([
    {"tin": "111-222-333", "name": "Company A"},
    {"tin": "444-555-666", "name": "Company B"},
])
```

### REST API

```
POST /api/v1/validate/tin
Content-Type: application/json
Authorization: Bearer <token>

{
  "tin": "123-456-789-000",
  "submitted_name": "ABC Corporation Inc.",
  "options": {
    "name_match_threshold": 0.85,
    "allow_cache": true
  }
}

Response:
{
  "tin": "123-456-789-000",
  "status": "VALID",
  "registered_name": "ABC CORPORATION INC",
  "name_match": true,
  "name_similarity": 0.95,
  "verification_source": "cache",
  "verified_at": "2025-01-10T08:30:00Z"
}
```

### Validation Rule Integration

```yaml
# In core_validations.yaml
- rule_id: V_TXN_010
  name: TIN Registry Verification
  description: Verify TIN exists in registry and name matches
  severity: warning  # Not blocking; flags for review
  condition:
    # Always run after V_TXN_001 passes
    "==": [{"var": "v_txn_001_passed"}, true]
  action: tin_registry_lookup
  on_failure:
    - queue_for_manual_verification
    - flag_transaction
```

---

## Dependencies

- [ ] TIN Registry table created and seeded with known-good TINs
- [ ] Manual verification workflow (UI for reviewers)
- [ ] Third-party provider evaluation (if pursuing automated external lookup)
- [ ] rapidfuzz library for name matching

---

## Open Questions

1. What's the acceptable false positive rate for name mismatches?
2. Should we block transactions with unverified TINs, or just flag them?
3. How do we handle TINs that are valid but for a different entity type than expected?
4. Is there budget for a third-party TIN verification service?

---

## References

- BIR RR 11-2018: TIN validation requirements for withholding agents
- PDPA guidelines on handling TIN data
- SEC company name search: https://www.sec.gov.ph/
