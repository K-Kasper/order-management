"""Labeled form field widgets."""

import tkinter as tk
from tkinter import ttk
from typing import Any

from tkcalendar import DateEntry


class LabeledEntry(ttk.Frame):
    """Entry widget with a label."""

    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        width: int = 24,
        state: str = "normal",
        **kwargs: Any,
    ) -> None:
        super().__init__(parent)
        self._variable = variable

        ttk.Label(self, text=label + ":", width=18, anchor="e").pack(side="left", padx=(0, 3))
        self._entry = ttk.Entry(self, textvariable=variable, width=width, state=state)
        self._entry.pack(side="left", **kwargs)

    @property
    def variable(self) -> tk.StringVar:
        return self._variable

    @property
    def entry(self) -> ttk.Entry:
        return self._entry


class LabeledCombobox(ttk.Frame):
    """Combobox widget with a label."""

    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...] = (),
        width: int = 24,
        state: str = "readonly",
        **kwargs: Any,
    ) -> None:
        super().__init__(parent)
        self._variable = variable

        ttk.Label(self, text=label + ":", width=18, anchor="e").pack(side="left", padx=(0, 3))
        self._combo = ttk.Combobox(
            self, textvariable=variable, values=values, width=width, state=state
        )
        self._combo.pack(side="left", **kwargs)

    @property
    def variable(self) -> tk.StringVar:
        return self._variable

    @property
    def combobox(self) -> ttk.Combobox:
        return self._combo

    def configure_values(self, values: tuple[str, ...] | list[str]) -> None:
        """Update the combobox values."""
        self._combo.configure(values=values)


class LabeledDateEntry(ttk.Frame):
    """DateEntry widget with a label."""

    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        width: int = 18,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent)
        self._variable = variable

        ttk.Label(self, text=label + ":", width=18, anchor="e").pack(side="left", padx=(0, 3))
        self._entry = DateEntry(
            self,
            textvariable=variable,
            width=width,
            date_pattern="dd/mm/yyyy",
        )
        self._entry.pack(side="left", **kwargs)

    @property
    def variable(self) -> tk.StringVar:
        return self._variable

    @property
    def date_entry(self) -> DateEntry:
        return self._entry


class LabeledText(ttk.LabelFrame):
    """Text widget with a labeled frame."""

    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        height: int = 5,
        wrap: str = "word",
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, text=label, **kwargs)
        self._text = tk.Text(self, height=height, wrap=wrap)
        self._text.pack(fill="both", expand=True, padx=6, pady=4)

    @property
    def text(self) -> tk.Text:
        return self._text

    def get_content(self) -> str:
        """Get the text content."""
        return self._text.get("1.0", "end").strip()

    def set_content(self, content: str) -> None:
        """Set the text content."""
        self._text.delete("1.0", "end")
        self._text.insert("1.0", content)
