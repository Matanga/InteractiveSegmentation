from __future__ import annotations

from pathlib import Path
from typing import Any


from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal, Slot

from  segmentation_core import SymbolicThread, RigidThread, RepeatableThread, fix_facade_expression

# --------------------------------------------------------------------------- #
# 1.  Re-usable image drop label (Unchanged)
# --------------------------------------------------------------------------- #

class ImageDropLabel(QtWidgets.QLabel):
    image_loaded = Signal(str)
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setWordWrap(True)
        self.setStyleSheet("ImageDropLabel { border: 2px dashed #aaa; border-radius: 5px; color: #777; padding: 10px; }")
    def dragEnterEvent(self, ev: QtGui.QDragEnterEvent):
        if ev.mimeData().hasUrls(): ev.acceptProposedAction()
    def dropEvent(self, ev: QtGui.QDropEvent):
        if ev.mimeData().hasUrls():
            path = ev.mimeData().urls()[0].toLocalFile()
            if Path(path).suffix.lower() in (".jpg", ".jpeg", ".png"): self.image_loaded.emit(path)
    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Image", "", "Image files (*.png *.jpg *.jpeg)")
        if path: self.image_loaded.emit(path)
    def set_image(self, path: str):
        self.setPixmap(QtGui.QPixmap(path).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

# --------------------------------------------------------------------------- #
# 2.  Main Panel widget (Unchanged from the previous correct version)
# --------------------------------------------------------------------------- #
class EndpointPanel(QtWidgets.QWidget):
    patternGenerated = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image-Seed → Repeatable Panel")
        self._image_path: str | None = None
        self._symbolic_bytes: bytes | None = None
        self._rigid_text: str | None = None
        self._final_repeatable_text: str | None = None
        self.current_thread: QtCore.QThread | None = None
        self.in_label = ImageDropLabel("Click or drop an image")
        input_box = QtWidgets.QGroupBox("Input Image")
        input_layout = QtWidgets.QVBoxLayout(input_box); input_layout.addWidget(self.in_label)
        self.out_label = QtWidgets.QLabel("Symbolic / Main Viz", alignment=Qt.AlignCenter)
        self.grid_viz1_label = QtWidgets.QLabel("Grid Viz 1", alignment=Qt.AlignCenter)
        self.grid_viz2_label = QtWidgets.QLabel("Grid Viz 2", alignment=Qt.AlignCenter)
        for label in (self.out_label, self.grid_viz1_label, self.grid_viz2_label):
            label.setFrameShape(QtWidgets.QFrame.StyledPanel); label.setMinimumSize(100, 100)
        visuals_box = QtWidgets.QGroupBox("Visual Outputs")
        visuals_layout = QtWidgets.QVBoxLayout(visuals_box)
        grid_layout = QtWidgets.QHBoxLayout(); grid_layout.addWidget(self.grid_viz1_label, 1); grid_layout.addWidget(self.grid_viz2_label, 1)
        visuals_layout.addWidget(self.out_label, 3); visuals_layout.addLayout(grid_layout, 1)
        self.rigid_text_edit = QtWidgets.QTextEdit(readOnly=True, placeholderText="Rigid expression will appear here.")
        self.repeatable_text_edit = QtWidgets.QTextEdit(readOnly=True, placeholderText="Final repeatable expression will appear here.")
        expressions_splitter = QtWidgets.QSplitter(Qt.Horizontal)
        expressions_splitter.addWidget(self.rigid_text_edit); expressions_splitter.addWidget(self.repeatable_text_edit)
        self.params_box = self._build_params_box()
        self.progress = QtWidgets.QProgressBar(textVisible=False); self.progress.hide()
        self.status = QtWidgets.QLabel("Please load an image to begin.")
        self.btn_sym = QtWidgets.QPushButton("1. Generate Symbolic"); self.btn_sym.setEnabled(False)
        self.btn_rigid = QtWidgets.QPushButton("2. Generate Rigid"); self.btn_rigid.setEnabled(False)
        self.btn_rep = QtWidgets.QPushButton("3. Generate Repeatable"); self.btn_rep.setEnabled(False)
        self.btn_send_to_editor = QtWidgets.QPushButton("➤ Send to Editor")
        self.btn_send_to_editor.setEnabled(False)
        self.btn_send_to_editor.setStyleSheet("background-color: #5a9b5a; font-weight: bold;")
        left_panel = QtWidgets.QVBoxLayout(); left_panel.addWidget(input_box, 1); left_panel.addWidget(self.params_box, 0)
        right_panel = QtWidgets.QVBoxLayout(); right_panel.addWidget(visuals_box, 2); right_panel.addWidget(expressions_splitter, 1)
        main_splitter = QtWidgets.QSplitter(Qt.Horizontal)
        left_widget = QtWidgets.QWidget(); left_widget.setLayout(left_panel)
        right_widget = QtWidgets.QWidget(); right_widget.setLayout(right_panel)
        main_splitter.addWidget(left_widget); main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(0, 1); main_splitter.setStretchFactor(1, 2)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.btn_sym); btn_row.addWidget(self.btn_rigid); btn_row.addWidget(self.btn_rep)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_send_to_editor)
        status_row = QtWidgets.QHBoxLayout()
        status_row.addWidget(self.progress, 1); status_row.addWidget(self.status, 2)
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(main_splitter, 1); main_layout.addLayout(btn_row); main_layout.addLayout(status_row)
        self.in_label.image_loaded.connect(self.on_image_loaded)
        self.btn_sym.clicked.connect(self.start_symbolic)
        self.btn_rigid.clicked.connect(self.start_rigid)
        self.btn_rep.clicked.connect(self.start_repeatable)
        self.btn_send_to_editor.clicked.connect(self._on_send_to_editor)
    def _build_params_box(self) -> QtWidgets.QGroupBox:
        grp = QtWidgets.QGroupBox("Parameters"); form = QtWidgets.QFormLayout(grp)
        self.spin_win_conn = QtWidgets.QSpinBox(maximum=100, value=8); self.cmb_win_mode = QtWidgets.QComboBox(); self.cmb_win_mode.addItems(["Count", "Percentage", "Random"]); self.spin_win_val = QtWidgets.QSpinBox(maximum=20, value=2)
        self.spin_door_conn = QtWidgets.QSpinBox(maximum=100, value=8); self.cmb_door_mode = QtWidgets.QComboBox(); self.cmb_door_mode.addItems(["Count", "Percentage", "Random"]); self.spin_door_val = QtWidgets.QSpinBox(maximum=20, value=1)
        self.cmb_floor_mode = QtWidgets.QComboBox(); self.cmb_floor_mode.addItems(["Auto Detect", "Exact Count"]); self.spin_floor_inc = QtWidgets.QSpinBox(minimum=-99, maximum=99, value=0)
        self.cmb_col_mode = QtWidgets.QComboBox(); self.cmb_col_mode.addItems(["Auto Detect", "Exact Count"]); self.spin_col_inc = QtWidgets.QSpinBox(minimum=-99, maximum=99, value=0)
        self.chk_auto_crop = QtWidgets.QCheckBox("Auto Crop", checked=True); self.chk_empty_wall = QtWidgets.QCheckBox("Empty to Wall", checked=True); self.chk_variations = QtWidgets.QCheckBox("Enable Variations", checked=True)
        self.cmb_model = QtWidgets.QComboBox(); self.cmb_model.addItems(["gpt-4.1", "o4-mini", "o3"])
        form.addRow("<b>Window Connectivity</b>", self.spin_win_conn); form.addRow("Window Mode", self.cmb_win_mode); form.addRow("Window Value", self.spin_win_val)
        form.addRow("<b>Door Connectivity</b>", self.spin_door_conn); form.addRow("Door Mode", self.cmb_door_mode); form.addRow("Door Value", self.spin_door_val)
        form.addRow("<b>Floor Mode</b>", self.cmb_floor_mode); form.addRow("Floor Δ", self.spin_floor_inc)
        form.addRow("<b>Column Mode</b>", self.cmb_col_mode); form.addRow("Column Δ", self.spin_col_inc)
        toggles = QtWidgets.QHBoxLayout(); toggles.addWidget(self.chk_auto_crop); toggles.addWidget(self.chk_empty_wall); toggles.addWidget(self.chk_variations)
        form.addRow(toggles); form.addRow("OpenAI Model", self.cmb_model)
        return grp
    def _cfg(self) -> dict[str, Any]:
        mode_map = {"Count": "exact count", "Percentage": "percentage", "Random": "random"}; fc_map = {"Auto Detect": "auto detect", "Exact Count": "exact count"}
        return {"windows": {"connectivity": self.spin_win_conn.value(), "mode": mode_map[self.cmb_win_mode.currentText()], "mode_value": self.spin_win_val.value(),}, "doors": {"connectivity": self.spin_door_conn.value(), "mode": mode_map[self.cmb_door_mode.currentText()], "mode_value": self.spin_door_val.value(),}, "floors": {"mode": fc_map[self.cmb_floor_mode.currentText()], "mode_value": self.spin_floor_inc.value(),}, "columns": {"mode": fc_map[self.cmb_col_mode.currentText()], "mode_value": self.spin_col_inc.value(),}, "auto_crop": self.chk_auto_crop.isChecked(), "empty_to_wall": self.chk_empty_wall.isChecked(), "enable_variations": self.chk_variations.isChecked(),}
    @Slot(str)
    def on_image_loaded(self, path: str):
        self._image_path = path; self.in_label.set_image(path); self._clear_outputs(); self.status.setText("Ready for Step 1: Generate Symbolic"); self._update_ui_state()
    def _clear_outputs(self):
        self.out_label.clear(); self.out_label.setText("Symbolic / Main Viz"); self.grid_viz1_label.clear(); self.grid_viz1_label.setText("Grid Viz 1"); self.grid_viz2_label.clear(); self.grid_viz2_label.setText("Grid Viz 2")
        self.rigid_text_edit.clear(); self.repeatable_text_edit.clear(); self._symbolic_bytes = None; self._rigid_text = None; self._final_repeatable_text = None
    def _set_label_pixmap_from_data(self, label: QtWidgets.QLabel, data: bytes):
        pixmap = QtGui.QPixmap(); pixmap.loadFromData(data); label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    def start_symbolic(self):
        if not self._image_path: return
        self._run_thread(SymbolicThread(self._image_path, self), self._symbolic_done, "1/3: Generating symbolic image...")
    def start_rigid(self):
        if not self._symbolic_bytes: return
        self._run_thread(RigidThread(self._symbolic_bytes, self._cfg(), self), self._rigid_done, "2/3: Generating rigid expression...")
    def start_repeatable(self):
        if not self._rigid_text: return
        model = self.cmb_model.currentText(); self._run_thread(RepeatableThread(self._rigid_text, model, self), self._repeat_done, "3/3: Generating repeatable expression...")
    def _run_thread(self, thread: QtCore.QThread, done_slot, status_msg: str):
        self._set_busy_state(status_msg); self.current_thread = thread; self.current_thread.result_ready.connect(done_slot); self.current_thread.error.connect(self._on_error); self.current_thread.finished.connect(self._on_thread_finished); self.current_thread.start()
    @Slot(bytes)
    def _symbolic_done(self, data: bytes):
        self._symbolic_bytes = data; self._set_label_pixmap_from_data(self.out_label, data); self.status.setText("✔ Symbolic done. Ready for Step 2.")
    @Slot(str, dict)
    def _rigid_done(self, text: str, visuals: dict):
        self._rigid_text = text; self._set_label_pixmap_from_data(self.out_label, visuals["visualization"]); self._set_label_pixmap_from_data(self.grid_viz1_label, visuals["grid_visualization_1"]); self._set_label_pixmap_from_data(self.grid_viz2_label, visuals["grid_visualization_2"])
        self.rigid_text_edit.setPlainText(text); self.status.setText("✔ Rigid expression done. Ready for Step 3.")
    @Slot(str)
    def _repeat_done(self, rep_text: str):
        repeatable_expression = fix_facade_expression(rep_text); self._final_repeatable_text = repeatable_expression
        self.repeatable_text_edit.setPlainText(repeatable_expression); self.status.setText("✔ Pipeline complete! Click 'Send to Editor' to continue.")
    @Slot(str)
    def _on_error(self, msg: str):
        self.status.setText(f"Error: {msg}"); self.status.setStyleSheet("color: red;")
    @Slot()
    def _on_thread_finished(self):
        if self.current_thread: self.current_thread.deleteLater(); self.current_thread = None
        self._update_ui_state()
    @Slot()
    def _on_send_to_editor(self):
        if self._final_repeatable_text: self.patternGenerated.emit(self._final_repeatable_text)
    def _set_busy_state(self, message: str):
        self.status.setText(message); self.status.setStyleSheet(""); self.progress.setRange(0, 0); self.progress.show()
        self.btn_sym.setEnabled(False); self.btn_rigid.setEnabled(False); self.btn_rep.setEnabled(False); self.btn_send_to_editor.setEnabled(False)
    def _update_ui_state(self):
        self.progress.hide(); is_idle = self.current_thread is None
        self.btn_sym.setEnabled(is_idle and self._image_path is not None); self.btn_rigid.setEnabled(is_idle and self._symbolic_bytes is not None)
        self.btn_rep.setEnabled(is_idle and self._rigid_text is not None); self.btn_send_to_editor.setEnabled(is_idle and self._final_repeatable_text is not None)