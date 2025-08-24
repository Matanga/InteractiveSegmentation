from __future__ import annotations
import json

from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QToolBar, QScrollArea, QSplitter, QPushButton, QFrame, QMessageBox, QHBoxLayout
)
from PySide6.QtGui import QAction, QActionGroup

from domain.building_generator_2d import BuildingGenerator2D
from domain.building_spec import BuildingDirector, PROCEDURAL_MODULE_HEIGHT
from services.resources_loader import IconFiles
from ui.building_viewer.building_assembly_panel import BuildingAssemblyPanel
from ui.pattern_editor.module_library import ModuleLibrary
from ui.pattern_editor.pattern_text_panels import PatternInputPanel, PatternOutputPanel
from ui.pattern_editor.pattern_area import PatternArea
from ui.pattern_editor.column_header_widget import ColumnHeaderWidget

from ui.building_viewer.building_viewer import BuildingViewerApp
# NOTE: The RepeatableExpressionWorker is part of the 'Rigid' to 'Repeatable'
# conversion feature, which is separate from our current refactor. We'll leave
# it imported but be aware its functionality might need updating later if used.
from services.facade_segmentation import RepeatableExpressionWorker
from services.stacking_resolver import StackingResolver
from domain.grammar import parse_building_json
import services.building_assembler as assembler
from services.facade_image_renderer import FacadeImageRenderer
from PySide6.QtWidgets import QFileDialog
from ui.mapping_editor.mapping_editor_panel import MappingEditorPanel
from services.floor_data_exporter import translate_floor_definitions

from services.ui_adapter import prepare_spec_from_ui

from services.building_image_exporter import generate_all_facade_strip_images

