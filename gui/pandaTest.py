import sys
from panda3d.core import NodePath, LineSegs, AmbientLight, DirectionalLight, Texture, CardMaker, TextureStage
from direct.showbase.ShowBase import ShowBase

# Import our backend system
from building_grammar.design_spec import BuildingSpec, FacadeSpec, BuildingDirector
from gui.resources_loader import IconFiles

from gui.panda_camara import CameraControllerBehaviour
from gui.panda_orbit_camera import OrbitCameraController


MODULE_WIDTH = 128
MODULE_HEIGHT = 128




class Panda3dBuildingGenerator:
    """
    This generator takes a full building blueprint and creates a 3D model.
    """

    def __init__(self, panda_loader):
        self.loader = panda_loader
        self.textures = {}

    def _get_texture(self, module_name: str) -> Texture:
        """Loads a module texture once and caches it."""
        if module_name not in self.textures:
            filepath = IconFiles.get_icons_for_category("Default").get(module_name)
            if not filepath:  # Fallback
                filepath = IconFiles.get_icons_for_category("Default").get("Wall00")
            self.textures[module_name] = self.loader.loadTexture(filepath)
        return self.textures[module_name]

    def _create_flat_facade_node(self, facade_blueprint: dict, side_name: str) -> NodePath:
        """
        Helper method to create a single, flat facade with its origin at its bottom-left.
        """
        facade_node = NodePath(f"facade-{side_name}")
        for floor_idx, modules in facade_blueprint.items():
            for module_idx, module_name in enumerate(modules):
                cm = CardMaker(f"{module_name}-{side_name}-{floor_idx}-{module_idx}")
                cm.setFrame(0, MODULE_WIDTH, 0, MODULE_HEIGHT)
                module_quad = facade_node.attachNewNode(cm.generate())
                module_quad.setTexture(self._get_texture(module_name))
                module_quad.setPos(module_idx * MODULE_WIDTH, 0, floor_idx * MODULE_HEIGHT)
        return facade_node

    def generate_building_nodess(self, blueprint: dict) -> NodePath:
        """
        Creates a single 3D object containing all facades, correctly positioned and rotated.
        """
        building_node = NodePath("building")

        # 1. Create the FRONT facade and determine its width
        front_blueprint = blueprint.get("front", {})
        front_width_px = 0
        if front_blueprint:
            front_node = self._create_flat_facade_node(front_blueprint, "front")
            front_node.reparentTo(building_node)  # Already at (0,0,0) with no rotation
            front_width_px = max(len(m) for m in front_blueprint.values()) * MODULE_WIDTH

        # 2. Create and place the RIGHT facade
        right_blueprint = blueprint.get("right", {})
        if right_blueprint:
            right_node = self._create_flat_facade_node(right_blueprint, "right")
            right_node.setHpr(90, 0, 0)  # Rotate to face right
            right_node.setPos(front_width_px, 0, 0)  # Position at the end of the front wall
            right_node.reparentTo(building_node)

        # You could add logic for 'back' and 'left' facades here in the same way.

        return building_node

    def _create_roof_node(self, width: float, depth: float, height: float) -> NodePath:
        """
        Creates a textured roof quad.
        """
        print(f"INFO: Creating roof with Width={width}, Depth={depth}, at Height={height}")
        cm = CardMaker("roof")
        # Create the roof flat on the XY plane. Its size is the building's footprint.
        cm.setFrame(0, width, 0, depth)
        roof_node = NodePath(cm.generate())

        # Load and apply the roof texture
        roof_texture = self._get_texture("Wall00")
        roof_node.setTexture(roof_texture)

        # This makes the texture repeat (tile) across the roof surface
        # instead of stretching. Adjust the numbers to change the tile density.
        roof_node.setTexScale(TextureStage.getDefault(), width / MODULE_WIDTH, depth / MODULE_WIDTH)

        # Now, rotate and position the entire roof node.
        # Rotate it to be flat (it's created vertically by default).
        roof_node.setHpr(0, -90, 0)  # Pitch it down by 90 degrees
        # Move it to the top of the building.
        roof_node.setPos(0, 0, height)

        return roof_node

    def generate_building_node(self, blueprint: dict) -> NodePath:
        """
        Creates a single 3D object containing all facades, correctly positioned and rotated.
        """
        building_node = NodePath("building")

        # --- 1. Calculate building dimensions from the blueprint ---
        front_bp = blueprint.get("front", {})
        right_bp = blueprint.get("right", {})
        num_floors = max(len(bp) for bp in blueprint.values()) if blueprint else 0

        front_width_px = max(len(m) for m in front_bp.values()) * MODULE_WIDTH if front_bp else 0
        right_width_px = max(len(m) for m in right_bp.values()) * MODULE_WIDTH if right_bp else 0
        building_height_px = num_floors * MODULE_HEIGHT

        # --- 2. Create and Place Facades ---
        # FRONT
        if front_bp:
            front_node = self._create_flat_facade_node(front_bp, "front")
            front_node.reparentTo(building_node)

        # RIGHT
        if right_bp:
            right_node = self._create_flat_facade_node(right_bp, "right")
            right_node.setHpr(90, 0, 0)
            right_node.setPos(front_width_px, 0, 0)
            right_node.reparentTo(building_node)

        # BACK
        back_bp = blueprint.get("back", {})
        if back_bp:
            back_node = self._create_flat_facade_node(back_bp, "back")
            back_node.setHpr(180, 0, 0)
            back_node.setPos(front_width_px, right_width_px, 0)
            back_node.reparentTo(building_node)

        # LEFT
        left_bp = blueprint.get("left", {})
        if left_bp:
            left_node = self._create_flat_facade_node(left_bp, "left")
            left_node.setHpr(-90, 0, 0)
            left_node.setPos(0, right_width_px, 0)
            left_node.reparentTo(building_node)

        # --- 3. Create and Place the Roof ---
        if front_width_px > 0 and right_width_px > 0:
            roof_node = self._create_roof_node(front_width_px, right_width_px, building_height_px)
            roof_node.reparentTo(building_node)

        return building_node


