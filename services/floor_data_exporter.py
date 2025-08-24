import json
from typing import Dict

def translate_floor_definitions(
    floor_definitions: list,
    mapping: Dict[str, str]
) -> list:
    """
    Translates the module names in a list of floor definitions using a
    provided mapping dictionary.
    """
    translated_data = []
    for floor in floor_definitions:
        new_floor = floor.copy()
        new_patterns = []
        for pattern_str in new_floor["Pattern"]:
            # This is a simple replacement. A more robust solution
            # would parse the grammar string.
            translated_pattern = pattern_str
            for internal_name, unreal_name in mapping.items():
                translated_pattern = translated_pattern.replace(internal_name, unreal_name)
            new_patterns.append(translated_pattern)
        new_floor["Pattern"] = new_patterns
        translated_data.append(new_floor)
    return translated_data