"""
Core functionality for the image segmentation and facade expression generation process.

This module provides three main components:
1.  API Functions: A set of functions to communicate with the backend services for
    symbolic image generation, rigid expression extraction, and repeatable
    expression generation.
2.  Utility Functions: Helpers for resizing images and cleaning up facade
    expression strings using regular expressions.
3.  Worker Threads: Qt-based QThread subclasses that perform the API calls in the
    background to avoid blocking the main UI thread.
"""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import requests
from PySide6 import QtCore, QtGui
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt, Signal

# =========================================================================== #
# 1.  API Call Functions
# =========================================================================== #

BASE_URL = "https://api.dev.atlas.design"
#BASE_URL = "https://api.sandbox.atlas.design"


def call_symbolic_image(image_bytes: bytes, filename: str) -> bytes:
    """
    Calls the symbolic-image API endpoint to convert a facade image to a symbolic representation.

    Args:
        image_bytes: The image content as bytes.
        filename: The original filename to use in the multipart request.

    Raises:
        requests.HTTPError: If the API call fails.
        RuntimeError: If the server returns an unexpected content type.
    """
    url = f"{BASE_URL}/symbolic-image"
    files = {"image": (filename, image_bytes, "image/jpeg")}
    r = requests.post(url, files=files, timeout=60)
    r.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    if "image/png" not in r.headers.get("Content-Type", ""):
        raise RuntimeError("Unexpected content-type from server")
    return r.content

def call_rigid_expression(symbolic_bytes: bytes, cfg: dict[str, Any]):
    """
    Calls the rigid-expression API to extract a facade pattern from a symbolic image.

    Args:
        symbolic_bytes: The symbolic image in PNG format as bytes.
        cfg: A configuration dictionary for the extraction process.

    Returns:
        A tuple containing the extracted expression string and a dictionary of
        visualization images (as bytes).

    Raises:
        requests.HTTPError: If the API call fails.
    """
    url = f"{BASE_URL}/rigid-expression"
    files = {"symbolic_image": ("symbolic.png", symbolic_bytes, "image/png")}
    data = {"cfg": json.dumps(cfg)}
    r = requests.post(url, files=files, data=data, timeout=120)
    r.raise_for_status()
    result = r.json()
    # Decode the base64-encoded visualization images returned by the API.
    decoded_images = {
        k: base64.b64decode(result[k])
        for k in ("visualization", "grid_visualization_1", "grid_visualization_2")
    }
    return result["expression"], decoded_images

def call_repeatable_expression(rigid_text: str, model: str) -> str:
    """
    Calls the repeatable-expression API to find repeating patterns in a rigid expression.

    Args:
        rigid_text: The rigid facade expression string.
        model: The name of the AI model to use for the analysis.

    Returns:
        The simplified repeatable expression string.

    Raises:
        requests.HTTPError: If the API call fails.
    """
    url = f"{BASE_URL}/repeatable-expression"
    payload = {"rigid_text": rigid_text, "openai_model": model}
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["repeatable_expression"]


# =========================================================================== #
# 2.  Utility Functions
# =========================================================================== #

# --- 2.1 Image Helpers ---

def resize_image_bytes(image_data: bytes, max_size: int = 1024) -> bytes:
    """
    Resizes image data if its dimensions exceed a max size, preserving aspect ratio.

    Args:
        image_data: The raw image data as bytes.
        max_size: The maximum width or height for the output image.

    Returns:
        The resized image data as bytes (in PNG format). If no resize was
        needed, the original bytes are returned.
    """
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(image_data)

    if pixmap.width() <= max_size and pixmap.height() <= max_size:
        return image_data  # No resizing needed

    # Scale the pixmap down, keeping the aspect ratio.
    scaled_pixmap = pixmap.scaled(
        max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )

    # Save the resized pixmap back to a bytes object via a buffer.
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.WriteOnly)
    scaled_pixmap.save(buffer, "PNG")  # Always save as PNG after scaling
    return byte_array.data()


# --- 2.2 REGEX Helpers ---

# Removes any characters that are not part of a valid facade expression.
RE_BAD_CHARS = re.compile(r"[^A-Za-z0-9><\[\]\-\s]+")
# Finds all valid group structures, like <...> or [...].
RE_GROUPS = re.compile(r"([<\[])(.*?)([>\]])", re.S)
# Matches a valid token (e.g., "window00", "door01").
RE_OK_TOKEN = re.compile(r"[A-Za-z]+[0-9]+$")
# Matches a token with a name but no number (e.g., "window").
RE_NAME_ONLY = re.compile(r"[A-Za-z]+$")
# Finds all complete group expressions on a single line.
RE_BRACKET_GRP = re.compile(r"(?:<[^>]+>|\[[^\]]+\])")


