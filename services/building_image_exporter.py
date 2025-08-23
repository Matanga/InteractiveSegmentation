from __future__ import annotations
import json
from typing import Dict

from PIL import Image

# Import the proven, existing classes we will reuse
from domain.building_spec import BuildingDirector
from domain.building_generator_2d import BuildingGenerator2D
from services.resources_loader import IconFiles
from services.ui_adapter import prepare_spec_from_ui


def generate_all_facade_strip_images(
        floor_definitions_json: str,
        building_width: int,
        building_depth: int
) -> Dict[str, Image.Image]:
    """
    Takes all UI data, runs the full procedural pipeline, and renders every
    single FacadeStrip into a PIL.Image.

    Returns:
        A dictionary where the key is a unique name (e.g., "Ground Floor-front")
        and the value is the corresponding rendered PIL.Image.
    """
    print("--- Starting Generation of All Facade Strip Images ---")

    # This dictionary will hold our final images
    rendered_images: Dict[str, Image.Image] = {}

    try:
        # --- Step 1: Use the Adapter and Director to get the resolved blueprint ---
        spec = prepare_spec_from_ui(floor_definitions_json, building_width, building_depth)
        director = BuildingDirector(spec)
        blueprint = director.produce_blueprint()
        print("Blueprint generated successfully.")

        # --- Step 2: Initialize the 2D Image Generator ---
        icon_set = IconFiles.get_icons_for_category("Default")
        generator = BuildingGenerator2D(icon_set)

        # --- Step 3: Parse the floor names from the original JSON ---
        # We need the names to create the dictionary keys.
        floor_data = json.loads(floor_definitions_json)
        # The JSON is ground-floor first, but the blueprint is top-floor first.
        # So we create a mapping from blueprint index to name.
        num_floors = len(floor_data)
        floor_names_map = {(num_floors - 1 - i): floor['Name'] for i, floor in enumerate(floor_data)}

        # --- Step 4: Iterate through the blueprint and render each strip ---
        for side_name, side_blueprint in blueprint.items():
            for floor_idx, module_names in side_blueprint.items():
                if not module_names:
                    continue  # Skip empty strips

                # Create a unique key for our dictionary
                floor_name = floor_names_map.get(floor_idx, f"Floor_{floor_idx}")
                image_key = f"{floor_name}-{side_name}"

                # Render the image for this single strip
                strip_image = generator.assemble_flat_floor(module_names)

                if strip_image:
                    rendered_images[image_key] = strip_image
                    print(f"  > Successfully rendered image for '{image_key}'")

    except Exception as e:
        print(f"ERROR during image generation: {e}")
        import traceback
        traceback.print_exc()

    return rendered_images