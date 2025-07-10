# main_window.py (Final version with integrated Sandbox Editor)

import sys
from pathlib import Path

from functools import partial

# --- Component Imports ---
from segmentation_panel import SegmentationPanel, RepeatableThread  # Import the thread
from module_library import ModuleLibrary
from panels import PatternInputPanel, PatternOutputPanel
from pattern_area import PatternArea

from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QAction, QActionGroup, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QScrollArea, QStackedWidget, QToolBar,
    QVBoxLayout, QWidget, QGroupBox, QSplitter, QPushButton, QLabel, QSizePolicy,
    QHBoxLayout
)

# ... (APP_STYLESHEET remains the same)
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

# ===================================================================
# VIEW 1: The Image-Seed Workflow (Unchanged)
# ===================================================================
class ImageSeedView(QWidget):
    """A dedicated widget that holds only the SegmentationPanel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.endpoint_panel = SegmentationPanel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.endpoint_panel)


# ===================================================================
# VIEW 2: The Pattern Editor (Now a Mode Controller)
# ===================================================================
class PatternEditorView(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._library = ModuleLibrary()
        self.pattern_area = PatternArea(3)  # <<< Create the one and only canvas
        self._input_panel = PatternInputPanel()
        self._output_panel = PatternOutputPanel()
        self._conversion_thread: RepeatableThread | None = None

        library_box = QGroupBox("Module Library");
        library_layout = QVBoxLayout(library_box);
        library_layout.addWidget(self._library)

        canvas_box = QGroupBox("Pattern Canvas");
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_toolbar = self._create_canvas_toolbar()
        canvas_layout.addWidget(canvas_toolbar)

        pattern_scroll = QScrollArea();
        pattern_scroll.setWidgetResizable(True);
        pattern_scroll.setWidget(self.pattern_area)
        canvas_layout.addWidget(pattern_scroll, 1)

        self.convert_button = QPushButton("➤ Convert to Structured Pattern");
        self.convert_button.setFixedHeight(30)
        self.convert_button.setStyleSheet("font-weight: bold; background-color: #5a9b5a;");
        self.convert_button.hide()
        canvas_layout.addWidget(self.convert_button)

        visual_splitter = QSplitter(Qt.Horizontal);
        visual_splitter.addWidget(library_box);
        visual_splitter.addWidget(canvas_box);
        visual_splitter.setSizes([250, 750])
        text_splitter = QSplitter(Qt.Horizontal);
        text_splitter.addWidget(self._input_panel);
        text_splitter.addWidget(self._output_panel)
        text_io_box = QGroupBox("Text Pattern I/O");
        text_io_layout = QVBoxLayout(text_io_box);
        text_io_layout.addWidget(text_splitter)
        main_splitter = QSplitter(Qt.Vertical);
        main_splitter.addWidget(visual_splitter);
        main_splitter.addWidget(text_io_box)
        main_splitter.setStretchFactor(0, 3);
        main_splitter.setStretchFactor(1, 1)
        root_layout = QVBoxLayout(self);
        root_layout.addWidget(main_splitter)

        self._input_panel.patternApplied.connect(self.load_pattern);
        self.pattern_area.patternChanged.connect(self._output_panel.update_pattern)
        self.convert_button.clicked.connect(self._on_convert_clicked)

        self._library.categoryChanged.connect(self.pattern_area.redraw)

    def _create_canvas_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Canvas Mode")
        toolbar.setMovable(False)
        self.act_structured = QAction("Repeatable", self)
        self.act_structured.setCheckable(True)
        self.act_structured.setChecked(True)
        self.act_sandbox = QAction("Rigid", self)
        self.act_sandbox.setCheckable(True)
        toolbar.addAction(self.act_structured)
        toolbar.addAction(self.act_sandbox)

        # Connect buttons to the set_mode method of the single PatternArea
        self.act_structured.triggered.connect(lambda: self.set_editor_mode("Repeatable"))
        self.act_sandbox.triggered.connect(lambda: self.set_editor_mode("Rigid"))

        # Use a group to manage the checked state
        action_group = QActionGroup(self)
        action_group.addAction(self.act_structured)
        action_group.addAction(self.act_sandbox)
        action_group.setExclusive(True)
        return toolbar

    @Slot(str)
    def set_editor_mode(self, mode: str):
        """Toggles the canvas mode and updates the UI to reflect it."""
        self.pattern_area.set_mode(mode)
        self.convert_button.setVisible(mode == "Rigid")

        # Update the toolbar to reflect the current mode
        if mode == "Repeatable":
            self.act_structured.setChecked(True)
        else:  # "Rigid"
            self.act_sandbox.setChecked(True)

    @Slot()
    def _on_convert_clicked(self):
        rigid_pattern = self.pattern_area.get_pattern_string()
        if not rigid_pattern.strip() or rigid_pattern == "[]": print("Sandbox is empty."); return
        model = "gpt-4o-mini";
        self._conversion_thread = RepeatableThread(rigid_pattern, model, self)
        self._conversion_thread.result_ready.connect(self._on_conversion_success)
        self._conversion_thread.error.connect(lambda msg: print(f"Conversion Error: {msg}"))
        self._conversion_thread.finished.connect(self._conversion_thread.deleteLater)
        self._conversion_thread.start();
        self.convert_button.setEnabled(False);
        self.convert_button.setText("Converting...")

    @Slot(str)
    def _on_conversion_success(self, structured_pattern: str):
        self.load_pattern(structured_pattern)
        # Find the toolbar action and check it to switch the mode visually
        self.set_editor_mode("Repeatable")
        for action in self.findChildren(QToolBar)[0].actions():
            if action.text() == "Repeatable": action.setChecked(True)
        self.convert_button.setEnabled(True);
        self.convert_button.setText("➤ Convert to Structured Pattern")

    @Slot(str)
    def load_pattern(self, pattern_str: str):
        try:
            # The mode is now set *before* this method is called.
            self.pattern_area.load_from_string(pattern_str, library=self._library)
            self._input_panel._editor.setPlainText(pattern_str)
        except Exception as e:
            print(f"Error loading pattern: {e}")


# ===================================================================
# MAIN APPLICATION WINDOW (The Top-Level View Switcher)
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
        self._setup_main_toolbar()

        # --- Connect the signal from the Image Seed view to the Pattern Editor view ---
        self.image_seed_view.endpoint_panel.patternGenerated.connect(
            self.on_pattern_generated
        )

    # The new, robust method
    def _setup_main_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # --- 1. Actions (on the left) ---
        act_show_seed = QAction("Image Seed Workflow", self)
        act_show_seed.setCheckable(True)
        act_show_editor = QAction("Pattern Editor", self)
        act_show_editor.setCheckable(True)

        action_group = QActionGroup(self)
        action_group.addAction(act_show_seed)
        action_group.addAction(act_show_editor)
        action_group.setExclusive(True)

        act_show_seed.triggered.connect(lambda: self.stack.setCurrentIndex(0))
        act_show_editor.triggered.connect(lambda: self.stack.setCurrentIndex(1))

        toolbar.addAction(act_show_seed)
        toolbar.addAction(act_show_editor)

        # --- 2. Spacer Widget (pushes everything to the right) ---
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # --- 3. Logos (Corrected with Manual Scaling) ---
        # Define a consistent height for the logos to fit the toolbar.
        LOGO_HEIGHT = 35

        # Construct paths to the logos
        base_path = Path(__file__).parent
        logo_se_path = base_path.parent / "assets" / "logos" / "logo_se.png"
        logo_atlas_path = base_path.parent / "assets" / "logos" / "logo_atlas.png"

        # --- Create and add the first logo ---
        logo_se_label = QLabel()
        if logo_se_path.exists():
            # 1. Load the original, full-resolution pixmap.
            original_pixmap = QPixmap(str(logo_se_path))

            # 2. Create a new, scaled version of the pixmap.
            #    scaledToHeight() automatically keeps the aspect ratio correct.
            scaled_pixmap = original_pixmap.scaledToHeight(
                LOGO_HEIGHT,
                Qt.TransformationMode.SmoothTransformation
            )

            # 3. Set the pre-scaled pixmap on the label.
            logo_se_label.setPixmap(scaled_pixmap)
            logo_se_label.setToolTip("SE")
            toolbar.addWidget(logo_se_label)

        # Add a small separator for better visual spacing
        toolbar.addSeparator()

        # --- Create and add the second logo ---
        logo_atlas_label = QLabel()
        if logo_atlas_path.exists():
            original_pixmap = QPixmap(str(logo_atlas_path))
            scaled_pixmap = original_pixmap.scaledToHeight(
                LOGO_HEIGHT,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_atlas_label.setPixmap(scaled_pixmap)
            logo_atlas_label.setToolTip("Atlas")
            toolbar.addWidget(logo_atlas_label)

        # --- 4. Final Connections and State ---
        self.stack.currentChanged.connect(
            lambda i: (act_show_seed.setChecked(i == 0), act_show_editor.setChecked(i == 1))
        )
        act_show_seed.setChecked(True)

    @Slot(str, str)
    def on_pattern_generated(self, pattern_str: str, mode: str):
        """Handles the pattern coming from the image workflow."""
        print(f"Pattern received for {mode} mode. Switching to editor...")

        # 1. Switch the main view to the Pattern Editor
        self.stack.setCurrentWidget(self.pattern_editor_view)

        # 2. Set the editor to the correct mode (structured/sandbox)
        self.pattern_editor_view.set_editor_mode(mode)

        # 3. Load the pattern string into the editor
        self.pattern_editor_view.load_pattern(pattern_str)


# --------------------------------------------------------------------------- #
# Application Entry Point
# --------------------------------------------------------------------------- #
def main():
    app = QApplication(sys.argv);
    app.setStyleSheet(APP_STYLESHEET)
    win = MainWindow();
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()