class BuildingViewer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # --- Run backend to generate blueprint (unchanged) ---
        building_spec = BuildingSpec(num_floors=3,
                                     facades={"front": FacadeSpec(width=5 * MODULE_WIDTH, grammar="<Wall00>[Door00]<Window00>"),
                                              "right": FacadeSpec(width=4 * MODULE_WIDTH, grammar="[Window00]<Wall00>")})

        director = BuildingDirector(spec=building_spec)
        full_blueprint = director.produce_blueprint()

        generator = Panda3dBuildingGenerator(self.loader)
        building_model = generator.generate_building_node(full_blueprint)
        building_model.reparentTo(self.render)

        # =======================================================
        # --- SETUP THE NEW ORBIT CAMERA CONTROLLER ---
        # =======================================================

        # 1. Create a target node for the camera to look at.
        #    This node is placed at the geometric center of our building.
        bounds = building_model.getBounds()
        camera_target = self.render.attachNewNode("camera-target")
        camera_target.setPos(bounds.getCenter())

        # 2. Set an initial distance for the camera from the target.
        #    We place the camera itself inside the target node for now.
        #    The handler will then move it out to its orbiting position.
        self.camera.reparentTo(camera_target)
        self.camera.setY(-3 * bounds.getRadius())  # Start at a reasonable distance
        self.camera.lookAt(camera_target)

        # 3. Create an instance of our new controller.
        self.cam_controller = OrbitCameraController(
            showbase=self,
            camera=self.camera,
            target=camera_target
        )
        self.cam_controller.gimbal.setP(-20)  # Set a nice starting pitch



        # --- General scene setup (grid, lighting) ---
        self.create_grid(size=4096, num_units=64).reparentTo(self.render)
        self.setup_lighting()



    def setup_fp_camera(self,model ):
        # =======================================================
        # --- SETUP THE NEW CAMERA CONTROLLER ---
        # =======================================================
        # 1. Remove the old CameraHandler logic completely.
        #    We no longer need a "target" node.

        # 2. Set a good initial camera position before handing control over.
        bounds = model.getBounds()
        center = bounds.getCenter()
        radius = bounds.getRadius()
        self.camera.setPos(center.x, center.y - 2.5 * radius, center.z)
        self.camera.lookAt(center)

        # 3. Create an instance of the new controller and set it up.
        #    We pass `self` as the showbase instance for good practice.
        self.cam_controller = CameraControllerBehaviour(self.camera, showbase=self)

        # Optional: Adjust speed and sensitivity
        self.cam_controller.setVelocity(100)  # Set a faster movement speed
        self.cam_controller.setMouseSensivity(0.01)

        # This is the most important step: activate the controller.
        # Note: The default keys are Z,Q,S,D (French keyboard layout).
        # We can remap them to W,A,S,D for standard English keyboards.
        self.cam_controller.setup(keys={
            'w': "forward",
            's': "backward",
            'a': "left",
            'd': "right",
            'space': "up",
            'lshift': "down"
        })



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


if __name__ == "__main__":
    if not IconFiles.get_icons_for_category("Default"):
        sys.exit("FATAL: Could not find 'Default' icon category.")
    app = BuildingViewer()
    app.run()