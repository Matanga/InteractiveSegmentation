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
from typing import List, Sequence, Dict, Any

__all__ = [
    "GrammarError",
    "GroupKind",
    "Module",
    "Group",
    "Floor",  # NEW
    "Pattern",
    "parse_building_json",  # NEW (replaces old 'parse')
    "parse_facade_string",  # NEW (repurposed from old 'parse_line')
    "REPEATABLE",
    "RIGID",
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
class Floor:
    """Represents a single floor with its metadata and four facades."""
    name: str
    height: int
    # Facades are stored in a dictionary, keyed by "front", "left", etc.
    facades: Dict[str, List[Group]] = field(default_factory=dict)


@dataclass
class Pattern:
    """Represents the entire multi-floor, multi-facade building structure."""
    # A Pattern is now a list of the new Floor objects.
    floors: List[Floor] = field(default_factory=list)

    def __len__(self) -> int:
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

def parse_facade_string(facade_str: str) -> List[Group]:
    """
    Parses a single facade pattern string (e.g., '<A>[B]2') into a list of Groups.
    This replaces the old 'parse_line' functionality.
    """
    line = facade_str.strip()
    if not line:
        return []  # An empty facade string is valid and results in an empty list.

    tokens = [m.group(0) for m in _GROUP_RE.finditer(line)]
    if "".join(tokens) != line.replace(" ", ""):
        raise GrammarError(f"Unexpected characters outside groups: '{line}'")

    return [_parse_group(tok.strip()) for tok in tokens]

def parse_building_json(building_data: List[Dict[str, Any]]) -> Pattern:
    """
    The new main parser. It takes a Python data structure (from JSON) and
    builds the complete, validated Pattern object.
    """
    if not isinstance(building_data, list):
        raise GrammarError("Building data must be a list of floor objects.")

    pattern = Pattern()
    facade_order = ["front", "left", "back", "right"]

    for i, floor_dict in enumerate(building_data):
        if not isinstance(floor_dict, dict):
            raise GrammarError(f"Floor {i} data is not a valid object.")

        name = floor_dict.get("Name")
        height = floor_dict.get("Height")
        pattern_array = floor_dict.get("Pattern", [])

        if name is None or height is None:
            raise GrammarError(f"Floor {i} is missing 'Name' or 'Height'.")

        if not isinstance(pattern_array, list) or len(pattern_array) != 4:
            raise GrammarError(
                f"Floor '{name}' must have a 'Pattern' array with exactly 4 strings."
            )

        new_floor = Floor(name=str(name), height=int(height))

        for idx, facade_key in enumerate(facade_order):
            facade_pattern_string = pattern_array[idx]
            # Parse each facade string individually
            new_floor.facades[facade_key] = parse_facade_string(facade_pattern_string)

        pattern.floors.append(new_floor)

    return pattern

# ---------------------------------------------------------------------------
# Removed?
# ---------------------------------------------------------------------------


def parse_pattern(pattern_str: str) -> Pattern:
    """Alias: clearer name for external callers."""
    return parse(pattern_str)

def validate_pattern(pattern_str: str) -> None:
    """Alias: clearer name for external callers."""
    return validate(pattern_str)

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


# ──────────────────────────────────────────────────────────────
# Text cleanup helpers moved from services/facade_segmentation
# ──────────────────────────────────────────────────────────────

_RE_BAD_CHARS = re.compile(r"[^A-Za-z0-9><\[\]\-\s]+")
_RE_GROUPS = re.compile(r"([<\[])(.*?)([>\]])", re.S)
_RE_OK_TOKEN = re.compile(r"[A-Za-z]+[0-9]+$")
_RE_NAME_ONLY = re.compile(r"[A-Za-z]+$")

def fix_facade_expression(expr: str) -> str:
    expr = _RE_BAD_CHARS.sub("", expr)

    def _fix_group(m: re.Match) -> str:
        open_bracket, body, close_bracket = m.groups()
        tokens = [tok.strip() for tok in body.split("-") if tok.strip()]
        fixed = []
        for tok in tokens:
            if _RE_OK_TOKEN.fullmatch(tok):
                fixed.append(tok)
            elif _RE_NAME_ONLY.fullmatch(tok):
                fixed.append(f"{tok}00")
        return f"{open_bracket}{'-'.join(fixed)}{close_bracket}" if fixed else ""

    expr = _RE_GROUPS.sub(_fix_group, expr)
    cleaned_lines = []
    for line in expr.splitlines():
        groups = re.findall(r"(?:<[^>]+>|\[[^\]]+\])", line)
        if groups:
            cleaned_lines.append(" ".join(groups))
    return "\n".join(cleaned_lines)

def sanitize_rigid_for_sandbox(text: str) -> str:
    processed_lines = []
    for line in text.strip().splitlines():
        modules_on_line = re.findall(r'\[([^,\]]+)\]', line)
        sanitized = []
        for module in modules_on_line:
            token = module.strip().capitalize()
            if not re.search(r'\d+$', token):
                token += "00"
            sanitized.append(token)
        if sanitized:
            processed_lines.append(f"[{'-'.join(sanitized)}]")
    return "\n".join(processed_lines)