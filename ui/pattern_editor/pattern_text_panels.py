# ibg_pe/ui/pattern_text_panels.py
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from domain.grammar import GrammarError, parse
from domain.pattern_validator import validate               # semantic checks


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
        self.setObjectName("PatternInputPanel")

        self._editor = QPlainTextEdit()
        self._editor.setObjectName("PatternInputEditor")

        self._apply_btn = QPushButton("Apply ↩︎")
        self._apply_btn.setObjectName("PatternApplyButton")

        layout = QVBoxLayout(self)
        layout.addWidget(self._editor, 1)
        layout.addWidget(self._apply_btn)

        # Wire button → validator
        self._apply_btn.clicked.connect(self._on_apply)

    def get_text(self) -> str:
        """Return the current pattern text."""
        return self._editor.toPlainText()

    def set_text(self, text: str) -> None:
        """Set the editor's text."""
        self._editor.setPlainText(text)

    def clear(self) -> None:
        """Clear the editor."""
        self._editor.clear()
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
        self.setObjectName("PatternOutputPanel")

        self._viewer = QPlainTextEdit(readOnly=True)
        self._viewer.setObjectName("PatternOutputViewer")

        layout = QVBoxLayout(self)
        layout.addWidget(self._viewer)

    # slot
    def update_pattern(self, new_str: str) -> None:           # noqa: D401
        """Receive canonical string from PatternArea and display it."""
        self._viewer.setPlainText(new_str)

    def clear(self) -> None:
        """Clear the viewer."""
        self._viewer.clear()


