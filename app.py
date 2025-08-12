# app.py (project root)
import sys
from PySide6.QtWidgets import QApplication
from ui.app.shell_window import ShellWindow, APP_STYLESHEET  # <- import from root module

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)  # safe even if it's an empty string
    win = ShellWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
