import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Set


class DataManager:
    """
    Manages the persistent storage of user assets, including Unreal Data Tables
    and their corresponding mappings, using a central manifest file.
    """

    def __init__(self):
        # --- Define Core Paths ---
        # Note: Assumes this file is in ui/mapping_editor/
        self.project_root = Path(__file__).parent.parent.parent
        self.user_assets_path = self.project_root / "user_assets"
        self.module_dbs_path = self.user_assets_path / "module_dbs"  # Matching your new name
        self.mappings_path = self.user_assets_path / "mappings"
        self.manifest_path = self.user_assets_path / "manifest.json"

        # --- Initialize ---
        self._setup_directories()
        self.manifest: Dict[str, List[Dict[str, Any]]] = self._load_manifest()
        self.module_name_cache: Dict[str, List[str]] = {}

    def _setup_directories(self):
        """Ensures that the required user_assets directory structure exists."""
        self.user_assets_path.mkdir(exist_ok=True)
        self.module_dbs_path.mkdir(exist_ok=True)
        self.mappings_path.mkdir(exist_ok=True)

    def _load_manifest(self) -> Dict[str, List[Dict[str, Any]]]:
        """Loads the manifest file from disk. Returns a default if not found."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Warning: Manifest.json is corrupted. Starting fresh.")
                return {"data_tables": []}
        return {"data_tables": []}

    def _save_manifest(self):
        """Saves the current state of the manifest to disk."""
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=4)

    def add_new_data_table(self, source_path_str: str, display_name: str) -> bool:
        """
        Adds a new Unreal Data Table to the system. This involves copying the
        file into the managed directory and creating a new manifest entry.
        """
        source_path = Path(source_path_str)
        if not source_path.exists():
            print(f"Error: Source file does not exist: {source_path}")
            return False

        base_id = display_name.lower().replace(" ", "_").strip()
        unique_id = base_id
        i = 1
        while any(dt['id'] == unique_id for dt in self.manifest['data_tables']):
            unique_id = f"{base_id}_{i}"
            i += 1

        internal_filename = f"{unique_id}.json"
        internal_path = self.module_dbs_path / internal_filename
        mapping_path = self.mappings_path / f"{unique_id}_mapping.json"

        try:
            shutil.copy(source_path, internal_path)
            new_entry = {
                "id": unique_id, "display_name": display_name,
                "source_path": str(source_path),
                "internal_path": str(internal_path.relative_to(self.project_root)),
                "mapping_file": str(mapping_path.relative_to(self.project_root)),
            }
            self.manifest["data_tables"].append(new_entry)
            self._save_manifest()
            self._load_module_names_from_file(internal_path, unique_id)
            print(f"Successfully added '{display_name}' to the manifest.")
            return True
        except Exception as e:
            print(f"Error during file copy or manifest update: {e}")
            return False

    def _load_module_names_from_file(self, file_path: Path, data_table_id: str):
        """
        Internal helper to parse a data table and cache its module names,
        correctly combining ModuleName and Variation.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Use a set to store the full, combined names to handle duplicates.
            full_module_names: Set[str] = set()
            for item in data:
                # Check if the item is a dictionary and has the required keys
                if isinstance(item, dict) and "ModuleName" in item and "Variation" in item:
                    base_name = item["ModuleName"]
                    variation = item["Variation"]

                    # Construct the full name, e.g., "J_17Wall::3"
                    # We can use zfill(3) to pad with zeros, e.g., "J_17Wall::003"
                    # if that is the desired format. Let's assume simple for now.
                    padded_variation = str(variation).zfill(3)
                    full_name = f"{base_name}::{padded_variation}"

                    full_module_names.add(full_name)

            # Store the sorted list of unique, fully-qualified names
            self.module_name_cache[data_table_id] = sorted(list(full_module_names))

        except Exception as e:
            print(f"Error parsing module names from {file_path}: {e}")
            self.module_name_cache[data_table_id] = []

    def get_data_table_entries(self) -> List[Dict[str, Any]]:
        """Returns the list of all data table entries from the manifest."""
        return self.manifest.get("data_tables", [])

    def get_module_names_for_id(self, data_table_id: str) -> List[str]:
        """Gets module names for a data table, loading them into cache if needed."""
        if data_table_id not in self.module_name_cache:
            entry = next((dt for dt in self.get_data_table_entries() if dt['id'] == data_table_id), None)
            if entry and 'internal_path' in entry:
                internal_path = self.project_root / entry['internal_path']
                self._load_module_names_from_file(internal_path, data_table_id)

        return self.module_name_cache.get(data_table_id, [])

    def get_entry_by_display_name(self, name: str) -> Dict[str, Any] | None:
        """Finds a data table entry in the manifest by its display name."""
        return next((dt for dt in self.get_data_table_entries() if dt['display_name'] == name), None)

    def load_mapping_for_id(self, data_table_id: str) -> Dict[str, str]:
        """
        Loads the mapping dictionary from the JSON file associated with a
        given data table ID.
        """
        entry = next((dt for dt in self.get_data_table_entries() if dt['id'] == data_table_id), None)
        if not entry or 'mapping_file' not in entry:
            return {}

        mapping_path = self.project_root / entry['mapping_file']
        if not mapping_path.exists():
            return {}

        try:
            with open(mapping_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Mapping file is corrupted: {mapping_path}")
            return {}

    def save_mapping_for_id(self, data_table_id: str, mapping_data: Dict[str, str]):
        """
        Saves the provided mapping dictionary to the JSON file associated
        with a given data table ID.
        """
        entry = next((dt for dt in self.get_data_table_entries() if dt['id'] == data_table_id), None)
        if not entry or 'mapping_file' not in entry:
            print(f"Error: Could not find manifest entry for ID '{data_table_id}' to save mapping.")
            return

        mapping_path = self.project_root / entry['mapping_file']
        try:
            with open(mapping_path, 'w') as f:
                json.dump(mapping_data, f, indent=4)
            print(f"Successfully saved mapping to {mapping_path}")
        except Exception as e:
            print(f"Error saving mapping file: {e}")