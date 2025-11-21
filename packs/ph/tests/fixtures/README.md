# TaxPulse PH Pack - Golden Dataset Test Fixtures

## Overview

These CSV files are **golden datasets** for regression testing the TaxPulse Engine. They represent known-good transaction sets with pre-calculated expected outputs.

Pattern inspired by **OpenTaxSolver's** approach: each tax year has a "golden" set of returns with known correct answers.

## Test Fixtures

### 1. vat_basic_transactions.csv
**Purpose**: Input transaction data for Q1 2025 VAT computation

**Schema**:
- `txn_id`: Unique transaction identifier
- `company_code`: Entity code (TBWA)
- `doc_type`: invoice (sales) or bill (purchases)
- `doc_date`: Transaction date
- `partner_id`: Customer/vendor ID
- `partner_name`: Customer/vendor name
- `tin`: Tax Identification Number (###-###-###-###)
- `vendor_type`: CUSTOMER, PROFESSIONAL, SUPPLIER, FOREIGN
- `tax_code`: VAT_12_SALES, VAT_12_PURCHASE, VAT_ZERO_EXPORTS
- `atc_code`: ATC code for withholding (W020, W157, etc.)
- `gross_amount`: Total amount including VAT
- `currency`: PHP (Philippine Peso)
- `gl_account`: General ledger account code
- `description`: Transaction description

**Contains**: 13 transactions (7 sales, 6 purchases) covering:
- Standard VAT sales (4 transactions)
- Zero-rated export sales (2 transactions)
- VAT purchases with various ATC codes (7 transactions)

### 2. vat_basic_expected_lines.csv
**Purpose**: Expected BIR Form 2550Q line values after processing the input transactions

**Schema**:
- `line_id`: BIR Form 2550Q line number
- `line_label`: Line description from form
- `expected_value`: Calculated amount (PHP)
- `calculation_notes`: How the value was derived

**Key Assertions**:
- Line 17 (Sales): ₱350,000.00
- Line 20 (Output VAT): ₱42,000.00
- Line 22 (Zero-rated exports): ₱392,000.00
- Line 26 (Input VAT): ₱11,160.00
- Line 29 (VAT Payable): ₱30,840.00
- Line 34 (Tax to be Paid): ₱30,840.00

### 3. ewt_expected_withholding.csv
**Purpose**: Expected EWT (Expanded Withholding Tax) amounts per transaction

**Schema**:
- `txn_id`: Transaction identifier (matches vat_basic_transactions.csv)
- `doc_type`: bill (purchases only)
- `partner_name`: Vendor name
- `atc_code`: ATC code (W020, W040, W157, W158, W169)
- `gross_amount`: Total purchase amount
- `expected_ewt_rate`: Withholding rate (decimal)
- `expected_ewt_amount`: Calculated withholding (PHP)
- `bucket_output`: Target output bucket from ewt.rules.yaml
- `notes`: Explanation

**Key Assertions**:
- W020 (Professional fees): 10% rate → ₱2,800.00 total
- W040 (Legal fees): 10% rate → ₱2,240.00
- W157 (Goods): 1% rate → ₱56.00
- W158 (Services): 2% rate → ₱403.20
- W169 (Rent): 5% rate → ₱1,400.00
- **EWT_TOTAL**: ₱6,899.20

## Usage in Tests

### Pattern: Fixture-Based Regression Testing

```python
# Pseudocode for test runner

def test_vat_golden_dataset():
    # 1. Load input transactions
    transactions = load_csv('vat_basic_transactions.csv')

    # 2. Run TaxPulse Engine
    engine = TaxPulseEngine(pack='ph', period='2025Q1')
    result = engine.process(transactions)

    # 3. Load expected outputs
    expected = load_csv('vat_basic_expected_lines.csv')

    # 4. Assert each form line matches expected
    for line in expected:
        actual_value = result.form_lines[line.line_id]
        assert_equal(actual_value, line.expected_value, tolerance=0.01)

    # 5. Assert output buckets
    assert_equal(result.buckets['VAT_OUTPUT_12'], 42000.00)
    assert_equal(result.buckets['VAT_INPUT_12'], 11160.00)
    assert_equal(result.buckets['VAT_PAYABLE'], 30840.00)

def test_ewt_golden_dataset():
    # 1. Load input transactions (same as VAT)
    transactions = load_csv('vat_basic_transactions.csv')

    # 2. Run TaxPulse Engine with EWT rules
    engine = TaxPulseEngine(pack='ph', period='2025Q1')
    result = engine.process(transactions)

    # 3. Load expected EWT outputs
    expected = load_csv('ewt_expected_withholding.csv')

    # 4. Assert each EWT amount matches
    for txn in expected:
        if txn.txn_id == 'TOTAL':
            assert_equal(result.buckets['EWT_TOTAL'], txn.expected_ewt_amount)
        else:
            actual_ewt = result.transactions[txn.txn_id].ewt_amount
            assert_equal(actual_ewt, txn.expected_ewt_amount, tolerance=0.01)
```

## Test Scenarios Covered

### VAT Computation
- ✅ Standard 12% VAT on sales
- ✅ Zero-rated exports (0% VAT)
- ✅ Input VAT from purchases
- ✅ VAT payable calculation (output - input)
- ✅ Form 2550Q line mapping

### EWT Computation
- ✅ Professional fees - juridical (W020): 10%
- ✅ Legal fees (W040): 10%
- ✅ Goods purchases (W157): 1%
- ✅ Services purchases (W158): 2%
- ✅ Rent - real property (W169): 5%
- ✅ Total EWT aggregation

## Extending the Golden Datasets

To add new test scenarios:

1. **Create new CSV file**: `[scenario]_transactions.csv`
2. **Calculate expected outputs**: `[scenario]_expected_lines.csv`
3. **Document edge cases**: Add README section explaining the scenario

**Examples of scenarios to add**:
- `vat_with_prior_credit.csv` - Carrying forward tax credit from prior period
- `vat_with_penalties.csv` - Late filing penalties
- `ewt_mixed_vendors.csv` - Individual vs juridical person withholding
- `annual_income_tax.csv` - Form 1702-RT corporate income tax
- `quarterly_income_tax.csv` - Form 1701Q quarterly income tax

## Quality Assurance

All golden datasets must:
1. ✅ Have complete and valid transaction data
2. ✅ Include pre-calculated expected outputs
3. ✅ Document calculation methodology
4. ✅ Cover edge cases and special scenarios
5. ✅ Be version-controlled and reviewed before release

## References

- **Pattern Source**: OpenTaxSolver (US tax software) uses "golden" tax returns for each year
- **BIR Forms**: https://www.bir.gov.ph/index.php/eservices/bir-forms.html
- **Tax Rates**: TRAIN Law (RA 10963), CREATE Law (RA 11534)
- **Withholding Rules**: RR 2-98 (Consolidated Withholding Tax Regulations)
