from __future__ import annotations

import json
from typing import Optional
from actions import add_context_menu
from enum import Enum, auto



from PySide6.QtCore import Qt, QByteArray, QMimeData, Signal
from PySide6.QtGui import QColor, QDrag, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QWidget
)

# --------------------------------------------------------------------------- #
# Domain-level helpers (pure enum, no core import to keep demo self-contained)
# --------------------------------------------------------------------------- #


class GroupKind(Enum):
    FILL = auto()
    RIGID = auto()

    def colour(self) -> QColor:
        return QColor("#f7d9b0") if self is GroupKind.FILL else QColor("#9ec3f7")

    def __str__(self) -> str:  # noqa: DunderStr
        return self.name.lower()


# --------------------------------------------------------------------------- #
# Utility
# --------------------------------------------------------------------------- #


def owning_layout(w: QWidget) -> Optional[QLayout]:
    par = w.parent()
    if isinstance(par, QLayout):
        return par
    if isinstance(par, QWidget):
        return par.layout()
    return None

def _cleanup_empty_group(lay: QLayout, emitter: QWidget) -> None:
    """If *lay* belongs to a GroupWidget now devoid of ModuleWidgets → remove the group."""
    parent = lay.parent()
    if not isinstance(parent, GroupWidget):
        return
    has_modules = any(
        isinstance(lay.itemAt(i).widget(), ModuleWidget)
        for i in range(lay.count())
    )
    if not has_modules:
        strip_lay = owning_layout(parent)
        if strip_lay:
            strip_lay.removeWidget(parent)
        parent.deleteLater()
        emitter.structureChanged.emit() # Ensure change is propagated even on cleanup


# --------------------------------------------------------------------------- #
# Draggable module chip
# --------------------------------------------------------------------------- #


class ModuleWidget(QLabel):
    ICONS: dict[str, QPixmap] = {}        # populated once by ModuleLibrary
    structureChanged = Signal() # <<< NEW SIGNAL

    def __init__(self, name: str, is_library: bool = False, parent: QWidget | None = None,) -> None:
        """
        Parameters
        ----------
        name
            Canonical module id (usually the PNG filename stem).
        is_library
            True when the widget lives in the palette; False when on the canvas.
        parent
            Standard Qt parent.
        """
        super().__init__(parent)
        self.name = name
        self.is_library = is_library

        # ------------------------------------------------------ icon vs. text
        if name in ModuleWidget.ICONS:
            pix: QPixmap = ModuleWidget.ICONS[name]
            self.setPixmap(pix)
            self.setFixedSize(pix.width() + 4, pix.height() + 4)  # margin
            self.setToolTip(name)                                 # accessibility
        else:                                                     # text fallback
            self.setText(name)
            self.setAlignment(Qt.AlignCenter)
           #self.setFixedWidth(60)
            self._apply_palette()                                 # existing style

        # ------------------------------------------------------ drag helpers
        self._origin_layout: Optional[QLayout] = None
        self._origin_index: int = -1

        # ------------------------------------------------------ Context Menu
        if not self.is_library:                    # <-- guard
            self.setFocusPolicy(Qt.ClickFocus)     # ← NEW
            add_context_menu(self, self._remove_self)

    # --- helpers ---------------------------------------------------------- #
    def _remove_self(self) -> None:
        lay = owning_layout(self)
        if lay:
            lay.removeWidget(self)
        self.deleteLater()
        _cleanup_empty_group(lay)  # already imported
        self.structureChanged.emit() # <<< EMIT after removal

    def _apply_palette(self) -> None:
        self.setStyleSheet(
            """
            QLabel {
                background: #ffffff;
                border: 1px solid #a0a0a0;
                padding: 4px;
                margin: 2px;
            }
            """
        )

    # --- Qt events ------------------------------------------------------- #
    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() != Qt.LeftButton:
            return

        mime = QMimeData()
        mime.setData(
            "application/x-ibg-module",
            QByteArray(
                json.dumps(
                    {
                        "type": "module",
                        "name": self.name,
                        "from_library": self.is_library,
                    }
                ).encode()
            ),
        )

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(e.pos())

        if not self.is_library:
            self._origin_layout = owning_layout(self)
            if self._origin_layout:
                self._origin_index = self._origin_layout.indexOf(self)
                self._origin_layout.removeWidget(self)
            self.hide()

        result = drag.exec( Qt.MoveAction)

        # drag cancelled
        if not self.is_library and self._origin_layout:
            if result != Qt.MoveAction:                        # drag cancelled → restore
                self._origin_layout.insertWidget(self._origin_index, self)
                self.show()
            else:                                              # moved away → maybe empty
                _cleanup_empty_group(self._origin_layout)


# --------------------------------------------------------------------------- #
# Group container  (NEW)
# --------------------------------------------------------------------------- #


