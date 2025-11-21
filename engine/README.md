# TaxPulse Engine - Core Implementation

## Overview

The TaxPulse Engine is a deterministic, rules-based tax computation engine that sits between ERP systems (Spectra, Odoo) and BIR filing tools. It uses JSONLogic-based rules stored as data (not code) to ensure tax computations are transparent, auditable, and version-controlled.

## Architecture

```
┌─────────────────┐
│  ERP Systems    │  (Spectra, Odoo, Xero)
│  - Transactions │
│  - Invoices     │
│  - Bills        │
└────────┬────────┘
         │
         │ Canonical Transaction Schema
         ↓
┌─────────────────────────────────────────────┐
│           TaxPulse Engine                    │
│  ┌─────────────────────────────────────┐   │
│  │  1. Rules Loader                     │   │
│  │     - Load tax rules from YAML       │   │
│  │     - Load rates from JSON           │   │
│  │     - Load mappings and forms        │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  2. Rules Evaluator (JSONLogic)      │   │
│  │     - Match transactions to rules     │   │
│  │     - Evaluate conditions             │   │
│  │     - Compute base × rate            │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  3. Formula Engine                   │   │
│  │     - Aggregate buckets (SUM, MAX)   │   │
│  │     - Compute form lines             │   │
│  │     - Evaluate formulas              │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  4. Validation Engine                │   │
│  │     - Transaction validations         │   │
│  │     - Aggregate validations          │   │
│  │     - Form line validations          │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         │
         │ Output Buckets + Form Lines
         ↓
┌─────────────────┐
│  BIR Forms      │  (2550Q, 1601-C, 1702-RT)
│  - Form Lines   │
│  - XML/PDF      │
│  - eFPS Format  │
└─────────────────┘
```

## Core Components

### 1. Rules Engine (`rules_engine/`)

**Purpose**: Load, evaluate, and apply tax rules to transactions

#### `loader.py` - RulesLoader
- Load tax rules from YAML files
- Load rates from JSON files
- Load form mappings and validations
- Cache loaded data for performance
- Extract rate values by code (W010, VAT_12_SALES, etc.)

**Key Methods**:
```python
loader = RulesLoader('packs/ph/')
vat_rules = loader.load_rules('vat.rules.yaml')
rates = loader.load_rates('ph_rates_2025.json')
mapping = loader.load_mapping('vat_2550Q.mapping.yaml')
```

#### `evaluator.py` - RulesEvaluator
- Evaluate JSONLogic conditions against transaction data
- Match transactions to applicable rules
- Compute tax amounts (base × rate)
- Accumulate results into output buckets

**Supported JSONLogic Operators**:
- Comparison: `==`, `!=`, `>`, `>=`, `<`, `<=`
- Logical: `and`, `or`
- Membership: `in`
- Conditional: `if`
- Arithmetic: `+`, `-`, `*`, `/`
- Variable: `var`

**Example Condition**:
```yaml
condition:
  and:
    - "==": [{"var": "doc_type"}, "invoice"]
    - "==": [{"var": "tax_code"}, "VAT_12_SALES"]
    - ">": [{"var": "gross_amount"}, 0]
```

**Key Methods**:
```python
evaluator = RulesEvaluator()
result = evaluator.apply_rules(vat_rules, transaction, rates_data)
buckets = result['buckets']  # {'VAT_OUTPUT_12': 42000.00, ...}
```

#### `formula.py` - FormulaEngine
- Evaluate aggregate formulas on buckets
- Compute derived buckets (e.g., VAT_PAYABLE = OUTPUT - INPUT)
- Evaluate form lines from bucket mappings
- Support formula functions: SUM, MAX, MIN, ABS, ROUND

**Example Formulas**:
```yaml
# Aggregation rule (priority 200)
formula: "SUM(VAT_OUTPUT_12, VAT_OUTPUT_ZERO) - SUM(VAT_INPUT_12, VAT_INPUT_ZERO)"
output_bucket: VAT_PAYABLE

# Form line computation
line: "29"
formula: "line_27 - line_28"  # Output VAT - Input VAT
```

**Key Methods**:
```python
formula_engine = FormulaEngine()

# Evaluate aggregation rules
buckets = formula_engine.evaluate_aggregation_rules(aggregation_rules, buckets)

# Compute form lines
form_lines = formula_engine.evaluate_form_lines(mapping, buckets)
```

### 2. Validation Engine (`validation/`)

**Status**: Pending implementation

**Purpose**: Validate transactions and aggregated results

**Components**:
- **Transaction Validator**: Per-row data quality checks
- **Aggregate Validator**: Post-computation sanity checks
- **Form Validator**: BIR form-specific validations

**Severity Levels**:
- `error`: Blocks processing, must be fixed
- `warning`: Logs warning, processing continues
- `info`: Advisory message, no impact

### 3. Reconciliation Engine (`reconciliation/`)

**Status**: Pending implementation

**Purpose**: Multi-layer verification of tax computations

**Reconciliation Types**:
- **GL vs Return**: General ledger totals vs tax return amounts
- **Subledger vs Return**: Subsidiary ledger vs tax return
- **Period vs Period**: Current period vs prior period consistency

