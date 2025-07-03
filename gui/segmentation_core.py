from __future__ import annotations

import base64
import json
import os
from typing import Any
import requests
import re

from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt, Signal, QByteArray, QBuffer, QIODevice



# --------------------------------------------------------------------------- #
# 0.  API Calls
# --------------------------------------------------------------------------- #

BASE_URL = "https://api.dev.atlas.design"

def call_symbolic_image(image_path: str) -> bytes:
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
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["repeatable_expression"]

# --0.1 Image Helpers ------------------------------------------------------- #

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

# --0.2 REGEX Helpers ------------------------------------------------------- #

RE_BAD_CHARS   = re.compile(r"[^A-Za-z0-9><\[\]\-\s]+")
RE_GROUPS      = re.compile(r"([<\[])(.*?)([>\]])", re.S)
RE_OK_TOKEN    = re.compile(r"[A-Za-z]+[0-9]+$")
RE_NAME_ONLY   = re.compile(r"[A-Za-z]+$")
RE_BRACKET_GRP = re.compile(r"(?:<[^>]+>|\[[^\]]+\])")

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
# 1.  Thread classes
# --------------------------------------------------------------------------- #

class SymbolicThread(QtCore.QThread):
    result_ready = Signal(bytes)
    error = Signal(str)
    def __init__(self, image_path: str, parent=None): super().__init__(parent); self.image_path = image_path
    def run(self):
        try: self.result_ready.emit(call_symbolic_image(self.image_path))
        except Exception as exc: self.error.emit(str(exc))

class RigidThread(QtCore.QThread):
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
    result_ready = Signal(str)
    error = Signal(str)
    def __init__(self, rigid_text: str, model: str, parent=None): super().__init__(parent); self.rigid_text = rigid_text; self.model = model
    def run(self):
        try: self.result_ready.emit(call_repeatable_expression(self.rigid_text, self.model))
        except Exception as exc: self.error.emit(str(exc))
