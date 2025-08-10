import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QSlider, QFormLayout
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

# Import our building system components
from building_grammar.pattern_resolver import PatternResolver
from building_grammar.building_generator import BuildingGenerator
from gui.resources_loader import IconFiles


MODULE_HEIGHT= 128
MODULE_WIDTH = 128

# --- Helper function (can be in this file or a separate 'utils.py') ---
def pil_to_qpixmap(pil_img):
    """Converts a PIL Image to a QPixmap for display in Qt."""
    if pil_img is None or pil_img.width == 0 or pil_img.height == 0:
        return QPixmap()
    byte_array = pil_img.tobytes("raw", "RGBA")
    q_image = QImage(byte_array, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(q_image)


# =======================================================
# --- THE REUSABLE QWIDGET ---
# =======================================================
class FacadeEditorWidget(QWidget):
    # Change the base class to QWidget
    def __init__(self, parent=None):
        # Accept a parent argument, which is standard for QWidgets
        super().__init__(parent)

        # --- 1. Initialize the Building System Backend ---
        # It's better to pass the generator in, but for a self-contained
        # example, we'll initialize it here.
        try:
            icon_set = IconFiles.get_icons_for_category("Default")
            if not icon_set:
                raise FileNotFoundError("Could not find 'Default' icon category.")
            self.generator = BuildingGenerator(icon_set=icon_set)
            self.resolver = PatternResolver(default_module_width=MODULE_WIDTH)
        except Exception as e:
            # If the backend fails, display an error message inside the widget
            error_layout = QVBoxLayout(self)
            error_label = QLabel(f"FATAL ERROR:\nCould not initialize backend.\n\n{e}")
            error_label.setWordWrap(True)
            error_layout.addWidget(error_label)
            return

        # --- 2. Create and Arrange UI Widgets ---
        self.setup_ui()

        # --- 3. Initial Generation ---
        self.regenerate_facade()

    def setup_ui(self):
        """Creates and lays out all the widgets for this widget."""
        # The main layout is now set directly on this QWidget instance
        main_layout = QHBoxLayout(self)

        # -- Left Side: Controls --
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_widget.setFixedWidth(300)

        # Width Slider
        width_layout = QHBoxLayout()
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setMinimum(128);
        self.width_slider.setMaximum(2048)
        self.width_slider.setValue(600);
        self.width_slider.setTickInterval(128)
        self.width_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.width_label = QLabel(str(self.width_slider.value()));
        self.width_label.setFixedWidth(40)
        width_layout.addWidget(self.width_slider);
        width_layout.addWidget(self.width_label)

        form_layout = QFormLayout()
        form_layout.addRow("Facade Width (px):", width_layout)

        # Grammar Input
        self.grammar_input = QTextEdit()
        default_grammar = "<Wall00>\n[Door00]<Wall00>\n[Wall00-Window00-Wall00]"
        self.grammar_input.setPlainText(default_grammar)

        controls_layout.addLayout(form_layout)
        controls_layout.addWidget(QLabel("Facade Grammar:"))
        controls_layout.addWidget(self.grammar_input)

        # -- Right Side: Image Preview --
        self.image_label = QLabel("Generating...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #333; color: white;")
        # Set a minimum size to ensure it's visible even when empty
        self.image_label.setMinimumSize(200, 200)

        # Add sub-widgets to the main layout
        main_layout.addWidget(controls_widget)
        main_layout.addWidget(self.image_label)

        # --- 4. Connect Signals to Slots ---
        self.width_slider.valueChanged.connect(self.update_width_label)
        self.width_slider.valueChanged.connect(self.regenerate_facade)
        self.grammar_input.textChanged.connect(self.regenerate_facade)

    def update_width_label(self, value):
        self.width_label.setText(str(value))

    def regenerate_facade(self):
        # This method is unchanged from the previous version. It's already perfect.
        try:
            width = self.width_slider.value()
            grammar = self.grammar_input.toPlainText()

            if not grammar.strip() or width <= 0:
                self.image_label.setText("Invalid Input");
                self.image_label.setPixmap(QPixmap());
                return

            num_floors = len([line for line in grammar.strip().splitlines() if line.strip()]) or 1
            floor_widths = {i: width for i in range(num_floors)}
            facade_blueprint = self.resolver.resolve(grammar, floor_widths)
            facade_image = self.generator.assemble_full_facade(facade_blueprint)
            pixmap = pil_to_qpixmap(facade_image)

            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.image_label.setText("Generated Empty Image");
                self.image_label.setPixmap(QPixmap())

        except Exception as e:
            self.image_label.setText(f"ERROR:\n{e}");
            self.image_label.setPixmap(QPixmap())
            print(f"ERROR during regeneration: {e}")


# =======================================================
# --- EXAMPLE USAGE WINDOW (can be in a separate file) ---
# =======================================================
# This part demonstrates how to USE your new widget.
if __name__ == "__main__":
    from PySide6.QtWidgets import QMainWindow


    # This is a simple container window to host our widget
    class ExampleHostWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Reusable Facade Editor Widget - DEMO")
            self.setGeometry(100, 100, 800, 600)

            # Create an instance of our reusable widget
            self.editor_widget = FacadeEditorWidget()

            # Set it as the central content of the window
            self.setCentralWidget(self.editor_widget)


    # --- Application Entry Point ---
    # Check for assets first
    if not IconFiles.get_icons_for_category("Default"):
        print("FATAL: Could not find 'Default' icon category in './resources/Default'.")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = ExampleHostWindow()
    window.show()
    sys.exit(app.exec())