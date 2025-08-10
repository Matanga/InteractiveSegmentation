# d_viewer.py - A standalone 3D pattern visualizer

import sys
from pathlib import Path

# --- Your existing parser is needed.
# For this standalone test, we will create a mock version.
# In the final app, you would import your real 'building_grammar' parser.
# --- MOCK PARSER START ---
from dataclasses import dataclass, field
from typing import List
import re


@dataclass
class Module:
    name: str


@dataclass
class Group:
    modules: List[Module] = field(default_factory=list)


@dataclass
class Floor:
    groups: List[Group] = field(default_factory=list)


@dataclass
class Model:
    floors: List[Floor] = field(default_factory=list)


def parse(pattern_str: str) -> Model:
    model = Model()
    for line in pattern_str.strip().split('\n'):
        floor = Floor()
        # Simple regex to find <...> or [...] groups
        for group_match in re.finditer(r"[<\[](.*?)?[>\]]", line):
            group = Group()
            content = group_match.group(1)
            if content:
                for module_name in content.split('-'):
                    group.modules.append(Module(name=module_name.strip()))
            floor.groups.append(group)
        model.floors.append(floor)
    return model


# --- MOCK PARSER END ---


from PySide6.QtCore import QSize
from PySide6.QtGui import QVector3D, QColor, QQuaternion, QMatrix4x4
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DRender import Qt3DRender
from PySide6.Qt3DExtras import Qt3DExtras

# ===================================================================
# 1. SETTINGS AND TEST DATA
# ===================================================================

# --- Building Dimensions ---
# These are the inputs your final function will take.
BUILDING_WIDTH_IN_MODULES = 8
BUILDING_DEPTH_IN_MODULES = 6
PATTERN_STRING = """
[Wall00-Wall00-Window01-Window01-Window01-Window01-Wall00-Wall00]
[Wall00-Door00-Door00-Wall00-Wall00-Door00-Door00-Wall00]
<Window00-Window00-Window00-Window00-Window00-Window00-Window00-Window00>
"""

# --- Module and Texture Settings ---
MODULE_WIDTH = 2.0  # meters
MODULE_HEIGHT = 3.0  # meters

# Assumes the same folder structure as our main app.
RESOURCES_PATH = Path(__file__).parent.parent / "resources"/"Default"


# ===================================================================
# 2. THE SCENE BUILDER (The core logic)
# ===================================================================