def fix_facade_expression(expr: str) -> str:
    """
    Cleans and standardizes a raw facade expression string from the API.

    This function performs several steps:
    1. Removes illegal characters.
    2. Fixes malformed tokens within groups (e.g., appends "00" to names).
    3. Removes empty groups.
    4. Ensures each line contains only valid, complete group expressions.

    Args:
        expr: The raw expression string.

    Returns:
        A cleaned and standardized expression string.
    """
    expr = RE_BAD_CHARS.sub("", expr)

    def _fix_group(m: re.Match) -> str:
        """A substitution function to fix tokens inside a single matched group."""
        open_bracket, body, close_bracket = m.groups()
        tokens = [tok.strip() for tok in body.split("-") if tok.strip()]
        fixed_tokens = []
        for tok in tokens:
            if RE_OK_TOKEN.fullmatch(tok):
                fixed_tokens.append(tok)
            elif RE_NAME_ONLY.fullmatch(tok):
                # If a token is just a name, append a default number.
                fixed_tokens.append(f"{tok}00")
        # Reconstruct the group, or return an empty string if it's now empty.
        return f"{open_bracket}{'-'.join(fixed_tokens)}{close_bracket}" if fixed_tokens else ""

    expr = RE_GROUPS.sub(_fix_group, expr)

    # Re-process the expression line by line to ensure clean formatting.
    cleaned_lines = []
    for line in expr.splitlines():
        groups = RE_BRACKET_GRP.findall(line)
        if groups:
            cleaned_lines.append(" ".join(groups))  # Use a single space as separator
    return "\n".join(cleaned_lines)


def _sanitize_rigid_for_sandbox( text: str) -> str:
    """
    Cleans and reformats a raw rigid expression for the sandbox editor.

    This performs several actions:
    1. Unifies all modules on a line into a single `[...]` group.
    2. Ensures all module names are capitalized.
    3. Appends "00" to module names that lack a number.
    4. Uses spaces as separators.
    """
    processed_lines = []
    for line in text.strip().splitlines():
        # 1. Find all individual module names on the current line.
        # This regex extracts the content from within each `[...]`.
        modules_on_line = re.findall(r'\[([^,\]]+)\]', line)

        sanitized_modules = []
        for module in modules_on_line:
            # 2. Capitalize the first letter.
            sanitized_module = module.strip().capitalize()

            # 3. Check if the module name ends with a number. If not, add "00".
            if not re.search(r'\d+$', sanitized_module):
                sanitized_module += "00"

            sanitized_modules.append(sanitized_module)

        # 4. If any modules were found, join them with spaces and wrap them
        #    in a single pair of brackets for the final line.
        if sanitized_modules:
            final_line = f"[{'-'.join(sanitized_modules)}]"
            processed_lines.append(final_line)

    # Join all processed lines back together with newlines.
    return "\n".join(processed_lines)

# =========================================================================== #
# 3.  Worker Threads
# =========================================================================== #

class SymbolicThread(QtCore.QThread):
    """A worker thread to call the symbolic-image API without blocking the UI."""
    result_ready = Signal(bytes)
    error = Signal(str)

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path

    def run(self):
        """The entry point for the thread's execution."""
        try:
            # Read and proactively resize the user-provided image to prevent upload errors.
            with open(self.image_path, "rb") as f:
                original_bytes = f.read()

            # A max dimension of 2048px is a generous but safe limit for facade photos.
            resized_input_bytes = resize_image_bytes(original_bytes, max_size=2048)

            result = call_symbolic_image(resized_input_bytes, os.path.basename(self.image_path))
            self.result_ready.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class RigidThread(QtCore.QThread):
    """A worker thread to call the rigid-expression API."""
    result_ready = Signal(str, dict)
    error = Signal(str)

    def __init__(self, symbolic_bytes: bytes, cfg: dict[str, Any], parent=None):
        super().__init__(parent)
        self.symbolic_bytes = symbolic_bytes
        self.cfg = cfg

    def run(self):
        """The entry point for the thread's execution."""
        try:
            # Resize the image before sending to avoid overly large payloads.
            print(f"Original symbolic image size: {len(self.symbolic_bytes) / 1024:.2f} KB")
            resized_bytes = resize_image_bytes(self.symbolic_bytes, max_size=1024)
            print(f"Resized symbolic image size: {len(resized_bytes) / 1024:.2f} KB")

            text, visuals = call_rigid_expression(resized_bytes, self.cfg)
            self.result_ready.emit(text, visuals)
        except Exception as exc:
            self.error.emit(str(exc))


class RepeatableThread(QtCore.QThread):
    """A worker thread to call the repeatable-expression API."""
    result_ready = Signal(str)
    error = Signal(str)

    def __init__(self, rigid_text: str, model: str, parent=None):
        super().__init__(parent)
        self.rigid_text = rigid_text
        self.model = model

    def run(self):
        """The entry point for the thread's execution."""
        try:
            result = call_repeatable_expression(self.rigid_text, self.model)
            self.result_ready.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))