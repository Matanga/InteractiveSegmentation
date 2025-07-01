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

from .core import GrammarError, GroupKind, Pattern, parse

__all__ = [
    "Severity",
    "ValidationIssue",
    "validate",
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
# Rule helpers
# ---------------------------------------------------------------------------

def _rule_at_least_one_fill(pattern: Pattern) -> List[ValidationIssue]:
    if any(g.kind is GroupKind.FILL for fl in pattern.floors for g in fl):
        return []
    return [
        ValidationIssue(
            line=-1,
            message="Pattern should contain at least one <fill> group",  # noqa: E501
            severity=Severity.WARNING,
        )
    ]


_RULES: List[Callable[[Pattern], List[ValidationIssue]]] = [
    _rule_at_least_one_fill,
]


# ---------------------------------------------------------------------------
# Public façade
# ---------------------------------------------------------------------------

def validate_pattern(pattern: Pattern) -> List[ValidationIssue]:
    """Run semantic checks on an already‑parsed :class:`Pattern`."""
    issues: List[ValidationIssue] = []
    for rule in _RULES:
        issues.extend(rule(pattern))
    return issues


def validate(pattern_str: str) -> List[ValidationIssue]:
    """Parse str and return semantic issues (syntax errors wrapped as ERROR)."""
    try:
        pattern = parse(pattern_str)
    except GrammarError as exc:
        return [ValidationIssue(line=-1, message=str(exc), severity=Severity.ERROR)]
    return validate_pattern(pattern)
