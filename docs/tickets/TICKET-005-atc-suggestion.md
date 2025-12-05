# TICKET-005: ATC Code Suggestion & Validation

> **Priority**: P2
> **Type**: Enhancement
> **Component**: Validation / AI Layer
> **Status**: Open
> **Created**: 2025-12-05

---

## Problem Statement

Alphalist Tax Codes (ATC) determine the correct withholding tax rate for transactions. Currently:

1. **Manual assignment**: Accountants manually select ATC codes during AP entry in Odoo
2. **No validation**: TaxPulse trusts the assigned ATC without verifying appropriateness
3. **Common errors**:
   - W010 (Professional Fees - 15%) used when W157 (Supplier - 1%) is correct
   - Missing ATC on EWT-applicable transactions
   - Wrong ATC for transaction type (e.g., using goods ATC for services)

**Business Impact**:
- Incorrect withholding tax remittances to BIR
- Penalties and surcharges on underpayment
- Supplier complaints on over-withholding
- Manual correction workload at month-end

---

## Scope & Constraints

### In Scope

- **ATC suggestion**: AI model recommends ATC code based on transaction attributes
- **ATC validation**: Flag when assigned ATC doesn't match transaction characteristics
- **Confidence scoring**: Indicate certainty of recommendation
- **Human-in-the-loop**: Suggestions require human confirmation before application
- **Learning from corrections**: Model improves from user feedback

### Out of Scope (This Ticket)

- Automatic ATC assignment without human review
- ATC master data management (BIR maintains official list)
- Retroactive ATC correction for posted transactions

### Constraints

- **Accuracy**: Suggestion accuracy must exceed 90% before production use
- **Explainability**: Each suggestion must explain reasoning
- **Fallback**: When confidence < 70%, defer to human selection
- **Audit trail**: All AI suggestions and human overrides logged

---

## Acceptance Criteria

### Functional

- [ ] System suggests ATC code for each EWT-applicable transaction
- [ ] Suggestion includes confidence score (0-100%)
- [ ] Suggestion includes top 3 contributing factors
- [ ] `V_TXN_011` validates assigned ATC against transaction attributes
- [ ] Mismatched ATC flagged with suggested alternative
- [ ] User can accept, reject, or modify suggestion
- [ ] Feedback loop captures corrections for model improvement

### Non-Functional

- [ ] Suggestion latency: <200ms per transaction
- [ ] Batch suggestion: 1,000 transactions in <30 seconds
- [ ] Model accuracy: >90% on validation dataset
- [ ] False positive rate: <5% (flagging correct ATCs as wrong)

### Testing

- [ ] Golden dataset: 1,000 labeled transactions with correct ATC
- [ ] Test case: Professional services (W010) correctly suggested
- [ ] Test case: Goods purchase (W157/W158) correctly suggested
- [ ] Test case: Rental payment (W040) correctly suggested
- [ ] Test case: Low confidence defers to human

---

## Technical Approach

### ATC Classification Model

```
┌─────────────────────────────────────────────────────────────────┐
│                   ATC SUGGESTION ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────────┘

[Transaction Input]
        │
        ├── description
        ├── vendor_type
        ├── account_code
        ├── partner_industry
        └── amount_range
        │
        ▼
┌───────────────────────┐
│  Feature Engineering  │
│  - Text embeddings    │
│  - Categorical encode │
│  - Numerical scaling  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Classification Model │ ← Fine-tuned BERT or Gradient Boosting
│  Multi-class: 20+ ATC │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Confidence Scoring   │
│  + Calibration        │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Explanation (SHAP)   │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  ATC Suggestion       │
│  + Confidence         │
│  + Reasoning          │
└───────────────────────┘
```

### Feature Set

| Feature | Description | Type | Importance |
|---------|-------------|------|------------|
| `description` | Transaction description text | Text (embedded) | High |
| `vendor_type` | Vendor classification | Categorical | High |
| `account_code` | GL account from Odoo | Categorical | Medium |
| `partner_industry` | Partner's business classification | Categorical | Medium |
| `amount` | Transaction amount (log-scaled) | Numeric | Low |
| `is_individual` | Partner is individual vs. corporation | Boolean | Medium |
| `historical_atc` | Most common ATC for this partner | Categorical | High |

### ATC Categories & Rules

| ATC Code | Description | Rate | Key Indicators |
|----------|-------------|------|----------------|
| **W010** | Professional fees (individuals) | 15% | "consulting", "legal", "accounting", individual partner |
| **W015** | Professional fees (corporations) | 15% | Same as W010 but corporate partner |
| **W040** | Income payments to prime contractors | 2% | "rent", "lease", "contractor", property-related |
| **W157** | Purchases of goods | 1% | "supplies", "materials", "inventory", "goods" |
| **W158** | Purchases of services | 2% | "services", "maintenance", "repairs" |
| **W159** | Purchases from top 20K | 1%/2% | Partner in top 20K withholding agent list |
| **W170** | Government payments | 1-15% | Government partner TIN pattern |

### Model Options

| Model | Pros | Cons | Recommendation |
|-------|------|------|----------------|
| **Fine-tuned BERT** | Excellent text understanding | Requires training data, GPU | Best accuracy |
| **Gradient Boosting + TF-IDF** | Fast, interpretable | Less nuanced text understanding | **MVP choice** |
| **Rule-based + LLM** | No training needed | LLM costs, less consistent | Fallback option |