### 4. Workflow Engine (`workflow/`)

**Status**: Pending implementation

**Purpose**: Maker-checker approval workflow

**States**: `draft` → `for_review` → `approved` → `filed` → `paid`

## Usage Example

```python
from engine.rules_engine import RulesLoader, RulesEvaluator, FormulaEngine

# 1. Initialize components
loader = RulesLoader('packs/ph/')
evaluator = RulesEvaluator()
formula_engine = FormulaEngine()

# 2. Load rules and rates
vat_rules = loader.load_rules('vat.rules.yaml')
ewt_rules = loader.load_rules('ewt.rules.yaml')
rates_data = loader.load_rates('ph_rates_2025.json')

# 3. Process transactions
all_buckets = {}

for transaction in transactions:
    # Apply VAT rules
    vat_result = evaluator.apply_rules(vat_rules, transaction, rates_data)
    for bucket, amount in vat_result['buckets'].items():
        all_buckets[bucket] = all_buckets.get(bucket, 0.0) + amount

    # Apply EWT rules
    ewt_result = evaluator.apply_rules(ewt_rules, transaction, rates_data)
    for bucket, amount in ewt_result['buckets'].items():
        all_buckets[bucket] = all_buckets.get(bucket, 0.0) + amount

# 4. Apply aggregation rules
aggregation_rules = [r for r in vat_rules if r.get('priority', 0) >= 200]
all_buckets = formula_engine.evaluate_aggregation_rules(aggregation_rules, all_buckets)

# 5. Compute form lines
mapping = loader.load_mapping('vat_2550Q.mapping.yaml')
form_lines = formula_engine.evaluate_form_lines(mapping, all_buckets)

# 6. Output results
print("Buckets:", all_buckets)
print("Form Lines:", form_lines)
```

## Testing

### Golden Dataset Testing

The engine includes fixture-based regression testing using "golden datasets" - known-good transaction sets with pre-calculated expected outputs.

**Run Tests**:
```bash
# Install dependencies
pip install -r engine/requirements.txt

# Run test script
python scripts/test_rules_engine.py
```

**Expected Output**:
```
================================================================================
TaxPulse Rules Engine Test
================================================================================

📂 Loading test data...
✅ Loaded 13 transactions
✅ Loaded 16 expected form lines

⚙️  Processing transactions through TaxPulse Engine...
✅ Loaded 11 VAT rules
✅ Loaded 10 EWT rules

Processing: TXN001 - Sale of advertising services
  → VAT_OUTPUT_12: ₱12,000.00

...

================================================================================
VALIDATION RESULTS
================================================================================
✅ line_17: ₱350,000.00 (expected: ₱350,000.00)
✅ line_20: ₱42,000.00 (expected: ₱42,000.00)
✅ line_26: ₱11,160.00 (expected: ₱11,160.00)
✅ line_29: ₱30,840.00 (expected: ₱30,840.00)
✅ line_34: ₱30,840.00 (expected: ₱30,840.00)

================================================================================
✅ ALL VALIDATIONS PASSED
================================================================================
```

## Patterns Implemented

| Pattern | Source | Purpose |
|---------|--------|---------|
| **JSONLogic Rules** | PayrollEngine | Condition evaluation as data, not code |
| **Per-Form Configuration** | OpenTaxSolver | Each BIR form has dedicated config |
| **Bucket System** | OpenTaxSolver | Intermediate aggregation buckets |
| **Country Pack** | ERPNext/Odoo | Self-contained localization modules |
| **Rate Tables** | node-sales-tax | JSON-based rate configuration |
| **Formula DSL** | PayrollEngine | String-based formula evaluation |

## Design Principles

### 1. Deterministic
- Same input → Same output, always
- No hidden state or side effects
- All rules versioned and auditable

### 2. Transparent
- Rules as configuration (YAML/JSON), not code
- Human-readable rule definitions
- Traceable from transaction → bucket → form line

### 3. Testable
- Golden dataset regression tests
- Parallel-run validation against legacy systems
- Snapshot testing for rule changes

### 4. Extensible
- Add new tax types by creating new rule files
- Support new BIR forms with mapping configs
- AI agents can explain, but never modify tax math

## Next Steps

1. ✅ **Rules Engine** - COMPLETED
   - JSONLogic evaluator
   - Formula engine
   - Bucket aggregation

2. ⏳ **Validation Engine** - PENDING
   - Transaction validations
   - Aggregate validations
   - Form validations

3. ⏳ **Reconciliation Engine** - PENDING
   - GL vs Return reconciliation
   - Subledger vs Return reconciliation
   - Period-to-period verification

4. ⏳ **Workflow Engine** - PENDING
   - Maker-checker state machine
   - Approval workflows
   - Filing status tracking

5. ⏳ **Integration Layer** - PENDING
   - Spectra integration
   - Odoo integration
   - REST API endpoints

## References

- **PRD**: `specs/001-taxpulse-engine.prd.md`
- **PH Pack**: `packs/ph/`
- **Test Fixtures**: `packs/ph/tests/fixtures/`
- **Patterns**: PayrollEngine, OpenTaxSolver, node-sales-tax, ERPNext, Odoo
