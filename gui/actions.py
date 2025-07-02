# ui/actions.py  – keep UI-adapter specific
from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QMenu, QWidget
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from gui.dragdrop_groups import ModuleWidget, GroupWidget

def add_context_menu(widget: QWidget, remove_cb: callable) -> None:
    """Attach a contextual menu with a single *Remove* action."""
    menu = QMenu(widget)

    menu.setAttribute(Qt.WA_StyledBackground, True)
    menu.setStyleSheet(
        """
        QMenu {
            background: #ffffff;        /* light background */
            color: #000000;             /* dark text  */
            border: 1px solid #a0a0a0;
        }
        QMenu::item:selected {
            background: #3874f2;        /* highlight  */
            color: #ffffff;
        }
        """
    )

    act_remove = QAction("Remove", widget)          # parent = widget (not menu)
    act_remove.setShortcut(QKeySequence.Delete)     # also catches Backspace on most keyboards
    act_remove.setShortcutContext(Qt.WidgetShortcut)  # fires only when *widget* has focus
    act_remove.triggered.connect(remove_cb)

    menu.addAction(act_remove)      # shows it in the menu
    widget.addAction(act_remove)    # activates shortcut while menu is closed

    # Qt will automatically spawn this menu on right-click
    widget.setContextMenuPolicy(Qt.CustomContextMenu)
    widget.customContextMenuRequested.connect(
        lambda pos: menu.exec(widget.mapToGlobal(pos))
    )
