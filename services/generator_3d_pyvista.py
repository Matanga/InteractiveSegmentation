import pyvista
from typing import Dict, List, Tuple

from services.resources_loader import IconFiles

from PIL import Image
import  numpy as np
from domain.building_spec import ICON_PIXEL_WIDTH,ICON_PIXEL_HEIGHT

class BuildingGenerator3D:
    """
    This class converts abstract building blueprints into 3D PyVista mesh objects.
    """

    def __init__(self):
        self.textures: Dict[str, pyvista.Texture] = {}

    def _get_texture( self, module_name: str, category: str = "Default", fallback_module: str = "Wall00" ) -> pyvista.Texture:
        if module_name in self.textures:
            return self.textures[module_name]

        icon_set = IconFiles.get_icons_for_category(category)
        filepath = icon_set.get(module_name) or icon_set.get(fallback_module)

        if not filepath:
            raise FileNotFoundError(
                f"No texture found for module '{module_name}' "
                f"in category '{category}' and no fallback '{fallback_module}' available."
            )

        texture = pyvista.Texture(str(filepath))
        self.textures[module_name] = texture
        return texture

    def create_module_mesh(self, module_name: str) -> pyvista.DataSet:
        """
        Creates a single, vertical, untextured 3D quad for a given module.
        It creates a simple horizontal plane and rotates it into position.
        """
        # 1. Create a simple horizontal plane at the origin.
        #    Its texture coordinates are generated correctly by default in this orientation.
        mesh = pyvista.Plane(
            center=(0, 0, 0),
            i_size=ICON_PIXEL_WIDTH,
            j_size=ICON_PIXEL_HEIGHT,
        )

        # 2. Rotate the entire mesh -90 degrees around the X-axis to make it stand up.
        mesh.rotate_x(90, inplace=True)

        # 3. Translate the now-vertical mesh up so its bottom edge is on the Z=0 plane.
        mesh.translate((ICON_PIXEL_WIDTH / 2, 0, ICON_PIXEL_HEIGHT / 2), inplace=True)

        return mesh

    def create_facade(self, facade_blueprint: dict) -> List[Tuple[pyvista.DataSet, pyvista.Texture]]:
        """
        Assembles a full, flat facade from a blueprint.

        Returns:
            A list of tuples, where each tuple contains a mesh and its
            corresponding texture, ready to be added to a plotter.
        """
        facade_components = []
        for floor_idx, modules in facade_blueprint.items():
            for module_idx, module_name in enumerate(modules):
                # 1. Create the basic module geometry (centered at origin)
                module_mesh = self.create_module_mesh(module_name)

                # 2. Calculate its final position in the facade
                x_pos = module_idx * ICON_PIXEL_WIDTH
                y_pos = 0
                z_pos = floor_idx * ICON_PIXEL_HEIGHT

                module_mesh.translate((x_pos, y_pos, z_pos), inplace=True)

                # 4. Get the corresponding texture
                texture = self._get_texture(module_name)

                facade_components.append((module_mesh, texture))

        return facade_components

    def create_roof(self, width: float, depth: float) -> Tuple[pyvista.DataSet, pyvista.Texture]:
        """
        Creates a single, flat roof mesh and its texture.

        Args:
            width: The width of the roof (along the X-axis).
            depth: The depth of the roof (along the Y-axis).

        Returns:
            A tuple containing the roof mesh and the 'Wall00' texture.
        """
        # 1. Create a horizontal plane for the roof's geometry.
        #    It's created at the origin; we will move it into place later.
        roof_mesh = pyvista.Plane(
            center=(0, 0, 0),
            i_size=width,
            j_size=depth,
        )

        # 2. Get the default 'Wall00' texture.
        roof_texture = self._get_texture("Wall00")


        return roof_mesh, roof_texture

    def create_facade_billboard(self, facade_image: Image.Image) -> Tuple[pyvista.DataSet, pyvista.Texture]:
        """
        Creates a single 3D plane (a billboard) from a pre-rendered facade image.
        """
        # 1. Create the 3D plane with the same dimensions as the image.
        width, height = facade_image.size
        mesh = pyvista.Plane(
            center=(0, 0, 0),
            i_size=width,
            j_size=height,
        )
        mesh.rotate_x(-90, inplace=True)
        mesh.translate((width / 2, 0, height / 2), inplace=True) # Set pivot to bottom-left

        image_as_array = np.flipud(np.array(facade_image))

        # 2. Create a PyVista Texture directly from the PIL Image object.
        texture = pyvista.Texture(image_as_array)

        return mesh, texture

    def create_procedural_billboard(self, facade_image: Image.Image, procedural_width: int, procedural_height: int) -> \
    Tuple[pyvista.DataSet, pyvista.Texture]:
        """
        Creates a single 3D plane (billboard) of a specific PROCEDURAL size,
        textures it with the given image, and sets its pivot to the BOTTOM-CENTER.
        """
        # 1. Create the 3D plane using the provided PROCEDURAL dimensions.
        mesh = pyvista.Plane(
            center=(0, 0, 0),
            i_size=procedural_width,
            j_size=procedural_height,
        )

        # 2. Rotate to be vertical.
        mesh.rotate_x(90, inplace=True)
        mesh.rotate_y(180, inplace=True)

        # 3. Translate so its BOTTOM-CENTER is at the origin (0,0,0).
        mesh.translate((0, 0, procedural_height / 2), inplace=True)

        # 4. Create the texture from the image (this part is the same).
        image_as_array = np.flipud(np.array(facade_image))
        texture = pyvista.Texture(image_as_array)

        return mesh, texture