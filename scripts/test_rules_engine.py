#!/usr/bin/env python3
"""
Test script for TaxPulse Rules Engine
Processes golden dataset transactions and validates output
"""

import sys
import csv
from pathlib import Path
from typing import List, Dict, Any

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.rules_engine import RulesLoader, RulesEvaluator, FormulaEngine


def load_transactions(csv_file: str) -> List[Dict[str, Any]]:
    """Load transactions from CSV file"""
    transactions = []

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert gross_amount to float
            row['gross_amount'] = float(row['gross_amount'])
            transactions.append(row)

    return transactions


def load_expected_lines(csv_file: str) -> Dict[str, float]:
    """Load expected form line values from CSV"""
    expected = {}

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            line_id = f"line_{row['line_id']}"
            expected_value = float(row['expected_value'])
            expected[line_id] = expected_value

    return expected


def process_transactions(pack_path: str, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process transactions through TaxPulse Engine

    Args:
        pack_path: Path to tax pack (e.g., 'packs/ph/')
        transactions: List of transaction dictionaries

    Returns:
        Dictionary with buckets and form_lines
    """
    # Initialize components
    loader = RulesLoader(pack_path)
    evaluator = RulesEvaluator()
    formula_engine = FormulaEngine()

    # Load rules and rates
    vat_rules = loader.load_rules('vat.rules.yaml')
    ewt_rules = loader.load_rules('ewt.rules.yaml')
    rates_data = loader.load_rates('ph_rates_2025.json')

    print(f"✅ Loaded {len(vat_rules)} VAT rules")
    print(f"✅ Loaded {len(ewt_rules)} EWT rules")

    # Initialize buckets
    all_buckets = {}

    # Process each transaction
    for txn in transactions:
        print(f"\nProcessing: {txn['txn_id']} - {txn['description']}")

        # Apply VAT rules
        vat_result = evaluator.apply_rules(vat_rules, txn, rates_data)
        for bucket, amount in vat_result['buckets'].items():
            if bucket in all_buckets:
                all_buckets[bucket] += amount
            else:
                all_buckets[bucket] = amount
            print(f"  → {bucket}: ₱{amount:,.2f}")

        # Apply EWT rules
        ewt_result = evaluator.apply_rules(ewt_rules, txn, rates_data)
        for bucket, amount in ewt_result['buckets'].items():
            if bucket in all_buckets:
                all_buckets[bucket] += amount
            else:
                all_buckets[bucket] = amount
            print(f"  → {bucket}: ₱{amount:,.2f}")

    # Apply aggregation rules (priority 200+)
    aggregation_rules = [r for r in vat_rules if r.get('priority', 0) >= 200]
    all_buckets = formula_engine.evaluate_aggregation_rules(aggregation_rules, all_buckets)

    # Load form mapping and evaluate form lines
    mapping = loader.load_mapping('vat_2550Q.mapping.yaml')
    form_lines = formula_engine.evaluate_form_lines(mapping, all_buckets)

    return {
        'buckets': all_buckets,
        'form_lines': form_lines
    }


def validate_results(computed: Dict[str, float], expected: Dict[str, float], tolerance: float = 0.01) -> bool:
    """
    Validate computed results against expected values

    Args:
        computed: Computed form line values
        expected: Expected form line values
        tolerance: Acceptable difference threshold

    Returns:
        True if all validations pass
    """
    all_passed = True

    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)

    for line_id, expected_value in expected.items():
        computed_value = computed.get(line_id, 0.0)
        diff = abs(computed_value - expected_value)

        if diff <= tolerance:
            print(f"✅ {line_id}: ₱{computed_value:,.2f} (expected: ₱{expected_value:,.2f})")
        else:
            print(f"❌ {line_id}: ₱{computed_value:,.2f} (expected: ₱{expected_value:,.2f}) [DIFF: ₱{diff:,.2f}]")
            all_passed = False

    return all_passed


def main():
    """Main test execution"""
    print("="*80)
    print("TaxPulse Rules Engine Test")
    print("="*80)

    # Paths
    pack_path = Path(__file__).parent.parent / "packs" / "ph"
    fixtures_path = pack_path / "tests" / "fixtures"

    # Load test data
    print("\n📂 Loading test data...")
    transactions = load_transactions(fixtures_path / "vat_basic_transactions.csv")
    expected_lines = load_expected_lines(fixtures_path / "vat_basic_expected_lines.csv")

    print(f"✅ Loaded {len(transactions)} transactions")
    print(f"✅ Loaded {len(expected_lines)} expected form lines")

    # Process transactions
    print("\n⚙️  Processing transactions through TaxPulse Engine...")
    result = process_transactions(str(pack_path), transactions)

    # Display bucket totals
    print("\n" + "="*80)
    print("COMPUTED BUCKETS")
    print("="*80)
    for bucket, amount in sorted(result['buckets'].items()):
        print(f"{bucket}: ₱{amount:,.2f}")

    # Display form lines
    print("\n" + "="*80)
    print("BIR FORM 2550Q LINE VALUES")
    print("="*80)
    for line_id, value in sorted(result['form_lines'].items()):
        print(f"{line_id}: ₱{value:,.2f}")

    # Validate results
    validation_passed = validate_results(result['form_lines'], expected_lines)

    # Summary
    print("\n" + "="*80)
    if validation_passed:
        print("✅ ALL VALIDATIONS PASSED")
        print("="*80)
        return 0
    else:
        print("❌ SOME VALIDATIONS FAILED")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
