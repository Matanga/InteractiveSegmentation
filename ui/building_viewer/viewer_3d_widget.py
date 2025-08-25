from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pyvista
from pyvistaqt import QtInteractor
from PySide6.QtCore import QTimer
from PySide6.QtCore import Signal


class PyVistaViewerWidget(QtInteractor):
    """A reusable QWidget for displaying a PyVista 3D scene."""
    picked = Signal(dict)   # emits {'facade': 'front', 'floor': 2, ...}

    def __init__(
        self,
        parent=None,
        *,
        grid_size: float = 4096.0,
        show_world_axes: bool = True,
        show_axis_labels: bool = True,
        theme: str = "light",  # "light" or "dark"
    ):
        super().__init__(parent)
        self._managed_actors: Dict[str, pyvista.Actor] = {}

        self._meta_by_actor = {}      # actor -> dict meta
        # self.enable_mesh_picking(self._on_mesh_pick, left_clicking=True, show_message=False,style='surface')
        # self.enable_picking(self._on_pick, show_message=False, left_clicking=True)
        self.enable_mesh_picking(self._on_mesh_pick, left_clicking=True, show_message=False, style='surface')

        self._non_pickable_actors = set()

        self._grid_size = float(grid_size)
        self._show_world_axes = bool(show_world_axes)
        self._show_axis_labels = bool(show_axis_labels)

        # Keep the camera upright using a timer
        self._camera_timer = QTimer(self)
        self._camera_timer.timeout.connect(self._lock_camera_roll)
        self._camera_timer.start(16)  # ~60 FPS

        # Scene bootstrap
        self._setup_scene(theme)

    def _setup_scene(self, theme: str) -> None:
        self.enable_lightkit()
        self.set_background_theme(theme)
        grid_mesh = pyvista.Plane(i_size=self._grid_size, j_size=self._grid_size, i_resolution=32, j_resolution=32)
        self.add_mesh(grid_mesh, style="wireframe", color="darkgrey", pickable=False)
        if self._show_world_axes:
            self._add_world_axes()

    def set_background_theme(self, theme: str = "light") -> None:
        """Switch background gradient between 'light' and 'dark'."""
        theme = (theme or "light").lower()
        if theme == "dark":
            self.set_background("black", top="dimgray")
        else:
            self.set_background("gray", top="lightblue")

    def _add_world_axes(self) -> None:
        half = self._grid_size / 2.0
        pts_x = np.array([[-half, -half, 0], [half, -half, 0]])
        self.add_lines(pts_x, color="red", width=5)
        pts_y = np.array([[-half, -half, 0], [-half, half, 0]])
        self.add_lines(pts_y, color="green", width=5)
        if self._show_axis_labels:
            self.add_point_labels([[half, -half, 0], [-half, half, 0]], ["X (Right)", "Y (Front)"], font_size=18,
                                  shape=None, pickable=False)

    # ------------------------------------------------------------------ #
    # Camera helpers
    # ------------------------------------------------------------------ #
    def _lock_camera_roll(self) -> None:
        """Keep camera 'up' vector aligned with +Z."""
        cam = getattr(self, "camera", None)
        if cam and cam.up != (0, 0, 1):
            cam.up = (0, 0, 1)

    def reset_camera(self):
        """
        Resets the camera to frame all actors currently in the scene.
        This uses the powerful built-in reset functionality of the plotter.
        """
        print("INFO: Resetting camera to frame all actors.")
        # We simply call the parent class's (QtInteractor's) reset_camera method.
        super().reset_camera()

    # ------------------------------------------------------------------ #
    # Managed actors
    # ------------------------------------------------------------------ #
    def add_managed_actor(
            self,
            actor_name: str,
            mesh: pyvista.DataSet,
            texture: Optional[pyvista.Texture] = None,
            meta: Optional[Dict] = None,
            *,
            culling: str = "back"
    ) -> None:
        if actor_name in self._managed_actors:
            self.remove_actor(self._managed_actors[actor_name])

        # --- THIS IS THE FIX ---
        # 2. When an actor is added, store its metadata directly on the mesh's field_data.
        #    This creates a direct, unbreakable link between the geometry and its info.
        if meta is not None:
            # PyVista's field_data can be treated like a dictionary.
            # We will store the entire metadata dictionary under a single key.
            # We serialize it to a JSON string to ensure it's stored correctly.
            import json
            mesh.field_data['meta_info'] = np.array([json.dumps(meta)])
        # --- END OF FIX ---

        actor = self.add_mesh(mesh, texture=texture, name=actor_name, culling=culling)
        self._managed_actors[actor_name] = actor

    def clear_scene(self):
        for actor in self._managed_actors.values():
            if actor in self._meta_by_actor:
                del self._meta_by_actor[actor]
            self.remove_actor(actor)
        self._managed_actors.clear()

    def _on_mesh_pick(self, mesh: pyvista.DataSet):
        """
        This callback is triggered when a mesh is picked. It reads the
        metadata directly from the mesh's field_data.
        """
        if not mesh:
            return

        # 3. Check if our custom metadata key exists on the picked mesh.
        if 'meta_info' in mesh.field_data:
            # 4. Deserialize the JSON string back into a Python dictionary.
            import json
            meta_json = mesh.field_data['meta_info'][0]
            meta = json.loads(meta_json)

            print(f">>> MESH PICKED: Emitting meta {meta}")
            self.picked.emit(meta)



    def clear_scene(self):
        """Removes all managed actors from the scene."""
        for actor in self._managed_actors.values():
            self.remove_actor(actor)
        self._managed_actors.clear()


