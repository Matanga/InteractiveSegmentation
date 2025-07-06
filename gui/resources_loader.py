"""
resources_loader.py – ultra-light PNG catalogue for IBG-PE
==========================================================

Purpose
-------
Keep a central list of all *.png icons shipped in the ./resources folder
with zero GUI / Qt dependencies.  The ModuleLibrary widget is free to
load QPixmaps (or anything else) based on these file paths.

Usage
-----
from resources_loader import IconFiles

print(IconFiles.names)        # ['door00', 'window00', ...]
png_path = IconFiles.paths['door00']   # Path object
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple

# Type alias for clarity: Dict[icon_name, icon_path]
IconSet = Dict[str, Path]


class IconFiles:
    """
    A static catalogue of categorized PNG icon files.

    Scans for subdirectories within the main 'resources' folder, treating
    each subdirectory as a distinct category or set of icons.
    """
    folder: Path = Path(__file__).parent.parent / "resources"

    # The main data structure: Dict[category_name, IconSet]
    # Example: {"default_set": {"window00": Path(...), ...}, "modern_set": {...}}
    categories: Dict[str, IconSet] = {}

    @classmethod
    def _scan(cls) -> None:
        """
        Scans for subdirectories in the 'resources' folder and populates the
        `categories` dictionary.
        """
        if not cls.folder.is_dir():
            raise FileNotFoundError(f"Resources folder not found: {cls.folder}")

        cls.categories = {}
        # Iterate through each item in the resources folder
        for category_path in cls.folder.iterdir():
            if category_path.is_dir():
                category_name = category_path.name
                icon_set: IconSet = {}
                # Scan for .png files within this subdirectory
                for png_file in category_path.glob("*.png"):
                    icon_set[png_file.stem] = png_file

                if icon_set:  # Only add categories that contain icons
                    cls.categories[category_name] = icon_set

    @classmethod
    def get_category_names(cls) -> List[str]:
        """Returns a sorted list of all discovered category names."""
        return sorted(cls.categories.keys())

    @classmethod
    def get_icons_for_category(cls, category_name: str) -> IconSet:
        """
        Returns the set of icons for a given category.

        Returns an empty dictionary if the category does not exist.
        """
        return cls.categories.get(category_name, {})

    @classmethod
    def reload(cls) -> None:
        """Forces a re-scan of the entire resources directory structure."""
        cls._scan()


# Initialize the catalogue on module import.
IconFiles._scan()


# A simple command-line interface for verification (smoke test).
# This block only runs when the script is executed directly.
if __name__ == "__main__":
    print(f"Scanning for icons in: '{IconFiles.folder.resolve()}'")
    if IconFiles.names:
        print(f"Found {len(IconFiles.names)} PNG icon(s):")
        for name in sorted(IconFiles.names):
            print(f"  • {name}")
    else:
        print("No PNG icons found in the specified directory.")