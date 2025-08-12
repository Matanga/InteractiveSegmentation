from __future__ import annotations
from typing import Dict, List, Tuple

# We import the building blocks from the core module
from domain.grammar import Group, GroupKind, parse as parse_grammar

# Define a type alias for clarity
ModuleDimensions = Dict[str, Tuple[int, int]]  # e.g., {'wall': (100, 300)}

__all__ = ["ResolutionError", "PatternResolver"]



class ResolutionError(ValueError):
    """Raised when a pattern cannot be resolved with the given constraints."""


class PatternResolver:
    # The __init__ is simple again.
    def __init__(self, default_module_width: int):
        if default_module_width <= 0:
            raise ValueError("Default module width must be positive.")
        self.default_module_width = default_module_width

    def _get_module_width(self, module_name: str) -> int:
        # It always returns the default width. No dictionary lookup.
        return self.default_module_width

    def _resolve_floor(self, floor_groups: List[Group], target_width: int) -> List[str]:
        """
        The core logic. Resolves a single floor's pattern to fit a target width
        using a more intelligent, iterative distribution strategy for fill groups.
        """
        # Create a list of "slots" for the final modules, one for each group.
        # This helps us insert modules in the correct order.
        resolved_slots = [[] for _ in floor_groups]
        rigid_width = 0

        # --- Step 1: Process RIGID groups first ---
        # This pass calculates their width and places them in their slots.
        fill_group_indices = []
        for i, group in enumerate(floor_groups):
            if group.kind is GroupKind.RIGID:
                group_module_names = [m.name for m in group.modules]
                # Place the rigid modules directly into their slot
                resolved_slots[i].extend(group_module_names * group.repeat)

                group_width = sum(self._get_module_width(m.name) for m in group.modules)
                rigid_width += group_width * group.repeat
            else:
                fill_group_indices.append(i)  # Keep track of which groups are fills

        if rigid_width > target_width:
            raise ResolutionError(
                f"Rigid groups alone ({rigid_width}px) exceed target width ({target_width}px)."
            )

        # --- Step 2: Iteratively fill the FILL groups ---
        # This is the new, smarter distribution logic.
        remaining_width = target_width - rigid_width

        if fill_group_indices:
            # Keep track of the next module to add from each fill group's pattern
            next_module_indices = {idx: 0 for idx in fill_group_indices}

            # Continue adding modules one-by-one until no more can fit
            can_add_more = True
            while can_add_more:
                can_add_more = False  # Assume we're done unless we successfully add a module

                # Cycle through the fill groups (e.g., group 1, then group 2, then group 1...)
                for group_idx in fill_group_indices:
                    group = floor_groups[group_idx]
                    module_pattern = [m.name for m in group.modules]

                    if not module_pattern:
                        continue  # Skip empty fill groups

                    # Get the name of the next module in this group's pattern
                    pattern_idx = next_module_indices[group_idx]
                    module_to_add = module_pattern[pattern_idx]
                    module_width = self._get_module_width(module_to_add)

                    if remaining_width >= module_width:
                        # We have space! Add the module.
                        resolved_slots[group_idx].append(module_to_add)
                        remaining_width -= module_width

                        # Move to the next module in the pattern for this group, wrapping around
                        next_module_indices[group_idx] = (pattern_idx + 1) % len(module_pattern)

                        # Since we added a module, we might be able to add more.
                        can_add_more = True
                    # If we can't fit it, we just move on to the next fill group.

        # --- Step 3: Flatten the slots into the final list ---
        final_module_list = [module for slot in resolved_slots for module in slot]

        return final_module_list


    def resolve(self, grammar_string: str, floor_widths: Dict[int, int]) -> Dict[int, List[str]]:
        """
        Resolves a full, multi-floor grammar string against specified widths for each floor.

        Args:
            grammar_string: The full pattern string (e.g., "<A>\n[B]2").
            floor_widths: A dictionary mapping floor index (0=top floor) to its target width.
                          Example: {0: 1000, 1: 1200}

        Returns:
            A dictionary mapping floor index to its resolved list of module names.
        """
        try:
            pattern = parse_grammar(grammar_string)
        except ValueError as e:
            # Re-raise as a ResolutionError to keep API consistent
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
            resolved_building[i] = self._resolve_floor(floor_groups, target_width)

        return resolved_building