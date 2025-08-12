"""
Minimal “walking-skeleton” GUI for IBG-PE.
Paste a façade-grammar string → parse & render → copy back to clipboard.

Compatible with building_grammar.core (parse / GrammarError / Pattern).
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# —— core imports ————————————————————————————————————————————————
from domain.grammar import GrammarError, Pattern, parse  # :contentReference[oaicite:0]{index=0}

# ---------------------------------------------------------------------------


class GridView(QScrollArea):
    """Very small, read-only view that lays Pattern modules in a grid."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._grid = QGridLayout()
        self._grid.setSpacing(4)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        container = QWidget()
        container.setLayout(self._grid)
        self.setWidget(container)
        self.setWidgetResizable(True)

    # ------------------------------------------------------------------ API
    def show_pattern(self, pattern: Pattern) -> None:
        """Clear old widgets and display *pattern* top-down (ground floor last)."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        # Houdini rule: last line = ground floor → draw reversed
        for row_idx, floor in enumerate(reversed(pattern.floors)):
            for col_idx, group in enumerate(floor):
                for m_idx, module in enumerate(group.modules):
                    lbl = QLabel(module.name)
                    lbl.setObjectName("moduleLabel")
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl.setStyleSheet(
                        "QLabel#moduleLabel {"
                        " border: 1px solid #777; padding: 3px; min-width: 48px; }"
                    )
                    # stagger modules of same group horizontally
                    self._grid.addWidget(lbl, row_idx, col_idx + m_idx)


class MainWindow(QMainWindow):
    """Minimal IBG-PE MVP window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IBG-PE – MVP")
        self._build_ui()

    # ---------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        # pattern input
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Paste façade-grammar string here…")
        root.addWidget(self.input_edit)

        # buttons row
        btn_row = QHBoxLayout()
        parse_btn = QPushButton("Parse & Render")
        export_btn = QPushButton("Copy to Clipboard")
        btn_row.addWidget(parse_btn)
        btn_row.addWidget(export_btn)
        root.addLayout(btn_row)

        # grid view
        self.grid_view = GridView()
        root.addWidget(self.grid_view, stretch=1)

        self.setCentralWidget(central)

        # signals
        parse_btn.clicked.connect(self._on_parse_clicked)
        export_btn.clicked.connect(self._on_export_clicked)

    # ---------------------------------------------------------- slots
    def _on_parse_clicked(self) -> None:
        raw = self.input_edit.toPlainText().strip()
        if not raw:
            return

        try:
            pattern = parse(raw)  # may raise GrammarError
        except GrammarError as exc:  # :contentReference[oaicite:1]{index=1}
            QMessageBox.critical(self, "Validation error", str(exc))
            return

        self.grid_view.show_pattern(pattern)

    def _on_export_clicked(self) -> None:
        raw = self.input_edit.toPlainText().strip()
        if not raw:
            return
        QApplication.clipboard().setText(raw, QClipboard.Clipboard)
        QMessageBox.information(self, "Export", "Pattern copied to clipboard.")


# ---------------------------------------------------------------------------


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(900, 600)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