class PatternEditorPanel(QWidget):
    # This signal is still valid. It will now emit the full JSON string.
    patternChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._library = ModuleLibrary()
        self.pattern_area = PatternArea(3)
        self._input_panel = PatternInputPanel()
        self._output_panel = PatternOutputPanel()
        self._mapping_panel = MappingEditorPanel()

        # --- UI Assembly ---

        # Library box
        library_box = QGroupBox("Module Library")
        lib_layout = QVBoxLayout(library_box)
        lib_layout.addWidget(self._library)

        # 3D viewer and Assembly Panel
        viewer_box = QGroupBox("3D Preview")
        viewer_layout = QVBoxLayout(viewer_box)
        self.building_viewer = BuildingViewerApp()
        viewer_layout.addWidget(self.building_viewer)

        self.assembly_panel = BuildingAssemblyPanel()
        viewer_and_controls_widget = QWidget()
        viewer_and_controls_layout = QVBoxLayout(viewer_and_controls_widget)
        viewer_and_controls_layout.setContentsMargins(0, 0, 0, 0)
        viewer_and_controls_layout.addWidget(viewer_box)
        viewer_and_controls_layout.addWidget(self.assembly_panel)

        # Canvas box
        canvas_box = QGroupBox("Pattern Canvas")
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.setContentsMargins(4, 4, 4, 4)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 5, 0, 0)
        content_layout.setSpacing(0)

        self.column_header = ColumnHeaderWidget()
        pattern_scroll = QScrollArea()
        pattern_scroll.setWidgetResizable(True)
        pattern_scroll.setWidget(self.pattern_area)
        pattern_scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_layout.addWidget(self.column_header)
        content_layout.addWidget(pattern_scroll, 1)

        # --- THIS IS THE FIX ---
        # The bottom bar layout lives inside PatternArea.
        # We create the export button and add it to that pre-existing layout.
        self.export_button = QPushButton("Export Floor Data Table...")
        # Add the export button directly after the Add Floor button.
        self.pattern_area.bottom_bar_layout.addWidget(self.export_button)

        # Assemble the main canvas_layout
        canvas_layout.addLayout(content_layout, 1)
        # --- END OF FIX ---

        # --- Main Window Splitters ---
        visual_splitter = QSplitter(Qt.Horizontal)
        visual_splitter.addWidget(library_box)
        visual_splitter.addWidget(canvas_box)
        visual_splitter.addWidget(viewer_and_controls_widget)
        visual_splitter.setSizes([250, 1000, 500])

        mapping_box = QGroupBox("Mapping Editor")
        mapping_layout = QVBoxLayout(mapping_box)
        mapping_layout.addWidget(self._mapping_panel)

        text_io_box = QGroupBox("Text Pattern I/O")
        text_io_layout = QVBoxLayout(text_io_box)
        text_io_layout.addWidget(self._input_panel)
        text_io_layout.addWidget(self._output_panel)

        bottom_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter.addWidget(mapping_box)
        bottom_splitter.addWidget(text_io_box)

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(visual_splitter)
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setStretchFactor(0, 4)
        main_splitter.setStretchFactor(1, 1)

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(main_splitter)

        # --- Signal Connections ---
        self.pattern_area.patternChanged.connect(self.patternChanged)
        self.pattern_area.patternChanged.connect(self._on_design_changed)
        self.assembly_panel.assemblyChanged.connect(self._on_design_changed)
        self._library.categoryChanged.connect(self.pattern_area.redraw)
        self.pattern_area.columnWidthsChanged.connect(self.column_header.update_column_widths)
        self.assembly_panel.generate_button.clicked.connect(self._on_generate_button_clicked)
        self.export_button.clicked.connect(self._on_export_button_clicked)

        # --- Load a default pattern on startup ---
        self._load_default_pattern()

    def _load_default_pattern(self):
        """Creates and loads a simple, default building pattern."""
        floor_facade ="<Wall00>[Door00-Window00]"
        window_facade1 ="[Wall00]<Window00>[Wall00]"
        window_facade2 ="<Window00-Wall00>"
        window_facade3 ="[Window01]<Window00-Wall00>[Window01]"
        default_facade = "<Wall00>"

        # Create a Python dictionary representing a simple 3-floor building
        default_building_data = [
            # Ground Floor (Index 0 in JSON)
            {
                "Name": "Ground",
                "Pattern": [floor_facade, window_facade1, default_facade, default_facade],
                "Height": 400
            },
            # Floor 1 (Index 1 in JSON)
            {
                "Name": "Floor1",
                "Pattern": [window_facade1, default_facade, window_facade1, window_facade2],
                "Height": 400
            },
            # Floor 2 (Index 2 in JSON)
            {
                "Name": "Floor2",
                "Pattern": [window_facade3, window_facade2, window_facade3, window_facade2],
                "Height": 400
            }
        ]

        # Convert the Python data to a JSON string
        default_json_str = json.dumps(default_building_data)

        # Use our existing public method to load this data
        self.load_pattern(default_json_str)

    def _on_view_pick(self, info: dict):
        # This functionality remains unchanged.
        print("Picked:", info)

    def get_floor_definitions_json(self) -> str:
        """
        Public method to retrieve the complete JSON string of all floor
        definitions from the pattern area.
        This can be used for features like exporting to a file.
        """
        return self.pattern_area.get_data_as_json()


    @Slot()
    def _on_design_changed(self):
        """
        This slot is connected to any change in the design. It gathers all
        data and, if live update is on, triggers the 3D viewer.
        """
        # We only run the update if the checkbox is checked.
        if not self.assembly_panel.live_update_checkbox.isChecked():
            return

        try:
            floor_defs_json = self.get_floor_definitions_json()
            b_width = int(self.assembly_panel.width_edit.text() or 0)
            b_depth = int(self.assembly_panel.depth_edit.text() or 0)
            b_height = int(self.assembly_panel.height_edit.text() or 0)
            stack_pattern = self.assembly_panel.pattern_edit.text()

            if b_width > 0 and b_depth > 0 and b_height > 0:
                # Call the new master function on the viewer
                self.building_viewer.display_full_building(
                    floor_defs_json, b_width, b_depth, b_height, stack_pattern
                )
        except (ValueError, KeyError) as e:
            # A ValueError can happen if text fields are empty/invalid.
            # A KeyError can happen if the floor_map is temporarily out of sync.
            # We can silently ignore these during live-editing.
            # print(f"Info: Live update skipped due to transient error: {e}")
            pass

    @Slot()
    def _on_export_button_clicked(self):
        """
        Handles the full workflow for exporting a translated floor data table.
        """
        # 1. Get the currently selected mapping from the mapping panel
        selected_dt_item = self._mapping_panel.data_table_list.currentItem()
        if not selected_dt_item:
            QMessageBox.warning(self, "No Mapping Selected",
                                "Please select a Data Table from the Mapping Editor to use for export.")
            return

        display_name = selected_dt_item.text()
        entry = self._mapping_panel.data_manager.get_entry_by_display_name(display_name)
        if not entry: return

        mapping = self._mapping_panel.data_manager.load_mapping_for_id(entry['id'])
        if not mapping:
            QMessageBox.warning(self, "Empty Mapping",
                                f"The mapping for '{display_name}' is empty. Please define mappings before exporting.")
            return

        # 2. Get the current floor definitions from the pattern area
        floor_defs_json = self.get_floor_definitions_json()
        floor_definitions = json.loads(floor_defs_json)

        # 3. Translate the definitions using the exporter service
        translated_data = translate_floor_definitions(floor_definitions, mapping)

        # 4. Ask the user where to save the new file
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Floor Data Table", f"DT_{display_name}_Floors.json", "JSON Files (*.json)"
        )

        if save_path:
            try:
                with open(save_path, 'w') as f:
                    json.dump(translated_data, f, indent=4)
                QMessageBox.information(self, "Success", f"Floor Data Table exported successfully to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file.\nError: {e}")

    # The public 'load_pattern' method needs to be updated to expect JSON
    @Slot(str)
    def load_pattern(self, pattern_json_str: str):
        """
        Public slot to load a pattern from a JSON string.
        This is the new entry point for loading data from outside.
        """
        try:
            # We delegate the entire loading process to our new PatternArea
            self.pattern_area.load_from_json(pattern_json_str)
        except Exception as e:
            print(f"Error loading pattern in PatternEditorPanel: {e}")

    @Slot()
    def _on_generate_button_clicked(self):
        """
        A dedicated slot for the manual generate button. It's the same
        logic as the live update, but without the checkbox check.
        """
        try:
            floor_defs_json = self.get_floor_definitions_json()
            b_width = int(self.assembly_panel.width_edit.text() or 0)
            b_depth = int(self.assembly_panel.depth_edit.text() or 0)
            b_height = int(self.assembly_panel.height_edit.text() or 0)
            stack_pattern = self.assembly_panel.pattern_edit.text()

            if b_width > 0 and b_depth > 0 and b_height > 0:
                self.building_viewer.display_full_building(
                    floor_defs_json, b_width, b_depth, b_height, stack_pattern
                )
        except Exception as e:
            # For a manual click, we should be more verbose with errors.
            print(f"ERROR on manual generation: {e}")
            import traceback
            traceback.print_exc()

