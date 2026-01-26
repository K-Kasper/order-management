"""Shared date formatting utilities used by UI and service layers."""

from datetime import datetime, timedelta

DATE_DISPLAY = "%d/%m/%Y"
DATE_STORAGE = "%Y-%m-%d"


def parse_date(value: str) -> str | None:
    """Parse a date string from display or storage format to storage format.

    Args:
        value: Date string in DD/MM/YYYY or YYYY-MM-DD format.

    Returns:
        Date string in YYYY-MM-DD format, or None if invalid.
    """
    if not value:
        return None
    for fmt in (DATE_DISPLAY, DATE_STORAGE):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime(DATE_STORAGE)
        except ValueError:
            continue
    return None


def format_date(value: object) -> str:
    """Format a storage date string for display.

    Args:
        value: Date string in YYYY-MM-DD format.

    Returns:
        Date string in DD/MM/YYYY format, or empty string if invalid.
    """
    if not value:
        return ""
    try:
        parsed = datetime.strptime(str(value), DATE_STORAGE)
        return parsed.strftime(DATE_DISPLAY)
    except ValueError:
        return str(value)


def format_datetime(value: object) -> str:
    """Format a datetime string for display.

    Args:
        value: Datetime string in ISO or SQLite format.

    Returns:
        Datetime string in DD/MM/YYYY HH:MM format, or empty string if invalid.
    """
    if not value:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(str(value), fmt)
            return parsed.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return str(value)


def date_status(value: object) -> str:
    """Determine the status of a deadline date relative to today.

    Args:
        value: Date string in YYYY-MM-DD format.

    Returns:
        One of: 'overdue', 'due_today', 'due_soon', 'ok', or 'none'.
    """
    if not value:
        return "none"
    try:
        parsed = datetime.strptime(str(value), DATE_STORAGE).date()
    except ValueError:
        return "none"
    today = datetime.today().date()
    if parsed < today:
        return "overdue"
    if parsed == today:
        return "due_today"
    if parsed <= today + timedelta(days=7):
        return "due_soon"
    return "ok"
