# TICKET-001: AI-Powered Anomaly Detection

> **Priority**: P1
> **Type**: Enhancement
> **Component**: Validation / AI Layer
> **Status**: Open
> **Created**: 2025-12-05

---

## Problem Statement

Current validation rules (V_TXN_* and V_AGG_*) are **deterministic and threshold-based**. They catch known patterns (e.g., negative amounts, TIN format errors, VAT ratio outside 1.5x) but fail to detect:

1. **Novel anomalies**: Fraud patterns or errors that don't match pre-defined rules
2. **Contextual outliers**: Transactions that are technically valid but unusual for *this specific agency* or *this time of year*
3. **Emerging patterns**: Gradual drift in transaction characteristics that indicate process breakdown
4. **Collusion indicators**: Coordinated transactions across multiple partners designed to evade single-rule detection

**Business Impact**: Without ML-based anomaly detection, tax teams rely on manual spot-checks and may miss sophisticated errors or fraud until BIR audit.

---

## Scope & Constraints

### In Scope

- **Transaction-level anomaly scoring**: Flag individual transactions as anomalous
- **Aggregate-level pattern detection**: Identify unusual period-over-period or agency-to-agency patterns
- **Explainability**: Each anomaly flag must include human-readable explanation
- **Integration with existing workflow**: Anomalies appear in review queue alongside V_AGG warnings

### Out of Scope (This Ticket)

- Real-time streaming anomaly detection (batch is acceptable for MVP)
- Cross-tenant anomaly correlation (see TICKET-003)
- Automated remediation (human review required)

### Constraints

- **Latency**: Anomaly scoring must complete within 30 seconds for batch of 10,000 transactions
- **Explainability**: No "black box" scores; must provide top contributing factors
- **Data Residency**: Model inference must run in PH region for FinServ compliance
- **False Positive Rate**: Target <5% to avoid alert fatigue

---

## Acceptance Criteria

### Functional

- [ ] System computes anomaly score (0.0-1.0) for each transaction
- [ ] Transactions with score >0.7 flagged as `requires_review`
- [ ] Each flag includes top 3 contributing factors (e.g., "amount 5x historical average", "new partner", "unusual ATC for this vendor type")
- [ ] Aggregate anomaly report generated per period showing top 10 anomalous transactions
- [ ] Anomaly scores persisted in audit log for compliance

### Non-Functional

- [ ] Batch processing: 10,000 transactions in <30 seconds
- [ ] Model retraining pipeline documented and executable
- [ ] Feature drift monitoring in place
- [ ] Fallback to rule-based validation if ML service unavailable

### Testing

- [ ] Golden dataset with labeled anomalies achieves:
  - Precision >80%
  - Recall >70%
  - F1 >0.75
- [ ] Performance test: 100,000 transactions in <5 minutes

---

## Technical Approach

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   ANOMALY DETECTION PIPELINE                    │
└─────────────────────────────────────────────────────────────────┘

[Validated Transactions]
        │
        ▼
┌───────────────────────┐
│  Feature Extraction   │ ← amount_zscore, partner_frequency,
│                       │   atc_distribution, day_of_month, etc.
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Isolation Forest /   │ ← Unsupervised anomaly detection
│  Autoencoder          │   Pre-trained on historical data
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  SHAP Explainer       │ ← Feature importance for each prediction
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Anomaly Score +      │
│  Explanation          │
└───────────────────────┘
```

### Feature Set (Initial)

| Feature | Description | Type |
|---------|-------------|------|
| `amount_zscore` | Standard deviations from agency mean | Numeric |
| `partner_frequency` | How often this partner appears | Numeric |
| `partner_is_new` | First transaction with this partner | Boolean |
| `atc_unusual_for_partner` | ATC code differs from partner's typical | Boolean |
| `day_of_month` | Cyclical encoding of transaction date | Numeric |
| `amount_round_number` | Amount is suspiciously round (e.g., 100,000) | Boolean |
| `description_length` | Unusually short/long description | Numeric |
| `time_since_last_txn` | Gap from previous transaction with partner | Numeric |

### Model Options

| Model | Pros | Cons | Recommendation |
|-------|------|------|----------------|
| Isolation Forest | Fast, interpretable, no labeled data needed | Less accurate on subtle anomalies | **MVP choice** |
| Autoencoder | Captures complex patterns | Harder to explain | Phase 2 |
| One-Class SVM | Good boundary detection | Slow on large datasets | Not recommended |

---

## Interface Sketch

### Python SDK

```python
from taxpulse.anomaly import AnomalyDetector

detector = AnomalyDetector(model_path="models/anomaly_v1.joblib")

# Score a batch of transactions
results = detector.score_batch(transactions)

# Result structure
# [
#     {
#         "transaction_id": "TXN001",
#         "anomaly_score": 0.82,
#         "is_anomalous": True,
#         "explanation": [
#             {"feature": "amount_zscore", "contribution": 0.45,
#              "detail": "Amount (₱2.5M) is 4.2σ above agency average (₱180K)"},
#             {"feature": "partner_is_new", "contribution": 0.25,
#              "detail": "First transaction with 'XYZ Consulting'"},
#             {"feature": "atc_unusual_for_partner", "contribution": 0.12,
#              "detail": "W010 unusual; partner typically coded W157"}
#         ]
#     },
#     ...
# ]
```

### REST API (Future)

```
POST /api/v1/anomaly/score
Content-Type: application/json

{
  "transactions": [...],
  "agency_id": "TBWA",
  "period": "2025-Q1"
}

Response:
{
  "scored_count": 150,
  "anomalous_count": 7,
  "results": [...],
  "model_version": "anomaly_v1.2",
  "processing_time_ms": 1250
}
```

---

## Dependencies

- [ ] Historical transaction data (minimum 12 months) for model training
- [ ] Feature store or caching layer for computed features
- [ ] Model serving infrastructure (can be same-process for MVP)
- [ ] SHAP library for explainability

---

## Open Questions

1. Should anomaly scores be visible to preparers, or only managers?
2. What's the threshold for auto-escalation vs. informational flag?
3. How frequently should the model be retrained?

---

## References

- Isolation Forest: Liu, Fei Tony, Kai Ming Ting, and Zhi-Hua Zhou. "Isolation forest." ICDM 2008.
- SHAP: Lundberg, Scott M., and Su-In Lee. "A unified approach to interpreting model predictions." NeurIPS 2017.
