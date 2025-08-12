from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pyvista
from pyvistaqt import QtInteractor
from PySide6.QtCore import QTimer


class PyVistaViewerWidget(QtInteractor):
    """A reusable QWidget for displaying a PyVista 3D scene."""

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

        # Ground grid
        grid_mesh = pyvista.Plane(
            i_size=self._grid_size,
            j_size=self._grid_size,
            i_resolution=32,
            j_resolution=32,
        )
        self.add_mesh(grid_mesh, style="wireframe", color="darkgrey")

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
        """Add world axes lines and optional labels along grid edges."""
        half = self._grid_size / 2.0

        # X axis (red) along -Y edge
        pts_x = np.array([[-half, -half, 0], [half, -half, 0]])
        self.add_lines(pts_x, color="red", width=5)

        # Y axis (green) along -X edge
        pts_y = np.array([[-half, -half, 0], [-half, half, 0]])
        self.add_lines(pts_y, color="green", width=5)

        if self._show_axis_labels:
            self.add_point_labels(
                [[half, -half, 0], [-half, half, 0]],
                ["X (Right)", "Y (Front)"],
                font_size=18,
                shape=None,
            )

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
        *,
        culling: str = "back",
    ) -> None:
        """Add or replace a named actor and remember it for clearing."""
        # Remove existing actor with the same name
        if actor_name in self._managed_actors:
            self.remove_actor(self._managed_actors[actor_name])

        actor = self.add_mesh(mesh, texture=texture, name=actor_name, culling=culling)
        self._managed_actors[actor_name] = actor

    def clear_scene(self):
        """Removes all managed actors from the scene."""
        for actor in self._managed_actors.values():
            self.remove_actor(actor)
        self._managed_actors.clear()


