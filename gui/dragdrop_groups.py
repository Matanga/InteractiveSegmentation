"""
pattern_editor.py  – IBG-PE spike (v0.1)
----------------------------------------
* Adds a lightweight `GroupWidget` that owns the “kind” metadata.
* You can now:
  • Drag several modules into the **same** group (fill orange by default).
  • Double-click the coloured frame to toggle Rigid ⇄ Fill.
  • Drag an entire group left / right along its strip.

Dependencies: Python 3.11, PySide 6.8
"""

from __future__ import annotations

import json
import sys
from enum import Enum, auto
from typing import Optional
from pathlib import Path
from resources_loader import IconFiles
from actions import add_context_menu
from panels import PatternInputPanel, PatternOutputPanel, EndpointPanel
from building_grammar.core import parse, validate



from PySide6.QtCore import Qt, QByteArray, QMimeData, QPoint, Signal
from PySide6.QtGui import QColor, QDrag, QMouseEvent, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QDockWidget,
    QMenuBar,
    QMenu
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

def _cleanup_empty_group(lay: QLayout) -> None:
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

# --------------------------------------------------------------------------- #
# Draggable module chip
# --------------------------------------------------------------------------- #


class ModuleWidget(QLabel):
    ICONS: dict[str, QPixmap] = {}        # populated once by ModuleLibrary

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

        result = drag.exec(Qt.MoveAction)

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

    # ------------------------------------------------------------------- #
    # Group-level drag
    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() != Qt.LeftButton:
            return

        mime = QMimeData()
        mime.setData(
            "application/x-ibg-group",
            QByteArray(json.dumps({"type": "group"}).encode()),
        )

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(e.pos())

        self._origin_strip = owning_layout(self)
        if self._origin_strip:
            self._origin_idx = self._origin_strip.indexOf(self)
            self._origin_strip.removeWidget(self)
        self.hide()

        result = drag.exec(Qt.MoveAction)
        if result != Qt.MoveAction and self._origin_strip:
            self._origin_strip.insertWidget(self._origin_idx, self)
            self.show()

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
            self._lay.insertWidget(idx, ModuleWidget(name, False))
        else:
            w: ModuleWidget = e.source()
            self._lay.insertWidget(idx, w)
            w.show()

        e.acceptProposedAction()
        if not data.get("from_library"):                # came from another group → clean that up
            _cleanup_empty_group(w._origin_layout)
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


# --------------------------------------------------------------------------- #
# Library palette
# --------------------------------------------------------------------------- #


