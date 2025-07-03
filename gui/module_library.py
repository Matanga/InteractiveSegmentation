from __future__ import annotations


from pathlib import Path
from resources_loader import IconFiles
from module_item import ModuleWidget


from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QGridLayout
)


class ModuleLibrary(QWidget):
    """Icon palette that automatically flows into a grid and is scrollable."""

    ICON_SIZE   = 48          # logical icon side in px
    PADDING     = 12          # spacing between cells

    # ------------------------------------------------------------------ #
    # constructor
    # ------------------------------------------------------------------ #
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ModuleLibrary")                # for QSS
        self._pixmaps = self._make_pixmap_cache()
        ModuleWidget.ICONS = self._pixmaps                 # global lookup

        # ---- outer wrapper (scroll-area) ------------------------------
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        self._content = QWidget()                          # holds the grid
        self._grid    = QGridLayout(self._content)
        self._grid.setSpacing(self.PADDING)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        scroll.setWidget(self._content)

        # ---- top-level layout -----------------------------------------
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(scroll)

        # ---- '+' button + icons ---------------------------------------
        self._item_widgets: list[QWidget] = []
        self._add_btn = QPushButton("＋", clicked=self._on_add_icon)
        self._add_btn.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._item_widgets.append(self._add_btn)

        for name in sorted(self._pixmaps):
            self._item_widgets.append(ModuleWidget(name, is_library=True))

        self._relayout_items()

        # ---- subtle background so it pops out -------------------------
        self.setStyleSheet("""
            QWidget#ModuleLibrary {            /* only this widget */
                background-color: #f4f6f8;     /* light grey */
            }
        """)

    # ------------------------------------------------------------------ #
    # layout helpers
    # ------------------------------------------------------------------ #
    def resizeEvent(self, event):                 # rewrap on dock-resize
        super().resizeEvent(event)
        self._relayout_items()

    def _relayout_items(self) -> None:
        """Place all widgets into a grid that wraps on width change."""
        for i in reversed(range(self._grid.count())):
            self._grid.itemAt(i).widget().setParent(None)

        cols = max(1, (self.width() // (self.ICON_SIZE + self.PADDING)))
        for index, widget in enumerate(self._item_widgets):
            row, col = divmod(index, cols)
            self._grid.addWidget(widget, row, col, Qt.AlignHCenter)

    # ------------------------------------------------------------------ #
    # pixmap cache
    # ------------------------------------------------------------------ #
    def _make_pixmap_cache(self) -> dict[str, QPixmap]:
        cache: dict[str, QPixmap] = {}
        for name in IconFiles.names:
            pix = QPixmap(str(IconFiles.paths[name])).scaled(
                self.ICON_SIZE, self.ICON_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            cache[name] = pix
        return cache

    # ------------------------------------------------------------------ #
    # '+' button handler – unchanged logic
    # ------------------------------------------------------------------ #
    def _on_add_icon(self) -> None:      # [snip] identical to old version
        ...
        self._rebuild_palette()

    def _rebuild_palette(self) -> None:
        """Refresh pixmap cache and grid after a new PNG is added."""
        self._pixmaps = self._make_pixmap_cache()
        ModuleWidget.ICONS = self._pixmaps

        # wipe items except '+'
        self._item_widgets = [self._add_btn] + [
            ModuleWidget(name, is_library=True)
            for name in sorted(self._pixmaps)
        ]
        self._relayout_items()
