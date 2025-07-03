"""
endpoint_panel_v7.py  –  Fixes "413 Request Entity Too Large" error.
================================================================================

*   Adds a helper function to resize image data using QPixmap.
*   The RigidThread now resizes the symbolic image to a maximum of 1024px
    before sending it to the server, preventing the 413 error.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests
from PySide6 import QtCore, QtGui, QtWidgets
# <<< ADDED IMPORTS for image resizing
from PySide6.QtCore import Qt, Signal, Slot, QByteArray, QBuffer, QIODevice

# (The top section of the file with constants and API calls is unchanged)
# ...
# --------------------------------------------------------------------------- #
# 0.  Constants, Helpers, and Ported Logic
# --------------------------------------------------------------------------- #

BASE_URL = "https://api.dev.atlas.design"

# --- API Callers (Unchanged) ---
def call_symbolic_image(image_path: str) -> bytes:
    # ... (no change)
    url = f"{BASE_URL}/symbolic-image"
    with open(image_path, "rb") as fp:
        img_bytes = fp.read()
    files = {"image": (os.path.basename(image_path), img_bytes, "image/jpeg")}
    r = requests.post(url, files=files, timeout=60)
    r.raise_for_status()
    if "image/png" not in r.headers.get("Content-Type", ""):
        raise RuntimeError("Unexpected content-type from server")
    return r.content

def call_rigid_expression(symbolic_bytes: bytes, cfg: dict[str, Any]):
    # ... (no change)
    url = f"{BASE_URL}/rigid-expression"
    files = {"symbolic_image": ("symbolic.png", symbolic_bytes, "image/png")}
    data = {"cfg": json.dumps(cfg)}
    r = requests.post(url, files=files, data=data, timeout=120)
    r.raise_for_status()
    result = r.json()
    decoded_images = {
        k: base64.b64decode(result[k])
        for k in ("visualization", "grid_visualization_1", "grid_visualization_2")
    }
    return result["expression"], decoded_images

def call_repeatable_expression(rigid_text: str, model: str) -> str:
    # ... (no change)
    url = f"{BASE_URL}/repeatable-expression"
    payload = {"rigid_text": rigid_text, "openai_model": model}
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["repeatable_expression"]

# <<< NEW HELPER FUNCTION TO RESIZE IMAGE DATA
def resize_image_bytes(image_data: bytes, max_size: int = 1024) -> bytes:
    """
    Resizes image data if its dimensions exceed max_size, preserving aspect ratio.
    Returns image data as bytes.
    """
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(image_data)

    if pixmap.width() <= max_size and pixmap.height() <= max_size:
        return image_data  # No resizing needed

    # Scale the pixmap down, keeping aspect ratio
    scaled_pixmap = pixmap.scaled(
        max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )

    # Save the resized pixmap back to a bytes object
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.WriteOnly)
    scaled_pixmap.save(buffer, "PNG")  # Save as PNG

    return byte_array.data()

RE_BAD_CHARS   = re.compile(r"[^A-Za-z0-9><\[\]\-\s]+")
RE_GROUPS      = re.compile(r"([<\[])(.*?)([>\]])", re.S)
RE_OK_TOKEN    = re.compile(r"[A-Za-z]+[0-9]+$")
RE_NAME_ONLY   = re.compile(r"[A-Za-z]+$")
RE_BRACKET_GRP = re.compile(r"(?:<[^>]+>|\[[^\]]+\])")
# (The rest of the ported logic is unchanged)
def fix_facade_expression(expr: str) -> str:
    # ... (no change)
    expr = RE_BAD_CHARS.sub("", expr)
    def _fix_group(m: re.Match) -> str:
        open_, body, close_ = m.groups()
        tokens = [tok.strip() for tok in body.split("-") if tok.strip()]
        fixed_tokens = []
        for tok in tokens:
            if RE_OK_TOKEN.fullmatch(tok):
                fixed_tokens.append(tok)
            elif RE_NAME_ONLY.fullmatch(tok):
                fixed_tokens.append(f"{tok}00")
        return f"{open_}{'-'.join(fixed_tokens)}{close_}" if fixed_tokens else ""
    expr = RE_GROUPS.sub(_fix_group, expr)
    cleaned_lines = []
    for line in expr.splitlines():
        groups = RE_BRACKET_GRP.findall(line)
        if groups:
            cleaned_lines.append(" ".join(groups))
    return "\n".join(cleaned_lines)

# --------------------------------------------------------------------------- #
# 1.  Thread classes (RigidThread is MODIFIED)
# --------------------------------------------------------------------------- #
class SymbolicThread(QtCore.QThread):
    # ... (no change)
    result_ready = Signal(bytes)
    error = Signal(str)
    def __init__(self, image_path: str, parent=None): super().__init__(parent); self.image_path = image_path
    def run(self):
        try: self.result_ready.emit(call_symbolic_image(self.image_path))
        except Exception as exc: self.error.emit(str(exc))


class RigidThread(QtCore.QThread):
    # <<< THIS THREAD IS MODIFIED
    result_ready = Signal(str, dict)
    error = Signal(str)

    def __init__(self, symbolic_bytes: bytes, cfg: dict[str, Any], parent=None):
        super().__init__(parent)
        self.symbolic_bytes = symbolic_bytes
        self.cfg = cfg

    def run(self):
        try:
            # <<< FIX: Resize the symbolic image before sending it to the server.
            print(f"Original symbolic image size: {len(self.symbolic_bytes) / 1024:.2f} KB")
            resized_bytes = resize_image_bytes(self.symbolic_bytes, max_size=1024)
            print(f"Resized symbolic image size: {len(resized_bytes) / 1024:.2f} KB")

            text, visuals = call_rigid_expression(resized_bytes, self.cfg)
            self.result_ready.emit(text, visuals)
        except Exception as exc:
            self.error.emit(str(exc))


class RepeatableThread(QtCore.QThread):
    # ... (no change)
    result_ready = Signal(str)
    error = Signal(str)
    def __init__(self, rigid_text: str, model: str, parent=None): super().__init__(parent); self.rigid_text = rigid_text; self.model = model
    def run(self):
        try: self.result_ready.emit(call_repeatable_expression(self.rigid_text, self.model))
        except Exception as exc: self.error.emit(str(exc))

# (The rest of the file, including ImageDropLabel and the entire EndpointPanel, is unchanged)
# ...
# --------------------------------------------------------------------------- #
# 2.  Re-usable image drop label (Unchanged)
# --------------------------------------------------------------------------- #
class ImageDropLabel(QtWidgets.QLabel):
    # ... (no change)
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
# 3.  Main Panel widget (Unchanged from the previous correct version)
# --------------------------------------------------------------------------- #
class EndpointPanel(QtWidgets.QWidget):
    # ... (no change)
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