# facade_strip.py (Refactored to be Mode-Aware)

from __future__ import annotations
import json
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QPaintEvent, QPainter, QMouseEvent, QDrag
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QWidget, QSizePolicy, QVBoxLayout, QLineEdit, QPushButton, QStyle, QStyleOption
)
from module_item import GroupWidget, ModuleWidget, _cleanup_empty_group, owning_layout, GroupKind


# ===================================================================
# StripHeader: The UI for floor name and remove button
# This component is unchanged but is used by the FacadeStrip.
# ===================================================================
class StripHeader(QWidget):
    remove_requested = Signal(object)

    def __init__(self, parent_strip: "FacadeStrip"):
        super().__init__(parent_strip)
        self.parent_strip = parent_strip
        self.setObjectName("StripHeader")
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("FloorNameEdit")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)
        self.remove_button = QPushButton(icon, "")
        self.remove_button.setObjectName("RemoveButton")
        self.remove_button.setFixedSize(22, 22)
        self.remove_button.setToolTip("Remove this floor")
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.parent_strip))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5);
        layout.setSpacing(4)
        layout.addWidget(self.name_edit);
        layout.addWidget(self.remove_button, 0, Qt.AlignLeft);
        layout.addStretch()
        self.setFixedWidth(120)
        self.setStyleSheet("""
            QWidget#StripHeader { background-color: #383838; border-radius: 4px; }
            QLineEdit#FloorNameEdit { font-weight: bold; color: #e0e0e0; border: 1px solid #555; border-radius: 3px; padding: 4px; background-color: #484848; }
            QPushButton#RemoveButton { font-family: "Segoe UI", Arial, sans-serif; font-weight: bold; font-size: 14px; color: #aaa; background-color: #484848; border: 1px solid #555; border-radius: 11px; }
            QPushButton#RemoveButton:hover { background-color: #d14545; color: white; border-color: #ff6a6a; }
            QPushButton#RemoveButton:pressed { background-color: #a13535; }
        """)

    def update_label(self, floor_index: int):
        floor_text = "Ground Floor" if floor_index == 0 else f"Floor {floor_index}"
        self.name_edit.setText(floor_text)

    def paintEvent(self, event: QPaintEvent) -> None:
        opt = QStyleOption();
        opt.initFrom(self);
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)


