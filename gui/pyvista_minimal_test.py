import sys
import pyvista
from PySide6.QtWidgets import QApplication, QMainWindow
from pyvistaqt import QtInteractor

pyvista.set_plot_theme("document")


class HostWindow(QMainWindow):
    """A simple QMainWindow to host our PyVista widget."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyVista + PySide6 Minimal Example")
        self.setGeometry(200, 200, 800, 600)

        # 1. Create the PyVista widget
        self.plotter_widget = QtInteractor(self)
        self.setCentralWidget(self.plotter_widget)

        # 2. Add 3D objects to the scene

        # --- Create a sphere mesh ---
        sphere_mesh = pyvista.Sphere()

        # ===================================================================
        # --- THE FIX IS HERE: Translate the mesh BEFORE adding it ---
        # ===================================================================
        # The .translate() method modifies the mesh in place.
        sphere_mesh.translate((-2, 0, 0), inplace=True)

        # Now, add the already-positioned mesh to the plotter.
        # We remove the 'center' argument.
        self.plotter_widget.add_mesh(
            sphere_mesh,
            color="red"
        )

        # --- Create a cube mesh ---
        cube_mesh = pyvista.Cube()

        # --- Translate the cube mesh as well ---
        cube_mesh.translate((2, 0, 0), inplace=True)

        # Add the positioned cube to the plotter.
        self.plotter_widget.add_mesh(
            cube_mesh,
            color="blue"
        )
        # ===================================================================

        # 3. Configure the scene (unchanged)
        self.plotter_widget.show_grid()
        self.plotter_widget.enable_lightkit()


# The main application entry point (unchanged)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HostWindow()
    window.show()
    sys.exit(app.exec())