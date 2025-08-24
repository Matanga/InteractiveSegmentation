from __future__ import annotations
import re
from typing import List, Dict

# We need the Floor object definition for type hinting
from domain.grammar import Floor


class StackingResolver:
    """
    Resolves a vertical stacking pattern (e.g., '[Ground]<Floor1>') against a
    total building height to produce an ordered list of floor names.
    """

    def __init__(self, floor_map: Dict[str, Floor]):
        """
        Initializes the resolver with a map of available floor definitions.
        Args:
            floor_map: A dictionary where the key is the floor 'Name' and the
                       value is the corresponding 'Floor' object.
        """
        self.floor_map = floor_map

    def _get_floor_height(self, floor_name: str) -> int:
        """Safely gets the height of a floor from the map."""
        if floor_name not in self.floor_map:
            raise ValueError(f"Stacking pattern references an undefined floor: '{floor_name}'")
        return self.floor_map[floor_name].height

    def resolve(self, stacking_pattern: str, total_height: int) -> List[str]:
        """
        The main resolution logic.

        Returns:
            An ordered list of floor names, from bottom to top.
        """
        # A simple regex to find all [rigid] or <fill> groups
        group_re = re.compile(r"(\[.*?\])|(<.*?>)")
        tokens = group_re.findall(stacking_pattern)
        groups = [item for tpl in tokens for item in tpl if item]

        resolved_slots = [[] for _ in groups]
        rigid_height = 0
        fill_group_indices = []

        # Step 1: Process rigid groups first (e.g., [Ground], [Roof])
        for i, group_str in enumerate(groups):
            if group_str.startswith('['):
                floor_names = [name.strip() for name in group_str.strip('[]').split('-')]
                resolved_slots[i].extend(floor_names)
                for name in floor_names:
                    rigid_height += self._get_floor_height(name)
            else:
                fill_group_indices.append(i)

        if rigid_height > total_height:
            raise ValueError(
                f"Rigid floors in stacking pattern ({rigid_height}cm) exceed total building height ({total_height}cm).")

        # Step 2: Iteratively fill the fill groups (e.g., <OfficeFloor>)
        remaining_height = total_height - rigid_height
        if fill_group_indices:
            next_floor_indices = {idx: 0 for idx in fill_group_indices}
            can_add_more = True
            while can_add_more:
                can_add_more = False
                for group_idx in fill_group_indices:
                    group_str = groups[group_idx]
                    floor_pattern = [name.strip() for name in group_str.strip('<>').split('-')]

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