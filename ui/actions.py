# ui/actions.py – UI-adapter for creating context-specific actions

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QWidget

# Use a TYPE_CHECKING block to import types for static analysis without
# creating circular dependencies at runtime.
if TYPE_CHECKING:
    pass


def add_remove_context_menu(widget: QWidget, remove_cb: Callable[[], None]) -> None:
    """
    Attaches a standardized context menu to a widget.

    This function creates and configures a QMenu with a single "Remove" action.
    It also sets up a keyboard shortcut (Delete/Backspace) that triggers the
    same remove action when the widget has focus.

    Args:
        widget: The QWidget to which the context menu and action will be attached.
        remove_cb: The callback function to be executed when the "Remove"
                   action is triggered by the menu or shortcut.
    """
    # Create the menu and associate it with the parent widget.
    menu = QMenu(widget)

    # Allow the menu to have a custom background color via stylesheets.
    menu.setAttribute(Qt.WA_StyledBackground, True)
    menu.setStyleSheet("""
        QMenu {
            background: #ffffff;
            color: #000000;
            border: 1px solid #a0a0a0;
        }
        QMenu::item:selected {
            background: #3874f2;
            color: #ffffff;
        }
    """)

    # Create the "Remove" action. Parenting it to the widget ensures the action's
    # lifecycle is tied to the widget's.
    act_remove = QAction("Remove", widget)

    # Assign a standard keyboard shortcut for deletion.
    act_remove.setShortcut(QKeySequence.Delete)

    # The shortcut should only be active when the widget itself has focus.
    act_remove.setShortcutContext(Qt.WidgetShortcut)

    # Connect the action's trigger to the provided callback function.
    act_remove.triggered.connect(remove_cb)

    # This adds the action as a visible item in the context menu.
    menu.addAction(act_remove)

    # This associates the action (and its shortcut) with the widget, allowing the
    # shortcut to work even when the menu is not visible.
    widget.addAction(act_remove)

    # Configure the widget to show a custom context menu on right-click.
    widget.setContextMenuPolicy(Qt.CustomContextMenu)

    # When the widget requests a context menu (e.g., on right-click),
    # execute the menu at the cursor's global position.
    widget.customContextMenuRequested.connect(
        lambda pos: menu.exec(widget.mapToGlobal(pos))
    )