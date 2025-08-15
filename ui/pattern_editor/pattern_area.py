from __future__ import annotations
import json

from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget, QPushButton

from domain.grammar import REPEATABLE, RIGID
from services.pattern_preprocessor import preprocess_unreal_json_data
from ui.pattern_editor.floor_row_widget import FloorRowWidget
from ui.pattern_editor.module_item import GroupWidget, ModuleWidget

class PatternArea(QWidget):
    patternChanged = Signal(str)
    columnWidthsChanged = Signal(list)

    def __init__(self, num_floors: int = 3, parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = REPEATABLE
        self._floor_rows: list[FloorRowWidget] = []

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setSpacing(8)
        self._root_layout.setAlignment(Qt.AlignTop)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(5)
        self._rows_layout.setAlignment(Qt.AlignTop)
        self._root_layout.addLayout(self._rows_layout)

        self.add_floor_button = QPushButton("➕ Add Floor")
        self.add_floor_button.clicked.connect(self._add_row_at_top)
        self.add_floor_button.setFixedWidth(200)
        self._root_layout.addWidget(self.add_floor_button, 0, Qt.AlignHCenter)
        self._root_layout.addStretch(1)

        for _ in range(num_floors):
            self._add_row_at_top()

    def set_mode(self, new_mode: str):
        if new_mode == self.mode or new_mode not in (REPEATABLE, RIGID): return
        self.mode = new_mode
        current_data_str = self.get_data_as_json()
        self.load_from_json(current_data_str)

    def get_data_as_json(self, indent: int = 4) -> str:
        building_data = [row.get_floor_data() for row in self._floor_rows]
        building_data.reverse()
        return json.dumps(building_data, indent=indent)

    def load_from_json(self, json_str: str) -> None:
        try:
            raw_data = json.loads(json_str)
            building_data = preprocess_unreal_json_data(raw_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing or processing JSON: {e}")
            return
        self._clear_view()
        for floor_data in reversed(building_data):
            new_row = self._create_row(len(self._floor_rows))
            new_row.set_floor_data(floor_data)
            self._rows_layout.addWidget(new_row)
            self._floor_rows.append(new_row)
        self._re_index_floors()

    def _create_row(self, floor_idx: int) -> FloorRowWidget:
        row = FloorRowWidget(floor_idx, mode=self.mode)
        row.remove_requested.connect(self._remove_row)
        row.move_up_requested.connect(self._move_row_up)
        row.move_down_requested.connect(self._move_row_down)
        row.structureChanged.connect(self._schedule_update)
        return row

    def _clear_view(self):
        self._floor_rows.clear()
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if widget := item.widget():
                widget.setParent(None); widget.deleteLater()

    @Slot()
    def _add_row_at_top(self):
        new_row = self._create_row(0) # Temp index
        self._rows_layout.insertWidget(0, new_row)
        self._floor_rows.insert(0, new_row)
        self._re_index_floors()

    @Slot(FloorRowWidget)
    def _remove_row(self, row_to_remove: FloorRowWidget):
        if row_to_remove in self._floor_rows:
            self._floor_rows.remove(row_to_remove)
            self._rows_layout.removeWidget(row_to_remove)
            row_to_remove.deleteLater()
            self._re_index_floors()

    @Slot(FloorRowWidget)
    def _move_row_up(self, row_to_move: FloorRowWidget):
        index = self._rows_layout.indexOf(row_to_move)
        if index > 0:
            self._rows_layout.removeWidget(row_to_move)
            self._rows_layout.insertWidget(index - 1, row_to_move)
            self._floor_rows.insert(index - 1, self._floor_rows.pop(index))
            self._re_index_floors()

    @Slot(FloorRowWidget)
    def _move_row_down(self, row_to_move: FloorRowWidget):
        index = self._rows_layout.indexOf(row_to_move)
        if index < self._rows_layout.count() - 1:
            self._rows_layout.removeWidget(row_to_move)
            self._rows_layout.insertWidget(index + 1, row_to_move)
            self._floor_rows.insert(index + 1, self._floor_rows.pop(index))
            self._re_index_floors()

    def _re_index_floors(self):
        """
        Updates the internal floor_index for all rows and schedules an update.
        Crucially, it DOES NOT change the visible text names.
        """
        num_floors = len(self._floor_rows)
        for i, row in enumerate(self._floor_rows):
            new_floor_idx = num_floors - 1 - i
            row.floor_index = new_floor_idx
        self._schedule_update()

    @Slot()
    def _schedule_update(self):
        """Schedules the update to run after the event loop has settled."""
        QTimer.singleShot(0, self._perform_update_and_regenerate)

    def _perform_update_and_regenerate(self):
        """The actual deferred update logic."""
        self._update_column_widths()
        self.patternChanged.emit(self.get_data_as_json())

    def _update_column_widths(self):
        """Manually synchronize column widths across all rows."""
        if not self._floor_rows: return
        max_widths = [0, 0, 0, 0]
        for row in self._floor_rows:
            for i, cell in enumerate(row.facade_cells):
                ideal_width = cell.module_container_layout.sizeHint().width()
                margins = cell.contentsMargins()
                total_ideal = ideal_width + margins.left() + margins.right()
                max_widths[i] = max(max_widths[i], total_ideal)
        for row in self._floor_rows:
            for i, cell in enumerate(row.facade_cells):
                cell.setFixedWidth(max_widths[i])
        header_width = self._floor_rows[0].header.width() if self._floor_rows else 150
        final_widths = [header_width] + max_widths
        self.columnWidthsChanged.emit(final_widths)

    def redraw(self):
        """Refreshes all module icons."""
        for row in self._floor_rows:
            for cell in row.facade_cells:
                for j in range(cell.module_container_layout.count()):
                    group = cell.module_container_layout.itemAt(j).widget()
                    if not isinstance(group, GroupWidget): continue
                    for k in range(group.layout().count()):
                        module = group.layout().itemAt(k).widget()
                        if isinstance(module, ModuleWidget):
                            module.refresh_icon()
        self._schedule_update()