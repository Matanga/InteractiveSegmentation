from __future__ import annotations
from typing import Dict, Any, List

from PySide6.QtWidgets import QWidget, QHBoxLayout, QFrame
from PySide6.QtCore import Signal, QObject

from domain.grammar import REPEATABLE, Group
from domain.grammar import parse_facade_string
from ui.pattern_editor.floor_header_widget import FloorHeaderWidget
from ui.pattern_editor.facade_cell_widget import FacadeCellWidget
from ui.pattern_editor.module_item import GroupWidget, ModuleWidget


# ===================================================================
# FloorRowWidget: The main container for a single floor
# ===================================================================

class FloorRowWidget(QWidget):
    """
    Represents a full row in the pattern editor, corresponding to one floor.

    This widget composes a FloorHeaderWidget (for metadata and controls) and
    four FacadeCellWidgets (for the front, left, back, and right facades).
    It acts as a bridge between the high-level PatternArea and the individual
    editing cells.
    """
    # Re-emit signals from the header for the PatternArea to catch
    remove_requested = Signal(object)  # pass self
    move_up_requested = Signal(object)  # pass self
    move_down_requested = Signal(object)  # pass self

    # This signal is crucial for notifying PatternArea to regenerate the JSON
    structureChanged = Signal()

    def __init__(self, floor_idx: int, mode: str = REPEATABLE, parent: QWidget | None = None):
        super().__init__(parent)
        self.floor_index = floor_idx
        self.mode = mode

        # --- Create Child Widgets ---
        self.header = FloorHeaderWidget()
        self.cell_front = FacadeCellWidget(mode=self.mode)
        self.cell_left = FacadeCellWidget(mode=self.mode)
        self.cell_back = FacadeCellWidget(mode=self.mode)
        self.cell_right = FacadeCellWidget(mode=self.mode)
        self.facade_cells = [
            self.cell_front, self.cell_left, self.cell_back, self.cell_right
        ]

        # --- Layout with Separators ---
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(5)
        root_layout.addWidget(self.header)

        def create_separator() -> QFrame:
            line = QFrame()
            line.setFrameShape(QFrame.Shape.VLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            line.setStyleSheet("QFrame { background-color: #2a2a2a; }")
            return line

        root_layout.addWidget(self.cell_front)
        root_layout.addWidget(create_separator())
        root_layout.addWidget(self.cell_left)
        root_layout.addWidget(create_separator())
        root_layout.addWidget(self.cell_back)
        root_layout.addWidget(create_separator())
        root_layout.addWidget(self.cell_right)
        root_layout.addStretch(1)

        # --- Signal Connections ---
        self.header.remove_requested.connect(lambda: self.remove_requested.emit(self))
        self.header.move_up_requested.connect(lambda: self.move_up_requested.emit(self))
        self.header.move_down_requested.connect(lambda: self.move_down_requested.emit(self))
        for cell in self.facade_cells:
            cell.structureChanged.connect(self.structureChanged)
        self.header.name_edit.textChanged.connect(self.structureChanged)
        self.header.height_edit.textChanged.connect(self.structureChanged)

        self.header.update_floor_label(self.floor_index)





    def get_floor_data(self) -> Dict[str, Any]:
        """
        Gathers data from the header and all four facade cells and returns it
        as a single dictionary, matching the JSON object format for a floor.
        """
        pattern_array = []
        for cell in self.facade_cells:
            floor_groups_text: list[str] = []
            sandbox_module_names: list[str] = []

            for j in range(cell.module_container_layout.count()):
                group = cell.module_container_layout.itemAt(j).widget()
                if not isinstance(group, GroupWidget): continue

                module_names = [
                    mod.name for k in range(group.layout().count())
                    if isinstance(mod := group.layout().itemAt(k).widget(), ModuleWidget)
                ]
                if not module_names: continue

                if self.mode == REPEATABLE:
                    group_text = "-".join(module_names)
                    wrapper = "<{}>" if group.kind.value == "fill" else "[{}]"
                    floor_groups_text.append(wrapper.format(group_text))
                else:
                    sandbox_module_names.extend(module_names)

            if self.mode == REPEATABLE:
                pattern_array.append("".join(floor_groups_text))
            else:
                pattern_array.append(f"[{'-'.join(sandbox_module_names)}]" if sandbox_module_names else "[]")

        floor_data = {
            "Name": self.header.name_edit.text(),
            "Pattern": pattern_array,
            "Height": int(self.header.height_edit.text() or 0)
        }
        return floor_data

    def set_floor_data(self, floor_data: Dict[str, Any]) -> None:
        """
        Configures the header and facade cells based on a dictionary of floor data.
        """
        self.header.name_edit.setText(floor_data.get("Name", ""))
        self.header.height_edit.setText(str(floor_data.get("Height", 400)))
        pattern_array = floor_data.get("Pattern", [])

        for i, cell in enumerate(self.facade_cells):
            facade_str = pattern_array[i] if i < len(pattern_array) else ""
            self._populate_cell_from_string(cell, facade_str)

    def _populate_cell_from_string(self, cell: FacadeCellWidget, facade_str: str) -> None:
        """Helper to build the UI for a single cell from a pattern string."""
        while cell.module_container_layout.count():
            item = cell.module_container_layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

        if not facade_str:
            return

        groups: List[Group] = parse_facade_string(facade_str)

        for grp_data in groups:
            ui_group = GroupWidget(kind=grp_data.kind)
            ui_group.repeat = grp_data.repeat
            ui_group.structureChanged.connect(self.structureChanged.emit)
            cell.module_container_layout.addWidget(ui_group)

            for mod_object in grp_data.modules:
                mod_widget = ModuleWidget(mod_object.name, False)
                mod_widget.structureChanged.connect(ui_group.structureChanged.emit)
                ui_group.layout().addWidget(mod_widget)