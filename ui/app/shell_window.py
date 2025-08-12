# shell_window.py  (keep at project root unless you move it under ui/app/)
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QToolBar, QSizePolicy, QLabel
)
from PySide6.QtGui import QPixmap, Qt, QAction, QActionGroup


# Import using your current file locations
from ui.segmentation_editor.segmentation_panel import SegmentationPanel
from ui.pattern_editor.pattern_editor_panel import PatternEditorPanel



APP_STYLESHEET = """
    QMainWindow, QDialog {
        background-color: #3c3c3c;
    }
    QDockWidget {
        titlebar-close-icon: url(close.png);
        titlebar-normal-icon: url(undock.png);
    }
    QDockWidget::title {
        text-align: left;
        background: #5a5a5a;
        padding-left: 10px;
        padding-top: 3px;
        padding-bottom: 3px;
        font-weight: bold;
    }
    /* This rule applies to both the main toolbar and the editor's toolbar */
    QToolBar {
        background-color: #3c3c3c;
        border-bottom: 1px solid #2b2b2b;
        padding: 2px;
    }
    QToolButton {
        color: #e0e0e0;
        padding: 8px 15px;
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
    }
    QToolButton:hover {
        background-color: #4f4f4f;
    }
    QToolButton:checked {
        background-color: #5c85ad;
        border: 1px solid #6d9dca;
        font-weight: bold;
        color: white;
    }
    QGroupBox {
        background-color: #4a4a4a;
        border: 1px solid #2b2b2b;
        border-radius: 5px;
        margin-top: 1ex;
        font-weight: bold;
        color: #e0e0e0;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
        color: #e0e0e0;
    }
    QLabel, QCheckBox {
        color: #e0e0e0;
    }
    QPushButton {
        background-color: #5c85ad;
        color: white;
        border-radius: 4px;
        padding: 6px 12px;
        font-weight: bold;
        border: 1px solid #4a6a8b;
    }
    QPushButton:hover {
        background-color: #6d9dca;
    }
    QPushButton:pressed {
        background-color: #4a6a8b;
    }
    QPushButton:disabled {
        background-color: #555;
        color: #888;
        border: 1px solid #444;
    }
    QPlainTextEdit, QTextEdit {
        background-color: #2b2b2b;
        color: #f0f0f0;
        border: 1px solid #555;
        border-radius: 4px;
        font-family: Consolas, "Courier New", monospace;
    }
    QSpinBox, QDoubleSpinBox, QComboBox {
        background-color: #4a4a4a; /* Match other inputs */

    }

    QSplitter::handle {
        background: #5a5a5a;
    }
    QSplitter::handle:hover {
        background: #6d9dca;
    }
    QSplitter::handle:pressed {
        background: #5c85ad;
    }
"""




class SegmentationWorkspace(QWidget):
    """Thin wrapper around SegmentationPanel so the shell can host it in a stack."""
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.panel = SegmentationPanel()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 5)
        lay.addWidget(self.panel)

class PatternEditorWorkspace(QWidget):
    """Thin wrapper around PatternEditorPanel with pass-through helpers."""
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.panel = PatternEditorPanel()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.panel)

    # pass-throughs for the shell
    def set_editor_mode(self, mode: str):
        self.panel.set_editor_mode(mode)

    def load_pattern(self, s: str):
        self.panel.load_pattern(s)

class ShellWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive Building Grammar")
        self.resize(1600, 900)

        # Workspaces
        self.segmentation_ws = SegmentationWorkspace()
        self.editor_ws = PatternEditorWorkspace()

        # Central stack
        self.stack = QStackedWidget()
        self.stack.addWidget(self.segmentation_ws)  # index 0
        self.stack.addWidget(self.editor_ws)        # index 1
        self.setCentralWidget(self.stack)

        # Toolbar
        self._setup_main_toolbar()

        # route patterns from segmentation → editor
        # (fix: ‘endpoint_panel’ doesn’t exist; use the wrapped panel)
        self.segmentation_ws.panel.patternGenerated.connect(self.on_pattern_generated)

    def _setup_main_toolbar(self) -> None:
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        self.addToolBar(tb)

        # View switchers
        act_seed = QAction("Segmentation", self, checkable=True)
        act_editor = QAction("Pattern Editor", self, checkable=True)

        grp = QActionGroup(self)
        grp.addAction(act_seed)
        grp.addAction(act_editor)
        grp.setExclusive(True)

        act_seed.triggered.connect(lambda: self.stack.setCurrentIndex(0))
        act_editor.triggered.connect(lambda: self.stack.setCurrentIndex(1))

        tb.addAction(act_seed)
        tb.addAction(act_editor)

        # Spacer pushes logos to the right (optional)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        # (Optional) Logos — safe if missing
        # Put your actual paths here if you want logos in the toolbar
        for logo_path in []:  # e.g. ["assets/logos/logo_se.png", "assets/logos/logo_atlas.png"]
            p = Path(logo_path)
            if p.exists():
                lbl = QLabel()
                pix = QPixmap(str(p)).scaledToHeight(24, Qt.SmoothTransformation)
                lbl.setPixmap(pix)
                tb.addWidget(lbl)

        # Initial checked state reflects the visible page
        self.stack.currentChanged.connect(
            lambda i: (act_seed.setChecked(i == 0), act_editor.setChecked(i == 1))
        )
        act_seed.setChecked(True)

    @Slot(str, str)
    def on_pattern_generated(self, pattern_str: str, mode: str):
        """Receive pattern from segmentation and push it into editor with proper mode."""
        self.stack.setCurrentWidget(self.editor_ws)
        self.editor_ws.set_editor_mode(mode)
        self.editor_ws.load_pattern(pattern_str)
