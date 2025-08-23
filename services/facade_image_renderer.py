from __future__ import annotations
from typing import List, Dict
from pathlib import Path

from PIL import Image

from services.resources_loader import IconFiles
from domain.building_spec import ICON_PIXEL_WIDTH


class FacadeImageRenderer:
    """
    A service to render a list of module names into a single PIL Image object,
    using the proven logic from the original BuildingGenerator2D.
    """

    def __init__(self, category: str = "Default"):
        """
        Initializes the renderer and pre-loads all icon images for a given
        category to optimize performance.
        """
        self.modules: Dict[str, Image.Image] = self._load_modules(category)
        if not self.modules:
            raise RuntimeError("Image renderer failed: Icon set is empty or images failed to load.")

        # Determine a consistent module height from the loaded icons
        self.module_height = next(iter(self.modules.values())).height

    def _load_modules(self, category: str) -> Dict[str, Image.Image]:
        """
        Loads all icon files from a category into memory, ensuring they are
        in the correct RGBA format.
        """
        loaded_modules = {}
        icon_paths = IconFiles.get_icons_for_category(category)
        for name, path in icon_paths.items():
            try:
                # --- THIS IS THE FIX FOR THE TRANSPARENCY BUG ---
                # Use .convert("RGBA") to ensure all images have a consistent
                # format with an alpha channel for pasting.
                img = Image.open(path).convert("RGBA")
                loaded_modules[name] = img
                # --- END OF FIX ---
            except Exception as e:
                print(f"Warning: Could not load image for '{name}'. Error: {e}")
        return loaded_modules

    def _get_module_image(self, module_name: str) -> Image.Image:
        """Safely retrieves a pre-loaded module's image object."""
        if module_name not in self.modules:
            # Create a placeholder if an icon is missing, to avoid crashing.
            print(f"Warning: Image for '{module_name}' not found. Using placeholder.")
            return Image.new("RGBA", (48, self.module_height), (255, 0, 255, 255))  # Bright pink
        return self.modules[module_name]

    def render_facade_cell(self, module_names: List[str]) -> Image.Image | None:
        """
        Takes a list of module names for a single floor's facade and pastes
        them side-by-side to create a single, flat image.
        """
        if not module_names:
            return None

        # Calculate total width based on the actual widths of the icons
        total_width = sum(self._get_module_image(name).width for name in module_names)
        if total_width == 0:
            return None

        # Create a new, blank canvas for the floor facade
        canvas = Image.new("RGBA", (total_width, self.module_height))

        current_x = 0
        for module_name in module_names:
            module_image = self._get_module_image(module_name)

            # Paste the module image onto the canvas at the current x position
            # The third argument (the mask) is the image itself, which uses
            # its own alpha channel for transparency. This is why .convert("RGBA") is critical.
            canvas.paste(module_image, (current_x, 0), module_image)

            current_x += module_image.width

        return canvas