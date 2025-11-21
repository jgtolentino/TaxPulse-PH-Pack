"""
TaxPulse Rules Engine - JSONLogic evaluation with formula computation
Pattern: PayrollEngine's rules DSL + OpenTaxSolver's per-form approach
"""

from .evaluator import RulesEvaluator
from .formula import FormulaEngine
from .loader import RulesLoader

__all__ = ["RulesEvaluator", "FormulaEngine", "RulesLoader"]
