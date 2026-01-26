"""Treeview utility functions."""

from tkinter import ttk

from order_management.ui.constants import TAG_COLORS


def clear_treeview(tree: ttk.Treeview) -> None:
    """Clear all items from a treeview.

    Args:
        tree: The treeview widget to clear.
    """
    for item in tree.get_children():
        tree.delete(item)


def configure_treeview_tags(tree: ttk.Treeview) -> None:
    """Configure standard deadline-based row tags for a treeview.

    Args:
        tree: The treeview widget to configure.
    """
    for tag, color in TAG_COLORS.items():
        tree.tag_configure(tag, background=color)
