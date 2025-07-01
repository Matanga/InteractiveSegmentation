# ibg_pe/gui/module_item.py
from __future__ import annotations

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QPainter, QFontMetrics
from PySide6.QtCore import QRectF, QPointF


class ModuleItem(QGraphicsItem):
    """Renders a single module (icon or fallback text)."""

    def __init__(self, name: str, size: float = 18.0):
        super().__init__()
        self._name = name
        self._size = size
        # TODO: cache pixmap of SVG icon if available

    # ---------- QGraphicsItem overrides ------------------------------------
    def boundingRect(self) -> QRectF:  # noqa: N802
        fm = QFontMetrics(self.scene().font())
        width = fm.horizontalAdvance(self._name) + 4
        height = fm.height() + 4
        return QRectF(0, 0, width, height)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: N802
        rect = self.boundingRect()
        painter.drawRect(rect)
        painter.drawText(rect.adjusted(2, 0, -2, 0), 0, self._name)
