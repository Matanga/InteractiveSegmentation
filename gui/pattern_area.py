from __future__ import annotations
from typing import Iterable

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget, QPushButton

from building_grammar.core import parse, GroupKind as CoreKind, Module
from facade_strip import FacadeStrip
from module_item import GroupWidget, ModuleWidget, GroupKind as UiKind


def _to_ui_kind(kind: CoreKind) -> UiKind:
    """Converts a core grammar GroupKind to its UI equivalent."""
    return UiKind.FILL if kind is CoreKind.FILL else UiKind.RIGID


class PatternArea(QWidget):
    """
    The main canvas for designing a building facade. It manages multiple
    FacadeStrips (floors) and can switch between two editing modes:
    - 'structured': Floors can contain multiple rigid or fill groups.
    - 'sandbox': Each floor is a single, simple strip of modules.
    """
    patternChanged = Signal(str)

    def __init__(self, num_floors: int = 3, parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = "structured"  # Default mode
        self.setAcceptDrops(True)

        # --- Internal State ---
        # Two separate lists to hold the strips for each mode, acting as a cache
        # when a mode is not active.
        self._structured_strips: list[FacadeStrip] = []
        self._sandbox_strips: list[FacadeStrip] = []

        # --- Layouts ---
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

    def set_mode(self, new_mode: str):
        """
        Switches the canvas between 'structured' and 'sandbox' modes by swapping
        the visible list of FacadeStrips.
        """
        if new_mode == self.mode or new_mode not in ("structured", "sandbox"):
            return

        # 1. Unload the currently visible strips into their corresponding cache list.
        # This involves removing them from the layout and hiding them.
        current_strips_cache = self._structured_strips if self.mode == "structured" else self._sandbox_strips
        current_strips_cache.clear()
        while self._strips_layout.count():
            item = self._strips_layout.takeAt(0)
            if strip := item.widget():
                strip.hide()
                current_strips_cache.append(strip)

        # 2. Update the mode.
        self.mode = new_mode

        # 3. Load the strips for the new mode from its cache list.
        new_strips_cache = self._structured_strips if self.mode == "structured" else self._sandbox_strips

        # If the target mode's cache is empty, create a default set of strips.
        if not new_strips_cache:
            for _ in range(3):  # Default to 3 new floors
                self._add_strip(self.mode)
        else:
            # If strips already exist, add them back to the layout and show them.
            for strip in new_strips_cache:
                self._strips_layout.addWidget(strip)
                strip.show()

        self._re_index_floors()

    def get_pattern_string(self) -> str:
        """Generates the pattern string based on the current visual layout and mode."""
        all_floors_text = []
        for i in range(self._strips_layout.count()):
            strip = self._strips_layout.itemAt(i).widget()
            if not isinstance(strip, FacadeStrip):
                continue

            floor_groups_text = []
            sandbox_module_names = []

            for j in range(strip.module_container_layout.count()):
                group = strip.module_container_layout.itemAt(j).widget()
                if not isinstance(group, GroupWidget):
                    continue

                module_names_in_group = [
                    mod.name for k in range(group.layout().count())
                    if isinstance(mod := group.layout().itemAt(k).widget(), ModuleWidget)
                ]

                if not module_names_in_group:
                    continue

                if self.mode == "structured":
                    group_text = "-".join(module_names_in_group)
                    wrapper = "<{}>" if group.kind == UiKind.FILL else "[{}]"
                    floor_groups_text.append(wrapper.format(group_text))
                else:  # Sandbox mode collects all modules into one list.
                    sandbox_module_names.extend(module_names_in_group)

            if self.mode == "sandbox":
                all_floors_text.append(f"[{'-'.join(sandbox_module_names)}]" if sandbox_module_names else "[]")
            else:
                all_floors_text.append("".join(floor_groups_text))

        return "\n".join(reversed(all_floors_text))

    def load_from_string(self, pattern_str: str, *, library: "ModuleLibrary") -> None:
        """Clears the view and builds a new layout from a pattern string."""
        try:
            model = parse(pattern_str)
        except Exception as e:
            print(f"Error parsing pattern string: {e}")
            return

        self._clear_view()

        # Build the UI from the parsed model, in reverse order for correct display.
        for floor_idx, floor_data in reversed(list(enumerate(model.floors))):
            strip = FacadeStrip(floor_idx, mode=self.mode)
            strip.header.remove_requested.connect(self._remove_strip)
            strip.header.move_up_requested.connect(self._move_strip_up)
            strip.header.move_down_requested.connect(self._move_strip_down)
            strip.structureChanged.connect(self._regenerate_and_emit_pattern)

            for grp_data in floor_data:
                ui_group = GroupWidget(kind=_to_ui_kind(grp_data.kind))
                ui_group.repeat = grp_data.repeat
                ui_group.structureChanged.connect(strip.structureChanged.emit)
                strip.module_container_layout.addWidget(ui_group)
                for mod_object in grp_data.modules:
                    mod_widget = ModuleWidget(mod_object.name, False)
                    mod_widget.structureChanged.connect(ui_group.structureChanged.emit)
                    ui_group.layout().addWidget(mod_widget)
            self._strips_layout.addWidget(strip)

        self.patternChanged.emit(self.get_pattern_string())

    def _clear_view(self):
        """Safely removes all strips from the current view and clears the cache."""
        # Clear the python list that holds the strip references for the active mode.
        target_list = self._structured_strips if self.mode == "structured" else self._sandbox_strips
        target_list.clear()

        # Clear the UI layout, deleting each widget.
        while self._strips_layout.count():
            item = self._strips_layout.takeAt(0)
            if widget := item.widget():
                widget.setParent(None)  # Disconnect from layout
                widget.deleteLater()  # Schedule for deletion

    def _add_strip(self, mode_to_add_to: str):
        """
        Creates a strip for a specific mode, adds it to the top of the layout,
        and prepends it to the correct internal list.
        """
        target_list = self._structured_strips if mode_to_add_to == "structured" else self._sandbox_strips
        new_floor_idx = len(target_list)

        strip = FacadeStrip(new_floor_idx, mode=mode_to_add_to)

        # Connect all signals from the strip's header.
        strip.header.remove_requested.connect(self._remove_strip)
        strip.header.move_up_requested.connect(self._move_strip_up)
        strip.header.move_down_requested.connect(self._move_strip_down)
        strip.structureChanged.connect(self._regenerate_and_emit_pattern)

        # insertWidget(0,...) adds to the top of the UI.
        self._strips_layout.insertWidget(0, strip)
        target_list.insert(0, strip)

    def _add_strip_at_top(self):
        """Slot for the 'Add Floor' button. Adds a strip to the currently active mode."""
        self._add_strip(self.mode)
        self._re_index_floors()

    @Slot(FacadeStrip)
    def _remove_strip(self, strip_to_remove: FacadeStrip):
        """Removes a specific strip from the active list and the layout."""
        target_list = self._structured_strips if self.mode == "structured" else self._sandbox_strips
        if strip_to_remove in target_list:
            target_list.remove(strip_to_remove)

        self._strips_layout.removeWidget(strip_to_remove)
        strip_to_remove.deleteLater()
        self._re_index_floors()

    @Slot(FacadeStrip)
    def _move_strip_up(self, strip_to_move: FacadeStrip):
        """Moves a given strip up by one position in the layout."""
        # Find the current visual index of the strip.
        index = self._strips_layout.indexOf(strip_to_move)
        # Cannot move up if it's already at the top (index 0).
        if index > 0:
            # Remove the strip from its current position.
            self._strips_layout.removeWidget(strip_to_move)
            # Re-insert it one position higher (index - 1).
            self._strips_layout.insertWidget(index - 1, strip_to_move)
            # Update all floor names and regenerate the pattern string.
            self._re_index_floors()

    @Slot(FacadeStrip)
    def _move_strip_down(self, strip_to_move: FacadeStrip):
        """Moves a given strip down by one position in the layout."""
        # Find the current visual index of the strip.
        index = self._strips_layout.indexOf(strip_to_move)
        # Cannot move down if it's already at the bottom.
        if index < self._strips_layout.count() - 1:
            # Remove the strip from its current position.
            self._strips_layout.removeWidget(strip_to_move)
            # Re-insert it one position lower (index + 1).
            self._strips_layout.insertWidget(index + 1, strip_to_move)
            # Update all floor names and regenerate the pattern string.
            self._re_index_floors()

    def _re_index_floors(self):
        """
        Updates the floor index and label for all visible strips.
        The index is calculated top-to-bottom (0 = Ground Floor at the bottom).
        """
        num_floors = self._strips_layout.count()
        for i in range(num_floors):
            strip: FacadeStrip = self._strips_layout.itemAt(i).widget()
            if not strip:
                continue
            # The visual item at index `i` (from top) corresponds to floor `num_floors - 1 - i`.
            new_floor_idx = num_floors - 1 - i
            strip.floor_index = new_floor_idx
            strip.header.update_label(new_floor_idx)
        self._regenerate_and_emit_pattern()

    def _regenerate_and_emit_pattern(self):
        """Helper to generate the pattern string from the UI and emit the changed signal."""
        pattern = self.get_pattern_string()
        self.patternChanged.emit(pattern)