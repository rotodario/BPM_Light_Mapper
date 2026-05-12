from __future__ import annotations

from datetime import datetime


def timestamped(message: str) -> str:
    now = datetime.now().strftime("%H:%M:%S")
    return f"[{now}] {message}"
