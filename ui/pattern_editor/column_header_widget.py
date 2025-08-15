from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout

class ColumnHeaderWidget(QWidget):
    """
    Displays the column titles for the PatternArea. Its layout is a precise
    mirror of the FloorRowWidget layout to ensure perfect alignment.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._layout = QHBoxLayout(self)
        self.setContentsMargins(10, 0, 0, 0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(5)

        self.header_floor = self._create_label("Floor")
        self.header_front = self._create_label("Front")
        self.header_left = self._create_label("Left")
        self.header_back = self._create_label("Back")
        self.header_right = self._create_label("Right")

        # --- THIS IS THE FIX ---
        # 1. Set a fixed width for the "Floor" label to match the header below it.
        self.header_floor.setFixedWidth(150)

        # 2. Add all widgets to the layout. The layout's main spacing of 5
        #    will now correctly create all the gaps.
        self._layout.addWidget(self.header_floor)
        self._layout.addWidget(self.header_front)
        self._layout.addWidget(self.header_left)
        self._layout.addWidget(self.header_back)
        self._layout.addWidget(self.header_right)
        self._layout.addStretch(1)
        # --- END OF FIX ---


    def _create_label(self, text: str) -> QLabel:
        """Helper to create a consistently styled QLabel."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #c0c0c0;
                padding: 4px;
                background-color: #383838;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        return label

    @Slot(list)
    def update_column_widths(self, widths: list[int]):
        """
        Public slot to receive new column widths.
        Note: We now ignore the first width (header_width) because we've set it manually.
        """
        if len(widths) != 5:
            return

        # We only need to update the widths of the facade columns.
        # widths[0] is the header width, which is now fixed.
        self.header_front.setFixedWidth(widths[1])
        self.header_left.setFixedWidth(widths[2])
        self.header_back.setFixedWidth(widths[3])
        self.header_right.setFixedWidth(widths[4])