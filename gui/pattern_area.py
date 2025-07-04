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
            strip.structureChanged.connect(self._regenerate_and_emit_pattern)

            for grp_data in floor_data:
                ui_group = GroupWidget(kind=_to_ui_kind(grp_data.kind))
                ui_group.repeat = grp_data.repeat
                ui_group.structureChanged.connect(strip.structureChanged.emit)

                strip.module_container_layout.addWidget(ui_group)

                sequence: Iterable[Module] = (
                    grp_data.modules * (grp_data.repeat or 1)
                    if grp_data.kind is CoreKind.RIGID else grp_data.modules
                )

                for mod_object in sequence:
                    mod_widget =ModuleWidget(mod_object.name, False)
                    mod_widget.structureChanged.connect(ui_group.structureChanged.emit)
                    ui_group.layout().addWidget(mod_widget)

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
        strip.structureChanged.connect(self._regenerate_and_emit_pattern)
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
        self._regenerate_and_emit_pattern() # <<< REGENERATE after remove

    def _re_index_floors(self):
        num_floors = self._strips_layout.count()
        for i in range(num_floors):
            strip: FacadeStrip = self._strips_layout.itemAt(i).widget()
            if not strip: continue

            new_floor_idx = num_floors - 1 - i
            strip.floor_index = new_floor_idx
            strip.header.update_label(new_floor_idx)
        self._regenerate_and_emit_pattern()

    def _regenerate_and_emit_pattern(self) -> None:
        """
        Reads the current visual layout of the canvas and builds the
        canonical pattern string, then emits the patternChanged signal.
        """
        print('waea')
        all_floors_text = []
        # Iterate from bottom to top of the visual layout to get logical order
        for i in range(self._strips_layout.count() - 1, -1, -1):
            strip: FacadeStrip = self._strips_layout.itemAt(i).widget()
            if not strip: continue

            floor_groups_text = []
            # Iterate through the groups in the strip
            for j in range(strip.module_container_layout.count()):
                group: GroupWidget = strip.module_container_layout.itemAt(j).widget()
                if not isinstance(group, GroupWidget): continue

                # Collect module names from within the group
                module_names = []
                for k in range(group.layout().count()):
                    module: ModuleWidget = group.layout().itemAt(k).widget()
                    if isinstance(module, ModuleWidget):
                        module_names.append(module.name)

                if not module_names: continue

                # Format the group text based on its kind
                group_text = "-".join(module_names)
                if group.kind == UiKind.FILL:
                    floor_groups_text.append(f"<{group_text}>")
                else:  # RIGID
                    floor_groups_text.append(f"[{group_text}]")

            all_floors_text.append("".join(floor_groups_text))

        final_pattern = "\n".join(reversed(all_floors_text))
        self.patternChanged.emit(final_pattern)