### Validation Rule

```yaml
# In core_validations.yaml
- rule_id: V_TXN_011
  name: ATC Code Validation
  description: Validate assigned ATC matches transaction characteristics
  severity: warning
  condition:
    and:
      - {"in": [{"var": "tax_code"}, ["EWT", "EWT_PROF", "EWT_GOODS", "EWT_SERVICES"]]}
      - {"!=": [{"var": "atc_code"}, null]}
  action: atc_validation
  parameters:
    confidence_threshold: 0.70
    flag_on_mismatch: true
    suggest_alternative: true
```

---

## Interface Sketch

### Python SDK

```python
from taxpulse.atc import ATCSuggester

suggester = ATCSuggester(model_path="models/atc_classifier_v1.joblib")

# Suggest ATC for a transaction
suggestion = suggester.suggest(
    description="Legal consulting services for Q1 contract review",
    vendor_type="PROFESSIONAL",
    partner_is_individual=True,
    account_code="5020",
    partner_tin="123-456-789"
)

# Result structure
# {
#     "suggested_atc": "W010",
#     "confidence": 0.92,
#     "alternatives": [
#         {"atc": "W015", "confidence": 0.06},
#         {"atc": "W158", "confidence": 0.02}
#     ],
#     "reasoning": [
#         {"factor": "description", "contribution": 0.45,
#          "detail": "Keywords 'legal', 'consulting' indicate professional services"},
#         {"factor": "vendor_type", "contribution": 0.30,
#          "detail": "Vendor classified as PROFESSIONAL"},
#         {"factor": "partner_is_individual", "contribution": 0.17,
#          "detail": "Individual partner → W010 (not W015)"}
#     ]
# }

# Validate existing ATC assignment
validation = suggester.validate(
    assigned_atc="W157",  # Assigned by user
    description="Legal consulting services",
    vendor_type="PROFESSIONAL",
    partner_is_individual=True
)

# Result structure
# {
#     "assigned_atc": "W157",
#     "is_valid": False,
#     "suggested_atc": "W010",
#     "mismatch_severity": "high",
#     "message": "W157 (Goods 1%) unlikely for professional services. Consider W010 (Professional 15%).",
#     "rate_impact": {
#         "assigned_rate": 0.01,
#         "suggested_rate": 0.15,
#         "potential_underwithholding": 14000.00  # On 100K transaction
#     }
# }
```

### REST API

```
POST /api/v1/atc/suggest
Content-Type: application/json
Authorization: Bearer <token>

{
  "transaction": {
    "description": "Monthly IT support services",
    "vendor_type": "SUPPLIER",
    "partner_tin": "444-555-666-000",
    "partner_is_individual": false,
    "account_code": "5030",
    "gross_amount": 50000
  },
  "options": {
    "include_alternatives": true,
    "top_k": 3
  }
}

Response:
{
  "suggested_atc": "W158",
  "confidence": 0.88,
  "alternatives": [
    {"atc": "W157", "confidence": 0.08},
    {"atc": "W040", "confidence": 0.04}
  ],
  "reasoning": [
    {"factor": "description", "detail": "'IT support services' indicates service transaction"},
    {"factor": "account_code", "detail": "5030 typically maps to service expenses"}
  ]
}
```

```
POST /api/v1/atc/validate
Content-Type: application/json
Authorization: Bearer <token>

{
  "assigned_atc": "W157",
  "transaction": {
    "description": "Monthly IT support services",
    ...
  }
}

Response:
{
  "is_valid": false,
  "assigned_atc": "W157",
  "suggested_atc": "W158",
  "confidence": 0.88,
  "message": "W157 (Goods) unlikely for 'IT support services'. Suggest W158 (Services).",
  "action_required": true
}
```

---

## Feedback Loop

```python
# Capture user corrections for model improvement
feedback_collector.record(
    transaction_id="TXN001",
    suggested_atc="W010",
    selected_atc="W015",  # User selected different ATC
    user_id="user_123",
    reason="Corporate partner, not individual"  # Optional explanation
)

# Batch retrain trigger (weekly or on threshold)
if feedback_collector.pending_count() > 100:
    model_trainer.retrain(
        base_model="models/atc_classifier_v1.joblib",
        feedback_data=feedback_collector.export(),
        output_path="models/atc_classifier_v2.joblib"
    )
```

---

## Training Data Requirements

| Data Source | Records Needed | Purpose |
|-------------|----------------|---------|
| Historical transactions with assigned ATC | 10,000+ | Training data |
| Expert-labeled golden dataset | 1,000+ | Validation & accuracy measurement |
| Correction feedback | Ongoing | Continuous improvement |

---

## Dependencies

- [ ] Historical transaction data export with ATC assignments
- [ ] ATC master data (BIR official list with descriptions)
- [ ] Feature engineering pipeline
- [ ] Model training infrastructure
- [ ] Feedback collection mechanism in UI

---

## Open Questions

1. What's the minimum confidence threshold to show a suggestion vs. "No suggestion"?
2. Should high-value transactions (>₱500K) require manual ATC selection regardless of AI confidence?
3. How do we handle new ATC codes added by BIR?
4. Should the model consider partner history more heavily than transaction description?

---

## References

- BIR ATC Master List (RR 2-98, as amended)
- RMC 8-2018: Updated ATC codes
- Scikit-learn documentation: https://scikit-learn.org/
- SHAP for model explainability: https://shap.readthedocs.io/
