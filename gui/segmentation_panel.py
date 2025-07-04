from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal, Slot

from segmentation_core import (
    SymbolicThread, RigidThread, RepeatableThread, fix_facade_expression
)

# =========================================================================== #
# 1.  Re-usable Image Drop Widget
# =========================================================================== #

class ImageDropLabel(QtWidgets.QLabel):
    """
    A custom QLabel that accepts image file drops and mouse clicks to open a file dialog.
    """
    image_loaded = Signal(str)  # Emitted with the local file path of the loaded image.

    def __init__(self, text: str = "", parent: QtWidgets.QWidget | None = None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setWordWrap(True)
        self.setStyleSheet("""
            ImageDropLabel { 
                border: 2px dashed #aaa; 
                border-radius: 5px; 
                color: #777; 
                padding: 10px; 
            }
        """)

    def dragEnterEvent(self, ev: QtGui.QDragEnterEvent):
        """Accepts the drag event if it contains URLs."""
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev: QtGui.QDropEvent):
        """Handles the drop event, emitting the path of a valid image file."""
        if ev.mimeData().hasUrls():
            path = ev.mimeData().urls()[0].toLocalFile()
            if Path(path).suffix.lower() in (".jpg", ".jpeg", ".png"):
                self.image_loaded.emit(path)

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        """Opens a file dialog when the label is clicked."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image files (*.png *.jpg *.jpeg)"
        )
        if path:
            self.image_loaded.emit(path)

    def set_image(self, path: str):
        """Loads and displays a pixmap from the given file path, scaled to fit."""
        pixmap = QtGui.QPixmap(path)
        self.setPixmap(pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

# =========================================================================== #
# 2.  Main Segmentation Panel
# =========================================================================== #

class SegmentationPanel(QtWidgets.QWidget):
    """
    A panel for managing the 3-step image-to-expression pipeline:
    1. Image -> Symbolic
    2. Symbolic -> Rigid Expression
    3. Rigid -> Repeatable Expression
    """
    patternGenerated: Signal = Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initializes the panel, its state, UI, and signal connections."""
        super().__init__(parent)
        self.setWindowTitle("Image-Seed → Repeatable Panel")

        self._init_state()
        self._build_ui()
        self._connect_signals()
        self._update_ui_state()

    def _init_state(self) -> None:
        """Initializes all non-UI state attributes for the pipeline."""
        self._image_path: str | None = None
        self._symbolic_bytes: bytes | None = None
        self._rigid_text: str | None = None
        self._final_repeatable_text: str | None = None
        self.current_thread: QtCore.QThread | None = None

    def _build_ui(self) -> None:
        """
        Assembles the widgets and layouts for the panel in a three-column layout.
        The final layout structure can be visualized as:

        +-------------------------------------------------------------------------+
        | root_splitter (stretches to fill available space)                       |
        | +----------------+ +--------------------------------------------------+ |
        | |                | | content_splitter                                 | |
        | |  action_column | | +-----------------------+ +--------------------+ | |
        | |   (Actions)    | | |                       | |                    | | |
        | |                | | |  input_params_column  | |   output_column    | | |
        | |                | | | (Input, Params)       | | (Visuals, Expr)  | | |
        | |                | | |                       | |                    | | |
        | |                | | +-----------------------+ +--------------------+ | |
        | +----------------+ +--------------------------------------------------+ |
        +-------------------------------------------------------------------------+
        | status_row (fixed height)                                               |
        +-------------------------------------------------------------------------+
        """
        # --- STEP 1: DEFINE ALL WIDGETS ---
        style = self.style()
        # Column 1: Actions
        self.btn_sym = QtWidgets.QPushButton("1. Generate Symbolic", icon=style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_rigid = QtWidgets.QPushButton("2. Generate Rigid", icon=style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_rep = QtWidgets.QPushButton("3. Generate Repeatable", icon=style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_send_to_editor = QtWidgets.QPushButton("➤ Send to Editor", icon=style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowRight))
        self.btn_send_to_editor.setObjectName("SendToEditor")

        # Column 2: Input & Parameters
        self.in_label = ImageDropLabel("Click or drop an image")
        self.params_box = self._build_params_box()

        # Column 3: Outputs
        self.out_label = self._make_label("Symbolic / Main Viz")
        self.grid_viz1_label = self._make_label("Grid Viz 1")
        self.grid_viz2_label = self._make_label("Grid Viz 2")
        self.rigid_text_edit = QtWidgets.QTextEdit(readOnly=True, placeholderText="Rigid...")
        self.repeatable_text_edit = QtWidgets.QTextEdit(readOnly=True, placeholderText="Repeatable...")

        # Bottom Status Row
        self.progress = QtWidgets.QProgressBar(textVisible=False)
        self.status = QtWidgets.QLabel("Please load an image to begin.")

        # --- STEP 2: ASSEMBLE EACH COLUMN'S LAYOUT ---
        # Column 1: Workflow Actions
        actions_box = QtWidgets.QGroupBox("Workflow Actions")
        actions_box.setObjectName("WorkflowActions")
        actions_lay = QtWidgets.QVBoxLayout(actions_box)
        actions_lay.addWidget(self.btn_sym)
        actions_lay.addWidget(self.btn_rigid)
        actions_lay.addWidget(self.btn_rep)
        actions_lay.addSpacing(20)
        actions_lay.addWidget(self.btn_send_to_editor)
        actions_column_layout = QtWidgets.QVBoxLayout()
        actions_column_layout.addWidget(actions_box)
        actions_column_layout.addStretch(1)
        actions_column_widget = QtWidgets.QWidget()
        actions_column_widget.setLayout(actions_column_layout)
        actions_column_widget.setMinimumWidth(220)

        # Column 2: Input & Parameters
        input_box = QtWidgets.QGroupBox("Input Image")
        input_lay = QtWidgets.QVBoxLayout(input_box)
        input_lay.addWidget(self.in_label)
        input_params_layout = QtWidgets.QVBoxLayout()
        input_params_layout.addWidget(input_box, 1)
        input_params_layout.addWidget(self.params_box)
        input_params_column_widget = QtWidgets.QWidget()
        input_params_column_widget.setLayout(input_params_layout)
        input_params_column_widget.setMinimumWidth(250)

        # Column 3: Visual & Text Outputs
        visuals_box = QtWidgets.QGroupBox("Visual Outputs")
        visuals_lay = QtWidgets.QHBoxLayout(visuals_box)
        visuals_lay.addWidget(self.out_label, 1)
        visuals_lay.addWidget(self.grid_viz1_label, 1)
        visuals_lay.addWidget(self.grid_viz2_label, 1)
        expressions_splitter = QtWidgets.QSplitter(Qt.Horizontal)
        expressions_splitter.addWidget(self.rigid_text_edit)
        expressions_splitter.addWidget(self.repeatable_text_edit)
        expressions_box = QtWidgets.QGroupBox("Output Expressions")
        expressions_box_layout = QtWidgets.QVBoxLayout(expressions_box)
        expressions_box_layout.addWidget(expressions_splitter)
        output_column_layout = QtWidgets.QVBoxLayout()
        output_column_layout.addWidget(visuals_box, 1)
        output_column_layout.addWidget(expressions_box, 2)
        output_column_widget = QtWidgets.QWidget()
        output_column_widget.setLayout(output_column_layout)

        # --- STEP 3: ASSEMBLE SPLITTERS AND ROOT LAYOUT ---
        content_splitter = QtWidgets.QSplitter(Qt.Horizontal)
        content_splitter.addWidget(input_params_column_widget)
        content_splitter.addWidget(output_column_widget)
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 2)

        root_splitter = QtWidgets.QSplitter(Qt.Horizontal)
        root_splitter.addWidget(actions_column_widget)
        root_splitter.addWidget(content_splitter)
        root_splitter.setStretchFactor(0, 0)
        root_splitter.setStretchFactor(1, 1)

        status_row_layout = QtWidgets.QHBoxLayout()
        status_row_layout.addWidget(self.progress, 1)
        status_row_layout.addWidget(self.status, 2)

        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.addWidget(root_splitter, 1)
        root_layout.addLayout(status_row_layout)

        # Apply specific stylesheets.
        self.setStyleSheet("""
            QGroupBox#WorkflowActions QPushButton {
                text-align: left;
                padding-left: 10px;
            }
            QGroupBox#WorkflowActions QPushButton#SendToEditor {
                background-color: #5a9b5a;
                font-weight: bold;
            }
        """)

    @staticmethod
    def _make_label(text: str) -> QtWidgets.QLabel:
        """Creates a styled, framed placeholder label."""
        lbl = QtWidgets.QLabel(text, alignment=Qt.AlignCenter)
        lbl.setFrameShape(QtWidgets.QFrame.StyledPanel)
        lbl.setMinimumSize(100, 100)
        return lbl

    def _build_params_box(self) -> QtWidgets.QGroupBox:
        """Creates and populates the GroupBox containing all pipeline parameters."""
        grp = QtWidgets.QGroupBox("Parameters")
        form = QtWidgets.QFormLayout(grp)

        # Define all parameter widgets
        self.spin_win_conn = QtWidgets.QSpinBox(maximum=100, value=8)
        self.cmb_win_mode = QtWidgets.QComboBox()
        self.cmb_win_mode.addItems(["Count", "Percentage", "Random"])
        self.spin_win_val = QtWidgets.QSpinBox(maximum=20, value=2)
        self.spin_door_conn = QtWidgets.QSpinBox(maximum=100, value=8)
        self.cmb_door_mode = QtWidgets.QComboBox()
        self.cmb_door_mode.addItems(["Count", "Percentage", "Random"])
        self.spin_door_val = QtWidgets.QSpinBox(maximum=20, value=1)
        self.cmb_floor_mode = QtWidgets.QComboBox()
        self.cmb_floor_mode.addItems(["Auto Detect", "Exact Count"])
        self.spin_floor_inc = QtWidgets.QSpinBox(minimum=-99, maximum=99, value=0)
        self.cmb_col_mode = QtWidgets.QComboBox()
        self.cmb_col_mode.addItems(["Auto Detect", "Exact Count"])
        self.spin_col_inc = QtWidgets.QSpinBox(minimum=-99, maximum=99, value=0)
        self.chk_auto_crop = QtWidgets.QCheckBox("Auto Crop", checked=True)
        self.chk_empty_wall = QtWidgets.QCheckBox("Empty to Wall", checked=True)
        self.chk_variations = QtWidgets.QCheckBox("Enable Variations", checked=True)
        self.cmb_model = QtWidgets.QComboBox()
        self.cmb_model.addItems(["o3", "gpt-4.1", "o4-mini"])

        # Add widgets to the form layout
        form.addRow("<b>Window Connectivity</b>", self.spin_win_conn)
        form.addRow("Window Mode", self.cmb_win_mode)
        form.addRow("Window Value", self.spin_win_val)
        form.addRow("<b>Door Connectivity</b>", self.spin_door_conn)
        form.addRow("Door Mode", self.cmb_door_mode)
        form.addRow("Door Value", self.spin_door_val)
        form.addRow("<b>Floor Mode</b>", self.cmb_floor_mode)
        form.addRow("Floor Δ", self.spin_floor_inc)
        form.addRow("<b>Column Mode</b>", self.cmb_col_mode)
        form.addRow("Column Δ", self.spin_col_inc)
        toggles = QtWidgets.QHBoxLayout()
        toggles.addWidget(self.chk_auto_crop)
        toggles.addWidget(self.chk_empty_wall)
        toggles.addWidget(self.chk_variations)
        form.addRow(toggles)
        form.addRow("OpenAI Model", self.cmb_model)
        return grp

    def _connect_signals(self) -> None:
        """Connects all UI widget signals to their corresponding slots."""
        self.in_label.image_loaded.connect(self.on_image_loaded)
        self.btn_sym.clicked.connect(self.start_symbolic)
        self.btn_rigid.clicked.connect(self.start_rigid)
        self.btn_rep.clicked.connect(self.start_repeatable)
        self.btn_send_to_editor.clicked.connect(self._on_send_to_editor)

    @Slot(str)
    def on_image_loaded(self, path: str) -> None:
        """Handles a new image being loaded, updating state and UI."""
        self._image_path = path
        self.in_label.set_image(path)
        self._clear_outputs()
        self.status.setText("Ready for Step 1: Generate Symbolic")
        self._update_ui_state()

    @Slot()
    def start_symbolic(self) -> None:
        """Starts the Symbolic generation thread."""
        if not self._image_path: return
        thread = SymbolicThread(self._image_path, self)
        self._run_thread(thread, self._symbolic_done, "1/3: Generating symbolic…")

    @Slot()
    def start_rigid(self) -> None:
        """Starts the Rigid expression generation thread."""
        if not self._symbolic_bytes: return
        thread = RigidThread(self._symbolic_bytes, self._cfg(), self)
        self._run_thread(thread, self._rigid_done, "2/3: Generating rigid expression…")

    @Slot()
    def start_repeatable(self) -> None:
        """Starts the Repeatable expression generation thread."""
        if not self._rigid_text: return
        model = self.cmb_model.currentText()
        thread = RepeatableThread(self._rigid_text, model, self)
        self._run_thread(thread, self._repeat_done, "3/3: Generating repeatable…")

    def _run_thread(self, thread: QtCore.QThread, done_slot: QtCore.Slot, status_msg: str) -> None:
        """
        A helper to configure and start a worker thread.

        Args:
            thread: The QThread instance to run.
            done_slot: The slot to connect to the thread's `result_ready` signal.
            status_msg: The message to display in the status bar while running.
        """
        self._set_busy_state(status_msg)
        self.current_thread = thread
        thread.result_ready.connect(done_slot)
        thread.error.connect(self._on_error)
        thread.finished.connect(self._on_thread_finished)
        thread.start()

    @Slot(bytes)
    def _symbolic_done(self, data: bytes) -> None:
        """Handles the completion of the symbolic generation step."""
        self._symbolic_bytes = data
        self._set_label_pixmap_from_data(self.out_label, data)
        self.status.setText("✔ Symbolic done. Ready for Step 2.")

    @Slot(str, dict)
    def _rigid_done(self, text: str, visuals: dict) -> None:
        """Handles the completion of the rigid expression generation step."""
        self._rigid_text = text
        self._set_label_pixmap_from_data(self.out_label, visuals["visualization"])
        self._set_label_pixmap_from_data(self.grid_viz1_label, visuals["grid_visualization_1"])
        self._set_label_pixmap_from_data(self.grid_viz2_label, visuals["grid_visualization_2"])
        self.rigid_text_edit.setPlainText(text)
        self.status.setText("✔ Rigid expression done. Ready for Step 3.")

    @Slot(str)
    def _repeat_done(self, rep_text: str) -> None:
        """Handles the completion of the repeatable expression generation step."""
        self._final_repeatable_text = fix_facade_expression(rep_text)
        self.repeatable_text_edit.setPlainText(self._final_repeatable_text)
        self.status.setText("✔ Pipeline complete! Click “Send to Editor” to continue.")

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        """Displays an error message in the status bar."""
        self.status.setText(f"Error: {msg}")
        self.status.setStyleSheet("color:red;")

    @Slot()
    def _on_thread_finished(self) -> None:
        """Resets UI state after a thread finishes, successfully or not."""
        if self.current_thread:
            self.current_thread.deleteLater()
            self.current_thread = None
        self._update_ui_state()

    @Slot()
    def _on_send_to_editor(self) -> None:
        """Emits the final generated pattern."""
        if self._final_repeatable_text:
            self.patternGenerated.emit(self._final_repeatable_text)

    def _set_busy_state(self, message: str) -> None:
        """Puts the UI into a busy/locked state while a thread is running."""
        self.status.setText(message)
        self.status.setStyleSheet("")
        self.progress.setRange(0, 0)  # Infinite progress bar
        self.progress.show()
        for btn in (self.btn_sym, self.btn_rigid, self.btn_rep, self.btn_send_to_editor):
            btn.setEnabled(False)

    def _update_ui_state(self) -> None:
        """Enables/disables pipeline controls based on the current state."""
        self.progress.hide()
        is_idle = self.current_thread is None
        self.btn_sym.setEnabled(is_idle and self._image_path is not None)
        self.btn_rigid.setEnabled(is_idle and self._symbolic_bytes is not None)
        self.btn_rep.setEnabled(is_idle and self._rigid_text is not None)
        self.btn_send_to_editor.setEnabled(is_idle and self._final_repeatable_text is not None)

    def _clear_outputs(self) -> None:
        """Resets all output widgets and internal derived data."""
        for lbl, txt in (
            (self.out_label, "Symbolic / Main Viz"),
            (self.grid_viz1_label, "Grid Viz 1"),
            (self.grid_viz2_label, "Grid Viz 2"),
        ):
            lbl.clear()
            lbl.setText(txt)
        self.rigid_text_edit.clear()
        self.repeatable_text_edit.clear()
        self._symbolic_bytes = None
        self._rigid_text = None
        self._final_repeatable_text = None

    @staticmethod
    def _set_label_pixmap_from_data(label: QtWidgets.QLabel, data: bytes) -> None:
        """Loads image data from bytes and displays it in a QLabel."""
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(data)
        label.setPixmap(pixmap.scaled(
            label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def _cfg(self) -> dict[str, Any]:
        """Collects current parameter-form values into a dictionary for the API."""
        mode_map = {"Count": "exact count", "Percentage": "percentage", "Random": "random"}
        fc_map = {"Auto Detect": "auto detect", "Exact Count": "exact count"}

        return {
            "windows": {
                "connectivity": self.spin_win_conn.value(),
                "mode": mode_map[self.cmb_win_mode.currentText()],
                "mode_value": self.spin_win_val.value(),
            },
            "doors": {
                "connectivity": self.spin_door_conn.value(),
                "mode": mode_map[self.cmb_door_mode.currentText()],
                "mode_value": self.spin_door_val.value(),
            },
            "floors": {
                "mode": fc_map[self.cmb_floor_mode.currentText()],
                "mode_value": self.spin_floor_inc.value(),
            },
            "columns": {
                "mode": fc_map[self.cmb_col_mode.currentText()],
                "mode_value": self.spin_col_inc.value(),
            },
            "auto_crop": self.chk_auto_crop.isChecked(),
            "empty_to_wall": self.chk_empty_wall.isChecked(),
            "enable_variations": self.chk_variations.isChecked(),
        }