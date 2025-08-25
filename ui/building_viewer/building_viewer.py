# ui/building_viewer/building_viewer.py
from __future__ import annotations

import random
from typing import Dict, List
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout

from services.ui_adapter import prepare_spec_from_ui
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
            floor_def: "Floor",
            blueprint: Dict[str, Dict[int, List[str]]],
            all_strip_images: Dict[str, Image.Image],
            building_width: int,
            building_depth: int,
            elevation: int
    ):
        """
        Takes all necessary data for a single floor and places its billboards
        in the 3D scene, attaching detailed metadata to each one.
        """
        half_width = building_width / 2
        half_depth = building_depth / 2

        facade_definitions = {
            "front": {"rot": 180, "pos": (0, half_depth, 0), "size": building_width},
            "back": {"rot": 0, "pos": (0, -half_depth, 0), "size": building_width},
            "right": {"rot": -90, "pos": (-half_width, 0, 0), "size": building_depth},
            "left": {"rot": 90, "pos": (half_width, 0, 0), "size": building_depth},
        }

        for side_name, side_data in facade_definitions.items():
            image_key = f"{floor_name}-{side_name}"
            strip_image = all_strip_images.get(image_key)
            if not strip_image: continue

            mesh, tex = self.generator_3d.create_procedural_billboard(
                facade_image=strip_image,
                procedural_width=side_data["size"],
                procedural_height=floor_def.height
            )
            mesh_instance = mesh.copy()
            mesh_instance.rotate_z(side_data["rot"], inplace=True)
            final_pos = (side_data["pos"][0], side_data["pos"][1], elevation)
            mesh_instance.translate(final_pos, inplace=True)

            # --- CONSTRUCT AND ADD METADATA ---
            # Find the correct floor index from the blueprint for this floor name
            # This is a bit complex, but finds the first matching floor index
            grammar_string = "".join([g.to_string() for g in floor_def.facades.get(side_name, [])])
            floor_idx = next((idx for idx, name in floor_names_map.items() if name == floor_name), -1)

            meta = {
                "type": "facade_panel",
                "floor_name": floor_name,
                "side": side_name,
                "elevation": elevation,
                "grammar": grammar_string,  # Use the clean string here
                "resolved_modules": blueprint.get(side_name, {}).get(floor_idx, [])
            }

            actor_name = f"{floor_name}_{side_name}_{elevation}"
            self.viewer.add_managed_actor(actor_name, mesh_instance, tex, meta=meta)

    def display_full_building(
            self,
            floor_definitions_json: str,
            building_width: int,
            building_depth: int,
            total_building_height: int,
            stacking_pattern: str
    ):
        """
        The main entry point for rendering a complete building. It orchestrates
        the process and calls the helper method to place each floor.
        """
        print("\n" + "=" * 20 + " Assembling Full Building " + "=" * 20)
        self.viewer.suppress_rendering = True
        try:
            # --- Step 1: Resolve all data ---
            floor_data = json.loads(floor_definitions_json)
            pattern_obj = parse_building_json(floor_data)
            floor_map = {floor.name: floor for floor in pattern_obj.floors}

            global floor_names_map  # Make this available to the helper function
            num_floors = len(floor_data)
            floor_names_map = {(num_floors - 1 - i): floor['Name'] for i, floor in enumerate(floor_data)}

            resolver = StackingResolver(floor_map)
            ordered_floor_names = resolver.resolve(stacking_pattern, total_building_height)

            all_strip_images = generate_all_facade_strip_images(floor_definitions_json, building_width, building_depth)

            spec = prepare_spec_from_ui(floor_definitions_json, building_width, building_depth)
            director = BuildingDirector(spec)
            blueprint = director.produce_blueprint()

            # --- Step 2: Clear scene and build iteratively ---
            self.viewer.clear_scene()
            current_elevation = 0
            for floor_name in ordered_floor_names:
                floor_def = floor_map.get(floor_name)
                if not floor_def: continue

                # --- CALL THE HELPER METHOD ---
                self._place_single_floor(
                    floor_name=floor_name,
                    floor_def=floor_def,
                    blueprint=blueprint,
                    all_strip_images=all_strip_images,
                    building_width=building_width,
                    building_depth=building_depth,
                    elevation=current_elevation
                )
                current_elevation += floor_def.height

            # --- Step 3: Add the Roof ---
            roof_mesh, roof_tex = self.generator_3d.create_roof(building_width, building_depth)
            roof_mesh.translate((0, 0, current_elevation), inplace=True)
            self.viewer.add_managed_actor("roof", roof_mesh, roof_tex)

        except Exception as e:
            print(f"ERROR during full building assembly: {e}");
            import traceback;
            traceback.print_exc()
        finally:
            self.viewer.suppress_rendering = False

        self.viewer.reset_camera()
        print("--- Full Building Assembly Complete ---")