class GroupWidget(QFrame):
    structureChanged = Signal() # <<< NEW SIGNAL

    def __init__(self, kind: GroupKind = GroupKind.FILL, parent: QWidget | None = None):
        super().__init__(parent)
        self.kind: GroupKind = kind
        self.repeat: int | None = None  # reserved
        self.setAcceptDrops(True)

        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(2,2,2,2)
        self._lay.setSpacing(2)
        self._indicator = QWidget()
        self._indicator.setFixedSize(6, 30)
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

        self._origin_strip: Optional[QLayout] = None
        self._origin_idx: int = -1

        self._apply_palette()

    # ------------------------------------------------------------------- #
    # Styling helpers
    def _apply_palette(self) -> None:
        col = self.kind.colour().name()
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {col};
                border: 2px solid {col};
                border-radius: 3px;
            }}
            """
        )

    # ------------------------------------------------------------------- #
    # Toggle kind by double-click
    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
        self.kind = (
            GroupKind.RIGID if self.kind is GroupKind.FILL else GroupKind.FILL
        )
        self._apply_palette()
        self.structureChanged.emit()  # <<< EMIT after changing kind

    # ------------------------------------------------------------------- #
    # Group-level drag
    def mousePressEvent(self, e: QMouseEvent) -> None:
        """
        Start a drag-and-drop operation for the entire group.

        ▸ We **do not** remove the widget from its strip until the drag is completed
          with ``Qt.MoveAction``.
        ▸ The widget is only hidden for visual feedback; this does not disturb the
          layout geometry, so the insert-index logic remains stable.
        """
        if e.button() != Qt.LeftButton:
            return

        # --- build MIME payload -------------------------------------------------
        mime = QMimeData()
        mime.setData(
            "application/x-ibg-group",
            QByteArray(json.dumps({"type": "group"}).encode()),
        )

        # --- configure QDrag ----------------------------------------------------
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())  # snapshot used as ghost cursor
        drag.setHotSpot(e.pos())

        # --- remember origin (but DON’T touch the layout yet) -------------------
        self._origin_strip = owning_layout(self)
        self._origin_idx = (
            self._origin_strip.indexOf(self) if self._origin_strip else -1
        )

        # Visual hint – keep geometry, just invisible
        self.setVisible(False)

        # --- run drag loop ------------------------------------------------------
        result = drag.exec(Qt.MoveAction)

        # --- finalise -----------------------------------------------------------
        self.setVisible(True)

        if result == Qt.MoveAction:
            # Move succeeded → the widget has been inserted at the drop location
            # Nothing else to do: Qt has already re-parented it in dropEvent().
            return

        # Drag was cancelled → widget never left its origin strip; nothing moved.
        # No cleanup required, but we keep the explicit guards for safety.
        if self._origin_strip and self._origin_idx >= 0:
            # Make sure we’re still at the original index (optional)
            current_idx = self._origin_strip.indexOf(self)
            if current_idx != self._origin_idx:
                self._origin_strip.insertWidget(self._origin_idx, self)

    # ------------------------------------------------------------------- #
    # Accept modules dropped *inside* the group
    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasFormat("application/x-ibg-module"):
            e.acceptProposedAction()

    def dragMoveEvent(self, e) -> None:
        if not e.mimeData().hasFormat("application/x-ibg-module"):
            return
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator()
        self._lay.insertWidget(idx, self._indicator)
        self._indicator.show()
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e) -> None:
        self._remove_indicator()

    def dropEvent(self, e) -> None:
        self._remove_indicator()
        data = json.loads(e.mimeData().data("application/x-ibg-module").data())
        name, from_lib = data["name"], data.get("from_library", False)
        idx = self._insert_index(e.position().toPoint().x())

        if from_lib:
            new_widget = ModuleWidget(name, False)
            # This is the crucial connection that was missing.
            new_widget.structureChanged.connect(self.structureChanged.emit)
            self._lay.insertWidget(idx, new_widget)
        else:
            w: ModuleWidget = e.source()
            w.structureChanged.connect(self.structureChanged.emit)
            self._lay.insertWidget(idx, w)
            w.show()

        e.acceptProposedAction()
        if not data.get("from_library"):                # came from another group → clean that up
            _cleanup_empty_group(w._origin_layout)
        self.structureChanged.emit()  # <<< EMIT after changing kind

    # ------------------------------------------------------------------- #
    # internal helpers
    def _insert_index(self, mouse_x: int) -> int:
        for i in range(self._lay.count()):
            w = self._lay.itemAt(i).widget()
            if w is None or w is self._indicator:
                continue
            if mouse_x < w.x() + w.width() // 2:
                return i
        return self._lay.count()

    def _remove_indicator(self) -> None:
        if self._indicator.parent() is self:
            self._lay.removeWidget(self._indicator)
        self._indicator.hide()

