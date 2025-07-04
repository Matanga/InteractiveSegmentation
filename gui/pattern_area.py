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

    def __init__(self, num_floors: int = 3, parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = "structured"  # Default mode
        self.setAcceptDrops(True)

        # --- Internal State ---
        #  two separate lists to hold the strips for each mode.
        self._structured_strips: list[FacadeStrip] = []
        self._sandbox_strips: list[FacadeStrip] = []

        # --- Layouts ---
        self._root_layout = QVBoxLayout(self);
        self._root_layout.setSpacing(8);
        self._root_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._strips_layout = QVBoxLayout();
        self._strips_layout.setSpacing(4);
        self._strips_layout.setAlignment(Qt.AlignTop)
        self._root_layout.addLayout(self._strips_layout)
        self.add_floor_button = QPushButton("➕ Add Floor");
        self.add_floor_button.clicked.connect(self._add_strip_at_top);
        self.add_floor_button.setFixedWidth(200)
        self._root_layout.addWidget(self.add_floor_button, 0, Qt.AlignHCenter);
        self._root_layout.addStretch(1)
        for _ in range(num_floors): self._add_strip_at_top()
    # --- Load/Clear Logic ---

    def set_mode(self, new_mode: str):
        """
        Switches the canvas between 'structured' and 'sandbox' modes by swapping
        the visible list of FacadeStrips.
        """
        if new_mode == self.mode or new_mode not in ("structured", "sandbox"):
            return

        # 1. Save the currently visible strips into the appropriate list.
        # We also hide them and remove them from the layout.
        current_list = self._structured_strips if self.mode == "structured" else self._sandbox_strips
        current_list.clear()
        while self._strips_layout.count():
            item = self._strips_layout.takeAt(0)
            if strip := item.widget():
                strip.hide()
                current_list.append(strip)

        # 2. Set the new mode.
        self.mode = new_mode

        # 3. Load the strips for the new mode.
        new_list = self._structured_strips if self.mode == "structured" else self._sandbox_strips

        # If the target mode's list is empty, create a default set of strips.
        if not new_list:
            for _ in range(3):  # Default to 3 new floors
                self._add_strip(self.mode)
        else:
            # If strips already exist for this mode, add them back to the layout.
            for strip in new_list:
                self._strips_layout.addWidget(strip)
                strip.show()

        self._re_index_floors()
    def get_pattern_string(self) -> str:
        """Generates the pattern string based on the current visual layout and mode."""
        all_floors_text = []
        for i in range(self._strips_layout.count()):
            if not isinstance(strip := self._strips_layout.itemAt(i).widget(), FacadeStrip): continue
            module_names = []
            floor_groups_text = []
            for j in range(strip.module_container_layout.count()):
                if not isinstance(group := strip.module_container_layout.itemAt(j).widget(), GroupWidget): continue
                module_names_in_group = [mod.name for k in range(group.layout().count()) if
                                         isinstance(mod := group.layout().itemAt(k).widget(), ModuleWidget)]
                if not module_names_in_group: continue
                group_text = "-".join(module_names_in_group)
                if self.mode == "structured":
                    floor_groups_text.append(f"<{group_text}>" if group.kind == UiKind.FILL else f"[{group_text}]")
                else:  # Sandbox mode implies one big rigid group
                    module_names.extend(module_names_in_group)

            if self.mode == "sandbox":
                all_floors_text.append(f"[{'-'.join(module_names)}]" if module_names else "[]")
            else:
                all_floors_text.append("".join(floor_groups_text))

        return "\n".join(reversed(all_floors_text))

    def load_from_string(self, pattern_str: str, *, library: "ModuleLibrary") -> None:
        try:
            model = parse(pattern_str)
        except Exception as e:
            print(f"Error parsing pattern string: {e}"); return
        self._clear_view()
        for floor_idx, floor_data in reversed(list(enumerate(model.floors))):
            strip = FacadeStrip(floor_idx, mode=self.mode);
            strip.header.remove_requested.connect(self._remove_strip);
            strip.structureChanged.connect(self._regenerate_and_emit_pattern)
            for grp_data in floor_data:
                ui_group = GroupWidget(kind=_to_ui_kind(grp_data.kind));
                ui_group.repeat = grp_data.repeat;
                ui_group.structureChanged.connect(strip.structureChanged.emit)
                strip.module_container_layout.addWidget(ui_group)
                for mod_object in grp_data.modules:
                    mod_widget = ModuleWidget(mod_object.name, False);
                    mod_widget.structureChanged.connect(ui_group.structureChanged.emit);
                    ui_group.layout().addWidget(mod_widget)
            self._strips_layout.addWidget(strip)
        self.patternChanged.emit(self.get_pattern_string())

    def _add_strip(self, mode_to_add_to: str):
        """Creates a strip for a specific mode and adds it to the layout and the correct list."""
        target_list = self._structured_strips if mode_to_add_to == "structured" else self._sandbox_strips
        new_floor_idx = len(target_list)

        strip = FacadeStrip(new_floor_idx, mode=mode_to_add_to)
        strip.header.remove_requested.connect(self._remove_strip)
        strip.structureChanged.connect(self._regenerate_and_emit_pattern)

        # Add to the visual layout and the internal list
        self._strips_layout.insertWidget(0, strip)
        target_list.insert(0, strip)  # Prepend to list as well

    def _clear_view(self):
        """Clears the currently active view."""
        target_list = self._structured_strips if self.mode == "structured" else self._sandbox_strips
        for strip in target_list:
            strip.deleteLater()
        target_list.clear()

        # Also clear the layout
        while self._strips_layout.count():
            item = self._strips_layout.takeAt(0)
            if widget := item.widget():
                widget.setParent(None)
                widget.deleteLater()

    def _add_strip_at_top(self):
        """Slot for the 'Add Floor' button. Adds to the currently active mode."""
        self._add_strip(self.mode)
        self._re_index_floors()

    @Slot(FacadeStrip)
    def _remove_strip(self, strip_to_remove: FacadeStrip):
        """Removes a strip from the active list and the layout."""
        target_list = self._structured_strips if self.mode == "structured" else self._sandbox_strips
        if strip_to_remove in target_list:
            target_list.remove(strip_to_remove)

        self._strips_layout.removeWidget(strip_to_remove)
        strip_to_remove.deleteLater()
        self._re_index_floors()

    def _re_index_floors(self):
        num_floors = self._strips_layout.count()
        for i in range(num_floors):
            if strip := self._strips_layout.itemAt(i).widget():
                new_floor_idx = num_floors - 1 - i; strip.floor_index = new_floor_idx; strip.header.update_label(new_floor_idx)
        self._regenerate_and_emit_pattern()
    def _re_index_floors(self):
        num_floors = self._strips_layout.count()
        for i in range(num_floors):
            strip: FacadeStrip = self._strips_layout.itemAt(i).widget()
            if not strip: continue

            new_floor_idx = num_floors - 1 - i
            strip.floor_index = new_floor_idx
            strip.header.update_label(new_floor_idx)
        self._regenerate_and_emit_pattern()

    def _regenerate_and_emit_pattern(self):
        """Helper to generate and emit the pattern string."""
        pattern = self.get_pattern_string()
        self.patternChanged.emit(pattern)

class SandboxPatternArea(QWidget):
    """A multi-floor canvas for the sandbox, where each floor is one rigid group."""
    def __init__(self, num_floors: int = 3, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        for _ in range(num_floors): self.add_floor()

    def get_pattern_string(self) -> str:
        """Reads the layout and generates a multi-line rigid-pattern string."""
        all_floors_text = []
        for i in range(self._layout.count()):
            if isinstance(strip := self._layout.itemAt(i).widget(), FacadeStrip):
                module_names = []
                if strip.module_container_layout.count() > 0:
                    if isinstance(group := strip.module_container_layout.itemAt(0).widget(), GroupWidget):
                        for k in range(group.layout().count()):
                            if isinstance(module := group.layout().itemAt(k).widget(), ModuleWidget):
                                module_names.append(module.name)
                all_floors_text.append(f"[{'-'.join(module_names)}]")
        return "\n".join(reversed(all_floors_text))

    def add_floor(self):
        """Adds a new strip in 'sandbox' mode."""
        new_floor_idx = self._layout.count()
        strip = FacadeStrip(new_floor_idx, mode="sandbox")
        # In sandbox, floor header/remove button is hidden, so no signal connection needed.
        self._layout.insertWidget(0, strip)

    def clear_view(self):
        while self._layout.count():
            if item := self._layout.takeAt(0):
                if widget := item.widget():
                    widget.setParent(None); widget.deleteLater()