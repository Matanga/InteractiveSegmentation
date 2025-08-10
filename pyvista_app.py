import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from gui.pyvista_viewer import PyVistaViewerWidget
from gui.pyvista_generator import PyVistaBuildingGenerator
import pyvista
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton

# Import our backend system
from building_grammar.design_spec import BuildingSpec, FacadeSpec, BuildingDirector
from gui.resources_loader import IconFiles


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
        self.generator = PyVistaBuildingGenerator()

        # --- 2. Widget Layout ---
        # This widget's layout will contain only the 3D viewer.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.viewer)

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
                parts = self.generator.create_facade(front_bp)
                for i, (mesh, texture) in enumerate(parts):
                    mesh.translate(centering_translation, inplace=True)
                    self.viewer.add_managed_actor(f"front_module_{i}", mesh, texture)

            # RIGHT
            if right_bp:
                parts = self.generator.create_facade(right_bp)
                for i, (mesh, texture) in enumerate(parts):
                    mesh.rotate_z(90, inplace=True)
                    mesh.translate((front_width_px, 0, 0), inplace=True)
                    mesh.translate(centering_translation, inplace=True) # Apply centering
                    self.viewer.add_managed_actor(f"right_module_{i}", mesh, texture)

            # BACK
            back_bp = blueprint.get("back", {})
            if back_bp:
                parts = self.generator.create_facade(back_bp)
                for i, (mesh, texture) in enumerate(parts):
                    mesh.rotate_z(180, inplace=True)
                    mesh.translate((front_width_px, right_width_px, 0), inplace=True)
                    mesh.translate(centering_translation, inplace=True) # Apply centering
                    self.viewer.add_managed_actor(f"back_module_{i}", mesh, texture)

            # LEFT
            left_bp = blueprint.get("left", {})
            if left_bp:
                parts = self.generator.create_facade(left_bp)
                for i, (mesh, texture) in enumerate(parts):
                    mesh.rotate_z(-90, inplace=True)
                    mesh.translate((0, right_width_px, 0), inplace=True)
                    mesh.translate(centering_translation, inplace=True) # Apply centering
                    self.viewer.add_managed_actor(f"left_module_{i}", mesh, texture)

            if front_width_px > 0 and right_width_px > 0:
                # 1. Call our new generator method to get the roof parts
                roof_mesh, roof_texture = self.generator.create_roof(front_width_px, right_width_px)

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


class HostWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Building Viewer Application")
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # 1. Create an instance of our powerful, reusable widget
        self.building_viewer = BuildingViewerApp()

        # 2. Create some control buttons
        button1 = QPushButton("Generate 2-Floor Building")
        button2 = QPushButton("Generate 4-Floor Building (Wide)")

        # 3. Add widgets to the layout
        layout.addWidget(self.building_viewer)
        layout.addWidget(button1)
        layout.addWidget(button2)

        # 4. Connect buttons to methods that use our widget's public API
        button1.clicked.connect(self.generate_building_1)
        button2.clicked.connect(self.generate_building_2)

        # 5. Generate a default building on startup
        self.generate_building_1()

    def generate_building_1(self):
        """Creates a spec for a 2-floor building and tells the viewer to display it."""
        spec = BuildingSpec(
            num_floors=2,
            facades={
                "front": FacadeSpec(width=8 * MODULE_WIDTH, grammar="<Wall00>\n[Door00]<Window00>"),
                "right": FacadeSpec(width=12 * MODULE_WIDTH, grammar="<Wall00>\n<Window00>")
            }
        )
        self.building_viewer.display_building(spec)

    def generate_building_2(self):
        """Creates a spec for a 4-floor building and tells the viewer to display it."""
        spec = BuildingSpec(
            num_floors=4,
            facades={"front": FacadeSpec(width=6 * MODULE_WIDTH, grammar="[Door00]<Window00>\n<Wall00>"),
                     "right": FacadeSpec(width=12 * MODULE_WIDTH, grammar="<Wall00>\n<Window00>")

                     }
        )
        self.building_viewer.display_building(spec)


if __name__ == "__main__":
    if not IconFiles.get_icons_for_category("Default"):
        sys.exit("FATAL: Could not find 'Default' icon category.")

    app = QApplication(sys.argv)
    window = HostWindow()
    window.show()
    sys.exit(app.exec())