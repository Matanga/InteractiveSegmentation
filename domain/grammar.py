"""building_grammar.core
~~~~~~~~~~~~~~~~~~~~~
Core domain model, parser and validator for the Interactive Building Grammar – Pattern Editor (IBG‑PE).
This module is *framework‑agnostic*

Exports
-------
- `Module` – atomic façade element
- `GroupKind` – *fill* vs *rigid*
- `Group` – one or more modules with metadata
- `Pattern` – multi‑floor façade pattern
- `parse` / `validate` – public API for converting strings ➜ objects and validation only

Example
~~~~~~~
```python
from building_grammar.core import parse
p = parse("<A-B>[C]2\n<D>")
print(p.to_string())  # canonical serialisation
<A-B>[C]2\n<D>
```

The *ground floor* is the **last** line, matching the PRD spec (§Scope).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Sequence

__all__ = [
    "GrammarError",
    "GroupKind",
    "Module",
    "Group",
    "Pattern",
    "parse",
    "validate",
    "parse_pattern",
    "validate_pattern",
    "REPEATABLE",
    "RIGID"
]


REPEATABLE = "Repeatable"
RIGID = "Rigid"


class GrammarError(ValueError):
    """Raised when a pattern string violates Houdini façade‑grammar rules."""


class GroupKind(str, Enum):
    """Group flavour as defined by Houdini façade grammar."""

    FILL = "fill"
    RIGID = "Rigid"

    def __str__(self) -> str:  # noqa: DunderStr
        return self.value


@dataclass(frozen=True, slots=True)
class Module:
    """Atomic façade element with a *unique* name (icon id)."""

    name: str

    def __post_init__(self) -> None:  # noqa: D401
        if not self.name:
            raise GrammarError("Module name cannot be empty")
        if any(ch in self.name for ch in "<>[]-\n\r\t"):
            raise GrammarError(f"Invalid character in module name: '{self.name}'")

    # Convenience aliases ---------------------------------------------------
    def __str__(self) -> str:  # noqa: DunderStr
        return self.name


@dataclass
class Group:
    """Consecutive sequence of :class:`Module` instances.

    Args
    ----
    kind
        Whether the group is *fill* ( <…> ) or *rigid* ( […]n ).
    modules
        Ordered collection of modules in this group.
    repeat
        For *rigid* groups the exact repeat count (≥1). Must be *None* for *fill* groups.
    """

    kind: GroupKind
    modules: List[Module]
    repeat: int | None = None

    def __post_init__(self) -> None:  # noqa: D401
        if not self.modules:
            raise GrammarError("Group must contain at least one module")
        if self.kind is GroupKind.FILL and self.repeat is not None:
            raise GrammarError("Fill group cannot specify repeat count")
        if self.kind is GroupKind.RIGID:
            if self.repeat is None:
                self.repeat = 1
            if self.repeat < 1:
                raise GrammarError("Repeat count must be ≥ 1 for rigid groups")

    # Serialisation ---------------------------------------------------------
    def to_string(self) -> str:
        inner = "-".join(m.name for m in self.modules)
        if self.kind is GroupKind.FILL:
            return f"<{inner}>"
        suffix = "" if self.repeat == 1 else str(self.repeat)
        return f"[{inner}]{suffix}"

    # Convenience -----------------------------------------------------------
    def __str__(self) -> str:  # noqa: DunderStr
        return self.to_string()


@dataclass
class Pattern:
    """Entire multi‑floor façade pattern.

    The *ground floor* is conventionally the **last** line in the string
    representation – aligning with Houdini conventions (PRD §Scope).
    """

    floors: List[List[Group]] = field(default_factory=list)

    # Serialisation ---------------------------------------------------------
    def to_string(self) -> str:
        """Canonical grammar string (no extraneous whitespace)."""
        return "\n".join("-".join(g.to_string() for g in floor) for floor in self.floors)

    # Convenience -----------------------------------------------------------
    def __str__(self) -> str:  # noqa: DunderStr
        return self.to_string()

    def __len__(self) -> int:  # noqa: DunderLen
        return len(self.floors)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_GROUP_RE = re.compile(
    r"""
    (?P<fill><(?P<fill_inner>[^>]+)>)      # <fill>
  | (?P<rigid>\[(?P<rigid_inner>[^\]]+)\]  # [rigid]
      (?P<count>\d*))                      # optional count
    """,
    re.VERBOSE,
)

def parse_pattern(pattern_str: str) -> Pattern:
    """Alias: clearer name for external callers."""
    return parse(pattern_str)

def validate_pattern(pattern_str: str) -> None:
    """Alias: clearer name for external callers."""
    return validate(pattern_str)

def _parse_group(token: str) -> Group:
    """Transform raw *token* into a validated :class:`Group`."""
    m = _GROUP_RE.fullmatch(token)
    if not m:
        raise GrammarError(f"Malformed group token: '{token}'")

    if m.group("fill"):
        inner = m.group("fill_inner")
        modules = [Module(name.strip()) for name in inner.split("-")]
        return Group(kind=GroupKind.FILL, modules=modules)

    # Rigid
    inner = m.group("rigid_inner")
    count = int(m.group("count") or "1")
    modules = [Module(name.strip()) for name in inner.split("-")]
    return Group(kind=GroupKind.RIGID, modules=modules, repeat=count)

def _split_line(line: str) -> Sequence[str]:
    """Return the sequence of <fill> / [rigid]n groups exactly as they appear.

    Raises GrammarError if *any* stray character is found between groups.
    """
    tokens = [m.group(0) for m in _GROUP_RE.finditer(line)]
    if "".join(tokens) != line.replace(" ", ""):   # guard against garbage
        raise GrammarError(f"Unexpected characters outside groups: '{line}'")
    return tokens

def parse_line(line: str) -> List[Group]:
    """Parse a *single floor* pattern line."""
    tokens = _split_line(line.strip())
    return [_parse_group(tok.strip()) for tok in tokens]

def parse(pattern_str: str) -> Pattern:
    """Parse full *pattern_str* into :class:`Pattern`.

    Raises
    ------
    GrammarError
        If *pattern_str* contains any syntax or semantic error.
    """
    lines = [ln for ln in (pattern_str or "").strip().splitlines() if ln.strip()]
    if not lines:
        raise GrammarError("Pattern string is empty")

    floors = [parse_line(ln) for ln in lines]
    return Pattern(floors=floors)

def validate(pattern_str: str) -> None:
    """Validate *pattern_str* by attempting to parse it."""
    parse(pattern_str)
