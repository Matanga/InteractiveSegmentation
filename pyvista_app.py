import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from gui.pyvista_viewer import PyVistaViewerWidget
from gui.pyvista_generator import PyVistaBuildingGenerator

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
        self.generate_facade()

    def generate_facade(self):
        """The main logic block for generating and displaying the facade."""
        # 1. Define a spec for one facade
        spec = BuildingSpec(
            num_floors=2,
            facades={"front": FacadeSpec(width=3 * MODULE_WIDTH, grammar="<Window00>\n[Door00]<Wall00>"),
                     "right": FacadeSpec(width=4 * MODULE_WIDTH, grammar="<Window00>\n<Wall00>")
                     }
        )
        # 2. Use the Director to get the blueprint
        director = BuildingDirector(spec=spec)
        blueprint = director.produce_blueprint()
        front_blueprint = blueprint["front"]

        # 3. Use the Generator to create the list of meshes and textures
        facade_components = self.generator.create_facade(front_blueprint)

        # 4. Add each component to the viewer
        self.viewer.clear_scene()
        for i, (mesh, texture) in enumerate(facade_components):
            # ===================================================================
            # --- THE FIX IS HERE: Call the new, non-conflicting method name ---
            # ===================================================================
            self.viewer.add_managed_actor(f"module_{i}", mesh, texture)

        print("--- Facade generated and displayed successfully! ---")


if __name__ == "__main__":
    if not IconFiles.get_icons_for_category("Default"):
        sys.exit("FATAL: Could not find 'Default' icon category.")

    app = QApplication(sys.argv)
    window = HostWindow()
    window.show()
    sys.exit(app.exec())