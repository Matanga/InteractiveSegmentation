from __future__ import annotations
import json

from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QToolBar, QScrollArea, QSplitter, QPushButton, QFrame
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

import services.building_assembler as assembler
from services.facade_image_renderer import FacadeImageRenderer
from PySide6.QtWidgets import QFileDialog

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
        self._conversion_thread: RepeatableExpressionWorker | None = None

        # --- UI Assembly ---

        # Library box
        library_box = QGroupBox("Module Library")
        lib_layout = QVBoxLayout(library_box)
        lib_layout.addWidget(self._library)

        # 3D viewer
        viewer_box = QGroupBox("3D Preview")
        viewer_layout = QVBoxLayout(viewer_box)
        self.building_viewer = BuildingViewerApp()
        viewer_layout.addWidget(self.building_viewer)
        self.building_viewer.viewer.picked.connect(self._on_view_pick)

        self.assembly_panel = BuildingAssemblyPanel()

        # --- NEW: Create a new container for the viewer and its controls ---
        viewer_and_controls_widget = QWidget()
        viewer_and_controls_layout = QVBoxLayout(viewer_and_controls_widget)
        viewer_and_controls_layout.setContentsMargins(0, 0, 0, 0)
        viewer_and_controls_layout.addWidget(viewer_box)
        viewer_and_controls_layout.addWidget(self.assembly_panel)

        # Canvas box
        canvas_box = QGroupBox("Pattern Canvas")
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.setContentsMargins(4, 4, 4, 4)

        canvas_toolbar = self._create_canvas_toolbar()

        # A new layout to hold the header and scroll area seamlessly
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0) # No space between header and rows

        self.column_header = ColumnHeaderWidget()

        pattern_scroll = QScrollArea()
        pattern_scroll.setWidgetResizable(True)
        pattern_scroll.setWidget(self.pattern_area)
        pattern_scroll.setFrameShape(QFrame.Shape.NoFrame) # Removes border

        # Assemble the content_layout
        content_layout.addWidget(self.column_header)
        content_layout.addWidget(pattern_scroll, 1) # Scroll area stretches

        # Assemble the main canvas_layout
        canvas_layout.addWidget(canvas_toolbar)
        canvas_layout.addLayout(content_layout, 1) # Content layout stretches

        self.convert_button = QPushButton("➤ Convert to Structured Pattern")
        self.convert_button.setFixedHeight(30)
        self.convert_button.setStyleSheet("font-weight: bold; background-color: #5a9b5a;")
        self.convert_button.hide()
        canvas_layout.addWidget(self.convert_button)

        # --- Main Window Splitters ---

        # Top split: library | canvas | viewer
        visual_splitter = QSplitter(Qt.Horizontal)
        visual_splitter.addWidget(library_box)
        visual_splitter.addWidget(canvas_box)
        # visual_splitter.addWidget(viewer_box)
        visual_splitter.addWidget(viewer_and_controls_widget)
        visual_splitter.setSizes([250, 1000, 500])

        # Text I/O
        text_splitter = QSplitter(Qt.Horizontal)
        text_splitter.addWidget(self._input_panel)
        text_splitter.addWidget(self._output_panel)
        text_io_box = QGroupBox("Text Pattern I/O")
        text_io_layout = QVBoxLayout(text_io_box)
        text_io_layout.addWidget(text_splitter)

        # Root
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(visual_splitter)
        main_splitter.addWidget(text_io_box)
        main_splitter.setStretchFactor(0, 4)
        main_splitter.setStretchFactor(1, 1)

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(main_splitter)

        # --- Signal Connections ---
        self.pattern_area.patternChanged.connect(self.patternChanged)

        self.pattern_area.patternChanged.connect(self._on_design_changed)
        self.assembly_panel.assemblyChanged.connect(self._on_design_changed)

        self.convert_button.clicked.connect(self._on_convert_clicked)
        self._library.categoryChanged.connect(self.pattern_area.redraw)
        self.pattern_area.columnWidthsChanged.connect(self.column_header.update_column_widths)




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

    def _create_canvas_toolbar(self) -> QToolBar:
        # This functionality remains unchanged.
        tb = QToolBar("Canvas Mode")
        tb.setMovable(False)

        self.act_structured = QAction("Repeatable", self, checkable=True)
        self.act_structured.setChecked(True)
        self.act_sandbox = QAction("Rigid", self, checkable=True)
        tb.addAction(self.act_structured)
        tb.addAction(self.act_sandbox)

        # Debug buttons can remain for now
        btn_kit = QAction("Preview: Kit", self)
        btn_bill = QAction("Preview: Billboard", self)
        tb.addSeparator()
        tb.addAction(btn_kit)
        tb.addAction(btn_bill)

        self.act_structured.triggered.connect(lambda: self.set_editor_mode("Repeatable"))
        self.act_sandbox.triggered.connect(lambda: self.set_editor_mode("Rigid"))
        btn_kit.triggered.connect(self.building_viewer.generate_building_1_kit)
        btn_bill.triggered.connect(self.building_viewer.generate_building_1_billboard)

        # tb.addSeparator()
        # btn_test_render = QAction("TEST: Render Facade Strip", self)
        # btn_test_render.triggered.connect(self._on_test_render_facade_strip)
        # tb.addAction(btn_test_render)

        tb.addSeparator()
        btn_export_strips = QAction("TEST: Export All Strips", self)
        btn_export_strips.triggered.connect(self._on_test_export_all_strips)
        tb.addAction(btn_export_strips)

        btn_test_3d = QAction("TEST: Render Ground Floor 3D", self)
        btn_test_3d.triggered.connect(self._on_test_render_ground_floor_3d)
        tb.addAction(btn_test_3d)

        grp = QActionGroup(self)
        grp.addAction(self.act_structured)
        grp.addAction(self.act_sandbox)
        grp.setExclusive(True)
        return tb

    def get_floor_definitions_json(self) -> str:
        """
        Public method to retrieve the complete JSON string of all floor
        definitions from the pattern area.
        This can be used for features like exporting to a file.
        """
        return self.pattern_area.get_data_as_json()

    @Slot()
    def _on_test_render_ground_floor_3d(self):
        """
        A test function that renders just the ground floor of the current
        design in the 3D viewer.
        """
        print("--- Running Ground Floor 3D Render Test ---")

        # 1. Gather all the current UI data
        floor_defs_json = self.get_floor_definitions_json()
        b_width = int(self.assembly_panel.width_edit.text())
        b_depth = int(self.assembly_panel.depth_edit.text())

        # 2. Get the dictionary of all rendered images
        all_images = generate_all_facade_strip_images(floor_defs_json, b_width, b_depth)

        if not all_images:
            print("3D Render Test FAILED: No images were generated.")
            return

        # 3. Filter for just the "Ground Floor" images
        ground_floor_images = {
            key: img for key, img in all_images.items() if key.startswith("Ground")
        }
        print(f'========{len(ground_floor_images)}')
        if not ground_floor_images:
            print("3D Render Test FAILED: No images found for 'Ground Floor'.")
            return

        # 4. Prepare the viewer and call the new placement method
        self.building_viewer.viewer.clear_scene()

        # Call the new private method with elevation 0
        self.building_viewer._place_single_floor(
            floor_name="Ground",
            facade_strip_images=ground_floor_images,
            building_width=b_width,
            building_depth=b_depth,
            elevation=0,
            floor_height=PROCEDURAL_MODULE_HEIGHT  # Using our standard procedural height

        )

        self.building_viewer.viewer.reset_camera()
        print("--- Ground Floor 3D Render Test Complete ---")

    @Slot()
    def _on_test_export_all_strips(self):
        """
        A test function that calls the image factory and saves all the
        generated images to the project root for inspection.
        """
        print("--- Running Export All Strips Test ---")

        # 1. Gather all the current UI data
        floor_defs_json = self.get_floor_definitions_json()
        b_width = int(self.assembly_panel.width_edit.text())
        b_depth = int(self.assembly_panel.depth_edit.text())

        # 2. Call our new "factory" function to get the dictionary of images
        all_images = generate_all_facade_strip_images(floor_defs_json, b_width, b_depth)

        if not all_images:
            print("Export Test FAILED: No images were generated.")
            return

        # 3. Save all the images to the project's root directory
        import os
        for image_key, image_obj in all_images.items():
            # Sanitize the key to create a valid filename
            filename = f"{image_key.replace(' ', '_')}.png"
            save_path = os.path.join(os.getcwd(), filename)  # os.getcwd() gets the project root
            try:
                image_obj.save(save_path)
                print(f"  > Saved '{filename}' successfully.")
            except Exception as e:
                print(f"  > FAILED to save '{filename}'. Error: {e}")

        print("--- Export Test Complete ---")

    @Slot()
    def _on_test_render_facade_strip(self):
        """
        A simple, debuggable test to generate an image of a single facade strip.
        It uses the proven UI -> Adapter -> Director -> Resolver -> 2D Generator pipeline.
        """
        print("--- Running Facade Strip Render Test ---")

        # 1. Gather all the current UI data
        floor_defs_json = self.get_floor_definitions_json()
        b_width = int(self.assembly_panel.width_edit.text())
        b_depth = int(self.assembly_panel.depth_edit.text())

        try:
            # 2. Use our new Adapter to create the BuildingSpec
            spec = prepare_spec_from_ui(floor_defs_json, b_width, b_depth)
            print("Adapter created BuildingSpec successfully.")

            # 3. Use the existing BuildingDirector to get the resolved blueprint
            director = BuildingDirector(spec)
            blueprint = director.produce_blueprint()
            print("BuildingDirector produced blueprint successfully.")

            # Let's test the "front" facade, floor index 0 (the top floor in the old system)
            front_blueprint = blueprint.get("front")
            if not front_blueprint or 0 not in front_blueprint:
                raise ValueError("Blueprint does not contain a 'front' facade for the top floor (index 0).")

            # This is the resolved 1D list of modules for our target strip
            target_strip_modules = front_blueprint[0]
            print(f"Target strip modules to render: {target_strip_modules}")

            # 4. Use the existing BuildingGenerator2D to render just that strip
            icon_set = IconFiles.get_icons_for_category("Default")
            generator = BuildingGenerator2D(icon_set)

            # Call the proven, correct method
            facade_strip_image = generator.assemble_flat_floor(target_strip_modules)
            print("BuildingGenerator2D rendered image successfully.")

        except Exception as e:
            print(f"Render Test FAILED: Pipeline raised an exception: {e}")
            import traceback
            traceback.print_exc()
            return

        # 5. Save the final image so we can inspect it
        if facade_strip_image:
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Rendered Facade Strip", "rendered_strip.png", "PNG Images (*.png)"
            )
            if save_path:
                facade_strip_image.save(save_path)
                print(f"Render Test SUCCESS: Image saved to {save_path}")

    @Slot()
    def _on_design_changed(self):
        """
        This slot is connected to any change in the pattern area OR the
        assembly panel. It gathers all data needed for a 3D build and,
        for now, simply prints it for debugging.
        """
        print("=" * 20 + " DESIGN CHANGED " + "=" * 20)

        # 1. Get the floor definitions JSON
        floor_definitions = self.get_floor_definitions_json()
        print("\n--- Floor Definitions (from PatternArea) ---")
        print(floor_definitions)

        # 2. Get the assembly instructions
        print("\n--- Assembly Instructions (from AssemblyPanel) ---")
        assembly_data = {
            "Width (X)": self.assembly_panel.width_edit.text(),
            "Depth (Y)": self.assembly_panel.depth_edit.text(),
            "Height (Z)": self.assembly_panel.height_edit.text(),
            "Stacking Pattern": self.assembly_panel.pattern_edit.text(),
        }
        # Using pprint for a cleaner dictionary print
        from pprint import pprint
        pprint(assembly_data)

        print("=" * 58 + "\n")


    @Slot(str)
    def set_editor_mode(self, mode: str):
        # This functionality remains largely unchanged.
        self.pattern_area.set_mode(mode)
        self.convert_button.setVisible(mode == "Rigid")
        self.act_structured.setChecked(mode == "Repeatable")
        self.act_sandbox.setChecked(mode == "Rigid")

    # NOTE: The conversion logic now operates on the JSON output.
    # It will need to be adapted to extract the relevant facade string
    # from the JSON before sending it to the AI worker.
    # This is a future task if this feature is to be used.
    @Slot()
    def _on_convert_clicked(self):
        # For now, we'll just print a notice that this needs an update.
        print("NOTE: 'Convert to Structured' feature needs to be adapted for the new JSON data model.")
        # OLD LOGIC:
        # rigid = self.pattern_area.get_pattern_string()
        # if not rigid.strip() or rigid == "[]":
        #     print("Sandbox is empty.")
        #     return
        # model = "gpt-4o-mini"
        # self._conversion_thread = RepeatableExpressionWorker(rigid, model, self)
        # self._conversion_thread.result_ready.connect(self._on_conversion_success)
        # self._conversion_thread.error.connect(lambda msg: print(f"Conversion Error: {msg}"))
        # self._conversion_thread.finished.connect(self._conversion_thread.deleteLater)
        # self._conversion_thread.start()
        # self.convert_button.setEnabled(False)
        # self.convert_button.setText("Converting...")

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
