"""
Metric Calculator Module - Vietnamese Financial Analysis Webapp

Standardized calculation pipeline that follows metric source policy:
- Computed metrics: Calculate from raw financial statements
- Provided metrics: Use pre-computed value from financial_ratios table
- Hybrid metrics: Try computed first, fallback to provided with tolerance check
- Disabled metrics: Not available due to missing data

Author: Core Analysis Team
Version: 1.0.0
Date: 2026-02-16
"""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
import re

from .data_contract import (
    get_value,
    get_value_safe,
    get_value_magnitude,
    get_unit,
    safe_divide,
    safe_sum,
    calculate_free_cash_flow,
    COLUMN_ALIASES,
    UNIT_CONVENTIONS
)

# Module directory for relative path resolution
MODULE_DIR = Path(__file__).parent


class MetricCalculator:
    """
    Standardized metric calculator following source policy.

    Provides unified interface for computing financial metrics with proper:
    - Source policy enforcement (computed vs provided vs hybrid)
    - Column alias resolution via data_contract
    - Input validation
    - Standardized output format with metadata
    - Deterministic year selection

    Usage:
        calculator = MetricCalculator(financial_ratios, balance_sheet, income_statement, cash_flow)

        # Get a metric
        result = calculator.calculate_metric('roe')
        # Returns: {
        #     'metric': 'roe',
        #     'value': 0.21,
        #     'unit': 'decimal',
        #     'as_of_year': 2024,
        #     'status': 'OK',
        #     'source': 'computed',
        #     'inputs_used': ['net_profit=2100', 'equity_total=9767'],
        #     'formula': 'net_profit / equity_total'
        # }
    """

    def __init__(
        self,
        financial_ratios: Dict[str, Any],
        balance_sheet: Dict[str, Any],
        income_statement: Dict[str, Any],
        cash_flow_statement: Dict[str, Any]
    ):
        """
        Initialize metric calculator with financial data.

        Args:
            financial_ratios: Dict from financial_ratios table (flat row format)
            balance_sheet: Dict from balance_sheet table (flat row format)
            income_statement: Dict from income_statement table (flat row format)
            cash_flow_statement: Dict from cash_flow_statement table (flat row format)
        """
        self.financial_ratios = financial_ratios or {}
        self.balance_sheet = balance_sheet or {}
        self.income_statement = income_statement or {}
        self.cash_flow_statement = cash_flow_statement or {}

        # Load metric source policy
        self._load_policy()

        # Determine as_of_year (deterministic - always latest year)
        self.as_of_year = self._determine_year()

    def _load_policy(self):
        """Load metric source policy from YAML file."""
        policy_path = MODULE_DIR / "metric_source_policy.yml"

        try:
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy = yaml.safe_load(f)
                self.computed_metrics = policy.get('computed_metrics', {})
                self.provided_metrics = policy.get('provided_metrics', {})
                self.hybrid_metrics = policy.get('hybrid_metrics', {})
                self.disabled_metrics = policy.get('banking_metrics', {}).copy()
                self.disabled_metrics.update(policy.get('insurance_metrics', {}))
                self.disabled_metrics.update(policy.get('disabled_industry_metrics', {}))
        except Exception as e:
            # Fallback to empty policies if file not found
            self.computed_metrics = {}
            self.provided_metrics = {}
            self.hybrid_metrics = {}
            self.disabled_metrics = {}

    def _determine_year(self) -> Optional[int]:
        """
        Determine the as-of year deterministically.

        Checks all data sources and returns the latest year found.
        Priority: income_statement > balance_sheet > cash_flow_statement > financial_ratios

        Returns:
            Integer year or None if no year found
        """
        sources = [
            self.income_statement,
            self.balance_sheet,
            self.cash_flow_statement,
            self.financial_ratios
        ]

        years = []
        for source in sources:
            year = source.get('year')
            if year is not None:
                try:
                    years.append(int(year))
                except (ValueError, TypeError):
                    pass

        if not years:
            return None

        # Return latest year (deterministic)
        return max(years)

    def calculate_metric(self, metric_name: str) -> Dict[str, Any]:
        """
        Calculate a single metric following source policy.

        Args:
            metric_name: Name of metric to calculate

        Returns:
            Standardized result dict with metadata
        """
        # Check if metric is disabled
        if metric_name in self.disabled_metrics:
            return self._format_result(
                metric_name=metric_name,
                value=None,
                status='DISABLED',
                source=None,
                inputs_used=[],
                formula=None,
                reason=self.disabled_metrics[metric_name].get('reason', 'Not available')
            )

        # Check if metric is computed
        if metric_name in self.computed_metrics:
            return self._compute_metric(metric_name, self.computed_metrics[metric_name])

        # Check if metric is provided
        if metric_name in self.provided_metrics:
            return self._provide_metric(metric_name, self.provided_metrics[metric_name])

        # Check if metric is hybrid
        if metric_name in self.hybrid_metrics:
            return self._compute_hybrid_metric(metric_name, self.hybrid_metrics[metric_name])

        # Metric not found in policy
        return self._format_result(
            metric_name=metric_name,
            value=None,
            status='MISSING_INPUT',
            source=None,
            inputs_used=[],
            formula=None,
            reason='Metric not defined in source policy'
        )

    def _compute_metric(self, metric_name: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute a metric from raw financial statements.

        Args:
            metric_name: Name of metric
            policy: Metric policy definition

        Returns:
            Standardized result dict
        """
        formula = policy.get('formula', '')
        required_inputs = policy.get('required_inputs', [])
        validity_rules = policy.get('validity_rules', [])

        # Extract inputs using data_contract for alias resolution
        inputs = self._extract_inputs(required_inputs)

        # Check if all required inputs are available
        missing_inputs = [inp for inp, val in inputs.items() if val is None]
        if missing_inputs:
            return self._format_result(
                metric_name=metric_name,
                value=None,
                status='MISSING_INPUT',
                source='computed',
                inputs_used=[f'{k}={v}' for k, v in inputs.items() if v is not None],
                formula=formula,
                reason=f'Missing required inputs: {", ".join(missing_inputs)}'
            )

        # Validate input-based rules before computation (e.g., denominator > 0)
        context = self._build_rule_context(inputs)
        ok, fail_reason = self._validate_validity_rules(validity_rules, context, strict_missing=True)
        if not ok:
            return self._format_result(
                metric_name=metric_name,
                value=None,
                status='INVALID',
                source='computed',
                inputs_used=[f'{k}={v}' for k, v in inputs.items()],
                formula=formula,
                reason=fail_reason or 'Input failed validation rules'
            )

        # Compute using formula
        try:
            value = self._apply_formula(formula, inputs)
        except Exception as e:
            return self._format_result(
                metric_name=metric_name,
                value=None,
                status='ERROR',
                source='computed',
                inputs_used=[f'{k}={v}' for k, v in inputs.items()],
                formula=formula,
                reason=f'Computation error: {str(e)}'
            )

        if value is None:
            return self._format_result(
                metric_name=metric_name,
                value=value,
                status='ERROR',
                source='computed',
                inputs_used=[f'{k}={v}' for k, v in inputs.items()],
                formula=formula,
                reason='Computation returned null (likely division by zero or invalid expression)'
            )

        return self._format_result(
            metric_name=metric_name,
            value=value,
            status='OK',
            source='computed',
            inputs_used=[f'{k}={v}' for k, v in inputs.items()],
            formula=formula
        )

    def _provide_metric(self, metric_name: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide a metric from financial_ratios table.

        Args:
            metric_name: Name of metric
            policy: Metric policy definition

        Returns:
            Standardized result dict
        """
        required_inputs = policy.get('required_inputs', [])
        validity_rules = policy.get('validity_rules', [])

        # Get value from financial_ratios using data_contract
        if not required_inputs:
            return self._format_result(
                metric_name=metric_name,
                value=None,
                status='MISSING_INPUT',
                source='provided',
                inputs_used=[],
                formula=None,
                reason='No DB column specified in policy'
            )

        # Use first required input as DB column name
        db_column = required_inputs[0].split('.')[-1]
        value = get_value(self.financial_ratios, db_column, default=None)

        if value is None:
            return self._format_result(
                metric_name=metric_name,
                value=None,
                status='MISSING_INPUT',
                source='provided',
                inputs_used=[],
                formula=None,
                reason=f'Value not found in financial_ratios.{db_column}'
            )

        # Validate input-based rules (evaluated against available financial_ratios fields)
        context = self._build_rule_context()
        context[db_column] = value
        ok, fail_reason = self._validate_validity_rules(validity_rules, context, strict_missing=True)
        if not ok:
            return self._format_result(
                metric_name=metric_name,
                value=value,
                status='INVALID',
                source='provided',
                inputs_used=[f'{db_column}={value}'],
                formula=None,
                reason=fail_reason or 'Value failed validation rules'
            )

        return self._format_result(
            metric_name=metric_name,
            value=value,
            status='OK',
            source='provided',
            inputs_used=[f'{db_column}={value}'],
            formula=None
        )

    def _compute_hybrid_metric(self, metric_name: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute hybrid metric: try computed first, fallback to provided.

        Args:
            metric_name: Name of metric
            policy: Metric policy definition

        Returns:
            Standardized result dict
        """
        formula = policy.get('formula', '')
        required_inputs = policy.get('required_inputs', [])
        fallback = policy.get('fallback', {})
        validity_rules = policy.get('validity_rules', [])

        # Try computed first
        inputs = self._extract_inputs(required_inputs)

        # Check if we can compute
        missing_inputs = [inp for inp, val in inputs.items() if val is None]
        can_compute = len(missing_inputs) == 0

        computed_value = None
        if can_compute:
            # Validate input-based rules for computed path (strict)
            context = self._build_rule_context(inputs)
            ok, _ = self._validate_validity_rules(validity_rules, context, strict_missing=True)
            if not ok:
                can_compute = False
        if can_compute:
            try:
                computed_value = self._apply_formula(formula, inputs)
            except Exception:
                can_compute = False

        # Use computed value if available
        if can_compute and computed_value is not None:
            # Check if fallback exists and tolerance needs to be checked
            fallback_source = fallback.get('source', '')
            tolerance = fallback.get('tolerance')

            if fallback_source and tolerance is not None:
                # Get provided value for comparison
                db_column = fallback_source.split('.')[-1]
                provided_value = get_value(self.financial_ratios, db_column, default=None)

                if provided_value is not None:
                    # Check tolerance
                    diff = abs(computed_value - provided_value)
                    if diff > tolerance:
                        # Outside tolerance - flag but use computed
                        return self._format_result(
                            metric_name=metric_name,
                            value=computed_value,
                            status='OK',
                            source='hybrid',
                            inputs_used=[f'{k}={v}' for k, v in inputs.items()],
                            formula=formula,
                            warning=f'Computed differs from provided by {diff:.4f} (tolerance: {tolerance})'
                        )

            # Computed value is OK
            return self._format_result(
                metric_name=metric_name,
                value=computed_value,
                status='OK',
                source='hybrid',
                inputs_used=[f'{k}={v}' for k, v in inputs.items()],
                formula=formula
            )

        # Fallback to provided
        fallback_source = fallback.get('source', '')
        if not fallback_source:
            return self._format_result(
                metric_name=metric_name,
                value=None,
                status='MISSING_INPUT',
                source='hybrid',
                inputs_used=[f'{k}={v}' for k, v in inputs.items() if v is not None],
                formula=formula,
                reason='Cannot compute and no fallback specified'
            )

        db_column = fallback_source.split('.')[-1]
        provided_value = get_value(self.financial_ratios, db_column, default=None)

        if provided_value is None:
            return self._format_result(
                metric_name=metric_name,
                value=None,
                status='MISSING_INPUT',
                source='hybrid',
                inputs_used=[f'{k}={v}' for k, v in inputs.items() if v is not None],
                formula=formula,
                reason=f'Computed failed and fallback value not found in financial_ratios.{db_column}'
            )

        # Validate provided value against validity rules when possible.
        # For hybrid fallback we allow missing-rule inputs (lenient) so that provided
        # ratios can still be used even when statement inputs are unavailable.
        context = self._build_rule_context()
        context[db_column] = provided_value
        ok, fail_reason = self._validate_validity_rules(validity_rules, context, strict_missing=False)
        if not ok:
            return self._format_result(
                metric_name=metric_name,
                value=provided_value,
                status='INVALID',
                source='hybrid',
                inputs_used=[f'{db_column}={provided_value}'],
                formula=None,
                reason=fail_reason or 'Fallback value failed validation rules'
            )

        return self._format_result(
            metric_name=metric_name,
            value=provided_value,
            status='OK',
            source='hybrid',
            inputs_used=[f'{db_column}={provided_value}'],
            formula=None,
            note='Using provided fallback'
        )

    def _extract_inputs(self, required_inputs: List[str]) -> Dict[str, Optional[float]]:
        """
        Extract input values from financial statements.

        Handles table.column format and column alias resolution.

        Args:
            required_inputs: List of required inputs in format 'table.column'

        Returns:
            Dict mapping input names to values
        """
        inputs = {}

        for input_spec in required_inputs:
            # Parse table.column
            parts = input_spec.split('.')
            if len(parts) != 2:
                continue

            table, column = parts

            # Get value from appropriate table using data_contract
            if table == 'income_statement':
                value = get_value_magnitude(self.income_statement, column, default=None)
            elif table == 'balance_sheet':
                value = get_value(self.balance_sheet, column, default=None)
            elif table == 'cash_flow_statement':
                value = get_value(self.cash_flow_statement, column, default=None)
            elif table == 'financial_ratios':
                value = get_value(self.financial_ratios, column, default=None)
            else:
                value = None

            inputs[column] = value

        return inputs

    def _apply_formula(self, formula: str, inputs: Dict[str, Optional[float]]) -> Optional[float]:
        """
        Apply formula to input values.

        Supports basic arithmetic operations: +, -, *, /, ()

        Args:
            formula: Formula string (e.g., 'net_profit / equity_total')
            inputs: Dict of input values

        Returns:
            Computed value or None if calculation fails
        """
        # Evaluate expression safely (only allow whitelisted names)
        safe_locals: Dict[str, Any] = {"abs": abs}
        for key, value in inputs.items():
            if value is None:
                return None
            safe_locals[key] = float(value)

        try:
            result = eval(formula, {"__builtins__": {}}, safe_locals)
            return float(result) if result is not None else None
        except (ZeroDivisionError, ValueError, TypeError, SyntaxError, NameError):
            return None

    def _build_rule_context(self, inputs: Optional[Dict[str, Optional[float]]] = None) -> Dict[str, Any]:
        """
        Build evaluation context for validity rules.

        - Includes only keys with non-null values (so missing values raise NameError)
        - Coerces numeric-like values to float for comparisons
        """
        context: Dict[str, Any] = {}

        for source in (self.financial_ratios, self.balance_sheet, self.income_statement, self.cash_flow_statement):
            for key, value in (source or {}).items():
                if value is None:
                    continue
                try:
                    context[key] = float(value)
                except (TypeError, ValueError):
                    context[key] = value

        for key, value in (inputs or {}).items():
            if value is None:
                continue
            context[key] = float(value)

        return context

    def _validate_validity_rules(
        self,
        validity_rules: List[str],
        context: Dict[str, Any],
        strict_missing: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate metric using input-based validity rules from policy.

        Rules are Python-like expressions (e.g., "revenue > 0", "roic is not null").

        Args:
            validity_rules: List of rule strings
            context: Evaluation context containing available variables
            strict_missing: If True, missing variables fail validation; if False, missing-variable
                            rules are skipped (useful for hybrid fallback paths).

        Returns:
            (ok, reason_if_failed)
        """
        for rule in validity_rules or []:
            raw = (rule or "").strip()
            if not raw:
                continue

            expr = raw
            expr = re.sub(r"\\bis not null\\b", "is not None", expr, flags=re.IGNORECASE)
            expr = re.sub(r"\\bis null\\b", "is None", expr, flags=re.IGNORECASE)

            try:
                ok = bool(eval(expr, {"__builtins__": {}}, context))
            except NameError:
                if strict_missing:
                    return False, f"Missing inputs for validity rule: {raw}"
                continue
            except Exception:
                return False, f"Failed validity rule: {raw}"

            if not ok:
                return False, f"Failed validity rule: {raw}"

        return True, None

    def _format_result(
        self,
        metric_name: str,
        value: Optional[float],
        status: str,
        source: Optional[str],
        inputs_used: List[str],
        formula: Optional[str],
        reason: Optional[str] = None,
        warning: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format result in standardized output format.

        Args:
            metric_name: Name of metric
            value: Computed or provided value
            status: Status code (OK, MISSING_INPUT, INVALID, DISABLED, ERROR)
            source: Source type (computed, provided, hybrid)
            inputs_used: List of inputs used
            formula: Formula applied (if computed)
            reason: Reason for status (if not OK)
            warning: Warning message
            note: Additional note

        Returns:
            Standardized result dict
        """
        # Get unit from data_contract
        unit = get_unit(metric_name)

        result = {
            'metric': metric_name,
            'value': value,
            'unit': unit,
            'as_of_year': self.as_of_year,
            'status': status,
            'source': source,
            'inputs_used': inputs_used,
            'formula': formula
        }

        # Add optional fields
        if reason:
            result['reason'] = reason
        if warning:
            result['warning'] = warning
        if note:
            result['note'] = note

        return result

    def calculate_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate all metrics defined in source policy.

        Returns:
            Dict mapping metric names to result dicts
        """
        results = {}

        # Calculate all computed metrics
        for metric_name in self.computed_metrics.keys():
            results[metric_name] = self.calculate_metric(metric_name)

        # Get all provided metrics
        for metric_name in self.provided_metrics.keys():
            results[metric_name] = self.calculate_metric(metric_name)

        # Calculate all hybrid metrics
        for metric_name in self.hybrid_metrics.keys():
            results[metric_name] = self.calculate_metric(metric_name)

        # Mark disabled metrics
        for metric_name in self.disabled_metrics.keys():
            results[metric_name] = self.calculate_metric(metric_name)

        return results

    def get_metric_summary(self) -> Dict[str, Any]:
        """
        Get summary of all available metrics.

        Returns:
            Summary dict with counts and availability
        """
        all_results = self.calculate_all_metrics()

        available = {k: v for k, v in all_results.items() if v['status'] == 'OK'}
        missing = {k: v for k, v in all_results.items() if v['status'] == 'MISSING_INPUT'}
        invalid = {k: v for k, v in all_results.items() if v['status'] == 'INVALID'}
        disabled = {k: v for k, v in all_results.items() if v['status'] == 'DISABLED'}

        return {
            'total_metrics': len(all_results),
            'available_count': len(available),
            'missing_count': len(missing),
            'invalid_count': len(invalid),
            'disabled_count': len(disabled),
            'available_metrics': list(available.keys()),
            'missing_metrics': list(missing.keys()),
            'invalid_metrics': list(invalid.keys()),
            'disabled_metrics': list(disabled.keys()),
            'as_of_year': self.as_of_year
        }


# Convenience functions for direct usage
def calculate_metric(
    metric_name: str,
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    cash_flow_statement: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate a single metric with standardized output.

    Args:
        metric_name: Name of metric to calculate
        financial_ratios: Dict from financial_ratios table
        balance_sheet: Dict from balance_sheet table
        income_statement: Dict from income_statement table
        cash_flow_statement: Dict from cash_flow_statement table

    Returns:
        Standardized result dict
    """
    calculator = MetricCalculator(financial_ratios, balance_sheet, income_statement, cash_flow_statement)
    return calculator.calculate_metric(metric_name)


def calculate_all_metrics(
    financial_ratios: Dict[str, Any],
    balance_sheet: Dict[str, Any],
    income_statement: Dict[str, Any],
    cash_flow_statement: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate all metrics with standardized output.

    Args:
        financial_ratios: Dict from financial_ratios table
        balance_sheet: Dict from balance_sheet table
        income_statement: Dict from income_statement table
        cash_flow_statement: Dict from cash_flow_statement table

    Returns:
        Dict mapping metric names to result dicts
    """
    calculator = MetricCalculator(financial_ratios, balance_sheet, income_statement, cash_flow_statement)
    return calculator.calculate_all_metrics()


if __name__ == "__main__":
    # Example usage
    financial_ratios = {
        'year': 2024,
        'roe': 0.21,
        'roa': 0.12,
        'price_to_earnings': 15.5
    }

    balance_sheet = {
        'year': 2024,
        'liabilities_total': 400000000000,
        'liabilities_current': 200000000000,
        'equity_total': 600000000000,
        'assets_current': 300000000000
    }

    income_statement = {
        'year': 2024,
        'net_profit': 126000000000,
        'revenue': 500000000000,
        'gross_profit': 200000000000
    }

    cash_flow_statement = {
        'year': 2024,
        'net_cash_from_operating_activities': 150000000000,
        'purchase_purchase_fixed_assets': -50000000000
    }

    # Calculate specific metric
    result = calculate_metric('roe', financial_ratios, balance_sheet, income_statement, cash_flow_statement)
    print(f"ROE Result: {result}")

    # Calculate all metrics
    calculator = MetricCalculator(financial_ratios, balance_sheet, income_statement, cash_flow_statement)
    summary = calculator.get_metric_summary()
    print(f"\nMetric Summary:")
    print(f"  Total: {summary['total_metrics']}")
    print(f"  Available: {summary['available_count']}")
    print(f"  Missing: {summary['missing_count']}")
    print(f"  Disabled: {summary['disabled_count']}")
