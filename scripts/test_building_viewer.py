# scripts/test_building_viewer.py
from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton

from ui.building_viewer.building_viewer import BuildingViewerApp
from services.resources_loader import IconFiles


class HostWindow(QMainWindow):
    """Simple harness to try BuildingViewerApp in isolation."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Building Viewer – Demo")
        self.setGeometry(100, 100, 900, 700)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        self.viewer = BuildingViewerApp(icon_category="Default")
        self.btn_kit = QPushButton("Generate Building (Kit of Parts)")
        self.btn_bill = QPushButton("Generate Building (Image Billboards)")

        layout.addWidget(self.viewer)
        layout.addWidget(self.btn_kit)
        layout.addWidget(self.btn_bill)

        self.btn_kit.clicked.connect(self.viewer.generate_building_1_kit)
        self.btn_bill.clicked.connect(self.viewer.generate_building_1_billboard)

        # Generate a default building on startup
        self.viewer.generate_building_1_kit()


if __name__ == "__main__":
    if not IconFiles.get_icons_for_category("Default"):
        sys.exit("FATAL: Could not find 'Default' icon category.")
    app = QApplication(sys.argv)
    win = HostWindow()
    win.show()
    sys.exit(app.exec())
