from PySide6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QDockWidget, QWidget, QLabel, QVBoxLayout
)
import sys
from PySide6.QtCore import Qt

class PatternEditorDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Pattern Editor", parent)
        self.setObjectName("PatternEditorDock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Placeholder content
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(QLabel("Pattern Editor Content Placeholder"))
        content.setLayout(layout)
        self.setWidget(content)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IBG Pattern Editor")

        # Toolbar
        toolbar = QToolBar("Main Toolbar", self)
        self.addToolBar(toolbar)

        # Dockable Pattern Editor
        self.pattern_editor_dock = PatternEditorDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.pattern_editor_dock)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
