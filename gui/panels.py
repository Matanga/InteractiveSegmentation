# ibg_pe/gui/panels.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from building_grammar.core import GrammarError, parse
from building_grammar.validator import validate               # semantic checks


# ──────────────────────────────────────────────────────────────
# Pattern-input panel
# ──────────────────────────────────────────────────────────────
class PatternInputPanel(QWidget):
    """
    Text box + “Apply” button.
    Emits ``patternApplied(str)`` after the string passes syntax & semantic
    validation.
    """

    patternApplied: Signal = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        self._editor = QPlainTextEdit()
        self._apply_btn = QPushButton("Apply ↩︎")

        layout = QVBoxLayout(self)
        layout.addWidget(self._editor, 1)
        layout.addWidget(self._apply_btn)

        # Wire button → validator
        self._apply_btn.clicked.connect(self._on_apply)

    # ----------------------------------------------------------
    def _on_apply(self) -> None:
        txt = self._editor.toPlainText()
        try:
            parse(txt)                # syntax
            validate(txt)             # semantic
        except GrammarError as exc:
            QMessageBox.critical(self, "Invalid pattern", str(exc))
            return

        self.patternApplied.emit(txt)


# ──────────────────────────────────────────────────────────────
# Pattern-output panel
# ──────────────────────────────────────────────────────────────
class PatternOutputPanel(QWidget):
    """Read-only viewer kept in sync with :pyclass:`PatternArea`."""

    def __init__(self) -> None:
        super().__init__()

        self._viewer = QPlainTextEdit(readOnly=True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._viewer)

    # slot
    def update_pattern(self, new_str: str) -> None:           # noqa: D401
        """Receive canonical string from PatternArea and display it."""
        self._viewer.setPlainText(new_str)


# ──────────────────────────────────────────────────────────────
# Endpoint-workflow placeholder
# ──────────────────────────────────────────────────────────────
class EndpointPanel(QWidget):
    """
    Stub for the future “Image Seed Workflow”.
    Displays a placeholder until the PRD is updated to include networking.
    """

    def __init__(self) -> None:
        super().__init__()

        placeholder = QLabel(
            "⚠️  Image-seed workflow is *not* in PRD v0.1.\n"
            "Revise the scope before implementing."
        )
        placeholder.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(placeholder)
