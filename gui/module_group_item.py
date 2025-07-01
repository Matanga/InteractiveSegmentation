# ibg_pe/gui/module_group_item.py
from __future__ import annotations

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QPainter
from PySide6.QtCore import QRectF


class ModuleGroupItem(QGraphicsItem):
    """Displays a group box with optional repeat count."""

    def __init__(self, is_rigid: bool, repeat: int | None = None):
        super().__init__()
        self.is_rigid = is_rigid
        self.repeat = repeat or 1

    # ---------- QGraphicsItem overrides ------------------------------------
    def boundingRect(self) -> QRectF:  # noqa: N802
        return QRectF(0, 0, 40, 25)  # updated later

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: N802
        rect = self.boundingRect()
        # Draw brackets
        painter.drawRect(rect)
        # Draw repeat count if > 1
        if self.repeat > 1:
            painter.drawText(rect, 0, f"×{self.repeat}")
