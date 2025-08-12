# services/facade_segmentation.py
from __future__ import annotations

import base64
import json
import os
from typing import Any

import requests
from PySide6 import QtCore, QtGui
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt, Signal

# If you later move this to a config module, import from there.
BASE_URL = "https://api.dev.atlas.design"
# BASE_URL = "https://api.sandbox.atlas.design"

# ──────────────────────────────────────────────────────────────
# API calls (signatures unchanged)
# ──────────────────────────────────────────────────────────────
def call_symbolic_image(image_bytes: bytes, filename: str) -> bytes:
    url = f"{BASE_URL}/symbolic-image"
    files = {"image": (filename, image_bytes, "image/jpeg")}
    r = requests.post(url, files=files, timeout=60)
    r.raise_for_status()
    if "image/png" not in r.headers.get("Content-Type", ""):
        raise RuntimeError("Unexpected content-type from server")
    return r.content

def call_rigid_expression(symbolic_bytes: bytes, cfg: dict[str, Any]):
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
    url = f"{BASE_URL}/repeatable-expression"
    payload = {"rigid_text": rigid_text, "openai_model": model}
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["repeatable_expression"]

# ──────────────────────────────────────────────────────────────
# Utilities (unchanged; Qt-based resize)
# ──────────────────────────────────────────────────────────────
def resize_image_bytes(image_data: bytes, max_size: int = 1024) -> bytes:
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(image_data)

    if pixmap.width() <= max_size and pixmap.height() <= max_size:
        return image_data

    scaled_pixmap = pixmap.scaled(
        max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.WriteOnly)
    scaled_pixmap.save(buffer, "PNG")
    return byte_array.data()

# ──────────────────────────────────────────────────────────────
# Worker threads (original names + signatures restored)
# ──────────────────────────────────────────────────────────────
class SymbolicThread(QtCore.QThread):
    """Calls the symbolic-image API without blocking the UI."""
    result_ready = Signal(bytes)
    error = Signal(str)

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path

    def run(self):
        try:
            with open(self.image_path, "rb") as f:
                original_bytes = f.read()
            resized_input_bytes = resize_image_bytes(original_bytes, max_size=2048)
            result = call_symbolic_image(resized_input_bytes, os.path.basename(self.image_path))
            self.result_ready.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

class RigidThread(QtCore.QThread):
    """Calls the rigid-expression API."""
    result_ready = Signal(str, dict)
    error = Signal(str)

    def __init__(self, symbolic_bytes: bytes, cfg: dict[str, Any], parent=None):
        super().__init__(parent)
        self.symbolic_bytes = symbolic_bytes
        self.cfg = cfg

    def run(self):
        try:
            resized_bytes = resize_image_bytes(self.symbolic_bytes, max_size=1024)
            text, visuals = call_rigid_expression(resized_bytes, self.cfg)
            self.result_ready.emit(text, visuals)
        except Exception as exc:
            self.error.emit(str(exc))

class RepeatableThread(QtCore.QThread):
    """Calls the repeatable-expression API."""
    result_ready = Signal(str)
    error = Signal(str)

    def __init__(self, rigid_text: str, model: str, parent=None):
        super().__init__(parent)
        self.rigid_text = rigid_text
        self.model = model

    def run(self):
        try:
            result = call_repeatable_expression(self.rigid_text, self.model)
            self.result_ready.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

# ──────────────────────────────────────────────────────────────
# Compatibility aliases (so both old and new names work)
# ──────────────────────────────────────────────────────────────
SymbolicImageWorker = SymbolicThread
RigidExpressionWorker = RigidThread
RepeatableExpressionWorker = RepeatableThread
