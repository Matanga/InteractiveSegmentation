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
    QGroupBox,
    QSplitter
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
class PatternEditorView(QWidget):
    """
    A self-contained view for the pattern editor, using a flexible,
    splitter-based layout for a professional user experience.

    The layout is structured as follows:

    +------------------------------------------------------------------+
    | Main Vertical Splitter                                           |
    |------------------------------------------------------------------|
    |   TOP PANE (Visual Editing)                                      |
    |   +-------------------+ +--------------------------------------+ |
    |   |  Module Library   | |            Pattern Canvas            | |
    |   +-------------------+ +--------------------------------------+ |
    |------------------------------------------------------------------|
    |   BOTTOM PANE (Text I/O)                                         |
    |   +------------------------+ +---------------------------------+ |
    |   |    Input Textbox       | |        Output Textbox         | |
    |   +------------------------+ +---------------------------------+ |
    +------------------------------------------------------------------+
    """

    def __init__(self, parent: QWidget | None = None):
        # Change base class to QWidget, as we are managing our own layout now.
        super().__init__(parent)

        # ===================================================================
        #  1. CREATE CORE WIDGETS
        # ===================================================================
        self._library = ModuleLibrary()
        self._pattern_area = PatternArea(3)
        self._input_panel = PatternInputPanel()
        self._output_panel = PatternOutputPanel()

        # ===================================================================
        #  2. ASSEMBLE THE LAYOUT
        # ===================================================================

        # --- Assemble the TOP PANE (Visual Editing Area) ---
        # The library and canvas are wrapped in GroupBoxes for consistent styling.
        library_box = QGroupBox("Module Library")
        library_layout = QVBoxLayout(library_box)
        library_layout.addWidget(self._library)

        pattern_scroll = QScrollArea()
        pattern_scroll.setWidgetResizable(True)
        pattern_scroll.setWidget(self._pattern_area)

        canvas_box = QGroupBox("Pattern Canvas")
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.addWidget(pattern_scroll)

        # A horizontal splitter manages the library and the canvas.
        visual_splitter = QSplitter(Qt.Horizontal)
        visual_splitter.addWidget(library_box)
        visual_splitter.addWidget(canvas_box)
        # Set initial sizes to make the canvas larger, as requested.
        visual_splitter.setSizes([250, 750])  # e.g., 250px for library, 750px for canvas

        # --- Assemble the BOTTOM PANE (Text I/O Area) ---
        # A horizontal splitter manages the input and output text panels.
        text_splitter = QSplitter(Qt.Horizontal)
        text_splitter.addWidget(self._input_panel)
        text_splitter.addWidget(self._output_panel)

        # Wrap the text splitter in a GroupBox.
        text_io_box = QGroupBox("Text Pattern I/O")
        text_io_layout = QVBoxLayout(text_io_box)
        text_io_layout.addWidget(text_splitter)

        # --- Assemble the MAIN LAYOUT ---
        # A vertical splitter manages the top visual pane and the bottom text pane.
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(visual_splitter)
        main_splitter.addWidget(text_io_box)
        # Give more initial space to the visual editor.
        main_splitter.setStretchFactor(0, 3)  # 3/4 of the space for visuals
        main_splitter.setStretchFactor(1, 1)  # 1/4 of the space for text

        # Set the final layout for the entire PatternEditorView widget.
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(main_splitter)

        # ===================================================================
        #  3. CONNECT SIGNALS
        # ===================================================================
        # This logic remains the same, as the widgets themselves haven't changed.
        self._input_panel.patternApplied.connect(self.load_pattern)
        self._pattern_area.patternChanged.connect(self._output_panel.update_pattern)

    @Slot(str)
    def load_pattern(self, pattern_str: str):
        """Public slot to load a pattern from an external source."""
        try:
            # Load the pattern into the visual editor canvas.
            self._pattern_area.load_from_string(pattern_str, library=self._library)
            # Also update the text input panel to stay in sync.
            # Note: Accessing a "private" attribute like _editor is not ideal.
            # A cleaner approach would be a public set_text method on PatternInputPanel.
            self._input_panel._editor.setPlainText(pattern_str)
        except Exception as e:
            # A proper error dialog (QMessageBox) would be good here.
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