import math
from PySide6.QtCore import Qt, QPoint


class OrbitCamera:
    """
    A custom, stable camera controller that is driven by Qt mouse events.
    """

    def __init__(self, plotter, initial_distance=1000):
        self.plotter = plotter
        self.camera = self.plotter.camera

        # --- State Variables ---
        self.focal_point = [0, 0, 0]
        self.distance = initial_distance
        self.azimuth = 45
        self.elevation = 20
        self.last_mouse_pos: QPoint | None = None

        # --- Control Parameters ---
        self.orbit_rate = 0.5
        self.zoom_rate = 50  # Adjusted for Qt's pixel delta
        self.min_dist, self.max_dist = 200, 20000

        # Set the initial camera position
        self.update_camera_position()

    def set_focal_point(self, point):
        """Sets the center point for the camera to orbit."""
        self.focal_point = point
        self.update_camera_position()

    # --- These methods will be called by the QWidget's mouse events ---
    def on_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.position()

    def on_mouse_release(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = None

    def on_mouse_move(self, event):
        if self.last_mouse_pos is None:
            return

        current_pos = event.position()
        dx = current_pos.x() - self.last_mouse_pos.x()
        dy = current_pos.y() - self.last_mouse_pos.y()

        self.azimuth -= dx * self.orbit_rate
        self.elevation += dy * self.orbit_rate
        self.elevation = max(-89.0, min(89.0, self.elevation))

        self.last_mouse_pos = current_pos
        self.update_camera_position()

    def on_wheel_event(self, event):
        # The delta is usually a multiple of 120
        delta = event.angleDelta().y()
        if delta > 0:  # Wheel scrolled forward
            self.distance -= self.zoom_rate
        else:  # Wheel scrolled backward
            self.distance += self.zoom_rate

        self.distance = max(self.min_dist, min(self.max_dist, self.distance))
        self.update_camera_position()

    def update_camera_position(self):
        """Calculates the 3D position of the camera."""
        azimuth_rad = math.radians(self.azimuth)
        elevation_rad = math.radians(self.elevation)

        x = self.focal_point[0] + self.distance * math.cos(elevation_rad) * math.cos(azimuth_rad)
        y = self.focal_point[1] + self.distance * math.cos(elevation_rad) * math.sin(azimuth_rad)
        z = self.focal_point[2] + self.distance * math.sin(elevation_rad)

        self.camera.position = (x, y, z)
        self.camera.focal_point = self.focal_point