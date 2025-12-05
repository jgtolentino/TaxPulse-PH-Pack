# TICKET-002: Real-Time Validation API

> **Priority**: P1
> **Type**: Enhancement
> **Component**: API Layer / Validation
> **Status**: Open
> **Created**: 2025-12-05

---

## Problem Statement

Currently, validation only runs as part of the **full tax computation pipeline**. Users cannot:

1. **Pre-validate transactions** before importing them into TaxPulse
2. **Validate incrementally** as transactions are entered in source systems (Odoo, SAP, etc.)
3. **Expose validation** to external systems via API for integration scenarios

**Business Impact**:
- Errors are discovered late in the month-end process
- Source system integrations cannot fail-fast on invalid data
- No self-service validation for finance teams testing data before submission

---

## Scope & Constraints

### In Scope

- **Synchronous REST API** for real-time transaction validation
- **Batch validation endpoint** for validating multiple transactions in one call
- **Dry-run mode**: Validate without persisting or computing tax
- **Tier 1 (transaction-level) validations only** for real-time endpoint
- **OpenAPI specification** for integration documentation

### Out of Scope (This Ticket)

- Aggregate-level validations (require full computation context)
- Anomaly detection (see TICKET-001)
- Webhook/async notification of validation results
- GraphQL API (future enhancement)

### Constraints

- **Latency**: Single transaction validation <50ms p99
- **Throughput**: Support 100 concurrent validation requests
- **Idempotent**: Same input always returns same validation result
- **Stateless**: No server-side session; all context in request

---

## Acceptance Criteria

### Functional

- [ ] `POST /api/v1/validate/transaction` validates single transaction
- [ ] `POST /api/v1/validate/batch` validates up to 1,000 transactions
- [ ] Response includes pass/fail status per validation rule
- [ ] Response includes human-readable error messages
- [ ] API versioned (v1) with deprecation policy documented
- [ ] Authentication via API key or OAuth2 bearer token

### Non-Functional

- [ ] Single transaction: <50ms p99 latency
- [ ] Batch (1,000 txns): <2 seconds p99 latency
- [ ] 99.9% availability SLA
- [ ] Rate limiting: 1,000 requests/minute per API key

### Testing

- [ ] Unit tests for all validation rules via API
- [ ] Integration tests with mock transactions
- [ ] Load test: 100 concurrent users, 10 requests/second each
- [ ] Contract tests for API consumers

---

## Technical Approach

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   VALIDATION API ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────────┘

[External Client]
        │
        │ HTTPS
        ▼
┌───────────────────────┐
│  API Gateway          │ ← Rate limiting, auth, routing
│  (Kong / AWS API GW)  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  FastAPI Service      │ ← Validation endpoints
│  /api/v1/validate/*   │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Validation Engine    │ ← Reuses core_validations.yaml
│  (Stateless)          │   No DB access required
└───────────────────────┘
```

### Request/Response Schema

#### Single Transaction Validation

**Request:**
```json
POST /api/v1/validate/transaction
Content-Type: application/json
Authorization: Bearer <token>

{
  "transaction": {
    "transaction_id": "TXN001",
    "agency_code": "TBWA",
    "doc_type": "invoice",
    "doc_date": "2025-03-15",
    "partner_name": "Client Corp",
    "partner_tin": "123-456-789-000",
    "vendor_type": "DOMESTIC",
    "tax_code": "VAT",
    "atc_code": null,
    "gross_amount": 112000.00,
    "currency": "PHP",
    "description": "Consulting services"
  },
  "fiscal_year": 2025,
  "options": {
    "include_info_level": false,
    "strict_mode": false
  }
}
```

**Response (Success):**
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "valid": true,
  "transaction_id": "TXN001",
  "validation_results": [
    {"rule_id": "V_TXN_001", "passed": true, "severity": "error"},
    {"rule_id": "V_TXN_002", "passed": true, "severity": "error"},
    {"rule_id": "V_TXN_003", "passed": true, "severity": "error"},
    {"rule_id": "V_TXN_004", "passed": true, "severity": "error"},
    {"rule_id": "V_TXN_005", "passed": true, "severity": "warning"},
    {"rule_id": "V_TXN_006", "passed": true, "severity": "error"},
    {"rule_id": "V_TXN_007", "passed": true, "severity": "warning"}
  ],
  "errors": [],
  "warnings": [],
  "processing_time_ms": 12
}
```

**Response (Validation Failure):**
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "valid": false,
  "transaction_id": "TXN002",
  "validation_results": [
    {"rule_id": "V_TXN_001", "passed": false, "severity": "error",
     "message": "Invalid TIN format. Expected NNN-NNN-NNN or NNN-NNN-NNN-NNN, got: 12345"},
    {"rule_id": "V_TXN_002", "passed": false, "severity": "error",
     "message": "Gross amount must be positive, got: -5000.00"}
  ],
  "errors": [
    {"rule_id": "V_TXN_001", "message": "Invalid TIN format..."},
    {"rule_id": "V_TXN_002", "message": "Gross amount must be positive..."}
  ],
  "warnings": [],
  "processing_time_ms": 8
}
```

#### Batch Validation

**Request:**
```json
POST /api/v1/validate/batch
Content-Type: application/json
Authorization: Bearer <token>

{
  "transactions": [
    {"transaction_id": "TXN001", ...},
    {"transaction_id": "TXN002", ...},
    ...
  ],
  "fiscal_year": 2025,
  "options": {
    "stop_on_first_error": false,
    "include_passed": false
  }
}
```

**Response:**
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "total_count": 150,
  "valid_count": 142,
  "invalid_count": 8,
  "results": [
    {"transaction_id": "TXN003", "valid": false, "errors": [...]},
    {"transaction_id": "TXN017", "valid": false, "errors": [...]},
    ...
  ],
  "processing_time_ms": 450
}
```

---

## Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_REQUEST` | Malformed JSON or missing required fields |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Valid auth but insufficient permissions |
| 422 | `VALIDATION_SCHEMA_ERROR` | Request body doesn't match expected schema |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server-side error |

---

## OpenAPI Specification

Full OpenAPI 3.0 spec to be generated and published at:
```
/api/v1/openapi.json
/api/v1/docs  (Swagger UI)
/api/v1/redoc (ReDoc)
```

---

## Dependencies

- [ ] FastAPI framework setup
- [ ] API authentication mechanism (OAuth2 / API keys)
- [ ] Rate limiting infrastructure
- [ ] Validation engine extracted as importable module

---

## Open Questions

1. Should we support XML request/response for legacy integrations?
2. What's the maximum batch size before requiring async processing?
3. Should validation results be logged/audited, or is this purely stateless?

---

## References

- FastAPI documentation: https://fastapi.tiangolo.com/
- OpenAPI 3.0 specification: https://swagger.io/specification/
