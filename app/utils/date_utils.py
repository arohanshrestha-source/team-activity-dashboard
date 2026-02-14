"""
Date and time utilities. Uses system time (no external API).
"""
from datetime import datetime
from typing import Any, Dict


def get_current_datetime_info() -> Dict[str, Any]:
    """Return current date and time as a structured dict for the chatbot."""
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "date_formatted": now.strftime("%A, %B %d, %Y"),
        "time_12h": now.strftime("%I:%M %p"),
        "time_24h": now.strftime("%H:%M"),
        "day_of_week": now.strftime("%A"),
        "month": now.strftime("%B"),
        "year": now.strftime("%Y"),
        "iso_format": now.isoformat(),
    }
