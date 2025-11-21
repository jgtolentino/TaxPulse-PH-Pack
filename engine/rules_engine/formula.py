"""
Formula Engine - Evaluate aggregate formulas on computed buckets
"""

from typing import Dict, Any, List
import re


class FormulaEngine:
    """Evaluate formulas for bucket aggregations and form line computations"""

    def __init__(self):
        """Initialize formula engine"""
        self.functions = {
            "SUM": self._func_sum,
            "MAX": self._func_max,
            "MIN": self._func_min,
            "ABS": self._func_abs,
            "ROUND": self._func_round,
        }

    def evaluate(self, formula: str, buckets: Dict[str, float], form_lines: Dict[str, float] = None) -> float:
        """
        Evaluate a formula with access to buckets and form lines

        Args:
            formula: Formula string (e.g., "SUM(VAT_OUTPUT_12, VAT_OUTPUT_ZERO) - SUM(VAT_INPUT_12)")
            buckets: Dictionary of bucket names to values
            form_lines: Optional dictionary of form line IDs to values

        Returns:
            Computed result as float
        """
        if not formula:
            return 0.0

        # Replace bucket/line references with actual values
        resolved_formula = self._resolve_references(formula, buckets, form_lines or {})

        # Evaluate functions
        result = self._evaluate_functions(resolved_formula, buckets)

        # Evaluate remaining arithmetic
        try:
            return float(eval(result))
        except Exception:
            return 0.0

    def _resolve_references(self, formula: str, buckets: Dict[str, float], form_lines: Dict[str, float]) -> str:
        """
        Replace bucket and form line references with their values

        Examples:
            "bucket" → "100.50"
            "line_17" → "350000.00"
        """
        resolved = formula

        # Replace form line references (line_XX format)
        for line_id, value in form_lines.items():
            resolved = resolved.replace(line_id, str(value))

        # Replace bucket references (but not inside function calls)
        # This is tricky - we want to replace standalone bucket names but not those in SUM()
        # For now, we'll handle this in _evaluate_functions

        return resolved

    def _evaluate_functions(self, formula: str, buckets: Dict[str, float]) -> str:
        """
        Evaluate function calls like SUM(bucket1, bucket2)

        Args:
            formula: Formula with function calls
            buckets: Dictionary of bucket values

        Returns:
            Formula with functions replaced by computed values
        """
        result = formula

        # Match function patterns: FUNC(arg1, arg2, ...)
        pattern = r'(\w+)\(([\w\s,]+)\)'

        while True:
            match = re.search(pattern, result)
            if not match:
                break

            func_name = match.group(1)
            args_str = match.group(2)

            # Parse arguments
            args = [arg.strip() for arg in args_str.split(",")]

            # Evaluate function
            if func_name in self.functions:
                func_result = self.functions[func_name](args, buckets)
                result = result.replace(match.group(0), str(func_result))
            else:
                # Unknown function - leave as is
                break

        return result

    def _func_sum(self, args: List[str], buckets: Dict[str, float]) -> float:
        """
        SUM function - sum all specified buckets

        Args:
            args: List of bucket names
            buckets: Dictionary of bucket values

        Returns:
            Sum of all bucket values
        """
        total = 0.0
        for arg in args:
            value = buckets.get(arg, 0.0)
            try:
                total += float(value)
            except (ValueError, TypeError):
                pass
        return total

    def _func_max(self, args: List[str], buckets: Dict[str, float]) -> float:
        """
        MAX function - return maximum value

        Args:
            args: List of bucket names or literal values
            buckets: Dictionary of bucket values

        Returns:
            Maximum value
        """
        values = []
        for arg in args:
            # Try to get from buckets first
            if arg in buckets:
                values.append(float(buckets[arg]))
            else:
                # Try to parse as literal number
                try:
                    values.append(float(arg))
                except ValueError:
                    pass

        return max(values) if values else 0.0

    def _func_min(self, args: List[str], buckets: Dict[str, float]) -> float:
        """
        MIN function - return minimum value

        Args:
            args: List of bucket names or literal values
            buckets: Dictionary of bucket values

        Returns:
            Minimum value
        """
        values = []
        for arg in args:
            # Try to get from buckets first
            if arg in buckets:
                values.append(float(buckets[arg]))
            else:
                # Try to parse as literal number
                try:
                    values.append(float(arg))
                except ValueError:
                    pass

        return min(values) if values else 0.0

    def _func_abs(self, args: List[str], buckets: Dict[str, float]) -> float:
        """
        ABS function - absolute value

        Args:
            args: Single bucket name or value
            buckets: Dictionary of bucket values

        Returns:
            Absolute value
        """
        if not args:
            return 0.0

        arg = args[0]

        # Try to get from buckets first
        if arg in buckets:
            value = buckets[arg]
        else:
            # Try to parse as literal number
            try:
                value = float(arg)
            except ValueError:
                return 0.0

        return abs(float(value))

    def _func_round(self, args: List[str], buckets: Dict[str, float]) -> float:
        """
        ROUND function - round to specified decimal places

        Args:
            args: [value, decimal_places]
            buckets: Dictionary of bucket values

        Returns:
            Rounded value
        """
        if len(args) < 2:
            return 0.0

        value_arg = args[0]
        decimals_arg = args[1]

        # Get value
        if value_arg in buckets:
            value = buckets[value_arg]
        else:
            try:
                value = float(value_arg)
            except ValueError:
                return 0.0

        # Get decimal places
        try:
            decimals = int(decimals_arg)
        except ValueError:
            decimals = 2

        return round(float(value), decimals)

    def evaluate_form_lines(
        self,
        mapping: Dict[str, Any],
        buckets: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Evaluate all form lines using mapping configuration

        Args:
            mapping: Form mapping configuration (from mapping YAML)
            buckets: Computed bucket values

        Returns:
            Dictionary of form line IDs to computed values
        """
        form_lines = {}

        # Get all sections from mapping
        for section_key, section_data in mapping.items():
            if not isinstance(section_data, dict) or "lines" not in section_data:
                continue

            lines = section_data.get("lines", [])

            for line in lines:
                line_id = line.get("line")
                bucket_source = line.get("bucket")
                formula = line.get("formula")

                if not line_id:
                    continue

                # Compute line value
                if bucket_source:
                    # Direct bucket mapping
                    form_lines[f"line_{line_id}"] = buckets.get(bucket_source, 0.0)

                elif formula:
                    # Formula evaluation (may reference other lines)
                    computed_value = self.evaluate(formula, buckets, form_lines)
                    form_lines[f"line_{line_id}"] = computed_value

                else:
                    # No source - default to 0
                    form_lines[f"line_{line_id}"] = 0.0

        return form_lines

    def evaluate_aggregation_rules(
        self,
        rules: List[Dict[str, Any]],
        buckets: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Evaluate aggregation rules (priority 200+) that compute derived buckets

        Args:
            rules: List of rule dictionaries (filtered to aggregation rules)
            buckets: Current bucket values

        Returns:
            Updated buckets dictionary with aggregated values
        """
        for rule in rules:
            priority = rule.get("priority", 0)

            # Skip non-aggregation rules
            if priority < 200:
                continue

            bucket = rule.get("output_bucket")
            formula = rule.get("formula")

            if not bucket or not formula:
                continue

            # Evaluate formula
            computed_value = self.evaluate(formula, buckets)

            # Update bucket
            buckets[bucket] = computed_value

        return buckets
