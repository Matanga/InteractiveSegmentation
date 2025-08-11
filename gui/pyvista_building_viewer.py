import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from gui.pyvista_viewer import PyVistaViewerWidget
from gui.pyvista_generator import PyVistaBuildingGenerator
from building_grammar.building_generator import BuildingGenerator as PillowImageGenerator # Rename for clarity
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton

# Import our backend system
from building_grammar.design_spec import BuildingSpec, FacadeSpec, BuildingDirector
from gui.resources_loader import IconFiles
import random


MODULE_WIDTH= 128
MODULE_HEIGHT= 128

# =====================================================================
# --- THIS IS OUR NEW, PRIMARY REUSABLE WIDGET ---
# =====================================================================
class BuildingViewerApp(QWidget):
    """
    A self-contained QWidget that manages the entire building generation
    and 3D visualization process.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- 1. Internal Components ---
        # The viewer is the 3D "stage".
        self.viewer = PyVistaViewerWidget()
        # The generator is the "factory" for creating 3D parts.
        self.generator_3d = PyVistaBuildingGenerator()

        icon_set = IconFiles.get_icons_for_category("Default")
        self.generator_2d = PillowImageGenerator(icon_set=icon_set)

        # --- 2. Widget Layout ---
        # This widget's layout will contain only the 3D viewer.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.viewer)

    def display_building_kit_of_parts(self, spec: BuildingSpec):
        """
        The main public method. Takes a BuildingSpec and displays the
        corresponding 3D model using the detailed "Kit of Parts" method.
        """
        # This method is an alias for the original display_building method
        self.display_building(spec)

    def display_building(self, spec: BuildingSpec):
        """
        The main public method. Takes a BuildingSpec and displays the
        corresponding 3D model in the viewer.
        """
        # --- This is the orchestration logic, now correctly placed inside the widget ---

        # 1. Get the full 4-sided blueprint from the Director
        director = BuildingDirector(spec=spec)
        blueprint = director.produce_blueprint()

        # 2. Clear the viewer of any old models

        # 3. Calculate the dimensions needed for placement
        front_bp = blueprint.get("front", {})
        right_bp = blueprint.get("right", {})
        front_width_px = max(len(m) for m in front_bp.values()) * MODULE_WIDTH if front_bp else 0
        right_width_px = max(len(m) for m in right_bp.values()) * MODULE_WIDTH if right_bp else 0
        building_height_px = spec.num_floors * MODULE_HEIGHT

        x_offset = -front_width_px / 2
        y_offset = -right_width_px / 2
        centering_translation = (x_offset, y_offset, 0)

        self.viewer.suppress_rendering = True

        try:

            self.viewer.clear_scene()

            # --- Process, Transform, and Place ALL Four Facades ---
            # FRONT
            if front_bp:
                parts = self.generator_3d.create_facade(front_bp)
                for i, (mesh, texture) in enumerate(parts):
                    mesh.translate(centering_translation, inplace=True)
                    self.viewer.add_managed_actor(f"front_module_{i}", mesh, texture)

            # RIGHT
            if right_bp:
                parts = self.generator_3d.create_facade(right_bp)
                for i, (mesh, texture) in enumerate(parts):
                    mesh.rotate_z(90, inplace=True)
                    mesh.translate((front_width_px, 0, 0), inplace=True)
                    mesh.translate(centering_translation, inplace=True) # Apply centering
                    self.viewer.add_managed_actor(f"right_module_{i}", mesh, texture)

            # BACK
            back_bp = blueprint.get("back", {})
            if back_bp:
                parts = self.generator_3d.create_facade(back_bp)
                for i, (mesh, texture) in enumerate(parts):
                    mesh.rotate_z(180, inplace=True)
                    mesh.translate((front_width_px, right_width_px, 0), inplace=True)
                    mesh.translate(centering_translation, inplace=True) # Apply centering
                    self.viewer.add_managed_actor(f"back_module_{i}", mesh, texture)

            # LEFT
            left_bp = blueprint.get("left", {})
            if left_bp:
                parts = self.generator_3d.create_facade(left_bp)
                for i, (mesh, texture) in enumerate(parts):
                    mesh.rotate_z(-90, inplace=True)
                    mesh.translate((0, right_width_px, 0), inplace=True)
                    mesh.translate(centering_translation, inplace=True) # Apply centering
                    self.viewer.add_managed_actor(f"left_module_{i}", mesh, texture)

            if front_width_px > 0 and right_width_px > 0:
                # 1. Call our new generator method to get the roof parts
                roof_mesh, roof_texture = self.generator_3d.create_roof(front_width_px, right_width_px)

                # 2. Translate the roof to its final position
                #    It needs to be at the top of the building, and its center
                #    needs to align with the center of the building's footprint.
                center_x = front_width_px / 2
                center_y = right_width_px / 2
                roof_mesh.translate((center_x, center_y, building_height_px), inplace=True)
                roof_mesh.translate(centering_translation, inplace=True) # Apply centering

                # 3. Add the roof to the scene
                self.viewer.add_managed_actor("roof", roof_mesh, roof_texture)

        finally:
            # 2c. This is GUARANTEED to run. Re-enable rendering, which
            #     triggers a single, final redraw of the completed scene.
            self.viewer.suppress_rendering = False

        # 4. Adjust the camera to view the new building
        self.viewer.reset_camera()
        print(f"--- Building with {spec.num_floors} floors displayed successfully! ---")

    def display_building_billboard(self, spec: BuildingSpec):
        """
        An alternate method that displays the building using single-image billboards
        for each facade, with corrected orientation.
        """
        director = BuildingDirector(spec=spec)
        blueprint = director.produce_blueprint()

        front_bp = blueprint.get("front", {});
        right_bp = blueprint.get("right", {})
        back_bp = blueprint.get("back", {});
        left_bp = blueprint.get("left", {})
        building_height_px = spec.num_floors * MODULE_HEIGHT

        front_width_px = max(len(m) for m in front_bp.values()) * MODULE_WIDTH if front_bp else 0
        right_width_px = max(len(m) for m in right_bp.values()) * MODULE_WIDTH if right_bp else 0
        centering_translation = (-front_width_px / 2, right_width_px / 2, 0)

        self.viewer.suppress_rendering = True
        try:
            self.viewer.clear_scene()

            # FRONT FACADE (No rotation needed)
            if front_bp:
                facade_image = self.generator_2d.assemble_full_facade(front_bp)
                mesh, texture = self.generator_3d.create_facade_billboard(facade_image)
                mesh.translate(centering_translation, inplace=True)
                self.viewer.add_managed_actor("front_billboard", mesh, texture)



            # RIGHT FACADE
            if right_bp:
                facade_image = self.generator_2d.assemble_full_facade(right_bp)
                mesh, texture = self.generator_3d.create_facade_billboard(facade_image)
                mesh.rotate_z(-90, inplace=True)  # <-- Use -90 to face outwards
                mesh.translate((front_width_px, 0, 0), inplace=True)
                mesh.translate(centering_translation, inplace=True)
                self.viewer.add_managed_actor("right_billboard", mesh, texture)

            # BACK FACADE
            if back_bp:
                facade_image = self.generator_2d.assemble_full_facade(back_bp)
                mesh, texture = self.generator_3d.create_facade_billboard(facade_image)
                mesh.rotate_z(180, inplace=True)  # <-- 180 is correct
                mesh.translate((front_width_px, -right_width_px, 0), inplace=True)
                mesh.translate(centering_translation, inplace=True)
                self.viewer.add_managed_actor("back_billboard", mesh, texture)

            # LEFT FACADE
            if left_bp:
                facade_image = self.generator_2d.assemble_full_facade(left_bp)
                mesh, texture = self.generator_3d.create_facade_billboard(facade_image)
                mesh.rotate_z(90, inplace=True)  # <-- Use +90 to face outwards
                mesh.translate((0, -right_width_px, 0), inplace=True)
                mesh.translate(centering_translation, inplace=True)
                self.viewer.add_managed_actor("left_billboard", mesh, texture)

            if front_width_px > 0 and right_width_px > 0:
                # 1. Call our new generator method to get the roof parts
                roof_mesh, roof_texture = self.generator_3d.create_roof(front_width_px, right_width_px)

                # 2. Translate the roof to its final position
                #    It needs to be at the top of the building, and its center
                #    needs to align with the center of the building's footprint.
                center_x = front_width_px / 2
                center_y = right_width_px / 2
                roof_mesh.translate((center_x, center_y, building_height_px), inplace=True)
                roof_mesh.translate(centering_translation, inplace=True) # Apply centering
                roof_mesh.translate((0,-right_width_px,0), inplace=True) # Apply centering

                # 3. Add the roof to the scene
                self.viewer.add_managed_actor("roof", roof_mesh, roof_texture)



        finally:
            self.viewer.suppress_rendering = False

        self.viewer.reset_camera()
        print(f"--- Full Billboard building with {spec.num_floors} floors displayed successfully! ---")

    def generate_building_1_kit(self):
        """Creates a spec and displays it with the Kit-of-Parts method."""
        spec = BuildingSpec(
            num_floors=2,
            facades={
                "front": FacadeSpec(width=8 * MODULE_WIDTH, grammar="<Wall00>\n[Door00]<Window00>"),
                "right": FacadeSpec(width=12 * MODULE_WIDTH, grammar="<Wall00>\n<Window00>")
            }
        )
        self.display_building_kit_of_parts(spec)

    def generate_building_1_billboard(self):
        """Creates a randomized spec and displays it with the Billboard method."""
        front_modules = random.randint(5, 12)
        right_modules = random.randint(5, 12)
        spec = BuildingSpec(
            num_floors=random.randint(2, 12),
            facades={
                "front": FacadeSpec(width=front_modules * MODULE_WIDTH, grammar="<Wall00>\n[Door00]<Window00>"),
                "right": FacadeSpec(width=right_modules * MODULE_WIDTH, grammar="<Wall00>\n<Window00>")
            }
        )
        self.display_building_billboard(spec)



class HostWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Building Viewer Application")
        self.setGeometry(100, 100, 900, 700)
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        self.building_viewer = BuildingViewerApp()

        # --- Create control buttons ---
        self.button_kit = QPushButton("Generate Building (Kit of Parts Method)")
        self.button_billboard = QPushButton("Generate Building (Image Billboard Method)")

        layout.addWidget(self.building_viewer)
        layout.addWidget(self.button_kit)
        layout.addWidget(self.button_billboard)

        # --- Connect buttons to the correct methods ---
        self.button_kit.clicked.connect(self.generate_building_1_kit)
        self.button_billboard.clicked.connect(self.generate_building_1_billboard)

        # Generate a default building on startup
        self.generate_building_1_kit()

    def generate_building_1_kit(self):
        """Creates a spec and tells the viewer to display it with the Kit method."""
        spec = BuildingSpec(
            num_floors=2,
            facades={
                "front": FacadeSpec(width=8 * MODULE_WIDTH, grammar="<Wall00>\n[Door00]<Window00>"),
                "right": FacadeSpec(width=12 * MODULE_WIDTH, grammar="<Wall00>\n<Window00>")
            }
        )
        self.building_viewer.display_building_kit_of_parts(spec)

    def generate_building_1_billboard(self):
        """Creates a spec with random widths and tells the viewer to display it with the Billboard method."""
        # Generate a random number of modules for width, between 5 and 12
        front_modules = random.randint(5, 12)
        right_modules = random.randint(5, 12)

        print(
            f"\n--- Generating BILLBOARD building with Front Width: {front_modules} modules, Right Width: {right_modules} modules ---")

        # Create the spec using these new random widths
        spec = BuildingSpec(
            num_floors=random.randint(2, 12),
            facades={
                "front": FacadeSpec(width=front_modules * MODULE_WIDTH, grammar="<Wall00>\n[Door00]<Window00>"),
                "right": FacadeSpec(width=right_modules * MODULE_WIDTH, grammar="<Wall00>\n<Window00>")
            }
        )
        self.building_viewer.display_building_billboard(spec)


if __name__ == "__main__":
    if not IconFiles.get_icons_for_category("Default"):
        sys.exit("FATAL: Could not find 'Default' icon category.")

    app = QApplication(sys.argv)
    window = HostWindow()
    window.show()
    sys.exit(app.exec())