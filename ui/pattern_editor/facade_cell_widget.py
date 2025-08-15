from __future__ import annotations
import json

from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget, QSizePolicy
from PySide6.QtGui import QMouseEvent


from domain.grammar import REPEATABLE, RIGID
from ui.pattern_editor.module_item import (
    GroupWidget, ModuleWidget, _cleanup_empty_group, GroupKind
)

# NOTE: The entire StripHeader class has been REMOVED from this file.
# Its logic will be moved to a new 'floor_header_widget.py' file.

# ===================================================================
# FacadeCellWidget: The new, simplified component
# ===================================================================

class FacadeCellWidget(QFrame):
    """
    A container for a single facade's worth of modules. It acts as a drop
    target and holds a horizontal list of GroupWidgets.

    This class has been simplified from the original FacadeStrip to remove all
    header and floor-management logic, making it a pure, reusable component.
    """
    # This signal is still crucial. It will notify the parent (FloorRowWidget)
    # that its content has changed, triggering a regeneration of the JSON output.
    structureChanged = Signal()

    # NOTE: The constructor is now much simpler.
    def __init__(self, mode: str = REPEATABLE, parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = mode
        self.setAcceptDrops(True)
        self.setMinimumHeight(60) # Use min height instead of fixed
        self.setMinimumWidth(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setObjectName("FacadeCellWidget")

        # A border will visually separate the four cells.
        self.setStyleSheet("""
            QFrame#FacadeCellWidget {
                background-color: #4a4a4a;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)

        # The root layout now directly contains the module layout. No header.
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(5)

        # This layout is the direct target for modules and groups.
        self.module_container_layout = QHBoxLayout()
        self.module_container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        root_layout.addLayout(self.module_container_layout, 1)

        # The drop indicator remains, as it's part of the cell's own logic.
        self._indicator = QWidget()
        self._indicator.setFixedSize(10, 50) # Adjusted size slightly
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

    # NOTE: All header and floor-related methods have been REMOVED.
    # - set_header_visibility() is gone.
    # - mousePressEvent for dragging the whole strip is gone.
    # - Signals like remove_requested, move_up_requested are gone.

    def dragEnterEvent(self, e: QMouseEvent):
        """Accepts drags if they contain a module, or a group in 'structured' mode."""
        mime_data = e.mimeData()
        can_drop_module = mime_data.hasFormat("application/x-ibg-module")
        can_drop_group = self.mode == REPEATABLE and mime_data.hasFormat("application/x-ibg-group")

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

        if mime_data.hasFormat("application/x-ibg-module"):
            data = json.loads(mime_data.data("application/x-ibg-module").data())
            group = self._find_or_create_sandbox_group() if self.mode == RIGID else GroupWidget(parent=self)

            if self.mode == REPEATABLE:
                group.structureChanged.connect(self.structureChanged.emit)
                self.module_container_layout.insertWidget(insert_pos, group)

            module = ModuleWidget(data["name"], False) if data.get("from_library") else e.source()
            group_insert_pos = group.layout().count() if self.mode == RIGID else 0
            group.layout().insertWidget(group_insert_pos, module)

            if not data.get("from_library"):
                module.show()
                _cleanup_empty_group(module._origin_layout, self)

            e.acceptProposedAction()
            self.structureChanged.emit()

        elif self.mode == REPEATABLE and mime_data.hasFormat("application/x-ibg-group"):
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
        for i in range(self.module_container_layout.count()):
            widget = self.module_container_layout.itemAt(i).widget()
            if isinstance(widget, GroupWidget):
                return widget

        new_group = GroupWidget(kind=GroupKind.RIGID, parent=self)
        new_group.setStyleSheet("QFrame { background: transparent; border: none; }")
        new_group.structureChanged.connect(self.structureChanged.emit)
        self.module_container_layout.addWidget(new_group)
        return new_group

    def _insert_index(self, mouse_x: int) -> int:
        """Calculates the insert index for a new widget based on the mouse's X-position."""
        # NOTE: This logic is simpler now as there is no header width to account for.
        for i in range(self.module_container_layout.count()):
            widget = self.module_container_layout.itemAt(i).widget()
            if widget and widget is not self._indicator:
                # The drop zone is the first half of the widget's width.
                drop_zone_end = widget.x() + (widget.width() / 2)
                if mouse_x < drop_zone_end:
                    return i
        return self.module_container_layout.count()

    def _remove_indicator(self):
        """Removes the drop indicator widget from the layout and hides it."""
        if self._indicator.parent():
            if layout := self._indicator.parent().layout():
                layout.removeWidget(self._indicator)
        self._indicator.setParent(None)
        self._indicator.hide()