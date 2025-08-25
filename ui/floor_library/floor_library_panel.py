from __future__ import annotations

from PyQt5.QtWidgets import QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QPushButton, QInputDialog,
    QMessageBox, QListWidgetItem, QHBoxLayout, QToolBar
)
from PySide6.QtCore import Slot, Qt, Signal

from ui.mapping_editor.mapping_data_manager import AssetManager
from ui.actions import create_library_context_menu


class FloorLibraryPanel(QWidget):
    # --- Simplified Signals ---
    new_requested = Signal()
    save_as_requested = Signal()
    save_requested = Signal()
    load_requested = Signal(str)
    export_requested = Signal(str)

    def __init__(self, asset_manager: AssetManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.asset_manager = asset_manager

        # --- UI Elements ---
        self.floor_set_list = QListWidget()
        toolbar = QToolBar();
        toolbar.setMovable(False)
        self.new_action = toolbar.addAction("New")
        self.save_as_action = toolbar.addAction("Save As...")
        self.new_action.setToolTip("Create a new, blank floor set.")
        self.save_as_action.setToolTip("Save the current floors as a new set.")

        # --- Layout ---
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0);
        root_layout.setSpacing(2)
        root_layout.addWidget(toolbar)
        root_layout.addWidget(self.floor_set_list, 1)

        # --- Connect Signals ---
        self.new_action.triggered.connect(self.new_requested.emit)
        self.save_as_action.triggered.connect(self.save_as_requested.emit)

        self.floor_set_list.itemDoubleClicked.connect(self._on_load_clicked)
        self.floor_set_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.floor_set_list.customContextMenuRequested.connect(self._show_context_menu)

        self._populate_floor_set_list()

    def _populate_floor_set_list(self):
        """Populates the list of saved floor sets from the manifest."""
        self.floor_set_list.clear()
        default_item = QListWidgetItem("Default Floors (Built-in)")
        default_item.setData(Qt.UserRole, "default")
        self.floor_set_list.addItem(default_item)
        for entry in self.asset_manager.get_floor_set_entries():
            item = QListWidgetItem(entry['display_name'])
            item.setData(Qt.UserRole, entry['id'])
            self.floor_set_list.addItem(item)

    # --- Action Slots (Unchanged, but provided for completeness) ---
    def _populate_floor_set_list(self):
        # ... (This method is correct and unchanged) ...
        self.floor_set_list.clear()
        default_item = QListWidgetItem("Default Floors (Built-in)")
        default_item.setData(Qt.UserRole, "default")
        self.floor_set_list.addItem(default_item)
        for entry in self.asset_manager.get_floor_set_entries():
            item = QListWidgetItem(entry['display_name'])
            item.setData(Qt.UserRole, entry['id'])
            self.floor_set_list.addItem(item)

    @Slot()
    def _on_load_clicked(self):
        """
        Gets the ID of the selected floor set and emits the load_requested signal.
        """
        current_item = self.floor_set_list.currentItem()
        if not current_item and self.floor_set_list.count() > 0:
            current_item = self.floor_set_list.item(0) # Default to first item for startup
        if not current_item: return

        # --- THIS IS THE FIX ---
        # Get the ID (string) from the item's data and emit it.
        floor_set_id = current_item.data(Qt.UserRole)
        self.load_requested.emit(floor_set_id)
        # --- END OF FIX ---

    @Slot(object)
    def _show_context_menu(self, pos):
        item = self.floor_set_list.itemAt(pos)
        if not item: return

        is_user_item = item.data(Qt.UserRole) != "default"

        actions = {"Load": self._on_load_clicked}
        if is_user_item:
            actions["Save"] = self.save_requested.emit
            actions["---"] = None
            actions["Rename"] = self._on_rename_clicked
            actions["Delete"] = self._on_delete_clicked

        actions["---"] = None
        actions["Export..."] = self._on_export_clicked

        menu = create_library_context_menu(self, actions)
        menu.exec(self.floor_set_list.mapToGlobal(pos))

    @Slot()
    def _on_load_clicked(self):
        current_item = self.floor_set_list.currentItem()
        if not current_item and self.floor_set_list.count() > 0:
            current_item = self.floor_set_list.item(0)
        if not current_item: return
        floor_set_id = current_item.data(Qt.UserRole)
        if floor_set_id == "default":
            default_path = self.asset_manager.user_assets_path / "floor_sets" / "default_floors.json"
            if default_path.exists():
                with open(default_path, 'r') as f:
                    import json;
                    floor_data = json.load(f)
                    self.load_requested.emit(current_item.data(Qt.UserRole))
            else:
                QMessageBox.critical(self, "Error", "default_floors.json not found!")
            return
        floor_data = self.asset_manager.load_floor_set_data(floor_set_id)
        if floor_data:
            self.load_requested.emit(current_item.data(Qt.UserRole))
        else:
            QMessageBox.critical(self, "Error", "Failed to load floor set data.")

    @Slot()
    def _on_save_as_clicked(self):
        self.request_current_floors.emit(self.receive_current_floors_for_saving)

    def receive_current_floors_for_saving(self, current_floors_data: list):
        if not current_floors_data:
            QMessageBox.warning(self, "No Data", "There are no floors in the canvas to save.")
            return
        display_name, ok = QInputDialog.getText(self, "Save Floor Set", "Enter a name for this new floor set:")
        if not ok or not display_name.strip(): return
        success = self.asset_manager.save_new_floor_set(display_name.strip(), current_floors_data)
        if success:
            QMessageBox.information(self, "Success", f"Floor set '{display_name}' saved.")
            self._populate_floor_set_list()
        else:
            QMessageBox.critical(self, "Error", "An error occurred while saving the floor set.")

    @Slot()
    def _on_rename_clicked(self):
        current_item = self.floor_set_list.currentItem()
        if not current_item: return
        asset_id = current_item.data(Qt.UserRole);
        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Floor Set", "Enter new name:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            self.asset_manager.rename_asset("floor_sets", asset_id, new_name.strip())
            self._populate_floor_set_list()

    @Slot()
    def _on_delete_clicked(self):
        current_item = self.floor_set_list.currentItem()
        if not current_item: return
        asset_id = current_item.data(Qt.UserRole);
        display_name = current_item.text()
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete '{display_name}'?")
        if reply == QMessageBox.StandardButton.Yes:
            if self.asset_manager.delete_floor_set(asset_id):
                self._populate_floor_set_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete.")

    @Slot()
    def _on_export_clicked(self):
        current_item = self.floor_set_list.currentItem()
        if not current_item: return
        asset_id = current_item.data(Qt.UserRole)
        self.export_requested.emit(asset_id)

    @Slot(object)
    def _show_context_menu(self, pos):
        item = self.floor_set_list.itemAt(pos)
        if not item: return
        is_user_item = item.data(Qt.UserRole) != "default"
        actions = {"Load": self._on_load_clicked}
        if is_user_item:
            actions["---"] = None
            actions["Save"] = self.save_requested.emit
            actions["Rename"] = self._on_rename_clicked
            actions["Delete"] = self._on_delete_clicked
        actions["---"] = None
        actions["Export..."] = self._on_export_clicked
        menu = create_library_context_menu(self, actions)
        menu.exec(self.floor_set_list.mapToGlobal(pos))

    def _update_button_states(self, current_item):
        """Enable/disable buttons based on the current selection."""
        is_item_selected = current_item is not None

        # The export button should only be enabled when an item is selected
        self.export_button.setEnabled(is_item_selected)