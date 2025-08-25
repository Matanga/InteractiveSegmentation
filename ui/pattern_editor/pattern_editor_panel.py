from __future__ import annotations
import json

from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QScrollArea, QSplitter, QPushButton, QFrame, QMessageBox, QInputDialog
)

from ui.building_viewer.building_assembly_panel import BuildingAssemblyPanel
from ui.mapping_editor.mapping_data_manager import AssetManager
from ui.pattern_editor.module_library import ModuleLibrary
from ui.pattern_editor.pattern_text_panels import PatternInputPanel, PatternOutputPanel
from ui.pattern_editor.pattern_area import PatternArea
from ui.pattern_editor.column_header_widget import ColumnHeaderWidget

from ui.building_viewer.building_viewer import BuildingViewerApp

from PySide6.QtWidgets import QFileDialog
from ui.mapping_editor.mapping_editor_panel import MappingEditorPanel
from services.floor_data_exporter import translate_floor_definitions
from ui.floor_library.floor_library_panel import FloorLibraryPanel



class PatternEditorPanel(QWidget):
    # This signal is still valid. It will now emit the full JSON string.
    patternChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.active_floor_set_id: str | None = "default"

        self._create_managers_and_components()
        self._setup_layouts()
        self._connect_signals()
        self._perform_startup_actions()

    # ======================================================================
    # --- Initialization Steps ---
    # ======================================================================

    def _create_managers_and_components(self):
        """Initializes all the core data managers and UI panels."""
        self.asset_manager = AssetManager()
        self.pattern_area = PatternArea(num_floors=0)
        self._library = ModuleLibrary()
        self._input_panel = PatternInputPanel()
        self._output_panel = PatternOutputPanel()
        self.building_viewer = BuildingViewerApp()
        self.assembly_panel = BuildingAssemblyPanel()
        self.column_header = ColumnHeaderWidget()

        # Panels that require the asset manager
        self.floor_library_panel = FloorLibraryPanel(asset_manager=self.asset_manager)
        self._mapping_panel = MappingEditorPanel(asset_manager=self.asset_manager)

    def _setup_layouts(self):
        """Assembles all the widgets and layouts for the main UI."""
        # Left-Side Panel
        library_box = QGroupBox("Module Library")
        lib_layout = QVBoxLayout(library_box);
        lib_layout.addWidget(self._library)
        floor_library_box = QGroupBox("Floor Library")
        floor_library_layout = QVBoxLayout(floor_library_box);
        floor_library_layout.addWidget(self.floor_library_panel)
        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.addWidget(floor_library_box)
        left_panel_layout.addWidget(library_box, 1)

        # Right-Side Panel
        viewer_box = QGroupBox("3D Preview")
        viewer_layout = QVBoxLayout(viewer_box);
        viewer_layout.addWidget(self.building_viewer)
        viewer_and_controls_widget = QWidget()
        viewer_and_controls_layout = QVBoxLayout(viewer_and_controls_widget)
        viewer_and_controls_layout.setContentsMargins(0, 0, 0, 0)
        viewer_and_controls_layout.addWidget(viewer_box)
        viewer_and_controls_layout.addWidget(self.assembly_panel)

        # Center Panel
        canvas_box = QGroupBox("Pattern Canvas")
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.setContentsMargins(4, 4, 4, 4)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 5, 0, 0)
        content_layout.setSpacing(0)
        pattern_scroll = QScrollArea()
        pattern_scroll.setWidgetResizable(True)
        pattern_scroll.setWidget(self.pattern_area)
        pattern_scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_layout.addWidget(self.column_header)
        content_layout.addWidget(pattern_scroll, 1)
        canvas_layout.addLayout(content_layout, 1)

        # Bottom Panels
        mapping_box = QGroupBox("Mapping Editor")
        mapping_layout = QVBoxLayout(mapping_box);
        mapping_layout.addWidget(self._mapping_panel)
        text_io_box = QGroupBox("Text Pattern I/O")
        text_io_layout = QVBoxLayout(text_io_box)
        text_io_layout.addWidget(self._input_panel)
        text_io_layout.addWidget(self._output_panel)

        # Main Splitters
        visual_splitter = QSplitter(Qt.Horizontal)
        visual_splitter.addWidget(left_panel_widget)
        visual_splitter.addWidget(canvas_box)
        visual_splitter.addWidget(viewer_and_controls_widget)
        visual_splitter.setSizes([250, 1000, 500])
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

    def _connect_signals(self):
        """Connects all the signal and slot connections for the application."""
        # Pattern Area signals
        self.pattern_area.patternChanged.connect(self.patternChanged)
        self.pattern_area.patternChanged.connect(self._on_design_changed)
        self.pattern_area.columnWidthsChanged.connect(self.column_header.update_column_widths)

        # Assembly Panel signals
        self.assembly_panel.assemblyChanged.connect(self._on_design_changed)
        self.assembly_panel.generate_button.clicked.connect(self._on_generate_button_clicked)

        # Library signals
        self._library.categoryChanged.connect(self.pattern_area.redraw)

        # 3D Viewer signals
        self.building_viewer.viewer.picked.connect(self._on_view_pick)

        # Floor Library signals
        # Floor Library signals
        self.floor_library_panel.new_requested.connect(self._on_new_floor_set_requested)
        self.floor_library_panel.save_requested.connect(self._on_save_floor_set_requested)
        self.floor_library_panel.save_as_requested.connect(self._on_save_floor_set_as_requested)
        self.floor_library_panel.load_requested.connect(self._on_load_floors_requested) # Connect to the correct signal
        self.floor_library_panel.export_requested.connect(self._on_export_floors_requested)

    def _perform_startup_actions(self):
        """Runs any actions required when the application first starts."""
        # Automatically load the "Default Floors" set from the library.
        self.floor_library_panel._on_load_clicked()

    # ======================================================================
    # --- Initialization Steps ---
    # ======================================================================

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

    @Slot(dict)
    def _on_view_pick(self, info: dict):
        """
        Handles a pick event from the 3D viewer. It finds the corresponding
        2D facade cell and triggers its highlight effect.
        """
        # --- THIS IS THE FIX ---
        # The 'info' dictionary that the signal emits IS our metadata.
        # We do not need to look for a nested 'meta' key.
        if not info:
            return

        object_type = info.get("type")
        floor_name_from_meta = info.get("floor_name")
        side_name = info.get("side")
        # --- END OF FIX ---

        if object_type != "facade_panel" or not floor_name_from_meta or not side_name:
            return

        print(f"3D Pick Event: Highlighting {floor_name_from_meta} - {side_name}")

        target_row = None
        for row in self.pattern_area._floor_rows:
            ui_name = row.header.name_edit.text().strip()
            meta_name = floor_name_from_meta.strip()
            # Let's use a case-insensitive comparison for robustness
            if ui_name.lower() == meta_name.lower():
                target_row = row
                break

        if not target_row:
            print(f"Warning: Could not find a floor row named '{floor_name_from_meta}' in the UI.")
            return

        target_cell = None
        if side_name == "front":
            target_cell = target_row.cell_front
        elif side_name == "left":
            target_cell = target_row.cell_left
        elif side_name == "back":
            target_cell = target_row.cell_back
        elif side_name == "right":
            target_cell = target_row.cell_right

        if target_cell:
            target_cell.trigger_highlight()

    def get_floor_definitions_json(self) -> str:
        """
        Public method to retrieve the complete JSON string of all floor
        definitions from the pattern area.
        This can be used for features like exporting to a file.
        """
        return self.pattern_area.get_data_as_json()

    @Slot()
    def _on_save_as_triggered(self):
        """
        Orchestrates the entire "Save As..." workflow. This is called when
        the user clicks the "Save As..." button in the floor library.
        """
        # 1. Get the current floor data directly from the PatternArea.
        json_str = self.pattern_area.get_data_as_json()
        current_floors_data = json.loads(json_str)

        if not current_floors_data:
            QMessageBox.warning(self, "No Data", "There are no floors in the canvas to save.")
            return

        # 2. Ask the user for a name.
        display_name, ok = QInputDialog.getText(self, "Save Floor Set As...", "Enter a name for the new floor set:")
        if not ok or not display_name.strip():
            return

        # 3. Call the AssetManager to save the file and update the manifest.
        success = self.asset_manager.save_new_floor_set(
            display_name=display_name.strip(),
            floor_data=current_floors_data
        )

        # 4. If successful, command the FloorLibraryPanel to refresh its list.
        if success:
            QMessageBox.information(self, "Success", f"Floor set '{display_name}' saved successfully.")
            self.floor_library_panel._populate_floor_set_list()
        else:
            QMessageBox.critical(self, "Error", "An error occurred while saving the floor set.")
    @Slot()
    def _on_new_floor_set_requested(self):
        """Handles the 'New' action from the floor library."""
        # Create a single, simple default floor
        default_data = [{
            "Name": "New Floor 1",
            "Pattern": ["<Wall00>", "<Wall00>", "<Wall00>", "<Wall00>"],
            "Height": 400
        }]
        self.pattern_area.load_from_json(json.dumps(default_data))
        # Critically, set the active ID to None, indicating it's an unsaved file
        self.active_floor_set_id = None
        print("Created new, unsaved floor set.")

    @Slot()
    def _on_save_floor_set_requested(self):
        """Handles the 'Save' (overwrite) action."""
        if self.active_floor_set_id is None or self.active_floor_set_id == "default":
            # If the file is new or the default, "Save" must act like "Save As"
            self._on_save_floor_set_as_requested()
        else:
            # Otherwise, overwrite the existing file
            print(f"Overwriting floor set: {self.active_floor_set_id}")
            json_str = self.pattern_area.get_data_as_json()
            data = json.loads(json_str)
            self.asset_manager.update_floor_set(self.active_floor_set_id, data)
            QMessageBox.information(self, "Success", "Floor set saved successfully.")

    @Slot()
    def _on_save_floor_set_as_requested(self):
        """Handles the 'Save As...' action by asking the FloorLibraryPanel to do the work."""
        # This uses the same callback pattern as before
        self.floor_library_panel.request_current_floors.emit(
            self.floor_library_panel.receive_current_floors_for_saving
        )

    @Slot()
    def _on_test_highlight(self):
        """
        A test function to verify the highlight effect on a specific cell.
        It will attempt to highlight the "front" facade of the "Ground" floor.
        """
        print("--- Testing Highlight ---")

        # We need to find the specific widget in our layout.
        # This is a bit complex, but it simulates what the final function will do.

        # Get the list of all floor rows
        floor_rows = self.pattern_area._floor_rows

        # Find the "Ground" floor row
        target_row = None
        for row in floor_rows:
            if row.header.name_edit.text() == "Ground":
                target_row = row
                break

        if target_row:
            # Get the "front" cell from that row
            front_cell = target_row.cell_front
            print("Found target cell. Triggering highlight...")
            # Call our new public method
            front_cell.trigger_highlight()
        else:
            print("Could not find the 'Ground' floor to highlight.")

    @Slot(str)  # <-- It now receives a string ID
    def _on_load_floors_requested(self, floor_set_id: str):
        """Receives a floor set ID from the library, loads it, and sets it as active."""
        print(f"Load requested for floor set ID: {floor_set_id}")
        self.active_floor_set_id = floor_set_id  # <-- Set the active ID

        if floor_set_id == "default":
            default_path = self.asset_manager.user_assets_path / "floor_sets" / "default_floors.json"
            if default_path.exists():
                with open(default_path, 'r') as f:
                    floor_data = json.load(f)
                    self.pattern_area.load_from_json(json.dumps(floor_data))
            return

        floor_data = self.asset_manager.load_floor_set_data(floor_set_id)
        if floor_data:
            self.pattern_area.load_from_json(json.dumps(floor_data))

    @Slot(object)
    def _on_save_floors_requested(self, callback: callable):
        """
        Receives a request for the current floor data, gets it from the
        pattern area, and sends it back via the provided callback.
        """
        json_str = self.pattern_area.get_data_as_json()
        data = json.loads(json_str)
        callback(data)

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
    def _on_export_floors_requested(self, floor_set_id: str):
        """
            Handles the full workflow for exporting a translated floor data table.
            """
        print(f"Export requested for floor set ID: {floor_set_id}")

        # 1. Ask the user which mapping they want to use for this export
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
                                f"The mapping for '{display_name}' is empty.")
            return

        # 2. Get the floor definitions for the requested floor set
        if floor_set_id == 'default':
            # Handle the special case for the built-in default
            default_path = self.asset_manager.user_assets_path / "floor_sets" / "default_floors.json"
            with open(default_path, 'r') as f:
                floor_definitions = json.load(f)
        else:
            floor_definitions = self.asset_manager.load_floor_set_data(floor_set_id)

        if not floor_definitions:
            QMessageBox.critical(self, "Error", "Could not load the floor definitions for export.")
            return

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
                QMessageBox.information(self, "Success", f"Floor Data Table exported successfully.")
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

