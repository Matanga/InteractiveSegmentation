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
# ===================================================================
class StripHeader(QWidget):
    """
    A widget that displays the floor name and a remove button.
    It is positioned at the start of a FacadeStrip.
    """
    remove_requested = Signal(object)
    move_up_requested = Signal(object)
    move_down_requested = Signal(object)


    def __init__(self, parent_strip: "FacadeStrip"):
        super().__init__(parent_strip)
        self.parent_strip = parent_strip
        self.setObjectName("StripHeader")

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("FloorNameEdit")

        # --- Create Remove, Up and Down buttons ---
        self.up_button = QPushButton("▲")
        self.up_button.setObjectName("MoveButton")
        self.up_button.setToolTip("Move floor up")

        self.down_button = QPushButton("▼")
        self.down_button.setObjectName("MoveButton")
        self.down_button.setToolTip("Move floor down")

        self.remove_button = QPushButton("X")
        self.remove_button.setObjectName("RemoveButton")
        self.remove_button.setToolTip("Remove this floor")
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.parent_strip))

        # --- Connections ---
        self.up_button.clicked.connect(lambda: self.move_up_requested.emit(self.parent_strip))
        self.down_button.clicked.connect(lambda: self.move_down_requested.emit(self.parent_strip))
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.parent_strip))


        # --- Layouts ---
        # A horizontal layout for the buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(4)
        button_layout.addWidget(self.up_button)
        button_layout.addWidget(self.down_button)
        button_layout.addStretch() # Push the remove button to the right
        button_layout.addWidget(self.remove_button)

        # The main vertical layout for the header
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.addLayout(button_layout) # Button row is on top
        layout.addWidget(self.name_edit)
        layout.addStretch()
        self.setFixedWidth(150)
        self.setStyleSheet("""
            QWidget#StripHeader { background-color: #383838; border-radius: 4px; }
            QLineEdit#FloorNameEdit { font-weight: bold; color: #e0e0e0; border: 1px solid #555; padding: 4px; background-color: #484848; }
            QPushButton#RemoveButton { font-family: "Segoe UI", Arial, sans-serif; font-weight: bold; font-size: 14px; color: #aaa; background-color: #484848; border: 1px solid #555; }
            QPushButton#RemoveButton:hover { background-color: #d14545; color: white; border-color: #ff6a6a; }
            QPushButton#RemoveButton:pressed { background-color: #a13535; }
        """)

    def update_label(self, floor_index: int):
        """Sets the floor name text based on its index."""
        floor_text = "Ground Floor" if floor_index == 0 else f"Floor {floor_index}"
        self.name_edit.setText(floor_text)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Ensures custom styling is applied correctly."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)


