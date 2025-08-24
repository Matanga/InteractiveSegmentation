from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget,
    QPushButton, QFileDialog, QInputDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QComboBox, QHeaderView
)
from PySide6.QtCore import Slot, Qt, QEvent

from .mapping_data_manager import DataManager
# We need to get the list of our internal modules
from services.resources_loader import IconFiles


class MappingEditorPanel(QWidget):
    """
    The main panel for managing and editing module mappings.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("MappingEditorPanel")

        self.data_manager = DataManager()

        # --- Create Main Widgets ---
        self.data_table_list = QListWidget()
        self.load_data_table_button = QPushButton("Load Unreal Data Table...")

        # Create the Save Button
        self.save_mapping_button = QPushButton("Save Mapping")
        self.save_mapping_button.setEnabled(False)  # Disabled until a DT is selected

        # Create the Mapping Table
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(2)
        self.mapping_table.setHorizontalHeaderLabels(["Internal Module", "Mapped Unreal Module"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # --- Layouts ---

        # A new horizontal layout for the Load and Save buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.load_data_table_button)
        button_layout.addWidget(self.save_mapping_button)

        # The main layout for the left-side Data Table panel
        data_table_layout = QVBoxLayout()
        data_table_layout.addWidget(self.data_table_list)
        data_table_layout.addLayout(button_layout)  # Add the button layout here

        data_table_box = QGroupBox("Loaded Data Tables")
        data_table_box.setLayout(data_table_layout)

        # The layout for the right-side Mapping panel
        mapping_layout = QVBoxLayout()
        mapping_layout.addWidget(self.mapping_table)

        mapping_box = QGroupBox("Module Mappings")
        mapping_box.setLayout(mapping_layout)

        # The root layout holding both main panels
        root_layout = QHBoxLayout(self)
        root_layout.addWidget(data_table_box, 1)
        root_layout.addWidget(mapping_box, 3)

        # --- Connect Signals ---
        self.load_data_table_button.clicked.connect(self._on_load_data_table)
        self.save_mapping_button.clicked.connect(self._on_save_mapping)
        self.data_table_list.currentItemChanged.connect(self._on_data_table_selected)

        # --- Initial Population ---
        self._populate_data_table_list()
        self._populate_mapping_table_base()

    def _populate_data_table_list(self):
        """Populates the list widget from the manifest."""
        self.data_table_list.clear()
        for entry in self.data_manager.get_data_table_entries():
            # The item's text() is its display name, which is all we need.
            self.data_table_list.addItem(entry['display_name'])

    def _populate_mapping_table_base(self):
        """
        Populates the first column of the mapping table with all available
        internal module names. This is done only once.
        """
        # Get all modules from all our internal icon sets
        all_internal_modules = sorted(list(IconFiles.get_all_module_names()))

        self.mapping_table.setRowCount(len(all_internal_modules))

        for row, module_name in enumerate(all_internal_modules):
            item = QTableWidgetItem(module_name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make it read-only
            self.mapping_table.setItem(row, 0, item)

    @Slot()
    def _on_load_data_table(self):
        """Handles the workflow for loading a new data table."""
        # ... (This method is correct and unchanged) ...
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Unreal Module Data Table", "", "JSON Files (*.json)")
        if not file_path: return
        display_name, ok = QInputDialog.getText(self, "Enter Display Name", "Enter a friendly name:")
        if not ok or not display_name.strip(): return
        success = self.data_manager.add_new_data_table(file_path, display_name.strip())
        if success:
            self._populate_data_table_list()
        else:
            QMessageBox.warning(self, "Error", "Failed to load data table.")

    @Slot()
    def _on_data_table_selected(self, current_item, _previous_item):
        """
        Populates the dropdowns and loads any existing saved mapping for the
        selected data table. It also installs an event filter on the comboboxes
        to prevent them from stealing mouse wheel scroll events.
        """
        if not current_item:
            self.save_mapping_button.setEnabled(False)
            for row in range(self.mapping_table.rowCount()):
                self.mapping_table.setCellWidget(row, 1, None)
            return

        self.save_mapping_button.setEnabled(True)
        display_name = current_item.text()
        entry = self.data_manager.get_entry_by_display_name(display_name)
        if not entry: return

        data_table_id = entry['id']
        unreal_module_names = self.data_manager.get_module_names_for_id(data_table_id)
        saved_mapping = self.data_manager.load_mapping_for_id(data_table_id)
        unreal_module_names.insert(0, "")

        for row in range(self.mapping_table.rowCount()):
            combo = QComboBox()
            combo.addItems(unreal_module_names)

            internal_module_name = self.mapping_table.item(row, 0).text()
            if internal_module_name in saved_mapping:
                saved_unreal_name = saved_mapping[internal_module_name]
                combo.setCurrentText(saved_unreal_name)

            # 1. Define a simple event filter function.
            def wheel_event_filter(watched, event):
                if event.type() == QEvent.Type.Wheel:
                    # If the event is a Wheel event, ignore it.
                    event.ignore()
                    return True  # We have handled this event.
                # For all other events, do the default behavior.
                return False

            # 2. Install the filter on the combobox.
            combo.installEventFilter(self)
            self.eventFilter = wheel_event_filter

            self.mapping_table.setCellWidget(row, 1, combo)
    @Slot()
    def _on_save_mapping(self):
        """
        Reads the current state of the mapping table and saves it to the
        JSON file for the currently selected data table.
        """
        current_item = self.data_table_list.currentItem()
        if not current_item:
            return

        display_name = current_item.text()
        entry = self.data_manager.get_entry_by_display_name(display_name)
        if not entry: return

        data_table_id = entry['id']

        # Build the mapping dictionary from the table's current state
        new_mapping = {}
        for row in range(self.mapping_table.rowCount()):
            internal_module_item = self.mapping_table.item(row, 0)
            combo_box = self.mapping_table.cellWidget(row, 1)

            if internal_module_item and isinstance(combo_box, QComboBox):
                internal_name = internal_module_item.text()
                mapped_name = combo_box.currentText()

                # Only save non-empty mappings
                if mapped_name:
                    new_mapping[internal_name] = mapped_name

        # Use the data manager to save the file
        self.data_manager.save_mapping_for_id(data_table_id, new_mapping)
        QMessageBox.information(self, "Success", f"Mapping for '{display_name}' saved successfully.")