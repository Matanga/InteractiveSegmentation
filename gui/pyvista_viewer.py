from pyvistaqt import QtInteractor
import pyvista

class PyVistaViewerWidget(QtInteractor):
    """A reusable QWidget for displaying a PyVista 3D scene."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._managed_actors: dict = {}
        self.setup_scene()

    def setup_scene(self):
        """Configures the initial state of the 3D scene."""
        self.enable_lightkit()
        self.set_background('gray', top='lightblue')
        grid_mesh = pyvista.Plane(i_size=4096, j_size=4096, i_resolution=32, j_resolution=32)
        self.add_mesh(grid_mesh, style='wireframe', color='darkgrey')
        self.camera.position = (0, -1000, 500)
        self.camera.focal_point = (0, 0, 500)

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