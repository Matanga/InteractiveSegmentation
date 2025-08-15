from typing import List, Dict, Any

DEFAULT_FACADE_PATTERN = "<Wall00>"


def preprocess_unreal_json_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Cleans and completes building data loaded from an Unreal Engine JSON source.

    Specifically, it ensures every floor object:
    1. Has a "Pattern" key, which is a list.
    2. The "Pattern" list contains exactly 4 string elements.

    Missing facade patterns are filled with a default "<Wall00>" pattern.
    Extra facade patterns are truncated.

    Args:
        raw_data: A list of floor dictionaries, as loaded from JSON.

    Returns:
        A new list of floor dictionaries that is guaranteed to be well-formed
        and ready for parsing by the domain layer.
    """
    # We create a new list to avoid modifying the original data in-place
    processed_data = []

    for floor_data in raw_data:
        # Create a copy to ensure the original dictionary isn't changed
        new_floor_data = floor_data.copy()

        pattern_array = new_floor_data.get("Pattern", [])

        # Ensure it's a list
        if not isinstance(pattern_array, list):
            pattern_array = []

        # Fill missing facades
        while len(pattern_array) < 4:
            pattern_array.append(DEFAULT_FACADE_PATTERN)

        # Truncate extra facades
        if len(pattern_array) > 4:
            pattern_array = pattern_array[:4]

        new_floor_data["Pattern"] = pattern_array
        processed_data.append(new_floor_data)

    return processed_data