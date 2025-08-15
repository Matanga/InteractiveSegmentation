from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QFrame, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QPushButton, QLabel
)

class FloorHeaderWidget(QFrame):
    """
    A widget that displays a floor's name, height, and control buttons.
    It is styled as a self-contained, rounded box to match the facade cells.
    """
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
        self.name_edit.setFixedHeight(24)

        self.height_label = QLabel("H:")
        self.height_edit = QLineEdit("400")
        self.height_edit.setObjectName("FloorHeightEdit")
        self.height_edit.setValidator(QIntValidator(0, 99999))
        self.height_edit.setFixedWidth(40)
        self.height_edit.setToolTip("Floor Height (in cm)")
        self.height_edit.setFixedHeight(22)

        self.up_button = QPushButton("▲")
        self.up_button.setObjectName("MoveButton")
        self.up_button.setToolTip("Move floor up")
        self.up_button.setFixedSize(22, 22)

        self.down_button = QPushButton("▼")
        self.down_button.setObjectName("MoveButton")
        self.down_button.setToolTip("Move floor down")
        self.down_button.setFixedSize(22, 22)

        self.remove_button = QPushButton("X")
        self.remove_button.setObjectName("RemoveButton")
        self.remove_button.setToolTip("Remove this floor")
        self.remove_button.setFixedSize(22, 22)

        # --- Signal Connections ---
        self.up_button.clicked.connect(self.move_up_requested.emit)
        self.down_button.clicked.connect(self.move_down_requested.emit)
        self.remove_button.clicked.connect(self.remove_requested.emit)

        # --- Layout ---
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(2)
        controls_layout.addWidget(self.height_label)
        controls_layout.addWidget(self.height_edit)
        controls_layout.addStretch()
        controls_layout.addWidget(self.up_button)
        controls_layout.addWidget(self.down_button)
        controls_layout.addWidget(self.remove_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self.name_edit)
        layout.addLayout(controls_layout)

        self.setFixedWidth(150)
        self.setStyleSheet("""
            QFrame#FloorHeaderWidget {
                background-color: #4a4a4a;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QLineEdit#FloorNameEdit, QLineEdit#FloorHeightEdit {
                font-weight: bold;
                color: #e0e0e0;
                border: 1px solid #555;
                padding: 1px 2px;
                background-color: #383838;
            }
            QLabel { color: #c0c0c0; font-size: 10px; padding: 0; }
            QPushButton#RemoveButton {
                font-family: "Segoe UI", Arial, sans-serif; font-weight: bold;
                font-size: 12px; color: #aaa; background-color: #383838;
                border: 1px solid #555; padding: 0;
            }
            QPushButton#RemoveButton:hover { background-color: #d14545; color: white; border-color: #ff6a6a; }
            QPushButton#RemoveButton:pressed { background-color: #a13535; }
            QPushButton#MoveButton {
                font-size: 10px; padding: 0; background-color: #383838;
                border: 1px solid #555; color: #c0c0c0;
            }
            QPushButton#MoveButton:hover { background-color: #585858; }
        """)

    def set_initial_label(self, floor_index: int):
        """Sets the initial, default floor name when a new row is created."""
        floor_text = "Ground Floor" if floor_index == 0 else f"Floor {floor_index}"
        self.name_edit.setText(floor_text)