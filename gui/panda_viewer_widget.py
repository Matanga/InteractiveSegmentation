import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from QPanda3D import  QPanda3DWidget

# --- We only keep NON-PANDA3D imports at the top level ---
from building_grammar.design_spec import BuildingSpec, FacadeSpec, BuildingDirector
from gui.resources_loader import IconFiles

# --- Panda3D specific imports are moved inside the class ---
from panda3d.core import AmbientLight, DirectionalLight, NodePath, LineSegs
from panda3d.core import NodePath, LineSegs, AmbientLight, DirectionalLight, Texture, CardMaker, TextureStage


class Panda3dApp(QPanda3DWidget):
    """
    This is our main 3D viewer, now as a reusable QWidget.
    It uses delayed imports to ensure correct library initialization.
    """

    def __init__(self, parent=None):
        # This line MUST be called first. It initializes Panda3D via QPanda3d.
        super().__init__(parent)

        # =====================================================================
        # --- DELAYED IMPORTS ---
        # Now that the Panda3D environment is ready, we can safely import
        # our classes that depend on it.
        # =====================================================================
        from gui.pandaTest import Panda3dBuildingGenerator
        from panda_orbit_camera import OrbitCameraController

        # --- 1. Basic Scene Setup ---
        self.setup_lighting()
        self.create_grid(size=4096, num_units=64).reparentTo(self.render)

        # --- 2. Prepare the Generator ---
        self.generator = Panda3dBuildingGenerator(self.loader)

        # --- 3. Store a reference to the current building ---
        self.current_building_node = None

        # --- 4. Setup the Camera Controller ---
        self.camera_target = self.render.attachNewNode("camera-target")
        self.cam_controller = OrbitCameraController(self, self.camera, self.camera_target)
        self.camera.setY(-3000)

    def generate_and_display_building(self, spec: BuildingSpec):
        """Generates a new building based on a spec, replacing any existing one."""
        print(f"\n--- Request received to generate new building ---")
        if self.current_building_node:
            self.current_building_node.removeNode()

        director = BuildingDirector(spec=spec)
        full_blueprint = director.produce_blueprint()
        self.current_building_node = self.generator.generate_building_node(full_blueprint)
        self.current_building_node.reparentTo(self.render)

        bounds = self.current_building_node.getBounds()
        self.camera_target.setPos(bounds.getCenter())
        print(f"   Camera target updated to: {bounds.getCenter()}")

    # --- Helper methods ---
    def setup_lighting(self):
        alight = AmbientLight('alight');
        alight.setColor((0.6, 0.6, 0.6, 1))
        dlight = DirectionalLight('dlight');
        dlight.setColor((0.4, 0.4, 0.4, 1));
        dlnp = self.render.attachNewNode(dlight);
        dlnp.setHpr(30, -60, 0)
        self.render.setLight(self.render.attachNewNode(alight));
        self.render.setLight(dlnp)

    def create_grid(self, size: int, num_units: int) -> NodePath:
        lines = LineSegs("grid");
        lines.setColor(0.5, 0.5, 0.5, 1);
        lines.setThickness(1)
        half_size, step = size / 2, size / num_units
        for i in range(num_units + 1):
            x = -half_size + (i * step);
            lines.moveTo(x, -half_size, 0);
            lines.drawTo(x, half_size, 0)
        for i in range(num_units + 1):
            y = -half_size + (i * step);
            lines.moveTo(-half_size, y, 0);
            lines.drawTo(half_size, y, 0)
        return NodePath(lines.create())


# =======================================================
# --- The HostWindow and __main__ block are unchanged ---
# =======================================================
class HostWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Building Generator")
        self.setGeometry(100, 100, 900, 700)
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        self.panda_widget = Panda3dApp()
        self.button1 = QPushButton("Generate Building 1 (Tall)")
        self.button2 = QPushButton("Generate Building 2 (Wide)")
        layout.addWidget(self.panda_widget)
        layout.addWidget(self.button1)
        layout.addWidget(self.button2)
        self.button1.clicked.connect(self.generate_building_1)
        self.button2.clicked.connect(self.generate_building_2)
        self.generate_building_1()

    def generate_building_1(self):
        spec = BuildingSpec(num_floors=5, facades={"front": FacadeSpec(width=3 * 128, grammar="<W>"),
                                                   "right": FacadeSpec(width=3 * 128, grammar="<Win>")})
        self.panda_widget.generate_and_display_building(spec)

    def generate_building_2(self):
        spec = BuildingSpec(num_floors=2, facades={"front": FacadeSpec(width=8 * 128, grammar="<W>[D]<W>"),
                                                   "right": FacadeSpec(width=2 * 128, grammar="<W>")})
        self.panda_widget.generate_and_display_building(spec)


if __name__ == "__main__":
    if not IconFiles.get_icons_for_category("Default"):
        sys.exit("FATAL: Could not find 'Default' icon category.")
    app = QApplication(sys.argv)
    window = HostWindow()
    window.show()
    sys.exit(app.exec())