class ModuleLibrary(QWidget):
    """Vertical strip that lists every PNG in ./resources as a draggable icon."""

    ICON_SIZE = 48        # logical size for palette pixmaps

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(self.ICON_SIZE + 60)

        # Build a pixmap cache once, then share it with all ModuleWidgets
        self._pixmaps: dict[str, QPixmap] = self._make_pixmap_cache()
        ModuleWidget.ICONS = self._pixmaps          # one-liner integration

        # ------------------------- UI layout
        vbox = QVBoxLayout(self)
        vbox.setAlignment(Qt.AlignTop)

        self._add_btn = QPushButton("＋")
        self._add_btn.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._add_btn.clicked.connect(self._on_add_icon)     # import dialog
        vbox.addWidget(self._add_btn)

        for name in sorted(self._pixmaps):
            vbox.addWidget(ModuleWidget(name, is_library=True))

        vbox.addStretch()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _make_pixmap_cache(self) -> dict[str, QPixmap]:
        """Load/scales pixmaps for every PNG in IconFiles."""
        cache: dict[str, QPixmap] = {}
        for name in IconFiles.names:
            path = IconFiles.paths[name]
            pix = QPixmap(str(path)).scaled(
                self.ICON_SIZE,
                self.ICON_SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            cache[name] = pix
        return cache

    # ------------------------------------------------------------------
    # '＋' button handler – MVP implementation
    # ------------------------------------------------------------------
    def _on_add_icon(self) -> None:
        """Let the user copy a PNG into the resources folder, then refresh."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Add PNG icon",
            "",
            "PNG images (*.png)",
        )
        if not file_path:
            return  # user cancelled

        try:
            src = Path(file_path)
            dest = IconFiles.folder / src.name

            # Auto-rename on collision: door00 → door00_1 → door00_2 …
            counter = 1
            while dest.exists():
                dest = IconFiles.folder / f"{src.stem}_{counter}.png"
                counter += 1

            dest.write_bytes(src.read_bytes())
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Import error", str(exc))
            return

        IconFiles.reload()                 # re-scan folder
        self._rebuild_palette()            # refresh widget list

    # ------------------------------------------------------------------
    def _rebuild_palette(self) -> None:
        """Recreate pixmap cache and refresh child ModuleWidgets."""
        # Remove every widget except the '+' button
        layout = self.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            w = item.widget()
            if w and w is not self._add_btn:
                w.setParent(None)

        self._pixmaps = self._make_pixmap_cache()
        ModuleWidget.ICONS = self._pixmaps

        for name in sorted(self._pixmaps):
            layout.addWidget(ModuleWidget(name, is_library=True))

        layout.addStretch()

# --------------------------------------------------------------------------- #
# One horizontal façade strip
# --------------------------------------------------------------------------- #


class FacadeStrip(QFrame):
    def __init__(self, floor_idx: int, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet("background:#fafafa; border:1px solid #ccc;")
        self.setFixedHeight(60)

        self.lay = QHBoxLayout(self)
        self.lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)

        self._indicator = QWidget()
        self._indicator.setFixedSize(10, 45)
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

    # ------------------------------------------------------------------- #
    # Drag events
    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasFormat("application/x-ibg-module") or e.mimeData().hasFormat(
            "application/x-ibg-group"
        ):
            e.acceptProposedAction()

    def dragMoveEvent(self, e) -> None:
        if not (
            e.mimeData().hasFormat("application/x-ibg-module")
            or e.mimeData().hasFormat("application/x-ibg-group")
        ):
            return
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator()
        self.lay.insertWidget(idx, self._indicator)
        self._indicator.show()
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e) -> None:
        self._remove_indicator()

    def dropEvent(self, e) -> None:
        self._remove_indicator()

        # MODULE dropped
        if e.mimeData().hasFormat("application/x-ibg-module"):
            data=json.loads(e.mimeData().data("application/x-ibg-module").data())
            idx=self._insert_index(e.position().toPoint().x())

            # create new group container at drop index
            grp=GroupWidget()
            self.lay.insertWidget(idx,grp)

            # inject the module into that container
            w=ModuleWidget(data["name"],False) if data.get("from_library") else e.source()
            grp.layout().addWidget(w)
            w.show() if not data.get("from_library") else None
            e.acceptProposedAction()
            if not data.get("from_library"):
                _cleanup_empty_group(w._origin_layout)
            return



        # GROUP dropped
        if e.mimeData().hasFormat("application/x-ibg-group"):
            w: GroupWidget = e.source()
            idx = self._insert_index(e.position().toPoint().x())
            self.lay.insertWidget(idx, w)
            w.show()
            e.acceptProposedAction()

    # ------------------------------------------------------------------- #
    # helpers
    def _insert_index(self, mouse_x: int) -> int:
        for i in range(self.lay.count()):
            w = self.lay.itemAt(i).widget()
            if w is None or w is self._indicator:
                continue
            if mouse_x < w.x() + w.width() // 2:
                return i
        return self.lay.count()

    def _remove_indicator(self) -> None:
        if self._indicator.parent() is self:
            self.lay.removeWidget(self._indicator)
        self._indicator.hide()


# --------------------------------------------------------------------------- #
# Vertical container of strips
# --------------------------------------------------------------------------- #


class PatternArea(QWidget):
    patternChanged: Signal = Signal(str)

    def __init__(self, num_floors: int = 3, parent=None):
        super().__init__(parent)
        self._num_floors = num_floors

        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignTop)
        v.setSpacing(4)
        for f in range(num_floors):
            v.addWidget(FacadeStrip(num_floors - f - 1))  # ground = last

    # ------------------------------------------------------------------
    def load_from_string(self, pattern_str: str, *, library: "ModuleLibrary") -> None:
        """
        MVP: wipe the current view and rebuild it from *pattern_str*.
        """
        model = parse(pattern_str)                 # 1) parse / validate
        self._clear_view()                         # 2) clear existing strips

        floor_count = len(model.floors)
        for i, floor in enumerate(model.floors):   # 3) create a strip per line
            strip_w = FacadeStrip(floor_count - i - 1)
            self.layout().addWidget(strip_w)

            for group in floor:                    # 4) create groups + modules
                grp_w = GroupWidget(kind=group.kind)
                strip_w.lay.addWidget(grp_w)

                for mod in group.modules:
                    # Instantiate a module widget (icon look-up can be added later)
                    grp_w.layout().addWidget(ModuleWidget(mod.name, False))

        self.patternChanged.emit(model.to_string())  # keep Output panel in sync

    # ------------------------------------------------------------------
    def _clear_view(self) -> None:
        """Delete all child widgets (simple & brute-force)."""
        lay = self.layout()
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #


class MainWindow(QMainWindow):
    """IBG-PE prototype main window with menu bar & dockable panels."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IBG-PE – Pattern Editor (prototype)")

        # ── 1. Core widgets (no parents yet) ───────────────────────────
        self._library = ModuleLibrary()
        self._pattern_area = PatternArea(3)

        self._pattern_scroll = QScrollArea()
        self._pattern_scroll.setWidgetResizable(True)
        self._pattern_scroll.setWidget(self._pattern_area)

        # ── 2. Dock wrappers for the two main views ───────────────────
        self._library_dock = self._make_dock(
            title="Module Library",
            widget=self._library,
            initial_area=Qt.LeftDockWidgetArea,
            allowed_areas=Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
        )
        self._pattern_dock = self._make_dock(
            title="Pattern Area",
            widget=self._pattern_scroll,
            initial_area=Qt.RightDockWidgetArea,
            allowed_areas=Qt.AllDockWidgetAreas,
        )

        # Empty central widget (all canvases live in docks)
        self.setCentralWidget(QWidget())

        # ── 3. Build menu bar & keep a handle to 'Window' menu ────────
        self._build_menu_bar()

        # ── 4. Extra panels: input / output / endpoint ────────────────
        self._pattern_input_dock = self._make_dock(
            title="Pattern Input",
            widget=PatternInputPanel(),
            initial_area=Qt.BottomDockWidgetArea,
            allowed_areas=Qt.AllDockWidgetAreas,
        )
        self._pattern_output_dock = self._make_dock(
            title="Pattern Output",
            widget=PatternOutputPanel(),
            initial_area=Qt.BottomDockWidgetArea,
            allowed_areas=Qt.AllDockWidgetAreas,
        )
        # Show them as tabs
        self.tabifyDockWidget(self._pattern_input_dock, self._pattern_output_dock)

        self._endpoint_dock = self._make_dock(
            title="Image Seed Workflow",
            widget=EndpointPanel(),
            initial_area=Qt.RightDockWidgetArea,
            allowed_areas=Qt.AllDockWidgetAreas,
        )

        # ── 5. Add every dock’s toggleAction to Window ▸ ──────────────
        for dock in (
            self._library_dock,
            self._pattern_dock,
            self._pattern_input_dock,
            self._pattern_output_dock,
            self._endpoint_dock,
        ):
            self._window_menu.addAction(dock.toggleViewAction())

        # ── 6. Data-flow wiring ───────────────────────────────────────
        # Paste → Apply → PatternArea
        self._pattern_input_dock.widget().patternApplied.connect(self._apply_pattern)
        # PatternArea changed → keep output panel in sync
        self._pattern_area.patternChanged.connect(            self._pattern_output_dock.widget().update_pattern        )

    # ===================================================================
    # helpers
    # ===================================================================
    def _apply_pattern(self, s: str) -> None:
        """Slot: load a validated pattern string into the grid."""
        self._pattern_area.load_from_string(s, library=self._library)

    def _make_dock(
        self,
        *,
        title: str,
        widget: QWidget,
        initial_area: Qt.DockWidgetArea,
        allowed_areas: Qt.DockWidgetAreas,
    ) -> QDockWidget:
        """Create, configure and add a QDockWidget around *widget*."""
        dock = QDockWidget(title, self)
        dock.setObjectName(f"{title.replace(' ', '')}Dock")  # state save/restore
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(widget)
        self.addDockWidget(initial_area, dock)
        return dock

    # -------------------------------------------------------------------
    def _build_menu_bar(self) -> None:
        """Create top-level menus and store references."""
        bar: QMenuBar = self.menuBar()

        self._file_menu: QMenu = bar.addMenu("&File")
        self._edit_menu: QMenu = bar.addMenu("&Edit")
        self._window_menu: QMenu = bar.addMenu("&Window")
        self._help_menu: QMenu = bar.addMenu("&Help")

        # Core view toggles appear first
        self._window_menu.addAction(self._library_dock.toggleViewAction())
        self._window_menu.addAction(self._pattern_dock.toggleViewAction())

# --------------------------------------------------------------------------- #


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(700, 450)
    win.show()
    sys.exit(app.exec())
