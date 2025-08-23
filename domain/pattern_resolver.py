from __future__ import annotations
from typing import Dict, List

# --- Import the original, string-based parser from the grammar module ---
from domain.grammar import Group, GroupKind, parse as parse_grammar, GrammarError

__all__ = ["ResolutionError", "PatternResolver"]


class ResolutionError(ValueError):
    """Raised when a pattern cannot be resolved with the given constraints."""


class PatternResolver:
    def __init__(self, default_module_width: int):
        if default_module_width <= 0:
            raise ValueError("Default module width must be positive.")
        self.default_module_width = default_module_width

    def _get_module_width(self, module_name: str) -> int:
        return self.default_module_width

    def _resolve_strip(self, facade_strip_groups: List[Group], target_width: int) -> List[str]:
        """
        The core logic. Resolves a single facade strip (a list of groups)
        to fit a target width. Renamed from _resolve_facade for clarity.
        """
        resolved_slots = [[] for _ in facade_strip_groups]
        rigid_width = 0
        fill_group_indices = []

        # Step 1: Process RIGID groups first
        for i, group in enumerate(facade_strip_groups):
            if group.kind is GroupKind.RIGID:
                group_module_names = [m.name for m in group.modules]
                resolved_slots[i].extend(group_module_names * group.repeat)
                group_width = sum(self._get_module_width(m.name) for m in group.modules)
                rigid_width += group_width * group.repeat
            else:
                fill_group_indices.append(i)

        if rigid_width > target_width:
            raise ResolutionError(f"Rigid groups alone ({rigid_width}) exceed target width ({target_width}).")

        # Step 2: Iteratively fill the FILL groups
        remaining_width = target_width - rigid_width
        if fill_group_indices:
            next_module_indices = {idx: 0 for idx in fill_group_indices}
            can_add_more = True
            while can_add_more:
                can_add_more = False
                for group_idx in fill_group_indices:
                    group = facade_strip_groups[group_idx]
                    module_pattern = [m.name for m in group.modules]
                    if not module_pattern: continue
                    pattern_idx = next_module_indices[group_idx]
                    module_to_add = module_pattern[pattern_idx]
                    module_width = self._get_module_width(module_to_add)
                    if remaining_width >= module_width:
                        resolved_slots[group_idx].append(module_to_add)
                        remaining_width -= module_width
                        next_module_indices[group_idx] = (pattern_idx + 1) % len(module_pattern)
                        can_add_more = True

        # Step 3: Flatten the slots into the final list
        final_module_list = [module for slot in resolved_slots for module in slot]
        return final_module_list


    # --- THIS IS THE FIX ---
    # Revert the main 'resolve' method to its original, string-based signature
    # to be compatible with the existing BuildingDirector.
    def resolve(self, grammar_string: str, floor_widths: Dict[int, int]) -> Dict[int, List[str]]:
        """
        Resolves a full, multi-floor grammar string against specified widths.
        """
        try:
            # Use the original parser from grammar.py that works with strings
            pattern = parse_grammar(grammar_string)
        except GrammarError as e:
            raise ResolutionError(f"Invalid grammar: {e}") from e

        if len(pattern.floors) != len(floor_widths):
            raise ResolutionError(
                f"Mismatch: Grammar has {len(pattern.floors)} floors, but widths "
                f"were provided for {len(floor_widths)} floors."
            )

        resolved_building: Dict[int, List[str]] = {}
        for i, floor_groups in enumerate(pattern.floors):
            if i not in floor_widths:
                raise ResolutionError(f"Target width for floor {i} was not provided.")

            target_width = floor_widths[i]
            # Call our internal strip resolver for each floor
            resolved_building[i] = self._resolve_strip(floor_groups, target_width)

        return resolved_building