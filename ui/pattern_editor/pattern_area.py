from __future__ import annotations
import json

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget, QPushButton

from domain.grammar import REPEATABLE, RIGID
from services.pattern_preprocessor import preprocess_unreal_json_data

# --- NEW: Import our new composite widget ---
from ui.pattern_editor.floor_row_widget import FloorRowWidget
from ui.pattern_editor.module_item import GroupWidget, ModuleWidget

class PatternArea(QWidget):
    """
    The main canvas for designing a building. It manages a vertical list of
    FloorRowWidgets and handles the top-level serialization to and from the
    JSON data format.
    """
    patternChanged = Signal(str)  # This signal will now emit the full JSON string

    def __init__(self, num_floors: int = 3, parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = REPEATABLE
        self.setAcceptDrops(True)  # Note: drag/drop between floors might be a future feature

        # --- Internal State ---
        # NOTE: The caching logic is simplified. We only need one list for the
        # currently visible floor row widgets.
        self._floor_rows: list[FloorRowWidget] = []

        # --- Layouts ---
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setSpacing(8)
        self._root_layout.setAlignment(Qt.AlignTop)

        # This layout will hold the FloorRowWidgets
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(8)  # A bit more spacing between full rows
        self._rows_layout.setAlignment(Qt.AlignTop)
        self._root_layout.addLayout(self._rows_layout)

        self.add_floor_button = QPushButton("➕ Add Floor")
        self.add_floor_button.clicked.connect(self._add_row_at_top)
        self.add_floor_button.setFixedWidth(200)
        self._root_layout.addWidget(self.add_floor_button, 0, Qt.AlignHCenter)
        self._root_layout.addStretch(1)

        for _ in range(num_floors):
            self._add_row_at_top()

    def redraw(self) -> None:
        """
        Forces a full redraw of all module widgets.

        This iterates through the new component structure to find and refresh
        every ModuleWidget instance.
        """
        # 1. Iterate through every floor row.
        for row in self._floor_rows:
            # 2. Iterate through the four facade cells in that row.
            for cell in row.facade_cells:
                # 3. Iterate through the groups in that cell.
                for j in range(cell.module_container_layout.count()):
                    group = cell.module_container_layout.itemAt(j).widget()
                    if not isinstance(group, GroupWidget): continue
                    # 4. Finally, iterate through the modules in that group.
                    for k in range(group.layout().count()):
                        module = group.layout().itemAt(k).widget()
                        if isinstance(module, ModuleWidget):
                            # Tell the module to refresh its icon
                            module.refresh_icon()

        # After all icons are updated, regenerate the pattern.
        self._regenerate_and_emit_pattern()

    def set_mode(self, new_mode: str):
        """
        Switches the canvas between 'Repeatable' and 'Rigid' modes.
        This now involves telling each existing FloorRowWidget to update its cells.
        """
        if new_mode == self.mode or new_mode not in (REPEATABLE, RIGID):
            return

        self.mode = new_mode
        # The mode is now a property of the cells within each row.
        # We need to recreate the rows to apply the new mode correctly.
        # A simpler approach than full caching is to get the current data and reload it.
        current_data_str = self.get_data_as_json()
        self.load_from_json(current_data_str)

    def get_data_as_json(self, indent: int = 4) -> str:
        """
        Generates the building JSON string by querying each FloorRowWidget for its data.
        """
        building_data = []
        # The list of floor rows is kept in visual order (top-to-bottom).
        # We iterate through it and get the data for each floor.
        for row in self._floor_rows:
            building_data.append(row.get_floor_data())

        # The Unreal format expects ground floor (our last visual row) to be first
        # in the JSON array. So, we reverse the list before dumping.
        building_data.reverse()

        return json.dumps(building_data, indent=indent)

    def load_from_json(self, json_str: str) -> None:
        """
        Clears the view and builds a new layout from a building JSON string.
        """
        try:
            raw_data = json.loads(json_str)
            # --- NEW: Use our pre-processor service to ensure data is clean ---
            building_data = preprocess_unreal_json_data(raw_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing or processing JSON: {e}")
            return

        self._clear_view()

        # The JSON data has ground floor first, but we build our UI from top to bottom.
        # So we iterate through the data in reverse.
        for floor_data in reversed(building_data):
            new_row = self._create_row(len(self._floor_rows))
            new_row.set_floor_data(floor_data)

            self._rows_layout.addWidget(new_row)
            self._floor_rows.append(new_row)

        self._re_index_floors()

    def _create_row(self, floor_idx: int) -> FloorRowWidget:
        """Helper to create a new FloorRowWidget and connect its signals."""
        row = FloorRowWidget(floor_idx, mode=self.mode)
        row.remove_requested.connect(self._remove_row)
        row.move_up_requested.connect(self._move_row_up)
        row.move_down_requested.connect(self._move_row_down)
        row.structureChanged.connect(self._regenerate_and_emit_pattern)
        return row

    def _clear_view(self):
        """Safely removes all floor row widgets from the view and internal list."""
        self._floor_rows.clear()
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if widget := item.widget():
                widget.setParent(None)
                widget.deleteLater()

    def _add_row_at_top(self):
        """Slot for the 'Add Floor' button. Adds a new row to the top of the UI."""
        # A new row is inserted at visual index 0.
        new_row = self._create_row(0)  # Temp index, will be fixed by re-indexing
        self._rows_layout.insertWidget(0, new_row)
        self._floor_rows.insert(0, new_row)  # Add to the start of the list
        self._re_index_floors()

    @Slot(FloorRowWidget)
    def _remove_row(self, row_to_remove: FloorRowWidget):
        """Removes a specific floor row from the list and the layout."""
        if row_to_remove in self._floor_rows:
            self._floor_rows.remove(row_to_remove)

        self._rows_layout.removeWidget(row_to_remove)
        row_to_remove.deleteLater()
        self._re_index_floors()

    @Slot(FloorRowWidget)
    def _move_row_up(self, row_to_move: FloorRowWidget):
        """Moves a given row up by one position in the layout and internal list."""
        index = self._floor_rows.index(row_to_move)
        if index > 0:
            # Reorder in the list first
            self._floor_rows.insert(index - 1, self._floor_rows.pop(index))
            # Then update the UI to match
            self._rows_layout.removeWidget(row_to_move)
            self._rows_layout.insertWidget(index - 1, row_to_move)
            self._re_index_floors()

    @Slot(FloorRowWidget)
    def _move_row_down(self, row_to_move: FloorRowWidget):
        """Moves a given row down by one position in the layout and internal list."""
        index = self._floor_rows.index(row_to_move)
        if index < len(self._floor_rows) - 1:
            # Reorder in the list first
            self._floor_rows.insert(index + 1, self._floor_rows.pop(index))
            # Then update the UI to match
            self._rows_layout.removeWidget(row_to_move)
            self._rows_layout.insertWidget(index + 1, row_to_move)
            self._re_index_floors()

    def _re_index_floors(self):
        """
        Updates the floor index and label for all visible rows.
        The index is calculated top-to-bottom (0 = Ground Floor at the bottom).
        """
        num_floors = len(self._floor_rows)
        for i, row in enumerate(self._floor_rows):
            # The row at visual index `i` (from top) corresponds to floor `num_floors - 1 - i`.
            new_floor_idx = num_floors - 1 - i
            row.floor_index = new_floor_idx
            row.header.update_floor_label(new_floor_idx)

        self._regenerate_and_emit_pattern()
        self._update_column_widths()  # NEW: Call the adaptive width logic

    def _regenerate_and_emit_pattern(self):
        """Helper to generate the JSON string from the UI and emit the changed signal."""
        self.patternChanged.emit(self.get_data_as_json())

    def _update_column_widths(self):
        """
        Implements the adaptive column width logic...
        """
        if not self._floor_rows:
            return

        max_widths = [0, 0, 0, 0]
        for row in self._floor_rows:
            for i, cell in enumerate(row.facade_cells):
                layout = cell.module_container_layout
                margins = cell.contentsMargins()

                content_width = 0
                if layout.count() > 0:
                    content_width = layout.sizeHint().width()

                ideal_width = content_width + margins.left() + margins.right()
                max_widths[i] = max(max_widths[i], ideal_width)

        # Apply the maximum widths to all cells in each column.
        for row in self._floor_rows:
            for i, cell in enumerate(row.facade_cells):
                # --- THIS IS THE FIX ---
                cell.setFixedWidth(max_widths[i])

        # Apply the maximum widths to all cells in each column.
        # We use setMinimumWidth to ensure they don't get smaller.
        for row in self._floor_rows:
            for i, cell in enumerate(row.facade_cells):
                cell.setMinimumWidth(max_widths[i])

    # Note: The `redraw` method from the original file may need to be adapted
    # if you still need it, by iterating through the new structure.