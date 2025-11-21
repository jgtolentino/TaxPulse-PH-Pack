"""
Rules Loader - Load tax rules from YAML files
"""

import os
import yaml
from typing import Dict, List, Any
from pathlib import Path


class RulesLoader:
    """Load and parse tax rules from YAML configuration files"""

    def __init__(self, pack_path: str):
        """
        Initialize rules loader

        Args:
            pack_path: Path to tax pack directory (e.g., 'packs/ph/')
        """
        self.pack_path = Path(pack_path)
        self.rules_dir = self.pack_path / "rules"
        self.rates_dir = self.pack_path / "rates"
        self.mappings_dir = self.pack_path / "mappings"
        self.validations_dir = self.pack_path / "validations"
        self.forms_dir = self.pack_path / "forms"

        # Cached data
        self._rules_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._rates_cache: Dict[str, Dict[str, Any]] = {}
        self._mappings_cache: Dict[str, Dict[str, Any]] = {}
        self._validations_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._forms_cache: Dict[str, Dict[str, Any]] = {}

    def load_rules(self, rule_file: str) -> List[Dict[str, Any]]:
        """
        Load tax rules from YAML file

        Args:
            rule_file: Rule file name (e.g., 'vat.rules.yaml')

        Returns:
            List of rule dictionaries
        """
        if rule_file in self._rules_cache:
            return self._rules_cache[rule_file]

        file_path = self.rules_dir / rule_file

        if not file_path.exists():
            raise FileNotFoundError(f"Rule file not found: {file_path}")

        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])

        # Sort rules by priority (higher priority first)
        rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

        self._rules_cache[rule_file] = rules
        return rules

    def load_all_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load all rule files from rules directory

        Returns:
            Dictionary mapping rule file names to rule lists
        """
        all_rules = {}

        if not self.rules_dir.exists():
            return all_rules

        for rule_file in self.rules_dir.glob("*.rules.yaml"):
            rule_name = rule_file.name
            all_rules[rule_name] = self.load_rules(rule_name)

        return all_rules

    def load_rates(self, rates_file: str) -> Dict[str, Any]:
        """
        Load tax rates from JSON file

        Args:
            rates_file: Rates file name (e.g., 'ph_rates_2025.json')

        Returns:
            Dictionary of rate data
        """
        if rates_file in self._rates_cache:
            return self._rates_cache[rates_file]

        file_path = self.rates_dir / rates_file

        if not file_path.exists():
            raise FileNotFoundError(f"Rates file not found: {file_path}")

        import json
        with open(file_path, "r") as f:
            rates = json.load(f)

        self._rates_cache[rates_file] = rates
        return rates

    def load_mapping(self, mapping_file: str) -> Dict[str, Any]:
        """
        Load form mapping from YAML file

        Args:
            mapping_file: Mapping file name (e.g., 'vat_2550Q.mapping.yaml')

        Returns:
            Dictionary of mapping data
        """
        if mapping_file in self._mappings_cache:
            return self._mappings_cache[mapping_file]

        file_path = self.mappings_dir / mapping_file

        if not file_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {file_path}")

        with open(file_path, "r") as f:
            mapping = yaml.safe_load(f)

        self._mappings_cache[mapping_file] = mapping
        return mapping

    def load_validations(self, validation_file: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load validation rules from YAML file

        Args:
            validation_file: Validation file name (e.g., 'core_validations.yaml')

        Returns:
            Dictionary with 'transaction' and 'aggregate' validation lists
        """
        if validation_file in self._validations_cache:
            return self._validations_cache[validation_file]

        file_path = self.validations_dir / validation_file

        if not file_path.exists():
            raise FileNotFoundError(f"Validation file not found: {file_path}")

        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        validations = data.get("validations", {})

        self._validations_cache[validation_file] = validations
        return validations

    def load_form(self, form_file: str) -> Dict[str, Any]:
        """
        Load form definition from YAML file

        Args:
            form_file: Form file name (e.g., 'bir_2550Q_2025.form.yaml')

        Returns:
            Dictionary of form data
        """
        if form_file in self._forms_cache:
            return self._forms_cache[form_file]

        file_path = self.forms_dir / form_file

        if not file_path.exists():
            raise FileNotFoundError(f"Form file not found: {file_path}")

        with open(file_path, "r") as f:
            form = yaml.safe_load(f)

        self._forms_cache[form_file] = form
        return form

    def get_rate_value(self, rate_code: str, rates_data: Dict[str, Any]) -> float:
        """
        Extract rate value from rates data by code

        Args:
            rate_code: Rate code (e.g., 'W010', 'VAT_12_SALES')
            rates_data: Loaded rates dictionary

        Returns:
            Rate value as decimal (e.g., 0.10 for 10%)
        """
        # Check VAT rates
        if rate_code.startswith("VAT"):
            vat_data = rates_data.get("vat", {})
            if rate_code == "VAT_12_SALES" or rate_code == "VAT_12_PURCHASE":
                return vat_data.get("standard_rate", 0.12)
            elif rate_code == "VAT_ZERO_EXPORTS" or rate_code == "VAT_ZERO_PURCHASE":
                return vat_data.get("zero_rated_exports", 0.00)

        # Check EWT rates
        ewt_data = rates_data.get("expanded_withholding_tax", {})
        if rate_code in ewt_data:
            return ewt_data[rate_code].get("rate", 0.0)

        # Check FWT rates
        fwt_data = rates_data.get("final_withholding_tax", {})
        if rate_code in fwt_data:
            return fwt_data[rate_code].get("rate", 0.0)

        # Default: return 0.0 if not found
        return 0.0

    def clear_cache(self):
        """Clear all cached data"""
        self._rules_cache.clear()
        self._rates_cache.clear()
        self._mappings_cache.clear()
        self._validations_cache.clear()
        self._forms_cache.clear()
