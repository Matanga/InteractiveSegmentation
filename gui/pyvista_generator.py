import pyvista
from typing import Dict, List, Tuple

from gui.resources_loader import IconFiles

MODULE_WIDTH=128
MODULE_HEIGHT=128

class PyVistaBuildingGenerator:
    """
    This class converts abstract building blueprints into 3D PyVista mesh objects.
    """

    def __init__(self):
        self.textures: Dict[str, pyvista.Texture] = {}

    def _get_texture(self, module_name: str) -> pyvista.Texture:
        """Loads a texture image from a file once and caches it."""
        if module_name not in self.textures:
            filepath = IconFiles.get_icons_for_category("Default").get(module_name)
            if not filepath:
                filepath = IconFiles.get_icons_for_category("Default").get("Wall00")
            self.textures[module_name] = pyvista.Texture(str(filepath))
        return self.textures[module_name]


    def create_module_mesh(self, module_name: str) -> pyvista.DataSet:
        """
        Creates a single, vertical, untextured 3D quad for a given module.
        It creates a simple horizontal plane and rotates it into position.
        """
        # 1. Create a simple horizontal plane at the origin.
        #    Its texture coordinates are generated correctly by default in this orientation.
        mesh = pyvista.Plane(
            center=(0, 0, 0),
            i_size=MODULE_WIDTH,
            j_size=MODULE_HEIGHT,
        )

        # 2. Rotate the entire mesh -90 degrees around the X-axis to make it stand up.
        mesh.rotate_x(90, inplace=True)

        # 3. Translate the now-vertical mesh up so its bottom edge is on the Z=0 plane.
        mesh.translate((MODULE_WIDTH / 2, 0, MODULE_HEIGHT / 2), inplace=True)

        return mesh



    # =====================================================================
    # --- NEW METHOD FOR STEP 2 ---
    # =====================================================================
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
                x_pos = module_idx * MODULE_WIDTH
                y_pos = 0
                z_pos = floor_idx * MODULE_HEIGHT

                module_mesh.translate((x_pos, y_pos, z_pos), inplace=True)

                # 4. Get the corresponding texture
                texture = self._get_texture(module_name)

                facade_components.append((module_mesh, texture))

        return facade_components