from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QListWidget, QPushButton, QInputDialog, QMessageBox, QListWidgetItem
)
from PySide6.QtCore import Slot, Qt, Signal

# We will need to talk to the asset manager
from ui.mapping_editor.mapping_data_manager import AssetManager


class FloorLibraryPanel(QWidget):
    # --- NEW: Define signals to communicate with the main editor panel ---
    # Signal to request the current floor data from PatternArea for saving
    request_current_floors = Signal(object)  # The object will be a callback
    # Signal to load new floor data into the PatternArea
    load_floors_requested = Signal(list)

    def __init__(self, asset_manager: AssetManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.asset_manager = asset_manager

        # --- UI Elements ---
        self.floor_set_list = QListWidget()
        self.load_button = QPushButton("Load")
        self.save_as_button = QPushButton("Save As...")
        self.export_button = QPushButton("Export...")  # Not yet connected

        self.load_button.setToolTip("Load the selected floor set into the Pattern Canvas")
        self.save_as_button.setToolTip("Save the current floors in the Pattern Canvas as a new set")
        self.export_button.setToolTip("Export the selected floor set using a chosen module mapping")

        # --- Layout ---
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_as_button)
        button_layout.addWidget(self.export_button)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.floor_set_list, 1)
        root_layout.addLayout(button_layout)

        # --- Connect Signals ---
        self.load_button.clicked.connect(self._on_load_clicked)
        self.save_as_button.clicked.connect(self._on_save_as_clicked)

        # --- Initial Population ---
        self._populate_floor_set_list()

    def _populate_floor_set_list(self):
        """
        Populates the list of saved floor sets by reading the data from the
        AssetManager's manifest.
        """
        self.floor_set_list.clear()

        # 1. Add the special "Default" entry first. This is a virtual entry
        #    and doesn't exist in the user's manifest.
        default_item = QListWidgetItem("Default Floors (Built-in)")
        default_item.setData(Qt.UserRole, "default")
        self.floor_set_list.addItem(default_item)

        # 2. Get the list of all user-saved floor set entries from the AssetManager.
        for entry in self.asset_manager.get_floor_set_entries():
            # 3. For each entry, create a new list item.
            item = QListWidgetItem(entry['display_name'])
            # Store its unique ID in the item's data role for later retrieval.
            item.setData(Qt.UserRole, entry['id'])
            self.floor_set_list.addItem(item)

    @Slot()
    def _on_load_clicked(self):
        """Handles loading the selected floor set."""
        current_item = self.floor_set_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a floor set to load.")
            return

        floor_set_id = current_item.data(Qt.UserRole)

        if floor_set_id == "default":
            # Special case for loading the built-in default
            default_path = self.asset_manager.user_assets_path / "floor_sets" / "default_floors.json"
            if default_path.exists():
                with open(default_path, 'r') as f:
                    import json
                    floor_data = json.load(f)
                    self.load_floors_requested.emit(floor_data)
            else:
                QMessageBox.critical(self, "Error", "default_floors.json not found!")
            return

        # Regular case for user-saved sets
        floor_data = self.asset_manager.load_floor_set_data(floor_set_id)
        if floor_data:
            # Here we would do the reverse mapping in the future
            self.load_floors_requested.emit(floor_data)
        else:
            QMessageBox.critical(self, "Error", "Failed to load floor set data.")

    @Slot()
    def _on_save_as_clicked(self):
        """
        Starts the workflow to save the currently designed floors as a new set.
        It emits a signal to request the data from the PatternArea.
        """
        # The first step remains the same: ask the parent for the current data.
        self.request_current_floors.emit(self.receive_current_floors_for_saving)

    def receive_current_floors_for_saving(self, current_floors_data: list):
        """
        This is the callback that receives the floor data from the main panel
        and proceeds with the full, persistent saving workflow.
        """
        if not current_floors_data:
            QMessageBox.warning(self, "No Data", "There are no floors in the canvas to save.")
            return

        # 1. Ask for a display name for the new floor set.
        display_name, ok = QInputDialog.getText(self, "Save Floor Set", "Enter a name for this new floor set:")
        if not ok or not display_name.strip():
            return

        # TODO: In the future, we will also need to ask which Data Table this
        # floor set should be linked to. For now, we will save it as unlinked.
        linked_data_table_id = None

        # --- THIS IS THE FIX ---
        # 2. Use the AssetManager to perform the complete save operation.
        #    This will save the file AND update the manifest.
        success = self.asset_manager.save_new_floor_set(
            display_name=display_name.strip(),
            floor_data=current_floors_data,
            linked_data_table_id=linked_data_table_id
        )
        # --- END OF FIX ---

        # 3. If the save was successful, refresh the UI list.
        if success:
            QMessageBox.information(self, "Success", f"Floor set '{display_name}' saved successfully.")
            self._populate_floor_set_list() # This will now find the new entry in the manifest.
        else:
            QMessageBox.critical(self, "Error", "An error occurred while saving the floor set.")