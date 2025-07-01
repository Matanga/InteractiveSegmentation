# main.py
"""
Entry-point for smoke-testing the IBG-PE GUI skeleton.

Run:
    python main.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from building_grammar.core import parse  # domain-layer parser :contentReference[oaicite:0]{index=0}
from gui.main_window import MainWindow

# ---------------------------------------------------------------------------

DEMO_PATTERN = """
<A-B-C>                               
[D]2-<E>                              
<Win>-[Door]3                         
""".strip()


def main() -> None:
    """Bootstrap Qt, load demo pattern, and start the event-loop."""
    app = QApplication(sys.argv)

    # Top-level window
    window = MainWindow()
    window.show()

    # Domain model → GUI
    pattern = parse(DEMO_PATTERN)
    # `load_pattern()` is a thin helper added to MainWindow so we
    # don’t reach into its private attrs from the outside.
    window.load_pattern(pattern)

    sys.exit(app.exec())  # clean Qt shutdown


if __name__ == "__main__":
    main()
