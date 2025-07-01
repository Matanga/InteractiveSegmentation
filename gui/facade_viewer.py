# ibg_pe/gui/facade_viewer.py
from __future__ import annotations

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, QPointF


class FacadeViewer(QGraphicsView):
    """Displays the full façade pattern in a zoomable scene."""

    def __init__(self, parent: None = None) -> None:
        super().__init__(parent)

        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.NoDrag)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # TODO: install custom items once pattern is parsed

    # ---------- public slot ------------------------------------------------
    def center_on_floor(self, row: int) -> None:
        """Scroll the view so that the given floor row is roughly centered."""
        # Placeholder implementation - adjust when rows have real bounds
        self.centerOn(QPointF(0, row * 100))
