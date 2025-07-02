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

import sys
from panels import PatternInputPanel, PatternOutputPanel, EndpointPanel


from module_library import ModuleLibrary
from pattern_area import PatternArea

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QWidget,
    QDockWidget,
    QMenuBar,
    QMenu
)


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
