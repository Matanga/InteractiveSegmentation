import os
from PIL import Image
from typing import Dict, List, Tuple
from pathlib import Path # Add Path import

import math
from .perspective import PerspectiveTransform


# A type alias for our blueprint structure for clarity
IconSet = Dict[str, Path]
Blueprint = Dict[str, Dict[int, List[str]]]

class BuildError(Exception):
    """Custom exception for errors during the building generation process."""


class BuildingGenerator:
    """
    Generates a 2.5D image of a building from a resolved blueprint.
    """

    def __init__(self, icon_set: IconSet):
        """
        Initializes the generator by loading module assets from a provided icon set.

        Args:
            icon_set (IconSet): A dictionary mapping module names to their file paths.
        """
        print("INFO: BuildingGenerator received an icon set to load.")
        self.modules: Dict[str, Image.Image] = self._load_modules_from_set(icon_set)
        if not self.modules:
            raise BuildError("The provided icon set was empty or no images could be loaded.")

        self.default_height = 128
        print(f"INFO: Detected default module height of {self.default_height}px.")

    # This method replaces the old _load_modules
    def _load_modules_from_set(self, icon_set: IconSet) -> Dict[str, Image.Image]:
        """
        Private helper to load PIL Images from a dictionary of name -> path.
        """
        loaded_modules = {}
        for module_name, image_path in icon_set.items():
            try:
                # Use .convert("RGBA") for consistency
                loaded_modules[module_name] = Image.open(image_path).convert("RGBA")
            except Exception as e:
                print(f"WARNING: Could not load image for '{module_name}' from path '{image_path}': {e}")
        return loaded_modules

    def _get_module_image(self, module_name: str) -> Image.Image:
        """Safely retrieves a module's image object."""
        if module_name not in self.modules:
            raise BuildError(f"Module image for '{module_name}' not found. "
                             "Ensure a corresponding .png file exists.")
        return self.modules[module_name]

    # --- STEP 1 GOAL: This is our focus for now ---
    def assemble_flat_floor(self, floor_module_list: List[str]) -> Image.Image:
        """
        Takes a list of module names for a single floor and pastes them
        side-by-side to create a single, flat image of that floor.

        Args:
            floor_module_list: A list like ['Wall00', 'Door00', 'Wall00'].

        Returns:
            A PIL.Image.Image object of the assembled floor.
        """
        if not floor_module_list:
            # Return a tiny, transparent image if the floor is empty
            return Image.new("RGBA", (1, self.default_height), (0, 0, 0, 0))

        # Calculate the total width of the final image
        total_width = sum(self._get_module_image(name).width for name in floor_module_list)

        # Create a new, blank canvas for the floor
        # The height is determined by our default module height
        floor_canvas = Image.new("RGBA", (total_width, self.default_height), (0, 0, 0, 0))

        current_x = 0
        for module_name in floor_module_list:
            module_image = self._get_module_image(module_name)

            # Paste the module image onto the canvas at the current x position
            # The second argument is the box to paste into, or just top-left coords
            # The third argument is the mask, which should be the image's alpha channel
            floor_canvas.paste(module_image, (current_x, 0), module_image)

            # Move the "cursor" to the right for the next module
            current_x += module_image.width

        return floor_canvas

    def assemble_full_facade(self, facade_blueprint: Dict[int, List[str]]) -> Image.Image:
        """
        Assembles a full facade, ensuring all floors are stretched to the
        same width by adding 'Wall00' modules as padding.
        """
        if not facade_blueprint:
            return Image.new("RGBA", (1, 1))

        # --- Step 1: Post-process the blueprint to enforce equal widths ---

        # First, find the required width of the widest floor in pixels
        max_physical_width = 0
        floor_physical_widths = {}
        for floor_idx, modules in facade_blueprint.items():
            width = sum(self._get_module_image(m).width for m in modules)
            floor_physical_widths[floor_idx] = width
            if width > max_physical_width:
                max_physical_width = width

        # Now, create a new, corrected blueprint
        corrected_blueprint = {}
        for floor_idx, modules in facade_blueprint.items():
            current_width = floor_physical_widths[floor_idx]
            width_to_add = max_physical_width - current_width

            # We need the width of a single 'Wall00' to calculate padding
            # This assumes 'Wall00' exists and is our default padding module.
            try:
                wall_width = self._get_module_image('Wall00').width
                if wall_width == 0: raise BuildError  # Avoid division by zero
            except (BuildError, KeyError):
                print("WARNING: 'Wall00' module not found for padding. Floors may not align.")
                corrected_blueprint[floor_idx] = modules
                continue

            num_walls_to_add = round(width_to_add / wall_width)

            if num_walls_to_add > 0:
                # Distribute the padding walls on both sides for a centered look
                left_padding = ['Wall00'] * (num_walls_to_add // 2)
                right_padding = ['Wall00'] * (num_walls_to_add - len(left_padding))
                corrected_blueprint[floor_idx] = left_padding + modules + right_padding
                print(f"INFO: Padded Floor {floor_idx} with {num_walls_to_add} 'Wall00' modules to match max width.")
            else:
                corrected_blueprint[floor_idx] = modules

        # --- Step 2: Assemble the image using the corrected blueprint ---

        # Assemble each floor using the NEW corrected blueprint
        floor_images: Dict[int, Image.Image] = {
            floor_idx: self.assemble_flat_floor(modules)
            for floor_idx, modules in corrected_blueprint.items()
        }

        # The canvas width is now consistent
        canvas_width = max_physical_width
        total_height = sum(img.height for img in floor_images.values())

        if canvas_width == 0 or total_height == 0:
            return Image.new("RGBA", (1, 1))

        facade_canvas = Image.new("RGBA", (canvas_width, total_height))

        current_y = 0
        for floor_idx in sorted(floor_images.keys()):
            floor_image = floor_images[floor_idx]

            # No more centering logic needed, as all floors have the same width
            paste_x = 0

            facade_canvas.paste(floor_image, (paste_x, current_y), floor_image)
            current_y += floor_image.height

        return facade_canvas

    # This is the main generation method. It will now work as intended.
    def generate_3d_building(self, blueprint: Blueprint, camera_angle_deg: int = 30,
                             depth_ratio: float = 0.5) -> Image.Image:
        # --- 1. Generate all flat facades ---
        flat_facades = {
            side: self.assemble_full_facade(facade_blueprint)
            for side, facade_blueprint in blueprint.items()
        }
        front_facade = flat_facades.get("front")
        right_facade = flat_facades.get("right")
        if not front_facade or not right_facade:
            raise BuildError("Cannot generate 3D building without 'front' and 'right' facades.")

        # --- 2. Define 3D Geometry ---
        # (This part is simplified for clarity)
        canvas_width = front_facade.width + int(right_facade.width * depth_ratio)
        canvas_height = front_facade.height + int(right_facade.width * depth_ratio)
        final_canvas = Image.new("RGBA", (canvas_width, canvas_height))

        # Position the front facade
        ff_w, ff_h = front_facade.size
        ff_x, ff_y = 50, canvas_height - ff_h - 50
        final_canvas.paste(front_facade, (ff_x, ff_y), front_facade)
        front_corners = [(ff_x, ff_y), (ff_x + ff_w, ff_y), (ff_x + ff_w, ff_y + ff_h), (ff_x, ff_y + ff_h)]

        # --- 3. Transform and Paste Right Facade ---
        depth = right_facade.width * depth_ratio
        angle_rad = math.radians(camera_angle_deg)

        dx = depth * math.cos(angle_rad)
        dy = depth * math.sin(angle_rad)

        tr_corner = front_corners[1]  # Top-right
        br_corner = front_corners[2]  # Bottom-right

        # Define the target quadrilateral for the right facade
        right_target_corners = [
            tr_corner,
            (tr_corner[0] + dx, tr_corner[1] - dy),
            (br_corner[0] + dx, br_corner[1] - dy),
            br_corner
        ]

        # Use our new perspective helper
        transformer = PerspectiveTransform(target_corners=right_target_corners)
        warped_right_facade, paste_pos = transformer.transform_image(right_facade)

        final_canvas.paste(warped_right_facade, paste_pos, warped_right_facade)

        return final_canvas