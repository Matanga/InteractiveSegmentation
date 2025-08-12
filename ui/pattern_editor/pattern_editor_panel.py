from __future__ import annotations
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QToolBar, QScrollArea, QSplitter, QPushButton, QSizePolicy )
from PySide6.QtGui import QAction, QActionGroup

from ui.pattern_editor.module_library import ModuleLibrary
from ui.pattern_editor.pattern_text_panels import PatternInputPanel, PatternOutputPanel
from ui.pattern_editor.pattern_area import PatternArea
from ui.building_viewer.building_viewer import BuildingViewerApp
from services.facade_segmentation import RepeatableExpressionWorker  # same worker you already use

class PatternEditorPanel(QWidget):
    patternChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._library = ModuleLibrary()
        self.pattern_area = PatternArea(3)
        self._input_panel = PatternInputPanel()
        self._output_panel = PatternOutputPanel()
        self._conversion_thread: RepeatableExpressionWorker | None = None

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
        canvas_toolbar = self._create_canvas_toolbar()
        canvas_layout.addWidget(canvas_toolbar)
        pattern_scroll = QScrollArea()
        pattern_scroll.setWidgetResizable(True)
        pattern_scroll.setWidget(self.pattern_area)
        canvas_layout.addWidget(pattern_scroll, 1)

        self.convert_button = QPushButton("➤ Convert to Structured Pattern")
        self.convert_button.setFixedHeight(30)
        self.convert_button.setStyleSheet("font-weight: bold; background-color: #5a9b5a;")
        self.convert_button.hide()
        canvas_layout.addWidget(self.convert_button)



        # Top split: library | canvas | viewer
        visual_splitter = QSplitter(Qt.Horizontal)
        visual_splitter.addWidget(library_box)
        visual_splitter.addWidget(canvas_box)
        visual_splitter.addWidget(viewer_box)
        visual_splitter.setSizes([250, 750, 600])

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
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(main_splitter)

        # wiring
        self._input_panel.patternApplied.connect(self.load_pattern)
        self.pattern_area.patternChanged.connect(self._output_panel.update_pattern)
        self.pattern_area.patternChanged.connect(self.patternChanged)
        self.convert_button.clicked.connect(self._on_convert_clicked)
        self._library.categoryChanged.connect(self.pattern_area.redraw)

        # optional: preload a preview
        # self.building_viewer.generate_building_1_kit()

    def _on_view_pick(self, info: dict):
        # info: {'facade': 'front', 'floor': 2, 'module': 'Door01', ...}
        print("Picked:", info)


    def _create_canvas_toolbar(self) -> QToolBar:
        tb = QToolBar("Canvas Mode")
        tb.setMovable(False)

        self.act_structured = QAction("Repeatable", self, checkable=True)
        self.act_structured.setChecked(True)
        self.act_sandbox = QAction("Rigid", self, checkable=True)
        tb.addAction(self.act_structured)
        tb.addAction(self.act_sandbox)

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
        self.pattern_area.set_mode(mode)
        self.convert_button.setVisible(mode == "Rigid")
        self.act_structured.setChecked(mode == "Repeatable")
        self.act_sandbox.setChecked(mode == "Rigid")

    @Slot()
    def _on_convert_clicked(self):
        rigid = self.pattern_area.get_pattern_string()
        if not rigid.strip() or rigid == "[]":
            print("Sandbox is empty.")
            return
        model = "gpt-4o-mini"
        self._conversion_thread = RepeatableExpressionWorker(rigid, model, self)
        self._conversion_thread.result_ready.connect(self._on_conversion_success)
        self._conversion_thread.error.connect(lambda msg: print(f"Conversion Error: {msg}"))
        self._conversion_thread.finished.connect(self._conversion_thread.deleteLater)
        self._conversion_thread.start()
        self.convert_button.setEnabled(False)
        self.convert_button.setText("Converting...")

    @Slot(str)
    def _on_conversion_success(self, structured: str):
        self.load_pattern(structured)
        self.set_editor_mode("Repeatable")
        self.convert_button.setEnabled(True)
        self.convert_button.setText("➤ Convert to Structured Pattern")

    @Slot(str)
    def load_pattern(self, pattern_str: str):
        try:
            self.pattern_area.load_from_string(pattern_str, library=self._library)
            self._input_panel._editor.setPlainText(pattern_str)
        except Exception as e:
            print(f"Error loading pattern: {e}")