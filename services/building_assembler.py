from __future__ import annotations
import json
from typing import List, Dict, Any

from domain.grammar import parse_building_json, Pattern, Floor
from domain.pattern_resolver import PatternResolver, ResolutionError


# ===========================================================================
# Helper Class: StackingResolver
# ===========================================================================

class StackingResolver:
    """
    Resolves a vertical stacking pattern (e.g., '[Ground]<Floor1>') against a
    total building height to produce an ordered list of floor names.
    """

    def __init__(self, floor_map: Dict[str, Floor]):
        self.floor_map = floor_map

    def _get_floor_height(self, floor_name: str) -> int:
        """Safely gets the height of a floor from the map."""
        if floor_name not in self.floor_map:
            raise ValueError(f"Stacking pattern references undefined floor: '{floor_name}'")
        return self.floor_map[floor_name].height

    def resolve(self, stacking_pattern: str, total_height: int) -> List[str]:
        """The main resolution logic."""
        # Note: This is a simplified version of the domain's PatternResolver.
        # It handles a similar <fill> and [rigid] grammar.
        import re

        # A simple regex to find all [rigid] or <fill> groups
        group_re = re.compile(r"(\[.*?\])|(<.*?>)")
        tokens = group_re.findall(stacking_pattern)

        # Flatten the tuple results from findall
        groups = [item for tpl in tokens for item in tpl if item]

        resolved_slots = [[] for _ in groups]
        rigid_height = 0
        fill_group_indices = []

        # Step 1: Process rigid groups first
        for i, group_str in enumerate(groups):
            if group_str.startswith('['):
                floor_names = group_str.strip('[]').split('-')
                resolved_slots[i].extend(floor_names)
                for name in floor_names:
                    rigid_height += self._get_floor_height(name)
            else:
                fill_group_indices.append(i)

        if rigid_height > total_height:
            raise ValueError(f"Rigid floors in stacking pattern exceed total building height.")

        # Step 2: Iteratively fill the fill groups
        remaining_height = total_height - rigid_height
        if fill_group_indices:
            next_floor_indices = {idx: 0 for idx in fill_group_indices}
            can_add_more = True
            while can_add_more:
                can_add_more = False
                for group_idx in fill_group_indices:
                    group_str = groups[group_idx]
                    floor_pattern = group_str.strip('<>').split('-')

                    pattern_idx = next_floor_indices[group_idx]
                    floor_to_add = floor_pattern[pattern_idx]
                    floor_height = self._get_floor_height(floor_to_add)

                    if remaining_height >= floor_height:
                        resolved_slots[group_idx].append(floor_to_add)
                        remaining_height -= floor_height
                        next_floor_indices[group_idx] = (pattern_idx + 1) % len(floor_pattern)
                        can_add_more = True

        # Step 3: Flatten slots into the final ordered list
        final_floor_list = [floor_name for slot in resolved_slots for floor_name in slot]
        return final_floor_list


# ===========================================================================
# Main Service Function
# ===========================================================================

def assemble_building_blueprint(
        floor_definitions_json: str,
        stacking_pattern: str,
        building_width: int,
        building_depth: int,
        total_building_height: int,
        default_module_width: int = 48
) -> Dict[str, List[List[str]]]:
    """
    The main orchestration service for creating a resolved building blueprint.

    Args:
        floor_definitions_json: The JSON string from the PatternArea.
        stacking_pattern: The vertical assembly pattern (e.g., "[Ground]<Floor1>").
        building_width: The total width of the building (X-axis).
        building_depth: The total depth of the building (Y-axis).
        total_building_height: The maximum height of the building (Z-axis).
        default_module_width: The default width for resolving facade patterns.

    Returns:
        A dictionary mapping facade names ('front', 'left', etc.) to a
        2D list of resolved module names for that facade.
        Example: {"front": [["Door", "Wall"], ["Window", "Window"]]}
    """
    # --- Step 1: Parse Floor Definitions and Create Lookup Map ---
    try:
        floor_data = json.loads(floor_definitions_json)
        pattern_obj: Pattern = parse_building_json(floor_data)

        # Convert the list of Floor objects into a dictionary for fast lookup by name
        floor_map: Dict[str, Floor] = {floor.name: floor for floor in pattern_obj.floors}

    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: Failed to parse floor definitions. {e}")
        return {}

    # --- Step 2: Resolve the Stacking Pattern to get an ordered list of floors ---
    try:
        stacking_resolver = StackingResolver(floor_map)
        ordered_floor_names = stacking_resolver.resolve(stacking_pattern, total_building_height)

        # Create the final, ordered list of Floor objects
        final_floor_order: List[Floor] = [floor_map[name] for name in ordered_floor_names]

    except ValueError as e:
        print(f"ERROR: Failed to resolve stacking pattern. {e}")
        return {}

    # --- Step 3: Resolve each facade for the entire building height ---
    facade_resolver = PatternResolver(default_module_width=default_module_width)
    final_blueprint = {}
    facade_order = ["front", "left", "back", "right"]

    for facade_name in facade_order:
        # Determine the target width for this facade
        facade_width = building_width if facade_name in ["front", "back"] else building_depth

        resolved_facade_modules = []
        for floor_obj in final_floor_order:
            # Get the list of groups for this specific facade from the floor object
            facade_groups = floor_obj.facades.get(facade_name, [])

            try:
                # Use the domain resolver to get the list of modules for this single floor
                resolved_floor = facade_resolver._resolve_facade(facade_groups, facade_width)
                resolved_facade_modules.append(resolved_floor)
            except ResolutionError as e:
                print(f"ERROR: Failed to resolve {facade_name} facade for floor '{floor_obj.name}'. {e}")
                # Append an empty list to keep the structure consistent
                resolved_facade_modules.append([])

        final_blueprint[facade_name] = resolved_facade_modules

    return final_blueprint