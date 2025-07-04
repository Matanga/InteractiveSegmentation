from __future__ import annotations

import json
from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import Qt, QByteArray, QMimeData, Signal
from PySide6.QtGui import QColor, QDrag, QMouseEvent, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLayout, QWidget

from actions import add_context_menu

# =========================================================================== #
# Domain Enums & Utilities
# =========================================================================== #


class GroupKind(Enum):
    """Defines the behavioral type of a group of modules."""
    FILL = auto()
    RIGID = auto()

    def colour(self) -> QColor:
        """Returns the representative color for the group kind."""
        return QColor("#f7d9b0") if self is GroupKind.FILL else QColor("#9ec3f7")

    def __str__(self) -> str:
        return self.name.lower()


def owning_layout(w: QWidget) -> Optional[QLayout]:
    """Finds the layout that directly contains the given widget."""
    parent = w.parent()
    if isinstance(parent, QWidget):
        return parent.layout()
    # Fallback for cases where the parent might be a layout itself (less common).
    if isinstance(parent, QLayout):
        return parent
    return None


def _cleanup_empty_group(layout: QLayout, emitter: QWidget) -> None:
    """
    Checks if a layout's parent GroupWidget is empty, and if so, removes it.

    This is called after a module is moved or removed to prevent empty group
    containers from persisting on the canvas.

    Args:
        layout: The layout of the group to check.
        emitter: The widget that should emit the structureChanged signal if the
                 group is deleted.
    """
    if not layout:
        return  # Safety check
    parent_group = layout.parent()
    if not isinstance(parent_group, GroupWidget):
        return

    # Check if any module widgets remain in the group.
    has_modules = any(
        isinstance(layout.itemAt(i).widget(), ModuleWidget)
        for i in range(layout.count())
    )

    if not has_modules:
        if strip_layout := owning_layout(parent_group):
            strip_layout.removeWidget(parent_group)
        parent_group.deleteLater()
        # Ensure the overall structure change is reported.
        emitter.structureChanged.emit()


# =========================================================================== #
# Draggable Module Widget
# =========================================================================== #


class ModuleWidget(QLabel):
    """
    A draggable widget representing a single building module.

    It can exist in a "library" state (template for creation) or a "canvas"
    state (an instance in a group). It emits a `structureChanged` signal when
    its state change requires the parent view to update.
    """
    ICONS: dict[str, QPixmap] = {}  # Populated once by ModuleLibrary
    structureChanged = Signal()

    def __init__(self, name: str, is_library: bool = False, parent: QWidget | None = None) -> None:
        """
        Initializes a ModuleWidget.

        Args:
            name: The canonical ID of the module.
            is_library: True if the widget is a template in the library palette.
            parent: Standard Qt parent.
        """
        super().__init__(parent)
        self.name = name
        self.is_library = is_library

        # Display an icon if available; otherwise, fall back to text.
        if name in ModuleWidget.ICONS:
            pix: QPixmap = ModuleWidget.ICONS[name]
            self.setPixmap(pix)
            self.setFixedSize(pix.width() + 4, pix.height() + 4)  # Margin
            self.setToolTip(name)  # Accessibility
        else:
            self.setText(name)
            self.setAlignment(Qt.AlignCenter)
            self._apply_palette()  # Style for text-based modules

        # State for tracking drag-and-drop origin.
        self._origin_layout: Optional[QLayout] = None
        self._origin_index: int = -1

        # Add context menu for removal only to instances on the canvas.
        if not self.is_library:
            self.setFocusPolicy(Qt.ClickFocus)
            add_context_menu(self, self._remove_self)

    def _remove_self(self) -> None:
        """Removes the widget from its layout and deletes it."""
        parent_layout = owning_layout(self)
        if parent_layout:
            parent_layout.removeWidget(self)
            self.deleteLater()
            # After removal, check if the parent group is now empty.
            _cleanup_empty_group(parent_layout, self)
        else:
            self.deleteLater()
            self.structureChanged.emit()

    def _apply_palette(self) -> None:
        """Applies a default visual style for text-based modules."""
        self.setStyleSheet("""
            QLabel {
                background: #ffffff;
                border: 1px solid #a0a0a0;
                padding: 4px;
                margin: 2px;
            }
        """)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        """Initiates a drag-and-drop operation for the module."""
        if e.button() != Qt.LeftButton:
            return

        # 1. Prepare MIME data with module information.
        mime = QMimeData()
        payload = json.dumps({
            "type": "module",
            "name": self.name,
            "from_library": self.is_library,
        }).encode()
        mime.setData("application/x-ibg-module", QByteArray(payload))

        # 2. Configure and start the drag operation.
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(e.pos())

        # 3. If moving an existing module, hide it and store its origin.
        if not self.is_library:
            self._origin_layout = owning_layout(self)
            if self._origin_layout:
                self._origin_index = self._origin_layout.indexOf(self)
                self._origin_layout.removeWidget(self)
            self.hide()

        # 4. Execute the drag loop.
        result = drag.exec(Qt.MoveAction)

        # 5. Finalize after the drag ends.
        if not self.is_library and self._origin_layout:
            if result != Qt.MoveAction:  # Drag was cancelled, so restore it.
                self._origin_layout.insertWidget(self._origin_index, self)
                self.show()
            else:  # Drag succeeded, so clean up its original group if it's now empty.
                _cleanup_empty_group(self._origin_layout, self)