class SceneBuilder:
    """Parses a pattern and generates a 3D building from planes."""

    def __init__(self, root_entity: Qt3DCore.QEntity):
        self.root_entity = root_entity
        self.texture_cache = {}
        self.material_cache = {}

    def _get_material(self, module_name: str) -> Qt3DRender.QMaterial:
        """Creates or retrieves a cached textured material."""
        if module_name in self.material_cache:
            return self.material_cache[module_name]

        found_paths = list(RESOURCES_PATH.glob(f"**/{module_name}.png"))

        if not found_paths:
            print(f"Warning: Texture for '{module_name}' not found. Using color.")
            color_material = Qt3DExtras.QPhongMaterial()
            color_material.setDiffuse(QColor.fromRgbF(0.3, 0.3, 0.35))
            self.material_cache[f"color_fallback_{module_name}"] = color_material
            return color_material

        # --- This is the corrected texture loading process ---
        material = Qt3DExtras.QTextureMaterial()
        texture2D = Qt3DRender.QTexture2D()
        texture_image = Qt3DRender.QTextureImage()

        # <<< FIX: Convert the pathlib.Path object to a string before passing it.
        texture_image.setSource(str(found_paths[0]))

        texture2D.addTextureImage(texture_image)
        material.setTexture(texture2D)

        self.material_cache[module_name] = material
        return material

    def build_building(self, pattern_str: str, width_mods: int, depth_mods: int):
        """The main entry point to construct the entire building."""
        model = parse(pattern_str)
        num_floors = len(model.floors)

        building_width = width_mods * MODULE_WIDTH
        building_depth = depth_mods * MODULE_WIDTH

        # --- Create each of the four faces ---
        # Front Face (+Z direction)
        front_transform = Qt3DCore.QTransform()
        self._create_face(model.floors, width_mods, "front", front_transform)

        # Back Face (-Z direction, rotated 180 deg)
        back_transform = Qt3DCore.QTransform()
        back_transform.setTranslation(QVector3D(building_width, 0, building_depth))
        back_transform.setRotationY(180)
        self._create_face(model.floors, width_mods, "back", back_transform)

        # Left Face (-X direction, rotated 90 deg)
        left_transform = Qt3DCore.QTransform()
        left_transform.setTranslation(QVector3D(0, 0, building_depth))
        left_transform.setRotationY(90)
        self._create_face(model.floors, depth_mods, "left", left_transform)

        # Right Face (+X direction, rotated -90 deg)
        right_transform = Qt3DCore.QTransform()
        right_transform.setTranslation(QVector3D(building_width, 0, 0))
        right_transform.setRotationY(-90)
        self._create_face(model.floors, depth_mods, "right", right_transform)

    def _create_face(self, floors: list, num_modules_on_face: int, name: str, transform: Qt3DCore.QTransform):
        """Creates all the planes for a single face of the building."""
        face_entity = Qt3DCore.QEntity(self.root_entity)
        face_entity.addComponent(transform)

        for floor_idx, floor_data in enumerate(floors):
            x_offset = 0
            # Flatten all modules on this floor into a single list
            all_modules = [mod for group in floor_data.groups for mod in group.modules]

            for module_idx in range(num_modules_on_face):
                module_name = "Wall00"  # Default to a wall
                if module_idx < len(all_modules):
                    module_name = all_modules[module_idx].name

                # Create a plane for this module
                plane_entity = Qt3DCore.QEntity(face_entity)
                plane_mesh = Qt3DExtras.QPlaneMesh()
                plane_mesh.setWidth(MODULE_WIDTH)
                plane_mesh.setHeight(MODULE_HEIGHT)

                plane_transform = Qt3DCore.QTransform()
                # Position the plane correctly on the face
                plane_transform.setTranslation(QVector3D(
                    x_offset + MODULE_WIDTH / 2,
                    floor_idx * MODULE_HEIGHT + MODULE_HEIGHT / 2,
                    0  # Z is handled by the parent face's transform
                ))

                plane_entity.addComponent(plane_mesh)
                plane_entity.addComponent(plane_transform)
                plane_entity.addComponent(self._get_material(module_name))

                x_offset += MODULE_WIDTH


# ===================================================================
# 3. MAIN WINDOW AND APPLICATION SETUP
# ===================================================================

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Standalone 3D Pattern Viewer")
        self.resize(1200, 800)

        # --- Create the 3D View ---
        self.view = Qt3DExtras.Qt3DWindow()
        container = QWidget.createWindowContainer(self.view)
        self.setCentralWidget(container)

        # --- Scene Setup ---
        self.root_entity = Qt3DCore.QEntity()

        # Camera
        camera = self.view.camera()
        camera.setPosition(QVector3D(40, 20, 30))
        camera.setViewCenter(QVector3D(0, 5, 0))

        # Camera Controller (for orbit, zoom, pan)
        cam_controller = Qt3DExtras.QOrbitCameraController(self.root_entity)
        cam_controller.setLinearSpeed(50.0)
        cam_controller.setLookSpeed(180.0)
        cam_controller.setCamera(camera)

        # Light
        light_entity = Qt3DCore.QEntity(self.root_entity)
        light = Qt3DRender.QPointLight(light_entity)
        light.setColor(QColor("white"))
        light.setIntensity(1)
        light_entity.addComponent(light)
        light_transform = Qt3DCore.QTransform(light_entity)
        light_transform.setTranslation(QVector3D(20, 40, 30))
        light_entity.addComponent(light_transform)

        # --- Build the Scene ---
        builder = SceneBuilder(self.root_entity)
        builder.build_building(
            PATTERN_STRING,
            BUILDING_WIDTH_IN_MODULES,
            BUILDING_DEPTH_IN_MODULES
        )

        # Set the scene
        self.view.setRootEntity(self.root_entity)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())