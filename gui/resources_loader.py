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
from typing import Dict, List


class IconFiles:
    """
    A static catalogue of all PNG icon files in the 'resources' directory.

    This class automatically scans the resources folder upon module import and
    populates its class-level attributes with the names and paths of all
    found .png files. It provides a simple, dependency-free way for other
    parts of the application to access icon information.

    Attributes:
        folder (Path): The path to the 'resources' directory.
        names (List[str]): A list of icon names (file stems).
        paths (Dict[str, Path]): A dictionary mapping icon names to their full Path objects.
    """

    folder: Path = Path(__file__).parent.parent / "resources"
    names: List[str] = []
    paths: Dict[str, Path] = {}

    @classmethod
    def _scan(cls) -> None:
        """
        Scans the 'resources' folder and populates the `names` and `paths` attributes.

        This internal method is called automatically when the module is imported.
        It clears any existing data before scanning.

        Raises:
            FileNotFoundError: If the 'resources' directory does not exist.
        """
        if not cls.folder.is_dir():
            raise FileNotFoundError(f"Resources folder not found: {cls.folder}")

        # Reset the lists before re-populating them.
        cls.names = []
        cls.paths = {}
        for png in cls.folder.glob("*.png"):
            cls.names.append(png.stem)
            cls.paths[png.stem] = png

    @classmethod
    def reload(cls) -> None:
        """
        Forces a re-scan of the resources folder.

        This is useful if icons are added, removed, or renamed at runtime
        after the initial module import.
        """
        cls._scan()

    @classmethod
    def list(cls) -> List[str]:
        """
        Returns a defensive copy of the list of icon names.

        Returns:
            A new list containing all discovered icon names.
        """
        return cls.names.copy()


# Initialize the catalogue by scanning the folder when the module is first imported.
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