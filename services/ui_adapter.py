import json
from domain.building_spec import BuildingSpec, FacadeSpec


def prepare_spec_from_ui(
        floor_definitions_json: str,
        building_width: int,
        building_depth: int,
) -> BuildingSpec:
    """
    Acts as an Adapter between the new UI and the existing BuildingDirector.
    It takes data from the UI and constructs the BuildingSpec object that
    the Director needs to do its work.
    """
    # 1. Parse the floor definitions from the PatternArea's JSON
    floor_data = json.loads(floor_definitions_json)

    # 2. Re-format the data into multi-line grammar strings for each facade
    facade_grammars = {
        "front": [], "left": [], "back": [], "right": []
    }

    # The JSON is ground-floor first, but the grammar expects ground-floor last.
    # We iterate through the JSON as is, and will reverse the lists later.
    for floor in floor_data:
        patterns = floor.get("Pattern", [""] * 4)
        patterns.extend([""] * (4 - len(patterns)))  # Ensure 4 patterns

        facade_grammars["front"].append(patterns[0])
        facade_grammars["left"].append(patterns[1])
        facade_grammars["back"].append(patterns[2])
        facade_grammars["right"].append(patterns[3])

    # Join the lines for each facade, reversing to make the last line the ground floor
    front_grammar = "\n".join(reversed(facade_grammars["front"]))
    left_grammar = "\n".join(reversed(facade_grammars["left"]))
    back_grammar = "\n".join(reversed(facade_grammars["back"]))
    right_grammar = "\n".join(reversed(facade_grammars["right"]))

    # 3. Create the FacadeSpec objects
    facades = {
        "front": FacadeSpec(grammar=front_grammar, width=building_width),
        "left": FacadeSpec(grammar=left_grammar, width=building_depth),
        "back": FacadeSpec(grammar=back_grammar, width=building_width),
        "right": FacadeSpec(grammar=right_grammar, width=building_depth),
    }

    # The number of floors is simply the number of definitions from the UI
    num_floors = len(floor_data)

    # 4. Construct and return the final BuildingSpec
    return BuildingSpec(num_floors=num_floors, facades=facades)