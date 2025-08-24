# ui/building_viewer/building_viewer.py
from __future__ import annotations

import random
from typing import Dict, List
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.building_viewer.viewer_3d_widget import PyVistaViewerWidget
from services.generator_3d_pyvista import BuildingGenerator3D
from domain.building_generator_2d import BuildingGenerator2D
from domain.building_spec import BuildingSpec, FacadeSpec, BuildingDirector, PROCEDURAL_MODULE_WIDTH, PROCEDURAL_MODULE_HEIGHT
from services.resources_loader import IconFiles
from services.stacking_resolver import StackingResolver
from domain.grammar import parse_building_json
from services.building_image_exporter import generate_all_facade_strip_images
from PIL import Image
Blueprint = Dict[str, Dict[int, List[str]]]  # side -> floor_idx -> [module_names]


class BuildingViewerApp(QWidget):
    """
    Reusable QWidget that orchestrates:
      - spec -> blueprint (BuildingDirector),
      - 3D mesh generation (BuildingGenerator3D),
      - optional 2D billboard generation (BuildingGenerator2D),
      - display on a PyVista canvas.
    """

    def __init__(self, *, icon_category: str = "Default", parent: QWidget | None = None):
        super().__init__(parent)

        # 3D viewer stage
        self.viewer = PyVistaViewerWidget()

        # Generators
        self.generator_3d = BuildingGenerator3D()
        icon_set = IconFiles.get_icons_for_category(icon_category)
        if not icon_set:
            raise FileNotFoundError(f"Icon category '{icon_category}' is empty or missing.")
        self.generator_2d = BuildingGenerator2D(icon_set=icon_set)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.viewer)


    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def display_building_kit_of_parts(self, spec: BuildingSpec) -> None:
        """Render a full 3D model using the 'kit of parts' method (one quad per module)."""
        director = BuildingDirector(spec=spec)
        blueprint = director.produce_blueprint()
        self._render_kit_of_parts(blueprint, spec.num_floors)

    def display_building_billboard(self, spec: BuildingSpec) -> None:
        """Render a 3D model where each facade is a single textured billboard."""
        director = BuildingDirector(spec=spec)
        blueprint = director.produce_blueprint()
        self._render_billboard(blueprint, spec.num_floors)

    # Handy demo helpers you can invoke from buttons/menus:
    def generate_building_1_kit(self) -> None:
        spec = BuildingSpec(
            num_floors=2,
            facades={
                "front": FacadeSpec(width=8 * PROCEDURAL_MODULE_WIDTH, grammar="<Wall00>\n[Door00]<Window00>"),
                "right": FacadeSpec(width=12 * PROCEDURAL_MODULE_WIDTH, grammar="<Wall00>\n<Window00>"),
            },
        )
        self.display_building_kit_of_parts(spec)

    def generate_building_1_billboard(self) -> None:
        front_modules = random.randint(5, 12)
        right_modules = random.randint(5, 12)
        spec = BuildingSpec(
            num_floors=random.randint(2, 12),
            facades={
                "front": FacadeSpec(width=front_modules * PROCEDURAL_MODULE_WIDTH, grammar="<Wall00>\n[Door00]<Window00>"),
                "right": FacadeSpec(width=right_modules * PROCEDURAL_MODULE_WIDTH, grammar="<Wall00>\n<Window00>"),
            },
        )
        self.display_building_billboard(spec)

    # ------------------------------------------------------------------ #
    # Internal rendering
    # ------------------------------------------------------------------ #
    def _render_kit_of_parts(self, blueprint: Blueprint, num_floors: int) -> None:
        """Place every module as its own quad + texture."""
        front_bp = blueprint.get("front", {})
        right_bp = blueprint.get("right", {})
        back_bp  = blueprint.get("back", {})
        left_bp  = blueprint.get("left", {})

        front_width_px = max((len(m) for m in front_bp.values()), default=0) * PROCEDURAL_MODULE_WIDTH
        right_width_px = max((len(m) for m in right_bp.values()), default=0) * PROCEDURAL_MODULE_WIDTH
        building_height_px = num_floors * PROCEDURAL_MODULE_HEIGHT

        # Centering: put building footprint center at origin
        center = (-front_width_px / 2, -right_width_px / 2, 0)

        self.viewer.suppress_rendering = True
        try:
            self.viewer.clear_scene()

            # FRONT (facing +Y)
            if front_bp:
                for i, (mesh, tex) in enumerate(self.generator_3d.create_facade(front_bp)):
                    mesh.translate(center, inplace=True)
                    self.viewer.add_managed_actor(f"front_{i}", mesh, tex)

            # RIGHT (rotate +90 around Z, then shift +X)
            if right_bp:
                for i, (mesh, tex) in enumerate(self.generator_3d.create_facade(right_bp)):
                    mesh.rotate_z(90, inplace=True)
                    mesh.translate((front_width_px, 0, 0), inplace=True)
                    mesh.translate(center, inplace=True)
                    self.viewer.add_managed_actor(f"right_{i}", mesh, tex)

            # BACK (rotate 180; shift +X,+Y)
            if back_bp:
                for i, (mesh, tex) in enumerate(self.generator_3d.create_facade(back_bp)):
                    mesh.rotate_z(180, inplace=True)
                    mesh.translate((front_width_px, right_width_px, 0), inplace=True)
                    mesh.translate(center, inplace=True)
                    self.viewer.add_managed_actor(f"back_{i}", mesh, tex)

            # LEFT (rotate -90; shift +Y)
            if left_bp:
                for i, (mesh, tex) in enumerate(self.generator_3d.create_facade(left_bp)):
                    mesh.rotate_z(-90, inplace=True)
                    mesh.translate((0, right_width_px, 0), inplace=True)
                    mesh.translate(center, inplace=True)
                    self.viewer.add_managed_actor(f"left_{i}", mesh, tex)

            # ROOF
            if front_width_px > 0 and right_width_px > 0:
                roof_mesh, roof_tex = self.generator_3d.create_roof(front_width_px, right_width_px)
                roof_mesh.translate((front_width_px / 2, right_width_px / 2, building_height_px), inplace=True)
                roof_mesh.translate(center, inplace=True)
                self.viewer.add_managed_actor("roof", roof_mesh, roof_tex)

        finally:
            self.viewer.suppress_rendering = False

        self.viewer.reset_camera()

    def _render_billboard(self, blueprint: Blueprint, num_floors: int) -> None:
        """Place one billboard per facade from a pre-rendered 2D image."""
        front_bp = blueprint.get("front", {})
        right_bp = blueprint.get("right", {})
        back_bp  = blueprint.get("back", {})
        left_bp  = blueprint.get("left", {})

        front_width_px = max((len(m) for m in front_bp.values()), default=0) * PROCEDURAL_MODULE_WIDTH
        right_width_px = max((len(m) for m in right_bp.values()), default=0) * PROCEDURAL_MODULE_WIDTH
        building_height_px = num_floors * PROCEDURAL_MODULE_HEIGHT

        # Billboard centering differs (because we rotate Y walls outward):
        center = (-front_width_px / 2, right_width_px / 2, 0)

        self.viewer.suppress_rendering = True
        try:
            self.viewer.clear_scene()

            # FRONT
            if front_bp:
                img = self.generator_2d.assemble_full_facade(front_bp)
                mesh, tex = self.generator_3d.create_facade_billboard(img)
                mesh.translate(center, inplace=True)
                self.viewer.add_managed_actor("front_billboard", mesh, tex)

            # RIGHT (rotate -90; shift +X)
            if right_bp:
                img = self.generator_2d.assemble_full_facade(right_bp)
                mesh, tex = self.generator_3d.create_facade_billboard(img)
                mesh.rotate_z(-90, inplace=True)
                mesh.translate((front_width_px, 0, 0), inplace=True)
                mesh.translate(center, inplace=True)

                meta = { "facade": "front"  }


                self.viewer.add_managed_actor("right_billboard", mesh, tex,meta)

            # BACK (rotate 180; shift +X, -Y)
            if back_bp:
                img = self.generator_2d.assemble_full_facade(back_bp)
                mesh, tex = self.generator_3d.create_facade_billboard(img)
                mesh.rotate_z(180, inplace=True)
                mesh.translate((front_width_px, -right_width_px, 0), inplace=True)
                mesh.translate(center, inplace=True)
                self.viewer.add_managed_actor("back_billboard", mesh, tex)

            # LEFT (rotate +90; shift -Y)
            if left_bp:
                img = self.generator_2d.assemble_full_facade(left_bp)
                mesh, tex = self.generator_3d.create_facade_billboard(img)
                mesh.rotate_z(90, inplace=True)
                mesh.translate((0, -right_width_px, 0), inplace=True)
                mesh.translate(center, inplace=True)
                self.viewer.add_managed_actor("left_billboard", mesh, tex)

            # ROOF
            if front_width_px > 0 and right_width_px > 0:
                roof_mesh, roof_tex = self.generator_3d.create_roof(front_width_px, right_width_px)
                roof_mesh.translate((front_width_px / 2, right_width_px / 2, building_height_px), inplace=True)
                roof_mesh.translate(center, inplace=True)
                # Extra align for billboard Y-flip
                roof_mesh.translate((0, -right_width_px, 0), inplace=True)
                self.viewer.add_managed_actor("roof", roof_mesh, roof_tex)

        finally:
            self.viewer.suppress_rendering = False

        self.viewer.reset_camera()

    def _place_single_floor(
            self,
            floor_name: str,
            facade_strip_images: Dict[str, Image.Image],
            building_width: int,
            building_depth: int,
            elevation: int,
            floor_height: int
    ):
        """
        Takes pre-rendered images for a single floor and places them as
        billboards in the 3D scene at a specific elevation.
        """
        print("\n" + "=" * 20 + f" DEBUG: Placing Floor '{floor_name}' " + "=" * 20)
        print(
            f"  - Received building_width: {building_width}, building_depth: {building_depth}, elevation: {elevation}")

        # --- Centering and Pivot Offsets ---
        half_width = building_width / 2
        half_depth = building_depth / 2

        # Try to get the height from the front image, otherwise default to a reasonable value
        # front_image = facade_strip_images.get(f"{floor_name}-front")
        # image_height = front_image.height if front_image else 128  # Use ICON_PIXEL_HEIGHT as fallback
        half_module_height_offset = PROCEDURAL_MODULE_HEIGHT / 2



        print(f"  - Calculated half_width: {half_width}, half_depth: {half_depth}")
        print(f"  - half_module_height_offset: {half_module_height_offset}")

        facade_definitions = {
            "front": {"rot": 180,   "pos": (0, half_depth, elevation), "size": building_width},
            "back":  {"rot": 0, "pos": (0,  -half_depth, elevation), "size": building_width},
            "left":  {"rot": 90,  "pos": (half_width, 0, elevation), "size": building_depth},
            "right": {"rot": -90, "pos": ( -half_width, 0, elevation), "size": building_depth},
        }

        for side_name, side_data in facade_definitions.items():
            print(f"\n--- Processing '{side_name}' facade ---")
            image_key = f"{floor_name}-{side_name}"
            strip_image = facade_strip_images.get(image_key)

            if not strip_image:
                print(f"  - SKIP: Strip image not found for key: '{image_key}'")
                continue

            print(f"  - FOUND strip image for '{image_key}' with size: {strip_image.size}")

            mesh, tex = self.generator_3d.create_procedural_billboard(
                facade_image=strip_image,
                procedural_width=side_data["size"],
                procedural_height=floor_height
            )

            # Create the 3D plane for this strip
            # mesh, tex = self.generator_3d.create_facade_billboard(strip_image)
            print(f"  - Initial mesh bounds (bottom-left pivot at origin): {mesh.bounds}")

            # Apply rotation
            mesh.rotate_z(side_data["rot"], inplace=True)
            print(f"  - Mesh bounds AFTER rotation by {side_data['rot']} deg Z: {mesh.bounds}")

            # Apply centering translation and final elevation
            final_translation = (
                side_data["pos"][0],
                side_data["pos"][1],
                elevation
            )
            print(f"  - Calculated final translation vector: {final_translation}")

            mesh.translate(final_translation, inplace=True)
            print(f"  - FINAL mesh bounds before adding to scene: {mesh.bounds}")

            actor_name = f"{floor_name}_{side_name}"
            self.viewer.add_managed_actor(actor_name, mesh, tex)
            print(f"  - SUCCESS: Added actor '{actor_name}' to the viewer.")

    def display_full_building(
            self,
            floor_definitions_json: str,
            building_width: int,
            building_depth: int,
            total_building_height: int,
            stacking_pattern: str
    ):
        """
        The main entry point for rendering a complete building.
        """
        print("\n" + "=" * 20 + " Assembling Full Building " + "=" * 20)

        # --- FIX #1: Suppress Rendering ---
        self.viewer.suppress_rendering = True
        try:
            # --- Step 1: Resolve the Vertical Stacking Order ---
            floor_data = json.loads(floor_definitions_json)
            pattern_obj = parse_building_json(floor_data)
            floor_map = {floor.name: floor for floor in pattern_obj.floors}

            resolver = StackingResolver(floor_map)
            ordered_floor_names = resolver.resolve(stacking_pattern, total_building_height)
            print(f"  - Resolved floor order: {ordered_floor_names}")

            # --- Step 2: Generate ALL necessary facade strip images ---
            all_strip_images = generate_all_facade_strip_images(
                floor_definitions_json, building_width, building_depth
            )
            print(f"  - Generated {len(all_strip_images)} unique facade strip images.")

            # --- Step 3: Clear the old scene and place new floors ---
            self.viewer.clear_scene()
            current_elevation = 0

            for floor_name in ordered_floor_names:
                floor_def = floor_map.get(floor_name)
                if not floor_def: continue

                print(f"  - Placing floor '{floor_name}' at elevation {current_elevation}cm...")

                # --- FIX #3: Corrected Centering and Placement Logic ---
                half_width = building_width / 2
                half_depth = building_depth / 2

                facade_definitions = {
                    "front": {"rot": 180, "pos": (0, half_depth, 0), "size": building_width},
                    "back": {"rot": 0, "pos": (0, -half_depth, 0), "size": building_width},
                    "left": {"rot": 90, "pos": (half_width, 0, 0), "size": building_depth},
                    "right": {"rot": -90, "pos": (-half_width, 0, 0), "size": building_depth},
                }
                # facade_definitions = {
                #     "front": {"rot": 180, "pos": (0, half_depth, elevation), "size": building_width},
                #     "back": {"rot": 0, "pos": (0, -half_depth, elevation), "size": building_width},
                #     "left": {"rot": 90, "pos": (half_width, 0, elevation), "size": building_depth},
                #     "right": {"rot": -90, "pos": (-half_width, 0, elevation), "size": building_depth},
                # }




                for side_name, side_data in facade_definitions.items():
                    image_key = f"{floor_name}-{side_name}"
                    strip_image = all_strip_images.get(image_key)
                    if not strip_image: continue

                    mesh, tex = self.generator_3d.create_procedural_billboard(
                        facade_image=strip_image,
                        procedural_width=side_data["size"],
                        procedural_height=floor_def.height
                    )

                    # --- FIX #2: Create a Deep Copy for each instance ---
                    mesh_instance = mesh.copy()

                    # Apply rotation and final position
                    mesh_instance.rotate_z(side_data["rot"], inplace=True)
                    # The mesh pivot is now at its bottom-center, so we just add the elevation
                    final_pos = (side_data["pos"][0], side_data["pos"][1], current_elevation)
                    mesh_instance.translate(final_pos, inplace=True)

                    actor_name = f"{floor_name}_{side_name}_{current_elevation}"
                    self.viewer.add_managed_actor(actor_name, mesh_instance, tex)

                current_elevation += floor_def.height

            # --- Step 4: Add the Roof (with corrected centering) ---
            print(f"  - Placing roof at elevation {current_elevation}cm...")
            roof_mesh, roof_tex = self.generator_3d.create_roof(building_width, building_depth)
            roof_mesh.translate((0, 0, current_elevation), inplace=True)  # Center is already (0,0)
            self.viewer.add_managed_actor("roof", roof_mesh, roof_tex)

        except Exception as e:
            print(f"ERROR during full building assembly: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # --- FIX #1: Re-enable Rendering ---
            self.viewer.suppress_rendering = False

        self.viewer.reset_camera()
        print("--- Full Building Assembly Complete ---")