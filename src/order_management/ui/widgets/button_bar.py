"""Action button bar widget."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class ButtonBar(ttk.Frame):
    """Horizontal bar of action buttons."""

    def __init__(
        self,
        parent: tk.Widget,
        buttons: list[tuple[str, Callable[[], None]]],
        padding: tuple[int, int] = (6, 0),
    ) -> None:
        """Create a button bar.

        Args:
            parent: Parent widget.
            buttons: List of (label, command) tuples for each button.
            padding: Frame padding as (x, y).
        """
        super().__init__(parent, padding=padding)
        for label, command in buttons:
            ttk.Button(self, text=label, command=command).pack(side="left", padx=(0, 6))
