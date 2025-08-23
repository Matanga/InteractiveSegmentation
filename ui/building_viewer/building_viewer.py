# ui/building_viewer/building_viewer.py
from __future__ import annotations

import random
from typing import Dict, List

from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.building_viewer.viewer_3d_widget import PyVistaViewerWidget
from services.generator_3d_pyvista import BuildingGenerator3D
from domain.building_generator_2d import BuildingGenerator2D
from domain.building_spec import BuildingSpec, FacadeSpec, BuildingDirector, PROCEDURAL_MODULE_WIDTH, PROCEDURAL_MODULE_HEIGHT
from services.resources_loader import IconFiles


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
