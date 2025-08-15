from __future__ import annotations
from typing import Dict, List, Tuple

# We import the new, multi-facade-aware data structures from our grammar module
from domain.grammar import Group, GroupKind, Pattern

# --- NEW: Define type aliases for the complex data structures for clarity ---
BuildingWidths = List[Dict[str, int]]
ResolvedBuilding = List[Dict[str, List[str]]]
FacadeGroups = List[Group]

__all__ = ["ResolutionError", "PatternResolver"]


class ResolutionError(ValueError):
    """Raised when a pattern cannot be resolved with the given constraints."""


class PatternResolver:
    def __init__(self, default_module_width: int):
        if default_module_width <= 0:
            raise ValueError("Default module width must be positive.")
        self.default_module_width = default_module_width

    def _get_module_width(self, module_name: str) -> int:
        # In a more advanced system, this could look up dimensions from a dictionary.
        # For now, it returns a consistent default width.
        return self.default_module_width

    def _resolve_facade(self, facade_groups: FacadeGroups, target_width: int) -> List[str]:
        """
        The core logic. Resolves a single facade's pattern (a list of groups)
        to fit a target width.

        This is the repurposed '_resolve_floor' method, renamed for clarity.
        Its internal logic remains unchanged as it is perfectly suited for this task.
        """
        resolved_slots = [[] for _ in facade_groups]
        rigid_width = 0
        fill_group_indices = []

        # --- Step 1: Process RIGID groups first ---
        for i, group in enumerate(facade_groups):
            if group.kind is GroupKind.RIGID:
                group_module_names = [m.name for m in group.modules]
                resolved_slots[i].extend(group_module_names * group.repeat)
                group_width = sum(self._get_module_width(m.name) for m in group.modules)
                rigid_width += group_width * group.repeat
            else:
                fill_group_indices.append(i)

        if rigid_width > target_width:
            raise ResolutionError(
                f"Rigid groups alone ({rigid_width}) exceed target width ({target_width})."
            )

        # --- Step 2: Iteratively fill the FILL groups ---
        remaining_width = target_width - rigid_width
        if fill_group_indices:
            next_module_indices = {idx: 0 for idx in fill_group_indices}
            can_add_more = True
            while can_add_more:
                can_add_more = False
                for group_idx in fill_group_indices:
                    group = facade_groups[group_idx]
                    module_pattern = [m.name for m in group.modules]
                    if not module_pattern:
                        continue

                    pattern_idx = next_module_indices[group_idx]
                    module_to_add = module_pattern[pattern_idx]
                    module_width = self._get_module_width(module_to_add)

                    if remaining_width >= module_width:
                        resolved_slots[group_idx].append(module_to_add)
                        remaining_width -= module_width
                        next_module_indices[group_idx] = (pattern_idx + 1) % len(module_pattern)
                        can_add_more = True

        # --- Step 3: Flatten the slots into the final list ---
        final_module_list = [module for slot in resolved_slots for module in slot]
        return final_module_list

    def resolve(self, pattern: Pattern, building_widths: BuildingWidths) -> ResolvedBuilding:
        """
        The new main entry point. Resolves a full, multi-facade Pattern object
        against a detailed specification of widths for each facade of each floor.

        Args:
            pattern: The parsed Pattern object from grammar.py.
            building_widths: A list of dictionaries specifying target widths.
                             Example: [{ "front": 1000, "left": 500, ... }, { ... }]

        Returns:
            A list of dictionaries containing the resolved module lists for each facade.
        """
        if len(pattern.floors) != len(building_widths):
            raise ResolutionError(
                f"Mismatch: Pattern has {len(pattern.floors)} floors, but widths "
                f"were provided for {len(building_widths)} floors."
            )

        resolved_building: ResolvedBuilding = []
        facade_order = ["front", "left", "back", "right"]

        for i, floor in enumerate(pattern.floors):
            floor_widths = building_widths[i]
            resolved_floor: Dict[str, List[str]] = {}

            # Resolve each of the four facades for the current floor
            for facade_name in facade_order:
                if facade_name not in floor_widths:
                    raise ResolutionError(
                        f"Target width for facade '{facade_name}' on floor {i} "
                        f"(named '{floor.name}') was not provided."
                    )

                target_width = floor_widths[facade_name]
                facade_groups = floor.facades.get(facade_name, [])

                # Use the core logic to resolve this specific facade
                resolved_floor[facade_name] = self._resolve_facade(facade_groups, target_width)

            resolved_building.append(resolved_floor)

        return resolved_building