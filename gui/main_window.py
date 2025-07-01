from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QMenu,
    QDockWidget, QWidget, QLabel, QVBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
import sys


class PatternEditorDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Pattern Editor", parent)
        self.setObjectName("PatternEditorDock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Placeholder content
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(QLabel("Pattern Editor Content Placeholder"))
        self.setWidget(content)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IBG Pattern Editor")

        # Menu Bar
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        help_menu = menu_bar.addMenu("Window")

        # Example actions for File menu
        file_menu.addAction(QAction("Import Pattern", self))
        file_menu.addAction(QAction("Export Pattern", self))
        file_menu.addSeparator()
        file_menu.addAction(QAction("Exit", self))




        # Dockable Pattern Editor
        self.pattern_editor_dock = PatternEditorDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.pattern_editor_dock)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