# ===================================================================
# FacadeStrip: The main component, now mode-aware
# ===================================================================
class FacadeStrip(QFrame):
    structureChanged = Signal()
    remove_requested = Signal(object)

    def __init__(self, floor_idx: int, mode: str = "structured", parent=None):
        super().__init__(parent)
        self.floor_index = floor_idx; self.mode = mode
        self.setAcceptDrops(True); self.setFixedHeight(80); self.setMinimumWidth(240)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setObjectName("FacadeStrip"); self.setStyleSheet("QFrame#FacadeStrip { background-color: #4a4a4a; border: 1px solid #5a5a5a; border-radius: 4px; }")
        root_layout = QHBoxLayout(self); root_layout.setContentsMargins(5, 5, 5, 5); root_layout.setSpacing(10)
        self.header = StripHeader(self); self.header.remove_requested.connect(self.remove_requested)
        root_layout.addWidget(self.header)
        self.module_container_layout = QHBoxLayout(); self.module_container_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root_layout.addLayout(self.module_container_layout, 1)
        self._indicator = QWidget(); self._indicator.setFixedSize(10, 60); self._indicator.setStyleSheet("background:red;"); self._indicator.hide()
        self.header.update_label(self.floor_index)

    def set_header_visibility(self, visible: bool):
        """Public method to show or hide the header."""
        self.header.setVisible(visible)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        # In structured mode, allow dragging the entire strip to re-order.
        if self.mode == "structured" and e.button() == Qt.LeftButton:
            mime = QMimeData();
            mime.setData("application/x-facade-strip", b"")
            drag = QDrag(self);
            drag.setMimeData(mime);
            drag.setPixmap(self.grab());
            drag.setHotSpot(e.position().toPoint())
            self.hide()
            if drag.exec(Qt.MoveAction) == Qt.IgnoreAction: self.show()

    def dropEvent(self, e: QMouseEvent) -> None:
        self._remove_indicator()
        idx = self._insert_index(e.position().toPoint().x())
        if e.mimeData().hasFormat("application/x-ibg-module"):
            data = json.loads(e.mimeData().data("application/x-ibg-module").data())
            if self.mode == "structured":
                grp = GroupWidget();
                grp.structureChanged.connect(self.structureChanged.emit);
                self.module_container_layout.insertWidget(idx, grp)
            else:
                grp = self._find_or_create_sandbox_group()
            w = ModuleWidget(data["name"], False) if data.get("from_library") else e.source()
            group_idx = grp.layout().count() if self.mode == "sandbox" else 0
            grp.layout().insertWidget(group_idx, w)
            if not data.get("from_library"): w.show()
            e.acceptProposedAction();
            _cleanup_empty_group(w._origin_layout, self);
            self.structureChanged.emit()
            return
        if self.mode == "structured" and e.mimeData().hasFormat("application/x-ibg-group"):
            w: GroupWidget = e.source();
            w.structureChanged.connect(self.structureChanged.emit);
            self.module_container_layout.insertWidget(idx, w);
            w.show();
            e.acceptProposedAction();
            self.structureChanged.emit()

    def _find_or_create_sandbox_group(self) -> GroupWidget:
        for i in range(self.module_container_layout.count()):
            if isinstance(widget := self.module_container_layout.itemAt(i).widget(), GroupWidget): return widget
        new_grp = GroupWidget(kind=GroupKind.RIGID);
        new_grp.setStyleSheet("QFrame { background: transparent; border: none; }")

        new_grp.structureChanged.connect(self.structureChanged.emit);
        self.module_container_layout.addWidget(new_grp)
        return new_grp

    def mousePressEvent(self, e: QMouseEvent):
        if self.mode == "structured" and e.button() == Qt.LeftButton:
            mime = QMimeData();
            mime.setData("application/x-facade-strip", b"")
            drag = QDrag(self);
            drag.setMimeData(mime);
            drag.setPixmap(self.grab());
            drag.setHotSpot(e.position().toPoint())
            self.hide()
            if drag.exec(Qt.MoveAction) == Qt.IgnoreAction: self.show()

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/x-ibg-module"): e.acceptProposedAction()
        if self.mode == "structured" and e.mimeData().hasFormat("application/x-ibg-group"): e.acceptProposedAction()

    def dragMoveEvent(self, e):
        idx = self._insert_index(e.position().toPoint().x());
        self._remove_indicator();
        self.module_container_layout.insertWidget(idx, self._indicator);
        self._indicator.show();
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e):
        self._remove_indicator()

    def _insert_index(self, mouse_x: int):
        for i in range(self.module_container_layout.count()):
            if w := self.module_container_layout.itemAt(i).widget():
                if w is not self._indicator:
                    header_width = self.header.width() if self.header.isVisible() else 0
                    if mouse_x < header_width + w.x() + w.width() / 2: return i
        return self.module_container_layout.count()

    def _remove_indicator(self):
        if self._indicator.parent():
            if layout := self._indicator.parent().layout(): layout.removeWidget(self._indicator)
        self._indicator.setParent(None);
        self._indicator.hide()
    def _find_or_create_sandbox_group(self) -> GroupWidget:
        """Helper for sandbox mode to ensure only one group exists per strip."""
        # Search for an existing group on this strip.
        for i in range(self.module_container_layout.count()):
            widget = self.module_container_layout.itemAt(i).widget()
            if isinstance(widget, GroupWidget):
                return widget

        # If no group is found, create a new one.
        new_grp = GroupWidget(kind=GroupKind.RIGID, parent=self)
        new_grp.structureChanged.connect(self.structureChanged.emit)
        self.module_container_layout.addWidget(new_grp)
        return new_grp

    # --- Other methods are mostly unchanged ---
    def dragEnterEvent(self, e):
        # Allow dropping groups only in structured mode.
        if self.mode == "structured" and e.mimeData().hasFormat("application/x-ibg-group"):
            e.acceptProposedAction()
        if e.mimeData().hasFormat("application/x-ibg-module"):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        # ... (no changes needed here)
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator();
        self.module_container_layout.insertWidget(idx, self._indicator);
        self._indicator.show();
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e):
        self._remove_indicator()

    def _insert_index(self, mouse_x: int) -> int:
        for i in range(self.module_container_layout.count()):
            w = self.module_container_layout.itemAt(i).widget()
            if w and w is not self._indicator:
                # Adjust for header width when calculating drop position
                header_width = self.header.width() if self.mode == "structured" else 0
                if mouse_x < header_width + w.x() + w.width() / 2: return i
        return self.module_container_layout.count()

    def _remove_indicator(self):
        if self._indicator.parent():
            if layout := self._indicator.parent().layout(): layout.removeWidget(self._indicator)
        self._indicator.setParent(None);
        self._indicator.hide()