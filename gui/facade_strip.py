# facade_strip.py (Incrementally adding features)

from __future__ import annotations
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPaintEvent, QPainter
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QWidget, QSizePolicy, QVBoxLayout, QLineEdit, QPushButton, QStyle, QStyleOption
)
from module_item import GroupWidget, ModuleWidget, _cleanup_empty_group


class StripHeader(QWidget):
    """A dedicated widget for a strip's metadata: its name and remove button."""
    remove_requested = Signal(object)

    def __init__(self, parent_strip: "FacadeStrip"):
        super().__init__(parent_strip)
        self.parent_strip = parent_strip
        self.setObjectName("StripHeader")

        # --- Widgets ---
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("FloorNameEdit")

        self.remove_button = QPushButton("X")
        self.remove_button.setObjectName("RemoveButton")
        self.remove_button.setFixedSize(40, 30)
        self.remove_button.setToolTip("Remove this floor")
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.parent_strip))

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(4)
        layout.addWidget(self.name_edit)
        layout.addWidget(self.remove_button, 0, Qt.AlignLeft)
        layout.addStretch()

        self.setFixedWidth(120)

        # --- Styling ---
        self.setStyleSheet("""
            /* <<< FIX: Background now applies correctly due to paintEvent. */
            QWidget#StripHeader {
                background-color: #383838; /* Slightly darker background */
                border-radius: 4px;
            }

            QLineEdit#FloorNameEdit {
                font-weight: bold;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                background-color: #484848;
            }

            QPushButton#RemoveButton {
                font-family: "Segoe UI", Arial, sans-serif;
                font-weight: bold;
                font-size: 14px;
                color: #aaa;
                /* <<< FIX: Give it a subtle background by default to be visible. */
                background-color: #484848;
                border: 1px solid #555;
                border-radius: 11px; /* Make it circular */
            }
            QPushButton#RemoveButton:hover {
                background-color: #d14545; /* Red background on hover */
                color: white;
                border-color: #ff6a6a;
            }
            QPushButton#RemoveButton:pressed {
                background-color: #a13535;
            }
        """)

    def update_label(self, floor_index: int):
        """Updates the text based on the floor index."""
        floor_text = "Ground Floor" if floor_index == 0 else f"Floor {floor_index}"
        self.name_edit.setText(floor_text)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        <<< FIX: Add paintEvent to enable custom widget styling.

        This is standard boilerplate required for QSS background-color and
        border properties to work reliably on a plain QWidget subclass.
        """
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

class FacadeStrip(QFrame):
    structureChanged = Signal() # <<< NEW SIGNAL

    def __init__(self, floor_idx: int, parent=None):
        super().__init__(parent)
        self.floor_index = floor_idx
        self.setAcceptDrops(True)
        self.setFixedHeight(80)
        self.setMinimumWidth(240)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setObjectName("FacadeStrip")
        self.setStyleSheet(
            "QFrame#FacadeStrip { background-color: #4a4a4a; border: 1px solid #5a5a5a; border-radius: 4px; }")

        # --- Main Layout: Header | Droppable Area ---
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(5, 5, 5, 5)
        root_layout.setSpacing(10)

        # 1. The Header Widget (contains name and remove button)
        self.header = StripHeader(self)
        root_layout.addWidget(self.header)

        # 2. The Droppable Area for Modules
        self.module_container_layout = QHBoxLayout()
        self.module_container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        root_layout.addLayout(self.module_container_layout, 1)  # Give it stretch

        # --- Drag-and-drop indicator ---
        self._indicator = QWidget()
        self._indicator.setFixedSize(10, 60)
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

        # Initial label update
        self.header.update_label(self.floor_index)

    # ... The drag-and-drop logic for receiving modules is exactly the same as before ...
    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasFormat("application/x-ibg-module") or e.mimeData().hasFormat(
            "application/x-ibg-group"): e.acceptProposedAction()

    def dragMoveEvent(self, e) -> None:
        if not (e.mimeData().hasFormat("application/x-ibg-module") or e.mimeData().hasFormat(
            "application/x-ibg-group")): return
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator();
        self.module_container_layout.insertWidget(idx, self._indicator);
        self._indicator.show();
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e) -> None:
        self._remove_indicator()

    def dropEvent(self, e) -> None:
        self._remove_indicator();
        idx = self._insert_index(e.position().toPoint().x())
        if e.mimeData().hasFormat("application/x-ibg-module"):
            data = json.loads(e.mimeData().data("application/x-ibg-module").data())
            grp = GroupWidget();
            grp.structureChanged.connect(self.structureChanged.emit)

            self.module_container_layout.insertWidget(idx, grp)
            w = ModuleWidget(data["name"], False) if data.get("from_library") else e.source()
            grp.layout().addWidget(w)
            if not data.get("from_library"): w.show()
            e.acceptProposedAction()
            if not data.get("from_library"): _cleanup_empty_group(w._origin_layout)
            self.structureChanged.emit() # <<< EMIT after drop
            return
        if e.mimeData().hasFormat("application/x-ibg-group"):
            w: GroupWidget = e.source();
            w.structureChanged.connect(self.structureChanged.emit)
            self.module_container_layout.insertWidget(idx, w);
            w.show();
            e.acceptProposedAction()
            self.structureChanged.emit() # <<< EMIT after drop

    def _insert_index(self, mouse_x: int) -> int:
        for i in range(self.module_container_layout.count()):
            w = self.module_container_layout.itemAt(i).widget()
            if w and w is not self._indicator:
                # Adjust for the header width when calculating drop position
                if mouse_x < self.header.width() + w.x() + w.width() / 2: return i
        return self.module_container_layout.count()

    def _remove_indicator(self) -> None:
        if self._indicator.parent():
            layout = self._indicator.parent().layout()
            if layout: layout.removeWidget(self._indicator)
        self._indicator.setParent(None);
        self._indicator.hide()