# ===================================================================
# FacadeStrip: The main component, mode-aware
# ===================================================================
class FacadeStrip(QFrame):
    """
    A container for a single floor (strip) in the facade editor.
    It can operate in 'structured' mode (with groups and a header) or
    'sandbox' mode (a simple container for modules).
    """
    structureChanged = Signal()
    remove_requested = Signal(object)
    move_up_requested = Signal(object)
    move_down_requested = Signal(object)

    def __init__(self, floor_idx: int, mode: str = "repeatable", parent=None):
        super().__init__(parent)
        self.floor_index = floor_idx
        self.mode = mode
        self.setAcceptDrops(True)
        self.setFixedHeight(60)
        self.setMinimumWidth(240)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setObjectName("FacadeStrip")
        self.setStyleSheet("QFrame#FacadeStrip { background-color: #4a4a4a; border: 1px solid #5a5a5a; border-radius: 4px; }")
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(5)

        self.header = StripHeader(self)
        # Pass the signals up from the header to the strip
        self.header.remove_requested.connect(self.remove_requested)
        self.header.move_up_requested.connect(self.move_up_requested)
        self.header.move_down_requested.connect(self.move_down_requested)
        root_layout.addWidget(self.header)


        self.module_container_layout = QHBoxLayout()
        self.module_container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        root_layout.addLayout(self.module_container_layout, 1)

        self._indicator = QWidget()
        self._indicator.setFixedSize(10, 60)
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

        self.header.update_label(self.floor_index)


    def set_header_visibility(self, visible: bool):
        """Public method to show or hide the header."""
        self.header.setVisible(visible)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        """Initiates a drag operation for the entire strip in 'structured' mode."""
        if self.mode == "repeatable" and e.button() == Qt.LeftButton:
            mime = QMimeData()
            mime.setData("application/x-facade-strip", b"")
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.setHotSpot(e.position().toPoint())
            self.hide()
            if drag.exec(Qt.MoveAction) == Qt.IgnoreAction:
                self.show()

    def dragEnterEvent(self, e: QMouseEvent):
        """Accepts drags if they contain a module, or a group in 'structured' mode."""
        mime_data = e.mimeData()
        can_drop_module = mime_data.hasFormat("application/x-ibg-module")
        can_drop_group = self.mode == "repeatable" and mime_data.hasFormat("application/x-ibg-group")

        if can_drop_module or can_drop_group:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e: QMouseEvent):
        """Shows a visual indicator at the potential drop position."""
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator()
        self.module_container_layout.insertWidget(idx, self._indicator)
        self._indicator.show()
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e: QMouseEvent):
        """Hides the drop indicator when the drag leaves the widget."""
        self._remove_indicator()

    def dropEvent(self, e: QMouseEvent) -> None:
        """Handles dropping a module or a group onto the strip."""
        self._remove_indicator()
        mime_data = e.mimeData()
        insert_pos = self._insert_index(e.position().toPoint().x())

        # Case 1: A module is dropped
        if mime_data.hasFormat("application/x-ibg-module"):
            data = json.loads(mime_data.data("application/x-ibg-module").data())
            # In structured mode, create a new group. In sandbox, find the single group.
            group = self._find_or_create_sandbox_group() if self.mode == "rigid" else GroupWidget(parent=self)

            if self.mode == "repeatable":
                group.structureChanged.connect(self.structureChanged.emit)
                self.module_container_layout.insertWidget(insert_pos, group)

            module = ModuleWidget(data["name"], False) if data.get("from_library") else e.source()
            group_insert_pos = group.layout().count() if self.mode == "rigid" else 0
            group.layout().insertWidget(group_insert_pos, module)

            # If the module was moved (not new), show it and clean up its original container.
            if not data.get("from_library"):
                module.show()
                _cleanup_empty_group(module._origin_layout, self)

            e.acceptProposedAction()
            self.structureChanged.emit()

        # Case 2: A group is dropped (only in 'structured' mode)
        elif self.mode == "repeatable" and mime_data.hasFormat("application/x-ibg-group"):
            group_widget: GroupWidget = e.source()
            group_widget.structureChanged.connect(self.structureChanged.emit)
            self.module_container_layout.insertWidget(insert_pos, group_widget)
            group_widget.show()
            e.acceptProposedAction()
            self.structureChanged.emit()

    def _find_or_create_sandbox_group(self) -> GroupWidget:
        """
        Finds the single group widget on the strip, or creates one if it doesn't exist.
        This is used in 'sandbox' mode to ensure all modules live in one group.
        """
        # Search for an existing group on this strip.
        for i in range(self.module_container_layout.count()):
            widget = self.module_container_layout.itemAt(i).widget()
            if isinstance(widget, GroupWidget):
                return widget

        # If no group is found, create a new one, styled for sandbox mode.
        new_group = GroupWidget(kind=GroupKind.RIGID, parent=self)
        new_group.setStyleSheet("QFrame { background: transparent; border: none; }")
        new_group.structureChanged.connect(self.structureChanged.emit)
        self.module_container_layout.addWidget(new_group)
        return new_group

    def _insert_index(self, mouse_x: int) -> int:
        """Calculates the insert index for a new widget based on the mouse's X-position."""
        # In structured mode, the header takes up space that must be accounted for.
        header_width = self.header.width() if self.mode == "repeatable" else 0

        for i in range(self.module_container_layout.count()):
            widget = self.module_container_layout.itemAt(i).widget()
            # Ensure we don't check against the indicator widget itself.
            if widget and widget is not self._indicator:
                drop_zone_end = header_width + widget.x() + (widget.width() / 2)
                if mouse_x < drop_zone_end:
                    return i

        # If the drop is after all existing widgets, return the count to append.
        return self.module_container_layout.count()

    def _remove_indicator(self):
        """Removes the drop indicator widget from the layout and hides it."""
        if self._indicator.parent():
            if layout := self._indicator.parent().layout():
                layout.removeWidget(self._indicator)
        self._indicator.setParent(None)
        self._indicator.hide()