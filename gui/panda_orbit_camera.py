from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from panda3d.core import NodePath, Point3


class OrbitCameraController(DirectObject):
    """
    A camera controller for orbiting, panning, and zooming around a central target.
    This provides a more intuitive "model viewer" or "CAD" style camera.
    """

    def __init__(self, showbase, camera: NodePath, target: NodePath):
        self.showbase = showbase
        self.camera = camera
        self.target = target  # The NodePath the camera will orbit around

        # The gimbal is an invisible node that controls the camera's rotation (pitch/heading)
        self.gimbal = self.showbase.render.attachNewNode("camera-gimbal")
        self.gimbal.reparentTo(self.target)
        self.camera.reparentTo(self.gimbal)

        # Initialize control parameters
        self.zoom_step = 100
        self.min_dist, self.max_dist = 300, 20000
        self.pan_rate = 10
        self.orbit_rate = 0.5

        self.last_mouse_pos = Point3(0, 0, 0)

        # Disable the default, clunky mouse controls
        self.showbase.disableMouse()
        self.setup_controls()

    def setup_controls(self):
        """Activates all the mouse and keyboard bindings."""
        self.accept("wheel_up", self.zoom_in)
        self.accept("wheel_down", self.zoom_out)
        self.accept("mouse1", self.start_orbit)  # Left Mouse Button
        self.accept("mouse1-up", self.stop_task, ["orbit_task"])
        self.accept("mouse3", self.start_pan)  # Right Mouse Button (or middle, depending on OS)
        self.accept("mouse3-up", self.stop_task, ["pan_task"])

    def destroy(self):
        """Deactivates all controls and cleans up."""
        self.ignoreAll()
        self.stop_task("orbit_task")
        self.stop_task("pan_task")
        self.gimbal.removeNode()

    def zoom_in(self):
        new_dist = self.camera.getY() + self.zoom_step
        if new_dist < self.max_dist:
            self.camera.setY(min(new_dist, -self.min_dist))

    def zoom_out(self):
        new_dist = self.camera.getY() - self.zoom_step
        if new_dist > -self.max_dist:
            self.camera.setY(max(new_dist, -self.max_dist))

    def start_orbit(self):
        if self.showbase.mouseWatcherNode.hasMouse():
            mouse_pos = self.showbase.mouseWatcherNode.getMouse()
            self.last_mouse_pos = Point3(mouse_pos.getX(), mouse_pos.getY(), 0)
            self.showbase.taskMgr.add(self.orbit_task, "orbit_task")

    def start_pan(self):
        if self.showbase.mouseWatcherNode.hasMouse():
            mouse_pos = self.showbase.mouseWatcherNode.getMouse()
            self.last_mouse_pos = Point3(mouse_pos.getX(), mouse_pos.getY(), 0)
            self.showbase.taskMgr.add(self.pan_task, "pan_task")

    def stop_task(self, task_name: str):
        self.showbase.taskMgr.remove(task_name)

    def orbit_task(self, task):
        if self.showbase.mouseWatcherNode.hasMouse():
            mouse_pos = self.showbase.mouseWatcherNode.getMouse()
            current_pos = Point3(mouse_pos.getX(), mouse_pos.getY(), 0)
            delta = self.last_mouse_pos - current_pos

            h, p = self.gimbal.getH(), self.gimbal.getP()
            self.gimbal.setH(h + delta.x * 180 * self.orbit_rate)
            self.gimbal.setP(p + delta.y * 180 * self.orbit_rate)

            self.last_mouse_pos = current_pos
        return Task.cont

    def pan_task(self, task):
        if self.showbase.mouseWatcherNode.hasMouse():
            mouse_pos = self.showbase.mouseWatcherNode.getMouse()
            current_pos = Point3(mouse_pos.getX(), mouse_pos.getY(), 0)
            delta = self.last_mouse_pos - current_pos

            # Move the target node, which in turn moves the whole camera rig
            right = self.camera.getQuat(self.showbase.render).getRight()
            up = self.camera.getQuat(self.showbase.render).getUp()

            self.target.setPos(self.target.getPos() + right * delta.x * self.pan_rate)
            self.target.setPos(self.target.getPos() + up * delta.y * self.pan_rate)

            self.last_mouse_pos = current_pos
        return Task.cont