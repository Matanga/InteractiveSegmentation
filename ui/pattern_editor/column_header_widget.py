from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel


class ColumnHeaderWidget(QWidget):
    """
    A simple widget to display the column titles for the PatternArea.
    Its column widths are synchronized by connecting to a signal from the PatternArea.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(5)  # Matches the spacing in FloorRowWidget

        self.header_floor = self._create_label("Floor")
        self.header_front = self._create_label("Front")
        self.header_left = self._create_label("Left")
        self.header_back = self._create_label("Back")
        self.header_right = self._create_label("Right")

        # We need separator placeholders to match the layout in FloorRowWidget
        sep_width = 12  # Approximate width of a VLine separator + spacing

        self._layout.addWidget(self.header_floor)
        self._layout.addWidget(self.header_front)
        self._layout.addSpacing(sep_width)
        self._layout.addWidget(self.header_left)
        self._layout.addSpacing(sep_width)
        self._layout.addWidget(self.header_back)
        self._layout.addSpacing(sep_width)
        self._layout.addWidget(self.header_right)
        self._layout.addStretch(1)

    def _create_label(self, text: str) -> QLabel:
        """Helper to create a consistently styled QLabel."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-weight: bold; color: #c0c0c0; padding: 4px;")
        return label

    @Slot(list)
    def update_column_widths(self, widths: list[int]):
        """
        Public slot to receive new column widths and apply them.
        The list is expected to be [header, front, left, back, right].
        """
        if len(widths) != 5:
            return

        self.header_floor.setFixedWidth(widths[0])
        self.header_front.setFixedWidth(widths[1])
        self.header_left.setFixedWidth(widths[2])
        self.header_back.setFixedWidth(widths[3])
        self.header_right.setFixedWidth(widths[4])