from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QPushButton, QLabel
)


# ===================================================================
# FloorHeaderWidget: The UI for a floor's metadata and controls
# ===================================================================

class FloorHeaderWidget(QWidget):
    """
    A widget that displays a floor's name, height, and control buttons
    (move up, move down, remove).

    It emits signals when the user clicks the control buttons, which are
    handled by the parent FloorRowWidget.
    """
    # Define signals that the parent widget will connect to.
    remove_requested = Signal()
    move_up_requested = Signal()
    move_down_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FloorHeaderWidget")

        # --- Create Widgets ---
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("FloorNameEdit")
        self.name_edit.setToolTip("Floor Name")

        # --- NEW: Height Editor ---
        self.height_label = QLabel("Height:")
        self.height_edit = QLineEdit("400")  # Default height
        self.height_edit.setObjectName("FloorHeightEdit")
        self.height_edit.setValidator(QIntValidator(0, 99999))  # Only allow numbers
        self.height_edit.setFixedWidth(50)
        self.height_edit.setToolTip("Floor Height (in cm)")

        # --- Control Buttons ---
        self.up_button = QPushButton("▲")
        self.up_button.setObjectName("MoveButton")
        self.up_button.setToolTip("Move floor up")

        self.down_button = QPushButton("▼")
        self.down_button.setObjectName("MoveButton")
        self.down_button.setToolTip("Move floor down")

        self.remove_button = QPushButton("X")
        self.remove_button.setObjectName("RemoveButton")
        self.remove_button.setToolTip("Remove this floor")

        # --- Signal Connections ---
        # Note: The signals now emit no arguments. The parent FloorRowWidget
        # already knows it is the one being targeted.
        self.up_button.clicked.connect(self.move_up_requested.emit)
        self.down_button.clicked.connect(self.move_down_requested.emit)
        self.remove_button.clicked.connect(self.remove_requested.emit)

        # --- Layouts ---
        # Horizontal layout for the buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(4)
        button_layout.addWidget(self.up_button)
        button_layout.addWidget(self.down_button)
        button_layout.addStretch()
        button_layout.addWidget(self.remove_button)

        # Horizontal layout for the height editor
        height_layout = QHBoxLayout()
        height_layout.setContentsMargins(0, 0, 0, 0)
        height_layout.addWidget(self.height_label)
        height_layout.addWidget(self.height_edit)
        height_layout.addStretch()

        # Main vertical layout for the entire header
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addLayout(button_layout)
        layout.addWidget(self.name_edit)
        layout.addLayout(height_layout)

        self.setFixedWidth(150)
        self.setStyleSheet("""
            QWidget#FloorHeaderWidget {
                background-color: #383838;
                border-radius: 4px;
            }
            QLineEdit#FloorNameEdit, QLineEdit#FloorHeightEdit {
                font-weight: bold;
                color: #e0e0e0;
                border: 1px solid #555;
                padding: 4px;
                background-color: #484848;
            }
            QLabel {
                color: #c0c0c0;
                font-size: 10px;
            }
            QPushButton#RemoveButton {
                font-family: "Segoe UI", Arial, sans-serif;
                font-weight: bold;
                font-size: 14px;
                color: #aaa;
                background-color: #484848;
                border: 1px solid #555;
            }
            QPushButton#RemoveButton:hover {
                background-color: #d14545;
                color: white;
                border-color: #ff6a6a;
            }
            QPushButton#RemoveButton:pressed {
                background-color: #a13535;
            }
            QPushButton#MoveButton {
                /* Add styling for move buttons if desired */
            }
        """)

    def update_floor_label(self, floor_index: int):
        """
        Sets the default floor name text based on its index.
        This is a fallback for when no name is provided in the data.
        """
        floor_text = "Ground Floor" if floor_index == 0 else f"Floor {floor_index}"
        # Set text only if the user hasn't typed a custom name.
        if not self.name_edit.text() or self.name_edit.text().startswith("Floor"):
            self.name_edit.setText(floor_text)