# =========================================================================== #
# Group Container Widget
# =========================================================================== #


class GroupWidget(QFrame):
    """
    A container for ModuleWidgets that can be either 'RIGID' or 'FILL'.
    It accepts drops of modules and can itself be dragged and dropped.
    """
    structureChanged = Signal()

    def __init__(self, kind: GroupKind = GroupKind.FILL, parent: QWidget | None = None):
        super().__init__(parent)
        self.kind = kind
        self.repeat: int | None = None  # Reserved for future use
        self.setAcceptDrops(True)

        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(2, 2, 2, 2)
        self._lay.setSpacing(2)

        # A visual indicator for drop locations inside the group.
        self._indicator = QWidget()
        self._indicator.setFixedSize(6, 30)
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

        # State for tracking drag-and-drop origin.
        self._origin_strip: Optional[QLayout] = None
        self._origin_idx: int = -1

        self._apply_palette()

    def _apply_palette(self) -> None:
        """Applies styling based on the group's kind and its parent's mode."""
        parent_strip = self.parent()
        # Check if the parent FacadeStrip is in 'sandbox' mode.
        is_sandbox = (
            isinstance(parent_strip, QWidget) and
            getattr(parent_strip, 'mode', None) == "sandbox"
        )

        if is_sandbox:
            # In sandbox mode, the group is just a transparent container.
            self.setStyleSheet("QFrame { background: transparent; border: none; }")
        else:
            # In structured mode, styling depends on the group kind.
            col = self.kind.colour().name()
            self.setStyleSheet(f"""
                QFrame {{
                    background: {col};
                    border: 2px solid {col};
                    border-radius: 3px;
                }}
            """)

    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
        """Toggles the group's kind between FILL and RIGID."""
        self.kind = GroupKind.RIGID if self.kind is GroupKind.FILL else GroupKind.FILL
        self._apply_palette()
        self.structureChanged.emit()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        """Initiates a drag-and-drop operation for the entire group."""
        if e.button() != Qt.LeftButton:
            return

        # 1. Prepare MIME data.
        mime = QMimeData()
        mime.setData("application/x-ibg-group", QByteArray(b'{"type": "group"}'))

        # 2. Configure and start the drag.
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(e.pos())

        # 3. Store origin and hide. Unlike modules, we don't remove from the
        #    layout yet, just make it invisible to preserve layout geometry.
        self._origin_strip = owning_layout(self)
        self._origin_idx = self._origin_strip.indexOf(self) if self._origin_strip else -1
        self.setVisible(False)

        # 4. Execute the drag loop.
        result = drag.exec(Qt.MoveAction)

        # 5. Finalize after the drag ends.
        self.setVisible(True)  # Always restore visibility.
        if result == Qt.MoveAction:
            # The drop target has already re-parented the widget.
            # The structureChanged signal will be emitted by the strip.
            return
        # If the drag was cancelled, the widget was never moved, so no
        # further action is needed.

    def dragEnterEvent(self, e: QMouseEvent) -> None:
        """Accepts drops only if they contain a module."""
        if e.mimeData().hasFormat("application/x-ibg-module"):
            e.acceptProposedAction()

    def dragMoveEvent(self, e: QMouseEvent) -> None:
        """Shows a visual indicator at the potential drop position."""
        if not e.mimeData().hasFormat("application/x-ibg-module"):
            return
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator()
        self._lay.insertWidget(idx, self._indicator)
        self._indicator.show()
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e: QMouseEvent) -> None:
        """Hides the drop indicator when the drag leaves the widget."""
        self._remove_indicator()

    def dropEvent(self, e: QMouseEvent) -> None:
        """Handles dropping a module into this group."""
        self._remove_indicator()
        data = json.loads(e.mimeData().data("application/x-ibg-module").data())
        idx = self._insert_index(e.position().toPoint().x())
        source_module: ModuleWidget = e.source()

        if data.get("from_library"):
            # Create a new module instance from the library.
            new_widget = ModuleWidget(data["name"], is_library=False)
            new_widget.structureChanged.connect(self.structureChanged.emit)
            self._lay.insertWidget(idx, new_widget)
        else:
            # Move an existing module into this group.
            source_module.structureChanged.connect(self.structureChanged.emit)
            self._lay.insertWidget(idx, source_module)
            source_module.show()
            # Clean up the module's original group if it's now empty.
            _cleanup_empty_group(source_module._origin_layout, self)

        e.acceptProposedAction()
        self.structureChanged.emit()

    def _insert_index(self, mouse_x: int) -> int:
        """Calculates the insert index for a new module based on mouse X-position."""
        for i in range(self._lay.count()):
            widget = self._lay.itemAt(i).widget()
            if widget and widget is not self._indicator:
                if mouse_x < widget.x() + widget.width() / 2:
                    return i
        return self._lay.count()

    def _remove_indicator(self) -> None:
        """Removes the drop indicator widget from the layout and hides it."""
        if self._indicator.parent():
            self._lay.removeWidget(self._indicator)
        self._indicator.hide()