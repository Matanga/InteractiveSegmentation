from __future__ import annotations
import json

from PySide6.QtCore import Qt, Signal, QMimeData, QVariantAnimation, QEasingCurve
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget, QSizePolicy
from PySide6.QtGui import QMouseEvent, QColor

from domain.grammar import REPEATABLE, RIGID
from ui.pattern_editor.module_item import (
    GroupWidget, ModuleWidget, _cleanup_empty_group, GroupKind
)


class FacadeCellWidget(QFrame):
    """
    A container for a single facade's worth of modules that supports a
    smooth, animated highlight effect.
    """
    structureChanged = Signal()

    def __init__(self, mode: str = REPEATABLE, parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = mode
        self.setAcceptDrops(True)
        self.setMinimumHeight(60)
        self.setMinimumWidth(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setObjectName("FacadeCellWidget")

        # The initial stylesheet. The background color will be changed by the animation.
        self.setStyleSheet("""
            QFrame#FacadeCellWidget {
                background-color: #4a4a4a;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)

        # Main layout
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(5)

        self.module_container_layout = QHBoxLayout()
        self.module_container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        root_layout.addLayout(self.module_container_layout, 1)

        # Drop indicator
        self._indicator = QWidget()
        self._indicator.setFixedSize(10, 50)
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

        # Animation setup
        self.animation = QVariantAnimation(self)
        self.animation.valueChanged.connect(self._set_background_color)

    def _set_background_color(self, color: QColor):
        """Applies a background color to the widget's stylesheet."""
        self.setStyleSheet(f"""
            QFrame#FacadeCellWidget {{
                background-color: {color.name()};
                border: 1px solid #555;
                border-radius: 4px;
            }}
        """)

    def trigger_highlight(self):
        """
        Triggers a smooth fade-in and fade-out of the background color.
        """
        self.animation.stop()

        start_color = QColor("#4a4a4a")
        highlight_color = QColor("#A9A175")  # Desaturated yellow

        self.animation.setStartValue(start_color)
        self.animation.setKeyValueAt(0.3, highlight_color)
        self.animation.setEndValue(start_color)
        self.animation.setDuration(1200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.animation.start()

    # --- Drag-and-Drop and Helper Methods ---

    def dragEnterEvent(self, e: QMouseEvent):
        mime_data = e.mimeData()
        can_drop_module = mime_data.hasFormat("application/x-ibg-module")
        can_drop_group = self.mode == REPEATABLE and mime_data.hasFormat("application/x-ibg-group")
        if can_drop_module or can_drop_group:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e: QMouseEvent):
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator()
        self.module_container_layout.insertWidget(idx, self._indicator)
        self._indicator.show()
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e: QMouseEvent):
        self._remove_indicator()

    def dropEvent(self, e: QMouseEvent) -> None:
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
        for i in range(self.module_container_layout.count()):
            widget = self.module_container_layout.itemAt(i).widget()
            if widget and widget is not self._indicator:
                drop_zone_end = widget.x() + (widget.width() / 2)
                if mouse_x < drop_zone_end:
                    return i
        return self.module_container_layout.count()

    def _remove_indicator(self):
        if self._indicator.parent():
            if layout := self._indicator.parent().layout():
                layout.removeWidget(self._indicator)
        self._indicator.setParent(None)
        self._indicator.hide()