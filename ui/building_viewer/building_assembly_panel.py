from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
)
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Signal

class BuildingAssemblyPanel(QWidget):
    """
    A widget containing controls for assembling a final building from the
    defined floor patterns. This includes setting dimensions, the stacking
    pattern, and triggering the generation.
    """
    assemblyChanged = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("BuildingAssemblyPanel")

        # --- Create Widgets ---

        # Dimension Inputs
        self.width_edit = QLineEdit("1200")
        self.depth_edit = QLineEdit("1200")
        self.height_edit = QLineEdit("2400")

        for editor in [self.width_edit, self.depth_edit, self.height_edit]:
            editor.setValidator(QIntValidator(1, 99999))
            editor.setFixedWidth(60)

        # Stacking Pattern Input
        self.pattern_edit = QLineEdit("[Ground]<Floor1>[Floor2]")
        self.pattern_edit.setToolTip(
            "Define the vertical stacking order of floors.\n"
            "Use < > for repeatable (fill) floors.\n"
            "Use [ ] for rigid (one-off) floors."
        )

        # Action Buttons
        self.generate_button = QPushButton("Generate Building")
        self.generate_button.setObjectName("GenerateButton") # For styling
        self.live_update_checkbox = QCheckBox("Live Update")

        # --- Layouts ---
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(8)

        # Dimensions Group
        dimensions_box = QGroupBox("Building Dimensions (cm)")
        dimensions_layout = QHBoxLayout(dimensions_box)
        dimensions_layout.addWidget(QLabel("Width (X):"))
        dimensions_layout.addWidget(self.width_edit)
        dimensions_layout.addStretch()
        dimensions_layout.addWidget(QLabel("Depth (Y):"))
        dimensions_layout.addWidget(self.depth_edit)
        dimensions_layout.addStretch()
        dimensions_layout.addWidget(QLabel("Total Height (Z):"))
        dimensions_layout.addWidget(self.height_edit)

        # Stacking Pattern Group
        pattern_box = QGroupBox("Vertical Stacking Pattern")
        pattern_layout = QVBoxLayout(pattern_box)
        pattern_layout.addWidget(self.pattern_edit)

        # Actions Layout
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.live_update_checkbox)
        actions_layout.addStretch()
        actions_layout.addWidget(self.generate_button)

        # Assemble the root layout
        root_layout.addWidget(dimensions_box)
        root_layout.addWidget(pattern_box)
        root_layout.addLayout(actions_layout)
        root_layout.addStretch(1) # Push everything to the top

        #  Add SIGNAL CONNECTIONS
        self.width_edit.editingFinished.connect(self.assemblyChanged)
        self.depth_edit.editingFinished.connect(self.assemblyChanged)
        self.height_edit.editingFinished.connect(self.assemblyChanged)
        self.pattern_edit.editingFinished.connect(self.assemblyChanged)

        # --- Styling ---
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #c0c0c0;
            }
            QPushButton#GenerateButton {
                font-weight: bold;
                padding: 6px 12px;
                background-color: #5a9b5a;
            }
        """)