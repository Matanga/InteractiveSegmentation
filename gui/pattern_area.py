from __future__ import annotations

from building_grammar.core import parse, validate
from facade_strip import FacadeStrip
from module_item import GroupWidget, ModuleWidget

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)


class PatternArea(QWidget):
    patternChanged: Signal = Signal(str)

    def __init__(self, num_floors: int = 3, parent=None):
        super().__init__(parent)
        self._num_floors = num_floors

        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignTop)
        v.setSpacing(4)
        for f in range(num_floors):
            v.addWidget(FacadeStrip(num_floors - f - 1))  # ground = last

    # ------------------------------------------------------------------
    def load_from_string(self, pattern_str: str, *, library: "ModuleLibrary") -> None:
        """
        MVP: wipe the current view and rebuild it from *pattern_str*.
        """
        model = parse(pattern_str)                 # 1) parse / validate
        self._clear_view()                         # 2) clear existing strips

        floor_count = len(model.floors)
        for i, floor in enumerate(model.floors):   # 3) create a strip per line
            strip_w = FacadeStrip(floor_count - i - 1)
            self.layout().addWidget(strip_w)

            for group in floor:                    # 4) create groups + modules
                grp_w = GroupWidget(kind=group.kind)
                strip_w.lay.addWidget(grp_w)

                for mod in group.modules:
                    # Instantiate a module widget (icon look-up can be added later)
                    grp_w.layout().addWidget(ModuleWidget(mod.name, False))

        self.patternChanged.emit(model.to_string())  # keep Output panel in sync

    # ------------------------------------------------------------------
    def _clear_view(self) -> None:
        """Delete all child widgets (simple & brute-force)."""
        lay = self.layout()
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
