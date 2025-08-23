from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import logging

# We need PatternResolver for type hinting and instantiation inside the Director
from domain.pattern_resolver import PatternResolver

log = logging.getLogger(__name__)

# --- Constants for Clarity ---
OPPOSING_SIDES = {
    "front": "back",
    "back": "front",
    "right": "left",
    "left": "right",
}
ALL_SIDES = ["front", "right", "back", "left"]
MODULE_SIZE = 128
ICON_PIXEL_WIDTH = MODULE_SIZE
ICON_PIXEL_HEIGHT = MODULE_SIZE

PROCEDURAL_MODULE_WIDTH = 400
PROCEDURAL_MODULE_HEIGHT = 400


# --- Data Structures ---

@dataclass(frozen=True)
class FacadeSpec:
    """Specification for a single facade."""
    grammar: str
    width: int


@dataclass(frozen=True)
class BuildingSpec:
    num_floors: int
    facades: Dict[str, FacadeSpec]
    camera_angle: int = 30
    default_module_width: int = ICON_PIXEL_WIDTH
    def __post_init__(self):
        if self.num_floors < 1:
            raise ValueError("Building must have at least 1 floor.")
        # We move the stricter validation to the Director,
        # as it can now be a "policy" rather than a hard rule.



# --- Orchestration Logic ---

class BuildingDirector:
    def __init__(self, spec: BuildingSpec):
        if not isinstance(spec, BuildingSpec):
            raise TypeError("BuildingDirector must be initialized with a BuildingSpec object.")

        self.resolver = PatternResolver(default_module_width=PROCEDURAL_MODULE_WIDTH)
        # The completed spec is now generated and normalized in one go.
        self.completed_spec = self._normalize_and_complete_spec(spec)
        self._blueprint_cache: Dict[str, Dict[int, List[str]]] | None = None

    def _normalize_grammar(self, grammar: str, target_floors: int, side_name: str) -> str:
        """
        Ensures a grammar string has the correct number of floors.
        - Appends <Wall00> for missing floors.
        - Raises an error if there are too many floors.
        """
        lines = [ln.strip() for ln in grammar.strip().splitlines() if ln.strip()]
        current_floors = len(lines)

        if current_floors > target_floors:
            # Policy Decision: Be strict. The user's intent is contradictory.
            raise ValueError(
                f"Facade '{side_name}' grammar has {current_floors} floors, "
                f"but the building is defined with only {target_floors}."
            )

        if current_floors < target_floors:
            # Policy Decision: Be helpful. Autofill missing floors.
            missing_floors = target_floors - current_floors
            print(f"INFO: Facade '{side_name}' has {current_floors}/{target_floors} floors. "
                  f"Autofilling {missing_floors} floor(s) with '<Wall00>'.")
            autofill_lines = ["<Wall00>"] * missing_floors
            lines.extend(autofill_lines)

        return "\n".join(lines)

    def _normalize_and_complete_spec(self, original_spec: BuildingSpec) -> BuildingSpec:
        """
        Handles all default logic:
        1. Normalizes floor counts of existing facades.
        2. Creates default facades for missing sides.
        """
        normalized_facades = {}
        # First, normalize all user-provided facades
        for side, spec in original_spec.facades.items():
            normalized_grammar = self._normalize_grammar(
                spec.grammar, original_spec.num_floors, side
            )
            normalized_facades[side] = FacadeSpec(grammar=normalized_grammar, width=spec.width)

        # Now, create defaults for any missing facades
        completed_facades = normalized_facades.copy()
        for side in ALL_SIDES:
            if side not in completed_facades:
                # This logic remains the same, but now uses the global num_floors
                opposing_side_name = OPPOSING_SIDES[side]
                if opposing_side_name not in completed_facades:
                    raise ValueError(
                        f"Cannot create default for '{side}' because its opposing side '{opposing_side_name}' is also missing.")

                opposing_facade = completed_facades[opposing_side_name]
                default_width = opposing_facade.width
                default_grammar = "\n".join(["<Wall00>"] * original_spec.num_floors)

                print(f"INFO: Facade '{side}' not provided. Creating default with width "
                      f"{default_width} and {original_spec.num_floors} floor(s).")

                completed_facades[side] = FacadeSpec(grammar=default_grammar, width=default_width)

        return BuildingSpec(
            num_floors=original_spec.num_floors,
            facades=completed_facades,
            camera_angle=original_spec.camera_angle,
            default_module_width=original_spec.default_module_width
        )

    def produce_blueprint(self) -> Dict[str, Dict[int, List[str]]]:
        """
        Resolves the completed spec into a final blueprint.
        Caches the result for subsequent calls.
        """
        # If the blueprint hasn't been generated yet, generate and cache it.
        if self._blueprint_cache is None:
            print("INFO: Generating blueprint for the first time...")
            resolved_building = {}
            for side, facade_spec in self.completed_spec.facades.items():
                floor_widths = {i: facade_spec.width for i in range(self.completed_spec.num_floors)}
                resolved_building[side] = self.resolver.resolve(facade_spec.grammar, floor_widths)
            self._blueprint_cache = resolved_building

        return self._blueprint_cache

    def __str__(self) -> str:
        bp = self.produce_blueprint()
        output = ["\n=== Resolved Building Blueprint ==="]
        for side in ["front", "right", "back", "left"]:
            if side in bp:
                floors = bp[side]
                width = sum(self.resolver._get_module_width(m) for m in floors.get(0, []))
                output.append(f"\n◆ {side.upper()} (Width: ~{width}px)")
                for idx in sorted(floors):
                    output.append(f"  Floor {idx}:  {' '.join(floors[idx])}")
        output.append("=" * 35)
        return "\n".join(output)