# main_window.py (Refactored for Two-View Layout)

import sys
from functools import partial

# --- Component Imports ---
from segmentation_panel import SegmentationPanel
from module_library import ModuleLibrary
from panels import PatternInputPanel, PatternOutputPanel
from pattern_area import PatternArea

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QDockWidget,
)

# You can reuse the stylesheet from the previous step. For clarity, it's included here.
APP_STYLESHEET = """
    /* (Same stylesheet as before) */
    QMainWindow, QDialog { background-color: #3c3c3c; }
    QDockWidget::title { text-align: left; background: #5a5a5a; padding: 5px; font-weight: bold; }
    QToolBar { background-color: #4a4a4a; border: none; }
    QToolButton { color: white; padding: 10px; background-color: #4a4a4a; }
    QToolButton:checked { background-color: #5c85ad; font-weight: bold; }
    QGroupBox { background-color: #4a4a4a; border: 1px solid #666666; border-radius: 5px; margin-top: 1ex; font-weight: bold; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; left: 10px; }
    QLabel, QCheckBox { color: #e0e0e0; }
    QPushButton { background-color: #5c85ad; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
    QPushButton:hover { background-color: #6d9dca; }
    QPushButton:pressed { background-color: #4a6a8b; }
    QPushButton:disabled { background-color: #555; color: #888; }
    QPlainTextEdit, QTextEdit { background-color: #2b2b2b; color: #f0f0f0; border: 1px solid #555; border-radius: 4px; font-family: Consolas, "Courier New", monospace; }
    QSpinBox, QDoubleSpinBox, QComboBox { background-color: #4a4a4a; color: #f0f0f0; border: 1px solid #666; padding: 3px; }
    QComboBox::drop-down { border: none; }
"""


# ===================================================================
# VIEW 1: The Image-Seed Workflow
# ===================================================================
class ImageSeedView(QWidget):
    """A dedicated widget that holds only the EndpointPanel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # This is our complete image-to-pattern workflow widget
        self.endpoint_panel = SegmentationPanel()

        layout = QVBoxLayout(self)
        # Add a bit of margin so it doesn't touch the window edges
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.endpoint_panel)


# ===================================================================
# VIEW 2: The Pattern Editor Workflow
# ===================================================================
class PatternEditorView(QMainWindow):
    """
    A self-contained main window for the pattern editor, providing the
    exact dock layout requested.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # --- Core Components ---
        self._library = ModuleLibrary()
        self._pattern_area = PatternArea(3)
        self._input_panel = PatternInputPanel()
        self._output_panel = PatternOutputPanel()

        # The pattern area needs to be scrollable
        pattern_scroll = QScrollArea()
        pattern_scroll.setWidgetResizable(True)
        pattern_scroll.setWidget(self._pattern_area)
        self.setCentralWidget(pattern_scroll)

        # --- Dock Widgets Setup ---
        # 1. Module Library on the left
        library_dock = QDockWidget("Module Library", self)
        library_dock.setWidget(self._library)
        # Set a reasonable initial width
        library_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.LeftDockWidgetArea, library_dock)

        # 2. Input/Output panels at the bottom
        input_dock = QDockWidget("Text Pattern Input", self)
        input_dock.setWidget(self._input_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, input_dock)

        output_dock = QDockWidget("Text Pattern Output", self)
        output_dock.setWidget(self._output_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, output_dock)

        # Make them side-by-side as requested
        self.splitDockWidget(input_dock, output_dock, Qt.Horizontal)

        # --- Signal Connections (Internal to this view) ---
        self._input_panel.patternApplied.connect(self.load_pattern)
        self._pattern_area.patternChanged.connect(self._output_panel.update_pattern)

    @Slot(str)
    def load_pattern(self, pattern_str: str):
        """Public slot to load a pattern from an external source."""
        try:
            # Load the pattern into the visual editor
            self._pattern_area.load_from_string(pattern_str, library=self._library)
            # Also update the text input panel to stay in sync
            self._input_panel._editor.setPlainText(pattern_str)
        except Exception as e:
            # A proper error dialog would be good here
            print(f"Error loading pattern: {e}")


# ===================================================================
# MAIN APPLICATION WINDOW (The View Switcher)
# ===================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive Building Grammar")
        self.resize(1600, 900)

        # --- Create the two main views ---
        self.image_seed_view = ImageSeedView()
        self.pattern_editor_view = PatternEditorView()

        # --- Setup the QStackedWidget to manage views ---
        self.stack = QStackedWidget()
        self.stack.addWidget(self.image_seed_view)
        self.stack.addWidget(self.pattern_editor_view)
        self.setCentralWidget(self.stack)

        # --- Setup the Toolbar for switching views ---
        self._setup_toolbar()

        # --- Connect the signal from View 1 to a method that controls View 2 ---
        self.image_seed_view.endpoint_panel.patternGenerated.connect(
            self.on_pattern_generated
        )

    def _setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Action for View 1
        self.act_show_seed = QAction("Image Seed Workflow", self)
        self.act_show_seed.setCheckable(True)
        self.act_show_seed.setChecked(True)
        self.act_show_seed.triggered.connect(
            lambda: self.stack.setCurrentWidget(self.image_seed_view)
        )
        toolbar.addAction(self.act_show_seed)

        # Action for View 2
        self.act_show_editor = QAction("Pattern Editor", self)
        self.act_show_editor.setCheckable(True)
        self.act_show_editor.triggered.connect(
            lambda: self.stack.setCurrentWidget(self.pattern_editor_view)
        )
        toolbar.addAction(self.act_show_editor)

        # Ensure only one button is checked at a time
        self.stack.currentChanged.connect(self._update_toolbar_state)

    @Slot(int)
    def _update_toolbar_state(self, index: int):
        self.act_show_seed.setChecked(index == 0)
        self.act_show_editor.setChecked(index == 1)

    @Slot(str)
    def on_pattern_generated(self, pattern_str: str):
        """
        This is the magic link between the two views.
        When the image workflow is done, it calls this slot.
        """
        print("Pattern received from image workflow. Switching to editor...")
        # 1. Load the generated pattern into the editor view
        self.pattern_editor_view.load_pattern(pattern_str)
        # 2. Switch the main window's view to show the editor
        self.stack.setCurrentWidget(self.pattern_editor_view)


# --------------------------------------------------------------------------- #
# Application Entry Point
# --------------------------------------------------------------------------- #
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()