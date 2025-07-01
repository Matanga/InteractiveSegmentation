import sys
import json
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QMainWindow,
    QFrame, QLayout, QScrollArea
)
from PySide6.QtCore import Qt, QMimeData, QByteArray
from PySide6.QtGui import QDrag


# --------------------------------------------------------------------------- #
# Helper: layout owning `w`
# --------------------------------------------------------------------------- #
def owning_layout(w: QWidget) -> Optional[QLayout]:
    par = w.parent()
    if isinstance(par, QLayout):
        return par
    if isinstance(par, QWidget):
        return par.layout()
    return None


# --------------------------------------------------------------------------- #
# Draggable module chip
# --------------------------------------------------------------------------- #
class ModuleWidget(QLabel):
    def __init__(self, name: str, is_library: bool = False, parent=None):
        super().__init__(name, parent)
        self.name = name
        self.is_library = is_library
        self.setStyleSheet(
            "background: lightblue; padding: 4px; border: 1px solid gray; margin: 2px;"
        )
        self.setFixedWidth(60)
        self.setAlignment(Qt.AlignCenter)

        self._origin_layout: Optional[QLayout] = None
        self._origin_index: int = -1

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return

        mime = QMimeData()
        mime.setData(
            "application/x-ibg-module",
            QByteArray(json.dumps(
                {"type": "module", "name": self.name, "from_library": self.is_library}
            ).encode())
        )

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(e.pos())

        if not self.is_library:
            self._origin_layout = owning_layout(self)
            if self._origin_layout:
                self._origin_index = self._origin_layout.indexOf(self)
                self._origin_layout.removeWidget(self)
            self.hide()

        result = drag.exec(Qt.MoveAction)

        if result != Qt.MoveAction and not self.is_library and self._origin_layout:
            self._origin_layout.insertWidget(self._origin_index, self)
            self.show()


# --------------------------------------------------------------------------- #
# Static palette
# --------------------------------------------------------------------------- #
class ModuleLibrary(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(100)
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignTop)
        for n in ["A", "B", "C"]:
            v.addWidget(ModuleWidget(n, is_library=True))


# --------------------------------------------------------------------------- #
# One horizontal façade strip
# --------------------------------------------------------------------------- #
class FacadeStrip(QFrame):
    def __init__(self, floor_idx: int, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet("background:#fafafa; border:1px solid #ccc;")
        self.setFixedHeight(60)

        self.lay = QHBoxLayout(self)
        self.lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lay.setContentsMargins(8, 2, 8, 2)
        self.lay.setSpacing(4)

        # optional: floor label
        # self.lay.addWidget(QLabel(f"Floor {floor_idx} "), 0, Qt.AlignLeft)

        # red indicator
        self._indicator = QWidget()
        self._indicator.setFixedSize(10, 40)
        self._indicator.setStyleSheet("background:red;")
        self._indicator.hide()

    # --- drag events ------------------------------------------------------ #
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/x-ibg-module"):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if not e.mimeData().hasFormat("application/x-ibg-module"):
            return
        idx = self._insert_index(e.position().toPoint().x())
        self._remove_indicator()
        self.lay.insertWidget(idx, self._indicator)
        self._indicator.show()
        e.acceptProposedAction()

    def dragLeaveEvent(self, _):
        self._remove_indicator()

    def dropEvent(self, e):
        self._remove_indicator()
        data = json.loads(e.mimeData().data("application/x-ibg-module").data())
        name, from_lib = data["name"], data.get("from_library", False)
        idx = self._insert_index(e.position().toPoint().x())

        if from_lib:
            self.lay.insertWidget(idx, ModuleWidget(name, False))
        else:
            w = e.source()
            self.lay.insertWidget(idx, w)
            w.show()

        e.acceptProposedAction()

    # --- helpers ---------------------------------------------------------- #
    def _remove_indicator(self):
        if self._indicator.parent() is self:
            self.lay.removeWidget(self._indicator)
        self._indicator.hide()

    def _insert_index(self, mouse_x: int) -> int:
        for i in range(self.lay.count()):
            w = self.lay.itemAt(i).widget()
            if w is None or w is self._indicator:
                continue
            if mouse_x < w.x() + w.width() // 2:
                return i
        return self.lay.count()


# --------------------------------------------------------------------------- #
# Vertical container of strips
# --------------------------------------------------------------------------- #
class PatternArea(QWidget):
    def __init__(self, num_floors: int = 3, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignTop)
        v.setSpacing(6)
        for f in range(num_floors):
            v.addWidget(FacadeStrip(num_floors - f - 1))  # ground = last


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Strip Pattern Editor")

        library = ModuleLibrary()
        strips = PatternArea(3)

        # optional scroll if many floors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(strips)

        central = QWidget()
        h = QHBoxLayout(central)
        h.addWidget(library)
        h.addWidget(scroll)
        self.setCentralWidget(central)


# --------------------------------------------------------------------------- # WORKING
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(600, 400)
    win.show()
    sys.exit(app.exec())
