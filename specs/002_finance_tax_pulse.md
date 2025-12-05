# Finance Tax Pulse – PH Pack Integration

**Status:** Implemented v1.0
**Owner:** Finance/Tax Platform Team (InsightPulse AI SSC)
**Last Updated:** 2025-12-05

---

## Summary

Finance Tax Pulse is an AI-assisted review and scoring layer on top of the
TaxPulse PH Pack Odoo module and Supabase warehouse. It provides:

- Automated review of BIR 1601-C, 2550Q, 1702-RT data
- Self-improving Review Protocols (v1: High Compliance Mode)
- Run-level scoring on five dimensions:
  - **D1** Compliance Accuracy (30%)
  - **D2** Numerical Accuracy (25%)
  - **D3** Coverage & Risk Exposure (20%)
  - **D4** Timeliness & Operational Fit (15%)
  - **D5** Clarity & Auditability (10%)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TaxPulse PH Pack                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  Odoo 18.0   │───▶│   Supabase   │◀───│   n8n/CLI    │          │
│  │  BIR Forms   │    │   Warehouse  │    │   Triggers   │          │
│  └──────────────┘    └──────┬───────┘    └──────────────┘          │
│                             │                                       │
│                             ▼                                       │
│                    ┌────────────────┐                               │
│                    │  Edge Function │                               │
│                    │ finance-tax-   │                               │
│                    │    pulse       │                               │
│                    └────────┬───────┘                               │
│                             │                                       │
│                             ▼                                       │
│                    ┌────────────────┐                               │
│                    │   LLM API      │                               │
│                    │ (Claude/GPT)   │                               │
│                    └────────┬───────┘                               │
│                             │                                       │
│                             ▼                                       │
│                    ┌────────────────┐                               │
│                    │ tax_pulse_     │                               │
│                    │   run_log      │                               │
│                    └────────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Database Schema (`supabase/`)

| File | Purpose |
|------|---------|
| `003_tax_pulse_schema.sql` | Authority registry, run log tables, RPC functions |
| `004_tax_pulse_protocol_seed.sql` | Review Protocol v1 (High Compliance Mode) seed |

**Tables:**
- `tax_pulse_sources` – Authoritative tax source registry (Tier 0-3)
- `tax_pulse_source_aliases` – Domain aliases for multi-domain sources
- `tax_pulse_protocols` – Versioned review protocol definitions
- `tax_pulse_run_log` – Audit trail of review runs with scores
- `tax_pulse_protocol_audit` – Protocol change history

**Views:**
- `v_tax_pulse_source_domains` – Unified domain lookup
- `v_tax_pulse_protocol_stats` – Protocol performance metrics

**Functions:**
- `fn_fetch_finance_data()` – Aggregate BIR forms for review
- `fn_insert_tax_pulse_run()` – Record review results

### Edge Function (`supabase/functions/finance-tax-pulse/`)

| File | Purpose |
|------|---------|
| `index.ts` | Deno-based Supabase Edge Function entry point |

**Endpoints:**
- `POST /finance-tax-pulse` – Trigger compliance review

**Request:**
```json
{
  "entity_id": "RIM",
  "period_start": "2025-01-01",
  "period_end": "2025-01-31",
  "tax_types": ["1601-C", "2550Q"],
  "protocol_version": "v1"
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "scores": {
    "compliance": 85,
    "numeric": 92,
    "coverage": 78,
    "timeliness": 90,
    "clarity": 88
  },
  "composite_score": 86.2,
  "status": "pass",
  "memo_summary": "...",
  "findings": [...],
  "risk_flags": [...]
}
```

### Orchestrator Prompt (`engine/`)

| File | Purpose |
|------|---------|
| `finance_tax_pulse_orchestrator.md` | Full system prompt for LLM |
| `config/finance_tax_pulse_model.yaml` | Model binding and parameters |

---

## Review Protocol v1: High Compliance Mode

### Scoring Dimensions

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| D1 Compliance | 30% | BIR form completeness, TIN/RDO validation |
| D2 Numeric | 25% | Computation accuracy, reconciliations |
| D3 Coverage | 20% | Transaction completeness, risk flags |
| D4 Timeliness | 15% | Deadline adherence, amendments |
| D5 Clarity | 10% | Documentation, audit readiness |

