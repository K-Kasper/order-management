"""UI constants for colors, formats, and layout configuration."""

# Color scheme
PRIMARY_BLUE = "#1F3A5F"
BG_MAIN = "#c0c0c0"

# Tag colors for treeview rows
TAG_COLORS = {
    "overdue": "#ffe6e6",
    "due_today": "#fff4cc",
    "due_soon": "#fff8de",
}

# Default layout spacing
DEFAULT_LAYOUT = {
    "body_padding": 6,
    "panel_padx": 6,
    "section_padx": 6,
    "section_pady": 4,
    "entry_width": 24,
}

# Image file types for file dialogs
IMAGE_FILE_TYPES = [
    ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
    ("All Files", "*.*"),
]
