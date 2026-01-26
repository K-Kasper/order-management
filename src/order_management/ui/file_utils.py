"""File and folder opening utilities."""

import os
import subprocess
import sys
from pathlib import Path
from shutil import which


def open_path(path: Path) -> bool:
    """Open a file or folder using the system's default application.

    Args:
        path: Path to the file or folder to open.

    Returns:
        True if the operation was attempted, False if no opener was found.
    """
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)], start_new_session=True)
            return True
        opener = which("xdg-open")
        if opener:
            clean_env = os.environ.copy()
            # Avoid PyInstaller's bundled libs breaking system apps.
            clean_env.pop("LD_LIBRARY_PATH", None)
            clean_env.pop("LD_PRELOAD", None)
            subprocess.Popen(
                [opener, str(path)],
                start_new_session=True,
                env=clean_env,
            )
            return True
    except OSError:
        pass
    return False


def get_exports_folder() -> Path:
    """Get the default exports folder path."""
    return Path.home() / "Downloads" / "bp-order-management"


def open_exports_folder() -> bool:
    """Open the exports folder if it exists.

    Returns:
        True if the folder was opened, False otherwise.
    """
    exports_dir = get_exports_folder()
    if not exports_dir.exists():
        return False
    return open_path(exports_dir)