### Variance Thresholds (v1)

| Check | Threshold | Action |
|-------|-----------|--------|
| GL vs Return | 0.01% | Block submission |
| Period variance | 15% | Require narrative |
| Line item | PHP 100 | Flag for review |

### Status Determination

| Composite Score | Status |
|-----------------|--------|
| ≥ 80 (all dims ≥ 70) | PASS |
| 60-79 (any dim < 70) | CONDITIONAL |
| < 60 (any dim < 50) | FAIL |

---

## Authority Hierarchy

Finance Tax Pulse enforces strict citation precedence:

| Tier | Type | Examples | Sources |
|------|------|----------|---------|
| 0 | Primary Law | NIRC, CREATE Law | officialgazette.gov.ph |
| 1 | Administrative | RR, RMC, RMO | bir.gov.ph |
| 2 | Judicial/Research | SC/CTA decisions | judiciary.gov.ph |
| 3 | Practitioner | PICPA, TMAP guides | picpa.com.ph |

---

## Usage

### Via Supabase Edge Function

```bash
curl -X POST "https://xkxyvboeubffxxbebsll.supabase.co/functions/v1/finance-tax-pulse" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "RIM",
    "period_start": "2025-01-01",
    "period_end": "2025-03-31",
    "tax_types": ["1601-C", "2550Q"],
    "protocol_version": "v1"
  }'
```

### Via n8n Workflow

1. Create HTTP Request node pointing to Edge Function
2. Trigger on schedule (e.g., 5th of each month)
3. Process response and send to Slack/Teams

### Via Claude Code CLI

```bash
# Direct invocation with model config
claude-code --model-config engine/config/finance_tax_pulse_model.yaml \
  --input '{"entity_id": "RIM", "period_start": "2025-01-01", "period_end": "2025-01-31"}'
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key | Yes |
| `LLM_API_KEY` | Anthropic/OpenAI API key | Yes |
| `LLM_API_URL` | LLM endpoint URL | No (defaults to Anthropic) |
| `LLM_MODEL` | Model identifier | No (defaults to claude-sonnet-4) |

---

## Deployment

### Apply Migrations

```bash
psql "$POSTGRES_URL" -f supabase/001_create_bir_tables.sql
psql "$POSTGRES_URL" -f supabase/002_rpc_functions.sql
psql "$POSTGRES_URL" -f supabase/003_tax_pulse_schema.sql
psql "$POSTGRES_URL" -f supabase/004_tax_pulse_protocol_seed.sql
```

### Deploy Edge Function

```bash
supabase functions deploy finance-tax-pulse
```

### Set Secrets

```bash
supabase secrets set LLM_API_KEY=sk-...
supabase secrets set LLM_MODEL=claude-sonnet-4-20250514
```

---

## Monitoring

### Run Log Queries

```sql
-- Recent runs by entity
SELECT * FROM tax_pulse_run_log
WHERE entity_id = 'RIM'
ORDER BY run_ts DESC
LIMIT 10;

-- Protocol performance stats
SELECT * FROM v_tax_pulse_protocol_stats;

-- Failed runs requiring attention
SELECT * FROM tax_pulse_run_log
WHERE score_compliance < 70
   OR score_numeric < 70
ORDER BY run_ts DESC;
```

### Superset Dashboard

Connect to Supabase and visualize:
- Run counts by entity/period
- Average scores by dimension
- Failure rates by protocol version
- Trend analysis over time

---

## Roadmap

### v1.1 (Planned)
- [ ] Audit Response Mode (enhanced for BIR audit periods)
- [ ] Email notifications for failed runs
- [ ] Batch processing for multi-entity reviews

### v2.0 (Future)
- [ ] Standard Mode (relaxed thresholds)
- [ ] RAG-enhanced authority citations
- [ ] Self-improving protocol recommendations
- [ ] Integration with eBIRForms/eFPS

---

## References

- [TaxPulse Engine PRD](001-taxpulse-engine.prd.md)
- [BIR Revenue Issuances](https://www.bir.gov.ph/index.php/revenue-issuances.html)
- [NIRC of 1997 (as amended)](https://www.officialgazette.gov.ph/)

---

*Maintained by InsightPulse AI Finance SSC*
