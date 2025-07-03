from __future__ import annotations

from building_grammar.core import parse, validate
from facade_strip import FacadeStrip
from module_item import GroupWidget, ModuleWidget

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from typing import Iterable
from building_grammar.core import GroupKind as CoreKind
from module_item import GroupKind as UiKind, GroupWidget, ModuleWidget

def _to_ui_kind(kind: CoreKind) -> UiKind:
    """Map core.GroupKind → module_item.GroupKind."""
    return UiKind.FILL if kind is CoreKind.FILL else UiKind.RIGID


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
        Parse *pattern_str* and rebuild the canvas.

        Raises
        ------
        GrammarError
            If the input violates Houdini façade-grammar rules.
        """
        model = parse(pattern_str)  # 1) validate
        self._clear_view()  # 2) reset grid

        for floor_idx, floor in enumerate(model.floors):
            strip = FacadeStrip(len(model.floors) - floor_idx - 1)
            self.layout().addWidget(strip)

            for grp in floor:
                ui_grp = GroupWidget(kind=_to_ui_kind(grp.kind))
                ui_grp.repeat = grp.repeat  # keep meta for later editing
                strip.lay.addWidget(ui_grp)

                sequence: Iterable[str] = (
                    grp.modules * (grp.repeat or 1)
                    if grp.kind is CoreKind.RIGID  # visually honour repeat
                    else grp.modules
                )
                for mod in sequence:
                    ui_grp.layout().addWidget(ModuleWidget(mod.name, False))

        # 3) notify Output panel
        self.patternChanged.emit(model.to_string())
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
