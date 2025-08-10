import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from gui.pyvista_viewer import PyVistaViewerWidget
from gui.pyvista_generator import PyVistaBuildingGenerator
import pyvista

# Import our backend system
from building_grammar.design_spec import BuildingSpec, FacadeSpec, BuildingDirector
from gui.resources_loader import IconFiles

MODULE_WIDTH= 128

class HostWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyVista Building Generator - Step 2")
        self.setGeometry(100, 100, 900, 700)

        # The viewer is the main content of our window
        self.viewer = PyVistaViewerWidget()
        self.setCentralWidget(self.viewer)

        # The generator is our factory for creating 3D objects
        self.generator = PyVistaBuildingGenerator()

        # Generate the facade on startup
        self.generate_building()

    def generate_building(self):
        """Generates and displays the full building with debug spheres at origins."""
        # 1. Define the building spec (unchanged)
        spec = BuildingSpec(
            num_floors=2,
            facades={
                "front": FacadeSpec(width=3 * MODULE_WIDTH, grammar="<Window00>\n[Door00]<Wall00>"),
                "right": FacadeSpec(width=2 * MODULE_WIDTH, grammar="<Wall00>\n<Window00>")
            }
        )

        # 2. Get the full blueprint (unchanged)
        director = BuildingDirector(spec=spec)
        blueprint = director.produce_blueprint()

        # 3. Clear the viewer of any old models
        self.viewer.clear_scene()

        # 4. Calculate the dimensions needed for placement
        front_bp = blueprint.get("front", {})
        right_bp = blueprint.get("right", {})
        front_width_px = max(len(m) for m in front_bp.values()) * MODULE_WIDTH if front_bp else 0
        right_width_px = max(len(m) for m in right_bp.values()) * MODULE_WIDTH if right_bp else 0

        # --- Process, Transform, and Place ALL Four Facades ---

        # FRONT FACADE (Origin: 0,0,0 | Rotation: 0)
        if front_bp:
            parts = self.generator.create_facade(front_bp)
            for i, (mesh, texture) in enumerate(parts):
                self.viewer.add_managed_actor(f"front_module_{i}", mesh, texture)

        # RIGHT FACADE (Origin: front_width,0,0 | Rotation: 90 deg)
        if right_bp:
            parts = self.generator.create_facade(right_bp)
            for i, (mesh, texture) in enumerate(parts):
                mesh.rotate_z(90, inplace=True)
                mesh.translate((front_width_px, 0, 0), inplace=True)
                self.viewer.add_managed_actor(f"right_module_{i}", mesh, texture)

        # BACK FACADE (Origin: front_width, right_width, 0 | Rotation: 180 deg)
        back_bp = blueprint.get("back", {})
        if back_bp:
            parts = self.generator.create_facade(back_bp)
            for i, (mesh, texture) in enumerate(parts):
                mesh.rotate_z(180, inplace=True)
                mesh.translate((front_width_px, right_width_px, 0), inplace=True)
                self.viewer.add_managed_actor(f"back_module_{i}", mesh, texture)

        # LEFT FACADE (Origin: 0, right_width, 0 | Rotation: -90 deg)
        left_bp = blueprint.get("left", {})
        if left_bp:
            parts = self.generator.create_facade(left_bp)
            for i, (mesh, texture) in enumerate(parts):
                mesh.rotate_z(-90, inplace=True)
                mesh.translate((0, right_width_px, 0), inplace=True)
                self.viewer.add_managed_actor(f"left_module_{i}", mesh, texture)

        # Adjust the camera to view the whole building
        self.viewer.reset_camera()
        print("--- Full 4-sided building generated successfully! ---")

if __name__ == "__main__":
    if not IconFiles.get_icons_for_category("Default"):
        sys.exit("FATAL: Could not find 'Default' icon category.")

    app = QApplication(sys.argv)
    window = HostWindow()
    window.show()
    sys.exit(app.exec())