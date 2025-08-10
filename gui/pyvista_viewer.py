from pyvistaqt import QtInteractor
import pyvista
from PySide6.QtCore import QTimer  # <-- Import QTimer

class PyVistaViewerWidget(QtInteractor):
    """A reusable QWidget for displaying a PyVista 3D scene."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._managed_actors: dict = {}
        # self.camera_controller = OrbitCamera(self)

        # ===================================================================
        # --- THE CAMERA FIX IS HERE: Using a QTimer ---
        # ===================================================================
        # 1. Create a QTimer instance.
        self.camera_stabilizer_timer = QTimer(self)

        # 2. Connect the timer's 'timeout' signal to our stabilizing function.
        self.camera_stabilizer_timer.timeout.connect(self._lock_camera_roll)

        # 3. Start the timer to run repeatedly. 16ms is ~60 FPS.
        self.camera_stabilizer_timer.start(16)
        # ===================================================================



        self.setup_scene()


    def setup_scene(self):
        """Configures the initial state of the 3D scene."""
        self.enable_lightkit()
        self.set_background('gray', top='lightblue')
        grid_mesh = pyvista.Plane(i_size=4096, j_size=4096, i_resolution=32, j_resolution=32)
        self.add_mesh(grid_mesh, style='wireframe', color='darkgrey')
        # self.camera.position = (0, -1000, 500)
        # self.camera.focal_point = (0, 0, 500)


    def _lock_camera_roll(self):
        """The callback function to stabilize the camera's orientation."""
        # Check if the camera's current "up" vector is not (0, 0, 1)
        if not hasattr(self, 'camera'):
            return

        if self.camera.up != (0, 0, 1):
            self.camera.up = (0, 0, 1)


    def add_managed_actor(self, actor_name: str, mesh: pyvista.DataSet, texture: pyvista.Texture):
        """Adds a mesh with a texture to the scene and manages it."""
        if actor_name in self._managed_actors:
            self.remove_actor(self._managed_actors[actor_name])
        actor = self.add_mesh(mesh, texture=texture, name=actor_name, culling='back')
        self._managed_actors[actor_name] = actor

    def clear_scene(self):
        """Removes all managed actors from the scene."""
        for actor in self._managed_actors.values():
            self.remove_actor(actor)
        self._managed_actors.clear()

    def focus_on_actor(self, actor):
        """Points the camera controller's target to the center of an actor."""
        if self.camera_controller and actor:
            center = actor.center
            self.camera_controller.focal_point = center
            # Optional: a good initial distance could be based on object size
            self.camera_controller.distance = actor.length * 2.0
            self.camera_controller.update_camera_position()

    def reset_camera(self):
        """
        Resets the camera to frame all actors currently in the scene.
        This uses the powerful built-in reset functionality of the plotter.
        """
        print("INFO: Resetting camera to frame all actors.")
        # We simply call the parent class's (QtInteractor's) reset_camera method.
        super().reset_camera()

    def reset_camera2(self):
        """Overrides the default reset to use our controller's logic."""
        if self.camera_controller:
            self.camera_controller.azimuth = 45
            self.camera_controller.elevation = 20
            self.camera_controller.update_camera_position()