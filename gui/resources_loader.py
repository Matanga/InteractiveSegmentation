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
    """Simple, auto-initialised catalogue of PNG files."""

    folder: Path = Path(__file__).parent.parent / "resources"
    names: List[str] = []          # ['door00', 'window00', ...]
    paths: Dict[str, Path] = {}    # {'door00': Path('…/door00.png'), …}

    # ------- internal ----------------------------------------------------
    @classmethod
    def _scan(cls) -> None:
        """Populate *names* and *paths* once at import-time."""
        if not cls.folder.is_dir():
            raise FileNotFoundError(f"Resources folder not found: {cls.folder}")

        cls.names = []
        cls.paths = {}
        for png in cls.folder.glob("*.png"):
            cls.names.append(png.stem)
            cls.paths[png.stem] = png

    # ------- convenience helpers ----------------------------------------
    @classmethod
    def reload(cls) -> None:
        """Re-scan the folder (e.g. after user adds files at runtime)."""
        cls._scan()

    @classmethod
    def list(cls) -> List[str]:
        """Return a *copy* of the icon name list."""
        return cls.names.copy()


# auto-initialise on module import
IconFiles._scan()


# ------------------------------------------------------------------------
# quick CLI smoke-test
# ------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Scanning '{IconFiles.folder.resolve()}' …")
    print(f"Found {len(IconFiles.names)} PNG icon(s):")
    for name in sorted(IconFiles.names):
        print(f"  • {name}")
