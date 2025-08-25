import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Set


class AssetManager:
    """
    Manages the persistent storage of all user assets, including Unreal Data
    Tables, Floor Sets, and their mappings, using a central manifest file.
    """

    def __init__(self):
        # --- Define Core Paths ---
        self.project_root = Path(__file__).parent.parent.parent
        self.user_assets_path = self.project_root / "user_assets"
        self.data_tables_path = self.user_assets_path / "module_dbs"
        self.mappings_path = self.user_assets_path / "mappings"
        self.floor_sets_path = self.user_assets_path / "floor_sets"  # New
        self.manifest_path = self.user_assets_path / "manifest.json"

        # --- Initialize ---
        self._setup_directories()
        self.manifest = self._load_manifest()
        self.module_name_cache: Dict[str, List[str]] = {}

    def _setup_directories(self):
        """Ensures that the required user_assets directory structure exists."""
        for path in [self.user_assets_path, self.data_tables_path, self.mappings_path, self.floor_sets_path]:
            path.mkdir(exist_ok=True)

    def _load_manifest(self) -> Dict[str, List[Dict[str, Any]]]:
        """Loads the manifest file. Returns a default structure if not found or corrupted."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    data = json.load(f)
                    # Ensure both keys exist for compatibility with older versions
                    if "data_tables" not in data: data["data_tables"] = []
                    if "floor_sets" not in data: data["floor_sets"] = []
                    return data
            except (json.JSONDecodeError, TypeError):
                print("Warning: manifest.json is corrupted. Starting fresh.")
        return {"data_tables": [], "floor_sets": []}

    def _save_manifest(self):
        """Saves the current state of the manifest to disk."""
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=4)

    # --- Data Table Methods (Largely unchanged) ---
    def add_new_data_table(self, source_path_str: str, display_name: str) -> bool:
        # ... (This method is correct and does not need to be changed) ...
        source_path = Path(source_path_str)
        if not source_path.exists(): return False
        base_id = display_name.lower().replace(" ", "_").strip()
        unique_id = base_id
        i = 1
        while any(dt['id'] == unique_id for dt in self.manifest['data_tables']):
            unique_id = f"{base_id}_{i}"
            i += 1
        internal_path = self.data_tables_path / f"{unique_id}.json"
        mapping_path = self.mappings_path / f"{unique_id}_mapping.json"
        try:
            shutil.copy(source_path, internal_path)
            new_entry = {
                "id": unique_id, "display_name": display_name, "source_path": str(source_path),
                "internal_path": str(internal_path.relative_to(self.project_root)),
                "mapping_file": str(mapping_path.relative_to(self.project_root)),
            }
            self.manifest["data_tables"].append(new_entry)
            self._save_manifest()
            self._load_module_names_from_file(internal_path, unique_id)
            return True
        except Exception as e:
            print(f"Error adding data table: {e}")
            return False

    def save_new_floor_set(
            self,
            display_name: str,
            floor_data: List[Dict[str, Any]],
            linked_data_table_id: str | None = None,
            description: str = ""
    ) -> bool:
        """
        Saves a new floor set to a file, adds its metadata to the manifest,
        and saves the manifest.
        """
        # 1. Create a unique ID for the new floor set
        base_id = display_name.lower().replace(" ", "_").strip()
        unique_id = base_id
        i = 1
        # Ensure the ID is unique within the floor_sets list
        while any(fs.get('id') == unique_id for fs in self.manifest.get('floor_sets', [])):
            unique_id = f"{base_id}_{i}"
            i += 1

        # 2. Define the file path and save the floor data
        file_path = self.floor_sets_path / f"{unique_id}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(floor_data, f, indent=4)
        except Exception as e:
            print(f"Error: Failed to save floor set file at {file_path}. Reason: {e}")
            return False

        # 3. Create the new entry for the manifest
        new_entry = {
            "id": unique_id,
            "display_name": display_name,
            "file_path": str(file_path.relative_to(self.project_root)),
            "description": description,
            "linked_data_table_id": linked_data_table_id
        }

        # 4. Add the new entry and save the manifest
        self.manifest["floor_sets"].append(new_entry)
        self._save_manifest()

        print(f"Successfully saved new floor set '{display_name}' and updated manifest.")
        return True

    def get_data_table_entries(self) -> List[Dict[str, Any]]:
        return self.manifest.get("data_tables", [])

    def get_module_names_for_id(self, data_table_id: str) -> List[str]:
        if data_table_id not in self.module_name_cache:
            entry = next((dt for dt in self.get_data_table_entries() if dt['id'] == data_table_id), None)
            if entry and 'internal_path' in entry:
                internal_path = self.project_root / entry['internal_path']
                self._load_module_names_from_file(internal_path, data_table_id)
        return self.module_name_cache.get(data_table_id, [])

    def _load_module_names_from_file(self, file_path: Path, data_table_id: str):
        # ... (This method is correct and does not need to be changed) ...
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            full_module_names: Set[str] = set()
            for item in data:
                if isinstance(item, dict) and "ModuleName" in item and "Variation" in item:
                    base_name = item["ModuleName"];
                    variation = item["Variation"]
                    full_module_names.add(f"{base_name}::{str(variation).zfill(3)}")
            self.module_name_cache[data_table_id] = sorted(list(full_module_names))
        except Exception as e:
            print(f"Error parsing module names from {file_path}: {e}")
            self.module_name_cache[data_table_id] = []

    def load_mapping_for_id(self, data_table_id: str) -> Dict[str, str]:
        # ... (This method is correct and does not need to be changed) ...
        entry = next((dt for dt in self.get_data_table_entries() if dt['id'] == data_table_id), None)
        if not entry: return {}
        mapping_path = self.project_root / entry['mapping_file']
        if not mapping_path.exists(): return {}
        try:
            with open(mapping_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_mapping_for_id(self, data_table_id: str, mapping_data: Dict[str, str]):
        # ... (This method is correct and does not need to be changed) ...
        entry = next((dt for dt in self.get_data_table_entries() if dt['id'] == data_table_id), None)
        if not entry: return
        mapping_path = self.project_root / entry['mapping_file']
        with open(mapping_path, 'w') as f: json.dump(mapping_data, f, indent=4)

    def get_entry_by_display_name(self, name: str) -> Dict[str, Any] | None:
        """Finds a data table entry in the manifest by its display name."""
        return next((dt for dt in self.get_data_table_entries() if dt.get('display_name') == name), None)

    # --- NEW: Floor Set Methods ---

    def get_floor_set_entries(self) -> List[Dict[str, Any]]:
        """Returns the list of all floor set entries from the manifest."""
        return self.manifest.get("floor_sets", [])

    def load_floor_set_data(self, floor_set_id: str) -> List[Dict[str, Any]] | None:
        """Loads the floor definition data from a floor set's JSON file."""
        entry = next((fs for fs in self.get_floor_set_entries() if fs['id'] == floor_set_id), None)
        if not entry: return None

        file_path = self.project_root / entry['file_path']
        if not file_path.exists():
            print(f"Error: Floor set file not found at {file_path}")
            return None

        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Floor set file is corrupted: {file_path}")
            return None