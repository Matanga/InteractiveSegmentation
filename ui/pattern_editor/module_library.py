from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QComboBox
)

from ui.pattern_editor.module_item import ModuleWidget
from services.resources_loader import IconFiles


class ModuleLibrary(QWidget):
    """
    A scrollable and responsive icon palette for available modules.

    This widget displays all available `ModuleWidget` items in a grid that
    automatically reflows to fit the widget's width. It also includes a
    button to add new icons to the library at runtime.
    """

    categoryChanged = Signal(str)

    # --- Constants for layout ---
    ICON_SIZE = 48  # The logical size (width and height) for each icon in pixels.
    PADDING = 4    # The spacing between grid cells in pixels.

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initializes the ModuleLibrary widget."""
        super().__init__(parent)
        self.setObjectName("ModuleLibrary")  # For QSS styling

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(2, 2, 2, 2)
        root_layout.setSpacing(5)

        # --- Category Selector Dropdown ---
        self.category_selector = QComboBox()
        self.category_selector.addItems(IconFiles.get_category_names())
        self.category_selector.currentTextChanged.connect(self.set_category)
        root_layout.addWidget(self.category_selector)

        # --- Scroll Area and Grid ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._content = QWidget()
        self._grid = QGridLayout(self._content)
        self._grid.setSpacing(self.PADDING)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft) # Align left for consistency
        scroll.setWidget(self._content)
        root_layout.addWidget(scroll)

        # --- Widget Initialization ---
        self._item_widgets: list[QWidget] = []
        self._add_btn = QPushButton("＋")
        self._add_btn.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._add_btn.clicked.connect(self._on_add_icon)

        # --- Styling ---
        # <<< FIX: Remove background color to blend with parent QGroupBox.
        self.setStyleSheet("QWidget#ModuleLibrary { background-color: transparent; }")

        # Load the initial category.
        if initial_category := self.category_selector.currentText():
            self.set_category(initial_category)


        # Apply a background color to distinguish the library from the canvas.
        self.setStyleSheet("""
            QWidget#ModuleLibrary {
                background-color: #f4f6f8;
            }
        """)

    def set_category(self, category_name: str) -> None:
        """
        Clears and rebuilds the icon palette to display modules from the
        specified category.
        """
        # 1. Get icon data for the selected category.
        icon_set = IconFiles.get_icons_for_category(category_name)

        # 2. Create and cache scaled pixmaps for this category.
        pixmap_cache = self._make_pixmap_cache(icon_set)
        ModuleWidget.ICONS = pixmap_cache # Update the global lookup

        # 3. Re-create the list of widgets to display.
        self._item_widgets = [self._add_btn]
        self._item_widgets.extend([
            ModuleWidget(name, is_library=True)
            for name in sorted(icon_set.keys())
        ])

        # 4. Trigger a re-layout and emit the change signal.
        self._relayout_items()
        self.categoryChanged.emit(category_name)

    def resizeEvent(self, event) -> None:
        """
        Overrides QWidget.resizeEvent to trigger a re-layout of the grid items
        whenever the library's size changes.
        """
        super().resizeEvent(event)
        self._relayout_items()


    def _relayout_items(self) -> None:
        """Arranges all item widgets into a responsive grid."""
        for i in reversed(range(self._grid.count())):
            if widget := self._grid.itemAt(i).widget():
                widget.setParent(None)

        cols = max(1, (self.width() // (self.ICON_SIZE + self.PADDING * 2)))
        for index, widget in enumerate(self._item_widgets):
            row, col = divmod(index, cols)
            self._grid.addWidget(widget, row, col)


    def _make_pixmap_cache(self, icon_set: dict[str, Path]) -> dict[str, QPixmap]:
        """Creates a cache of scaled QPixmaps for a given set of icons."""
        cache: dict[str, QPixmap] = {}
        for name, path in icon_set.items():
            pix = QPixmap(str(path)).scaled(
                self.ICON_SIZE, self.ICON_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            cache[name] = pix
        return cache



    def _on_add_icon(self) -> None:
        """
        Slot for the 'Add Icon' button.

        This method should handle the logic for adding a new icon file to the
        project's user_assets (e.g., by opening a file dialog) and then
        trigger a palette rebuild.
        """
        # --- (The logic for adding a new icon file is handled here) ---
        IconFiles.reload()
        self.category_selector.clear()
        self.category_selector.addItems(IconFiles.get_category_names())
        self._rebuild_palette()

    def _rebuild_palette(self) -> None:
        """
        Refreshes the entire icon palette from the source files.

        This is called after a new icon has been added to the user_assets. It
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