from __future__ import annotations


from pathlib import Path
from resources_loader import IconFiles


from module_item import ModuleWidget


from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox
)


class ModuleLibrary(QWidget):
    """Vertical strip that lists every PNG in ./resources as a draggable icon."""

    ICON_SIZE = 48        # logical size for palette pixmaps

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(self.ICON_SIZE + 60)

        # Build a pixmap cache once, then share it with all ModuleWidgets
        self._pixmaps: dict[str, QPixmap] = self._make_pixmap_cache()
        ModuleWidget.ICONS = self._pixmaps          # one-liner integration

        # ------------------------- UI layout
        vbox = QVBoxLayout(self)
        vbox.setAlignment(Qt.AlignTop)

        self._add_btn = QPushButton("＋")
        self._add_btn.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._add_btn.clicked.connect(self._on_add_icon)     # import dialog
        vbox.addWidget(self._add_btn)

        for name in sorted(self._pixmaps):
            vbox.addWidget(ModuleWidget(name, is_library=True))

        vbox.addStretch()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _make_pixmap_cache(self) -> dict[str, QPixmap]:
        """Load/scales pixmaps for every PNG in IconFiles."""
        cache: dict[str, QPixmap] = {}
        for name in IconFiles.names:
            path = IconFiles.paths[name]
            pix = QPixmap(str(path)).scaled(
                self.ICON_SIZE,
                self.ICON_SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            cache[name] = pix
        return cache

    # ------------------------------------------------------------------
    # '＋' button handler – MVP implementation
    # ------------------------------------------------------------------
    def _on_add_icon(self) -> None:
        """Let the user copy a PNG into the resources folder, then refresh."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Add PNG icon",
            "",
            "PNG images (*.png)",
        )
        if not file_path:
            return  # user cancelled

        try:
            src = Path(file_path)
            dest = IconFiles.folder / src.name

            # Auto-rename on collision: door00 → door00_1 → door00_2 …
            counter = 1
            while dest.exists():
                dest = IconFiles.folder / f"{src.stem}_{counter}.png"
                counter += 1

            dest.write_bytes(src.read_bytes())
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Import error", str(exc))
            return

        IconFiles.reload()                 # re-scan folder
        self._rebuild_palette()            # refresh widget list

    # ------------------------------------------------------------------
    def _rebuild_palette(self) -> None:
        """Recreate pixmap cache and refresh child ModuleWidgets."""
        # Remove every widget except the '+' button
        layout = self.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            w = item.widget()
            if w and w is not self._add_btn:
                w.setParent(None)

        self._pixmaps = self._make_pixmap_cache()
        ModuleWidget.ICONS = self._pixmaps

        for name in sorted(self._pixmaps):
            layout.addWidget(ModuleWidget(name, is_library=True))

        layout.addStretch()
