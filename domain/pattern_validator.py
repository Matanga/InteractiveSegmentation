"""building_grammar.validator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Initial semantic‑level checks (PRD F‑05).

*Only* rule implemented (v0.1): warn if pattern lacks any `<fill>` group.
Extend `_RULES` list with more functions as requirements emerge.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List

from domain.grammar import GroupKind, Pattern, Floor

__all__ = [
    "Severity",
    "ValidationIssue",
    "validate_pattern",
]


class Severity(Enum):
    """Issue criticality level."""

    ERROR = auto()
    WARNING = auto()

    def __str__(self) -> str:  # noqa: DunderStr
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Single semantic problem detected in a pattern."""

    line: int  # 0‑based, ground=-1 when global
    message: str
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:  # noqa: DunderStr
        return f"[{self.severity}] line {self.line}: {self.message}"

# ---------------------------------------------------------------------------
# Rule Definitions
# ---------------------------------------------------------------------------

def _rule_at_least_one_fill(pattern: Pattern) -> List[ValidationIssue]:
    """
    Checks if the entire building pattern contains at least one <fill> group
    across any facade on any floor.
    """
    # We now need to iterate through the new multi-facade structure.
    for floor in pattern.floors:
        for facade_groups in floor.facades.values():
            for group in facade_groups:
                if group.kind is GroupKind.FILL:
                    return []  # Found one, rule passes.

    # If we finish all loops without finding a fill group, the rule fails.
    return [
        ValidationIssue(
            line=-1,  # This is a global issue, not tied to a specific floor.
            message="Pattern should contain at least one <fill> group",
            severity=Severity.WARNING,
        )
    ]


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

# The list of rules to apply. Add new rule functions here in the future.
_RULES: List[Callable[[Pattern], List[ValidationIssue]]] = [
    _rule_at_least_one_fill,
]

# ---------------------------------------------------------------------------
# Public façade
# ---------------------------------------------------------------------------

def validate_pattern(pattern: Pattern) -> List[ValidationIssue]:
    """
    The main entry point for validation.
    Runs all semantic checks on an already-parsed Pattern object.
    """
    issues: List[ValidationIssue] = []
    for rule in _RULES:
        issues.extend(rule(pattern))
    return issues

# ---------------------------------------------------------------------------
# Removed
# ---------------------------------------------------------------------------

def validate(pattern_str: str) -> List[ValidationIssue]:
    """Parse str and return semantic issues (syntax errors wrapped as ERROR)."""
    try:
        pattern = parse(pattern_str)
    except GrammarError as exc:
        return [ValidationIssue(line=-1, message=str(exc), severity=Severity.ERROR)]
    return validate_pattern(pattern)
