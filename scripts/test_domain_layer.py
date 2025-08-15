"""
test_domain_layer.py

A script to perform a thorough end-to-end test of the refactored 'domain' layer.

This script simulates the entire data flow:
1.  Loads a JSON file representing an Unreal Engine Data Table.
2.  Pre-processes the data to handle incomplete facade patterns.
3.  Parses the data into the domain's Pattern/Floor objects.
4.  Validates the parsed Pattern object for semantic correctness.
5.  Resolves the Pattern into a concrete list of modules based on target widths.

To run:
1.  Make sure this script is in the 'scripts' folder.
2.  Make sure 'DT_MultiFacadeExample.json' is also in the 'scripts' folder.
3.  Execute the script from your project's root directory:
    python scripts/test_domain_layer.py
"""

import json
import os
import sys
from pprint import pprint
from typing import List

# --- Path Setup ---
# This allows the script to find the 'domain' module by adding the project root
# to the Python path.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from domain.grammar import (
        parse_building_json,
        Pattern,
        GrammarError,
    )
    from domain.pattern_validator import validate_pattern, ValidationIssue
    from domain.pattern_resolver import PatternResolver, ResolutionError
except ImportError as e:
    print(f"ERROR: Could not import domain modules. Make sure you are running this script "
          f"from your project's root directory. \nDetails: {e}")
    sys.exit(1)

# --- Constants ---
JSON_FILE_PATH = os.path.join(os.path.dirname(__file__), "DT_MultiFacadeExample.json")
DEFAULT_FACADE_PATTERN = "<Wall00>"
DEFAULT_MODULE_WIDTH = 100  # A sensible default for testing the resolver.

# ANSI color codes for pretty printing
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"


def preprocess_json_data(data: list) -> list:
    """
    Ensures every floor in the dataset has a 'Pattern' array with exactly 4 elements.
    Fills missing elements with the default facade pattern.
    """
    for i, floor_data in enumerate(data):
        if "Pattern" not in floor_data:
            floor_data["Pattern"] = []

        pattern_array = floor_data["Pattern"]
        while len(pattern_array) < 4:
            pattern_array.append(DEFAULT_FACADE_PATTERN)

        if len(pattern_array) > 4:
            print(f"{COLOR_YELLOW}WARNING: Floor {i} ('{floor_data.get('Name')}') has "
                  f"more than 4 patterns. Truncating.{COLOR_RESET}")
            floor_data["Pattern"] = pattern_array[:4]

    return data


def main():
    """Main function to run the test suite."""
    print(f"{COLOR_BLUE}--- STARTING DOMAIN LAYER TEST SUITE ---{COLOR_RESET}\n")

    # ========================================================================
    # STEP 1: Load and Pre-process Input JSON
    # ========================================================================
    print(f"{COLOR_BLUE}--- STEP 1: Loading and Pre-processing JSON ---{COLOR_RESET}")
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            raw_data = json.load(f)
        print(f"{COLOR_GREEN}Successfully loaded '{JSON_FILE_PATH}'.{COLOR_RESET}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"{COLOR_RED}FAILED: Could not load or parse JSON file. Error: {e}{COLOR_RESET}")
        return

    processed_data = preprocess_json_data(raw_data)
    print("Pre-processed data (missing facades filled):")
    pprint(processed_data)
    print("-" * 50)

    # ========================================================================
    # STEP 2: Test `grammar.py` - Parsing
    # ========================================================================
    print(f"\n{COLOR_BLUE}--- STEP 2: Testing grammar.parse_building_json ---{COLOR_RESET}")
    parsed_pattern: Pattern | None = None
    try:
        parsed_pattern = parse_building_json(processed_data)
        print(f"{COLOR_GREEN}SUCCESS: JSON data was parsed into a Pattern object.{COLOR_RESET}")
        print(f"Parsed Pattern contains {len(parsed_pattern.floors)} floors.")
        # Optional: inspect a specific part of the parsed object
        print(f"  - Floor 0, 'left' facade: {[str(g) for g in parsed_pattern.floors[0].facades['left']]}")
        print(f"  - Floor 1, 'back' facade: {[str(g) for g in parsed_pattern.floors[1].facades['back']]}")
    except GrammarError as e:
        print(f"{COLOR_RED}FAILED: Parsing raised an exception: {e}{COLOR_RESET}")
        return
    print("-" * 50)

    # ========================================================================
    # STEP 3: Test `pattern_validator.py` - Validation
    # ========================================================================
    print(f"\n{COLOR_BLUE}--- STEP 3: Testing pattern_validator.validate_pattern ---{COLOR_RESET}")
    try:
        issues: List[ValidationIssue] = validate_pattern(parsed_pattern)
        if not issues:
            print(f"{COLOR_GREEN}SUCCESS: Validator found no issues.{COLOR_RESET}")
        else:
            print(f"{COLOR_YELLOW}COMPLETED: Validator found the following issues:{COLOR_RESET}")
            for issue in issues:
                color = COLOR_YELLOW if "WARNING" in str(issue) else COLOR_RED
                print(f"  {color}{issue}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}FAILED: Validator raised an unexpected exception: {e}{COLOR_RESET}")
        return
    print("-" * 50)

    # ========================================================================
    # STEP 4: Test `pattern_resolver.py` - Resolution
    # ========================================================================
    print(f"\n{COLOR_BLUE}--- STEP 4: Testing pattern_resolver.PatternResolver ---{COLOR_RESET}")
    try:
        resolver = PatternResolver(default_module_width=DEFAULT_MODULE_WIDTH)
        print(f"Resolver created with default module width: {DEFAULT_MODULE_WIDTH}px.")

        # Define a set of widths for our 4-floor building
        building_widths = [
            {"front": 1200, "left": 800, "back": 1200, "right": 800},  # Floor 0
            {"front": 1200, "left": 800, "back": 1200, "right": 800},  # Floor 1
            {"front": 1200, "left": 800, "back": 1200, "right": 800},  # Floor 2
            {"front": 1200, "left": 800, "back": 1200, "right": 800},  # Floor 3
        ]
        print("Using the following target widths for resolution:")
        pprint(building_widths)

        resolved_building = resolver.resolve(parsed_pattern, building_widths)
        print(f"\n{COLOR_GREEN}SUCCESS: Pattern was resolved without errors.{COLOR_RESET}")
        print("Resolved Building Modules:")
        pprint(resolved_building)

    except ResolutionError as e:
        print(f"{COLOR_RED}FAILED: Resolver raised an exception: {e}{COLOR_RESET}")
        return
    except Exception as e:
        print(f"{COLOR_RED}FAILED: Resolver raised an unexpected exception: {e}{COLOR_RESET}")
        return
    print("-" * 50)

    print(f"\n{COLOR_GREEN}--- DOMAIN LAYER TEST SUITE COMPLETED SUCCESSFULLY ---{COLOR_RESET}")


if __name__ == "__main__":
    main()