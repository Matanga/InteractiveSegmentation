from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QWidget
)

from ModuleItem import GroupWidget, ModuleWidget, _cleanup_empty_group



class FacadeStrip(QFrame):
    def __init__(self, floor_idx: int, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet("background:#fafafa; border:1px solid #ccc;")
        self.setFixedHeight(60)

        self.lay = QHBoxLayout(self)
        self.lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)

        self._indicator = QWidget()
        self._indicator.setFixedSize(10, 45)
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

    # ------------------------------------------------------------------- #
    # Drag events
    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasFormat("application/x-ibg-module") or e.mimeData().hasFormat(
            "application/x-ibg-group"
        ):
            e.acceptProposedAction()

    def dragMoveEvent(self, e) -> None:
        if not (
            e.mimeData().hasFormat("application/x-ibg-module")
            or e.mimeData().hasFormat("application/x-ibg-group")
        ):
            return
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator()
        self.lay.insertWidget(idx, self._indicator)
        self._indicator.show()
        e.acceptProposedAction()

    def dragLeaveEvent(self, _e) -> None:
        self._remove_indicator()

    def dropEvent(self, e) -> None:
        self._remove_indicator()

        # MODULE dropped
        if e.mimeData().hasFormat("application/x-ibg-module"):
            data=json.loads(e.mimeData().data("application/x-ibg-module").data())
            idx=self._insert_index(e.position().toPoint().x())

            # create new group container at drop index
            grp=GroupWidget()
            self.lay.insertWidget(idx,grp)

            # inject the module into that container
            w=ModuleWidget(data["name"],False) if data.get("from_library") else e.source()
            grp.layout().addWidget(w)
            w.show() if not data.get("from_library") else None
            e.acceptProposedAction()
            if not data.get("from_library"):
                _cleanup_empty_group(w._origin_layout)
            return



        # GROUP dropped
        if e.mimeData().hasFormat("application/x-ibg-group"):
            w: GroupWidget = e.source()
            idx = self._insert_index(e.position().toPoint().x())
            self.lay.insertWidget(idx, w)
            w.show()
            e.acceptProposedAction()

    # ------------------------------------------------------------------- #
    # helpers
    def _insert_index(self, mouse_x: int) -> int:
        for i in range(self.lay.count()):
            w = self.lay.itemAt(i).widget()
            if w is None or w is self._indicator:
                continue
            if mouse_x < w.x() + w.width() // 2:
                return i
        return self.lay.count()

    def _remove_indicator(self) -> None:
        if self._indicator.parent() is self:
            self.lay.removeWidget(self._indicator)
        self._indicator.hide()

