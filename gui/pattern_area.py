# pattern_area.py (Corrected for Module object handling)

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget, QPushButton

from building_grammar.core import parse
from facade_strip import FacadeStrip
from module_item import GroupWidget, ModuleWidget
from typing import Iterable
from building_grammar.core import GroupKind as CoreKind, Module  # Import Module
from module_item import GroupKind as UiKind


def _to_ui_kind(kind: CoreKind) -> UiKind:
    return UiKind.FILL if kind is CoreKind.FILL else UiKind.RIGID


class PatternArea(QWidget):
    patternChanged = Signal(str)

    def __init__(self, num_floors: int = 3, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setSpacing(8)
        self._root_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._strips_layout = QVBoxLayout()
        self._strips_layout.setSpacing(4)
        self._strips_layout.setAlignment(Qt.AlignTop)
        self._root_layout.addLayout(self._strips_layout)

        self.add_floor_button = QPushButton("➕ Add Floor")
        self.add_floor_button.clicked.connect(self._add_strip_at_top)
        self.add_floor_button.setFixedWidth(200)
        self._root_layout.addWidget(self.add_floor_button, 0, Qt.AlignHCenter)
        self._root_layout.addStretch(1)

        for _ in range(num_floors):
            self._add_strip_at_top()

    # --- Load/Clear Logic ---

    def load_from_string(self, pattern_str: str, *, library: "ModuleLibrary") -> None:
        try:
            model = parse(pattern_str)
        except Exception as e:
            print(f"Error parsing pattern string: {e}")
            return

        self._clear_view()

        # This builds the UI from the top floor down, matching the text file's visual order.
        for floor_idx, floor_data in list(enumerate(model.floors)):
            strip = FacadeStrip(floor_idx)
            strip.header.remove_requested.connect(self._remove_strip)

            for grp_data in floor_data:
                ui_group = GroupWidget(kind=_to_ui_kind(grp_data.kind))
                ui_group.repeat = grp_data.repeat
                strip.module_container_layout.addWidget(ui_group)

                sequence: Iterable[Module] = (
                    grp_data.modules * (grp_data.repeat or 1)
                    if grp_data.kind is CoreKind.RIGID else grp_data.modules
                )

                for mod_object in sequence:
                    ui_group.layout().addWidget(ModuleWidget(mod_object.name, False))

            # The key is to add each new strip to the *bottom* of the layout now.
            # Since we are iterating from the top floor down, this builds the correct visual stack.
            self._strips_layout.addWidget(strip)

        self._re_index_floors()
        self.patternChanged.emit(model.to_string())

    def _clear_view(self) -> None:
        while self._strips_layout.count():
            item = self._strips_layout.takeAt(0)
            if widget := item.widget():
                widget.setParent(None)
                widget.deleteLater()

    # --- Add/Remove Strip Logic ---
    def _add_strip(self, floor_idx: int):
        strip = FacadeStrip(floor_idx)
        strip.header.remove_requested.connect(self._remove_strip)
        self._strips_layout.insertWidget(0, strip)

    def _add_strip_at_top(self):
        new_floor_idx = self._strips_layout.count()
        self._add_strip(floor_idx=new_floor_idx)
        self._re_index_floors()

    @Slot(FacadeStrip)
    def _remove_strip(self, strip_to_remove: FacadeStrip):
        self._strips_layout.removeWidget(strip_to_remove)
        strip_to_remove.deleteLater()
        self._re_index_floors()

    def _re_index_floors(self):
        num_floors = self._strips_layout.count()
        for i in range(num_floors):
            strip: FacadeStrip = self._strips_layout.itemAt(i).widget()
            if not strip: continue

            new_floor_idx = num_floors - 1 - i
            strip.floor_index = new_floor_idx
            strip.header.update_label(new_floor_idx)