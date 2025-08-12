from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget, QPushButton

from domain.grammar import parse, GroupKind, REPEATABLE, RIGID
from ui.pattern_editor.facade_strip import FacadeStrip
from ui.pattern_editor.module_item import GroupWidget, ModuleWidget, GroupKind as UiKind



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
        self.mode = REPEATABLE    # Default mode
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
        if new_mode == self.mode or new_mode not in (REPEATABLE, RIGID):
            return

        # 1. Unload the currently visible strips into their corresponding cache list.
        # This involves removing them from the layout and hiding them.
        current_strips_cache = self._structured_strips if self.mode == REPEATABLE else self._sandbox_strips
        current_strips_cache.clear()
        while self._strips_layout.count():
            item = self._strips_layout.takeAt(0)
            if strip := item.widget():
                strip.hide()
                current_strips_cache.append(strip)

        # 2. Update the mode.
        self.mode = new_mode

        # 3. Load the strips for the new mode from its cache list.
        target_cache  = self._structured_strips if self.mode == REPEATABLE else self._sandbox_strips

        # If the target mode's cache is empty, create a default set of strips.
        if not target_cache :
            for _ in range(3):  # Default to 3 new floors
                self._add_strip(self.mode)
        else:
            # If strips already exist, add them back to the layout and show them.
            for strip in target_cache :
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

            floor_groups_text: list[str] = []
            sandbox_module_names: list[str] = []

            for j in range(strip.module_container_layout.count()):
                group = strip.module_container_layout.itemAt(j).widget()
                if not isinstance(group, GroupWidget):
                    continue

                module_names  = [
                    mod.name for k in range(group.layout().count())
                    if isinstance(mod := group.layout().itemAt(k).widget(), ModuleWidget)
                ]

                if not module_names :
                    continue

                if self.mode == REPEATABLE:
                    group_text = "-".join(module_names )
                    wrapper = "<{}>" if group.kind == GroupKind.FILL else "[{}]"
                    floor_groups_text.append(wrapper.format(group_text))
                else:  # Sandbox mode collects all modules into one list.
                    sandbox_module_names.extend(module_names )

            if self.mode == RIGID:
                all_floors_text.append(f"[{'-'.join(sandbox_module_names)}]" if sandbox_module_names else "[]")
            else:
                all_floors_text.append("".join(floor_groups_text))

        return "\n".join(all_floors_text)

    def load_from_string(self, pattern_str: str, *, library: "ModuleLibrary") -> None:
        """Clears the view and builds a new layout from a pattern string."""
        try:
            model = parse(pattern_str)
        except Exception as e:
            print(f"Error parsing pattern string: {e}")
            return

        self._clear_view()
        # Get the correct list to populate, which is now empty.
        target_list = self._structured_strips if self.mode == REPEATABLE else self._sandbox_strips

        # Build the UI from the parsed model, in reverse order for correct display.
        for floor_idx, floor_data in reversed(list(enumerate(model.floors))):
            strip = self._create_strip(floor_idx, self.mode)


            for grp_data in floor_data:
                ui_group = GroupWidget(kind=grp_data.kind)  # domain enum directly
                ui_group.repeat = grp_data.repeat
                ui_group.structureChanged.connect(strip.structureChanged.emit)
                strip.module_container_layout.addWidget(ui_group)

                for mod_object in grp_data.modules:
                    mod_widget = ModuleWidget(mod_object.name, False)
                    mod_widget.structureChanged.connect(ui_group.structureChanged.emit)
                    ui_group.layout().addWidget(mod_widget)

            self._strips_layout.addWidget(strip)
            target_list.append(strip)

        self.patternChanged.emit(self.get_pattern_string())


    def _create_strip(self, floor_idx: int, mode: str) -> FacadeStrip:
        strip = FacadeStrip(floor_idx, mode=mode)
        # header signals
        strip.header.remove_requested.connect(self._remove_strip)
        strip.header.move_up_requested.connect(self._move_strip_up)
        strip.header.move_down_requested.connect(self._move_strip_down)
        # structure changes
        strip.structureChanged.connect(self._regenerate_and_emit_pattern)
        return strip


    def _clear_view(self):
        """Safely removes all strips from the current view and clears the cache."""
        # Clear the python list that holds the strip references for the active mode.
        target_list = self._structured_strips if self.mode == REPEATABLE  else self._sandbox_strips
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
        target_list = self._structured_strips if mode_to_add_to == REPEATABLE  else self._sandbox_strips
        new_floor_idx = len(target_list)

        strip = self._create_strip(new_floor_idx, mode_to_add_to)

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
        target_list = self._structured_strips if self.mode == REPEATABLE else self._sandbox_strips
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
        self.patternChanged.emit(self.get_pattern_string())


    def redraw(self) -> None:
        """
        Forces a full redraw of all module widgets and regenerates the
        output pattern string.

        This is useful when external factors, like a change in the icon set,
        require the canvas to update its appearance without changing its
        underlying structure.
        """
        all_strips = self._structured_strips + self._sandbox_strips

        # 1. Iterate through every strip that exists, visible or not.
        for strip in all_strips:
            if not isinstance(strip, FacadeStrip): continue

            for j in range(strip.module_container_layout.count()):
                if isinstance(group := strip.module_container_layout.itemAt(j).widget(), GroupWidget):
                    for k in range(group.layout().count()):
                        if isinstance(module := group.layout().itemAt(k).widget(), ModuleWidget):
                            # Call the refresh method on every single module widget.
                            module.refresh_icon()

        # 2. After all icons are updated, regenerate the pattern for the active view.
        self._regenerate_and_emit_pattern()