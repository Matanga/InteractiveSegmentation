# module_library.py (Refactored for clarity)

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from module_item import ModuleWidget
from resources_loader import IconFiles


class ModuleLibrary(QWidget):
    """
    A scrollable and responsive icon palette for available modules.

    This widget displays all available `ModuleWidget` items in a grid that
    automatically reflows to fit the widget's width. It also includes a
    button to add new icons to the library at runtime.
    """

    # --- Constants for layout ---
    ICON_SIZE = 48  # The logical size (width and height) for each icon in pixels.
    PADDING = 12    # The spacing between grid cells in pixels.

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initializes the ModuleLibrary widget."""
        super().__init__(parent)
        self.setObjectName("ModuleLibrary")  # For QSS styling

        # --- Data Initialization ---
        # Load and cache pixmaps from resources.
        self._pixmaps = self._make_pixmap_cache()
        # This is a critical step: it provides all ModuleWidget instances
        # with a global lookup for their icons, avoiding redundant loading.
        ModuleWidget.ICONS = self._pixmaps

        # --- UI Setup: Scroll Area and Grid ---
        # Use a QScrollArea for content that might overflow.
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)  # Allows the grid to use all available space.

        # The content widget holds the grid layout.
        self._content = QWidget()
        self._grid = QGridLayout(self._content)
        self._grid.setSpacing(self.PADDING)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        scroll.setWidget(self._content)

        # The main layout for this widget simply contains the scroll area.
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(scroll)

        # --- Widget Creation ---
        # Create and store all items that will be placed in the grid.
        self._item_widgets: list[QWidget] = []
        self._add_btn = QPushButton("＋", clicked=self._on_add_icon)
        self._add_btn.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._item_widgets.append(self._add_btn)

        # Create a draggable ModuleWidget for each cached pixmap.
        for name in sorted(self._pixmaps):
            self._item_widgets.append(ModuleWidget(name, is_library=True))

        self._relayout_items()

        # Apply a background color to distinguish the library from the canvas.
        self.setStyleSheet("""
            QWidget#ModuleLibrary {
                background-color: #f4f6f8;
            }
        """)

    def resizeEvent(self, event) -> None:
        """
        Overrides QWidget.resizeEvent to trigger a re-layout of the grid items
        whenever the library's size changes.
        """
        super().resizeEvent(event)
        self._relayout_items()

    def _relayout_items(self) -> None:
        """
        Arranges all item widgets into a responsive grid.

        This method first clears the existing grid, then calculates the optimal
        number of columns based on the current widget width, and finally
        re-populates the grid, causing the items to reflow.
        """
        # Clear all existing widgets from the grid layout. Iterating in reverse is
        # necessary because removing a widget from the layout by setting its
        # parent to None will shift the indices of subsequent items.
        for i in reversed(range(self._grid.count())):
            if widget := self._grid.itemAt(i).widget():
                widget.setParent(None)

        # Calculate the number of columns for the new layout.
        # This ensures the grid reflows based on the available width.
        cols = max(1, (self.width() // (self.ICON_SIZE + self.PADDING)))

        # Re-populate the grid with all stored item widgets.
        for index, widget in enumerate(self._item_widgets):
            row, col = divmod(index, cols)
            self._grid.addWidget(widget, row, col, Qt.AlignHCenter)

    def _make_pixmap_cache(self) -> dict[str, QPixmap]:
        """
        Loads all icon files specified by IconFiles, scales them, and
        stores them in a dictionary cache.

        Returns:
            A dictionary mapping icon names (str) to QPixmap objects.
        """
        cache: dict[str, QPixmap] = {}
        for name in IconFiles.names:
            pix = QPixmap(str(IconFiles.paths[name])).scaled(
                self.ICON_SIZE, self.ICON_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            cache[name] = pix
        return cache

    def _on_add_icon(self) -> None:
        """
        Slot for the 'Add Icon' button.

        This method should handle the logic for adding a new icon file to the
        project's resources (e.g., by opening a file dialog) and then
        trigger a palette rebuild.
        """
        # --- (The logic for adding a new icon file is handled here) ---
        ...
        self._rebuild_palette()

    def _rebuild_palette(self) -> None:
        """
        Refreshes the entire icon palette from the source files.

        This is called after a new icon has been added to the resources. It
        re-scans the icons, rebuilds the internal widget list, and triggers
        a re-layout of the grid.
        """
        # 1. Re-scan resource files and update the pixmap cache.
        self._pixmaps = self._make_pixmap_cache()
        ModuleWidget.ICONS = self._pixmaps  # Update the global icon lookup.

        # 2. Re-create the list of widgets to display.
        # The '+' button is always the first item.
        self._item_widgets = [self._add_btn]
        new_module_widgets = [
            ModuleWidget(name, is_library=True)
            for name in sorted(self._pixmaps)
        ]
        self._item_widgets.extend(new_module_widgets)

        # 3. Trigger a re-layout to display the updated set of icons.
        self._relayout_items()