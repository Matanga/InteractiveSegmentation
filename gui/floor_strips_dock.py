# ibg_pe/gui/floor_strips_dock.py
from __future__ import annotations

from PySide6.QtWidgets import QDockWidget, QScrollArea, QWidget, QVBoxLayout
from PySide6.QtCore import Signal
from  PySide6 import QtCore
from PySide6.QtCore import Qt

from .floor_strip import FloorStrip


class FloorStripsDock(QDockWidget):
    """Hosts a vertical stack of `FloorStrip` widgets, one per floor."""

    floor_selected: Signal = Signal(int)  # floor index (0 = roof)

    def __init__(self, title: str, parent: None = None) -> None:
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)

        scroll = QScrollArea(self)
        container = QWidget(scroll)
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(2)
        self._layout.setContentsMargins(2, 2, 2, 2)

        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        self.setWidget(scroll)

    # ---------- API --------------------------------------------------------
    def populate_from_pattern(self, pattern: "building_grammar.Pattern") -> None:  # noqa: F821
        """Rebuild all strips to mirror the given domain pattern."""
        # Clear old strips
        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().deleteLater()

        # Re-create
        for floor_idx, groups in enumerate(pattern.floors):
            strip = FloorStrip(floor_idx, groups, self)
            strip.clicked.connect(self.floor_selected)  # pass through
            self._layout.addWidget(strip)

        self._layout.addStretch(1)
