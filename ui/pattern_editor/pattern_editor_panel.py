from __future__ import annotations
import json

from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QToolBar, QScrollArea, QSplitter, QPushButton, QFrame
)
from PySide6.QtGui import QAction, QActionGroup

from ui.pattern_editor.module_library import ModuleLibrary
from ui.pattern_editor.pattern_text_panels import PatternInputPanel, PatternOutputPanel
from ui.pattern_editor.pattern_area import PatternArea
from ui.pattern_editor.column_header_widget import ColumnHeaderWidget

from ui.building_viewer.building_viewer import BuildingViewerApp
# NOTE: The RepeatableExpressionWorker is part of the 'Rigid' to 'Repeatable'
# conversion feature, which is separate from our current refactor. We'll leave
# it imported but be aware its functionality might need updating later if used.
from services.facade_segmentation import RepeatableExpressionWorker

class PatternEditorPanel(QWidget):
    # This signal is still valid. It will now emit the full JSON string.
    patternChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._library = ModuleLibrary()
        self.pattern_area = PatternArea(3)
        self._input_panel = PatternInputPanel()
        self._output_panel = PatternOutputPanel()
        self._conversion_thread: RepeatableExpressionWorker | None = None

        # --- UI Assembly ---

        # Library box
        library_box = QGroupBox("Module Library")
        lib_layout = QVBoxLayout(library_box)
        lib_layout.addWidget(self._library)

        # 3D viewer
        viewer_box = QGroupBox("3D Preview")
        viewer_layout = QVBoxLayout(viewer_box)
        self.building_viewer = BuildingViewerApp()
        viewer_layout.addWidget(self.building_viewer)
        self.building_viewer.viewer.picked.connect(self._on_view_pick)

        # Canvas box
        canvas_box = QGroupBox("Pattern Canvas")
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.setContentsMargins(4, 4, 4, 4)

        canvas_toolbar = self._create_canvas_toolbar()

        # A new layout to hold the header and scroll area seamlessly
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0) # No space between header and rows

        self.column_header = ColumnHeaderWidget()

        pattern_scroll = QScrollArea()
        pattern_scroll.setWidgetResizable(True)
        pattern_scroll.setWidget(self.pattern_area)
        pattern_scroll.setFrameShape(QFrame.Shape.NoFrame) # Removes border

        # Assemble the content_layout
        content_layout.addWidget(self.column_header)
        content_layout.addWidget(pattern_scroll, 1) # Scroll area stretches

        # Assemble the main canvas_layout
        canvas_layout.addWidget(canvas_toolbar)
        canvas_layout.addLayout(content_layout, 1) # Content layout stretches

        self.convert_button = QPushButton("➤ Convert to Structured Pattern")
        self.convert_button.setFixedHeight(30)
        self.convert_button.setStyleSheet("font-weight: bold; background-color: #5a9b5a;")
        self.convert_button.hide()
        canvas_layout.addWidget(self.convert_button)

        # --- Main Window Splitters ---

        # Top split: library | canvas | viewer
        visual_splitter = QSplitter(Qt.Horizontal)
        visual_splitter.addWidget(library_box)
        visual_splitter.addWidget(canvas_box)
        visual_splitter.addWidget(viewer_box)
        visual_splitter.setSizes([250, 1000, 500])

        # Text I/O
        text_splitter = QSplitter(Qt.Horizontal)
        text_splitter.addWidget(self._input_panel)
        text_splitter.addWidget(self._output_panel)
        text_io_box = QGroupBox("Text Pattern I/O")
        text_io_layout = QVBoxLayout(text_io_box)
        text_io_layout.addWidget(text_splitter)

        # Root
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(visual_splitter)
        main_splitter.addWidget(text_io_box)
        main_splitter.setStretchFactor(0, 4)
        main_splitter.setStretchFactor(1, 1)

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(main_splitter)

        # --- Signal Connections ---
        self.pattern_area.patternChanged.connect(self.patternChanged)
        self.convert_button.clicked.connect(self._on_convert_clicked)
        self._library.categoryChanged.connect(self.pattern_area.redraw)
        self.pattern_area.columnWidthsChanged.connect(self.column_header.update_column_widths)

        # --- Load a default pattern on startup ---
        self._load_default_pattern()

    def _load_default_pattern(self):
        """Creates and loads a simple, default building pattern."""
        default_facade = "<Wall00>"

        # Create a Python dictionary representing a simple 3-floor building
        default_building_data = [
            # Ground Floor (Index 0 in JSON)
            {
                "Name": "Ground Floor",
                "Pattern": [default_facade, default_facade, default_facade, default_facade],
                "Height": 400
            },
            # Floor 1 (Index 1 in JSON)
            {
                "Name": "Floor 1",
                "Pattern": [default_facade, default_facade, default_facade, default_facade],
                "Height": 400
            },
            # Floor 2 (Index 2 in JSON)
            {
                "Name": "Floor 2",
                "Pattern": [default_facade, default_facade, default_facade, default_facade],
                "Height": 400
            }
        ]

        # Convert the Python data to a JSON string
        default_json_str = json.dumps(default_building_data)

        # Use our existing public method to load this data
        self.load_pattern(default_json_str)

    def _on_view_pick(self, info: dict):
        # This functionality remains unchanged.
        print("Picked:", info)

    def _create_canvas_toolbar(self) -> QToolBar:
        # This functionality remains unchanged.
        tb = QToolBar("Canvas Mode")
        tb.setMovable(False)

        self.act_structured = QAction("Repeatable", self, checkable=True)
        self.act_structured.setChecked(True)
        self.act_sandbox = QAction("Rigid", self, checkable=True)
        tb.addAction(self.act_structured)
        tb.addAction(self.act_sandbox)

        # Debug buttons can remain for now
        btn_kit = QAction("Preview: Kit", self)
        btn_bill = QAction("Preview: Billboard", self)
        tb.addSeparator()
        tb.addAction(btn_kit)
        tb.addAction(btn_bill)

        self.act_structured.triggered.connect(lambda: self.set_editor_mode("Repeatable"))
        self.act_sandbox.triggered.connect(lambda: self.set_editor_mode("Rigid"))
        btn_kit.triggered.connect(self.building_viewer.generate_building_1_kit)
        btn_bill.triggered.connect(self.building_viewer.generate_building_1_billboard)

        grp = QActionGroup(self)
        grp.addAction(self.act_structured)
        grp.addAction(self.act_sandbox)
        grp.setExclusive(True)
        return tb

    @Slot(str)
    def set_editor_mode(self, mode: str):
        # This functionality remains largely unchanged.
        self.pattern_area.set_mode(mode)
        self.convert_button.setVisible(mode == "Rigid")
        self.act_structured.setChecked(mode == "Repeatable")
        self.act_sandbox.setChecked(mode == "Rigid")

    # NOTE: The conversion logic now operates on the JSON output.
    # It will need to be adapted to extract the relevant facade string
    # from the JSON before sending it to the AI worker.
    # This is a future task if this feature is to be used.
    @Slot()
    def _on_convert_clicked(self):
        # For now, we'll just print a notice that this needs an update.
        print("NOTE: 'Convert to Structured' feature needs to be adapted for the new JSON data model.")
        # OLD LOGIC:
        # rigid = self.pattern_area.get_pattern_string()
        # if not rigid.strip() or rigid == "[]":
        #     print("Sandbox is empty.")
        #     return
        # model = "gpt-4o-mini"
        # self._conversion_thread = RepeatableExpressionWorker(rigid, model, self)
        # self._conversion_thread.result_ready.connect(self._on_conversion_success)
        # self._conversion_thread.error.connect(lambda msg: print(f"Conversion Error: {msg}"))
        # self._conversion_thread.finished.connect(self._conversion_thread.deleteLater)
        # self._conversion_thread.start()
        # self.convert_button.setEnabled(False)
        # self.convert_button.setText("Converting...")

    # The public 'load_pattern' method needs to be updated to expect JSON
    @Slot(str)
    def load_pattern(self, pattern_json_str: str):
        """
        Public slot to load a pattern from a JSON string.
        This is the new entry point for loading data from outside.
        """
        try:
            # We delegate the entire loading process to our new PatternArea
            self.pattern_area.load_from_json(pattern_json_str)
        except Exception as e:
            print(f"Error loading pattern in PatternEditorPanel: {e}")
