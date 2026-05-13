"""Version information for the application."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["get_version"]


def get_version() -> str | None:
    """
    Get the application version from package metadata.

    Returns the version from installed package metadata if available,
    otherwise returns None (version will not be displayed).

    Returns:
        Version string (e.g., "0.1.1") or None if unavailable
    """
    try:
        return version("bp-order-management")
    except PackageNotFoundError:
        # Version unavailable - will not be displayed in UI
        return None
