from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QIcon


APP_NAME = "BeatScope"
APP_SUBTITLE = "BPM & Audio Tempo Analysis"
ASSETS_FOLDER = "BeatScope_brand_assets"
AUTHOR_NAME = "Jose Osuna"
AUTHOR_URL = "www.joseosuna.com"
CURRENT_YEAR = datetime.now().year
AUTHOR_CREDIT = f"{CURRENT_YEAR} {AUTHOR_NAME}  {AUTHOR_URL}"
FOOTER_TEXT = f"{APP_NAME} · {CURRENT_YEAR} {AUTHOR_NAME} · {AUTHOR_URL}"


def resource_path(relative_path: str) -> Path:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return Path(base_path) / relative_path
    return Path(__file__).resolve().parents[3] / relative_path


ASSETS_DIR = resource_path(ASSETS_FOLDER)
ICON_PATH = ASSETS_DIR / "beatscope.ico"
ICON_PNG_PATH = ASSETS_DIR / "beatscope_icon_256_transparent.png"
LOGO_DARK_PATH = ASSETS_DIR / "beatscope_logo_dark_ui_transparent.png"


def window_icon() -> QIcon:
    for path in (ICON_PATH, ICON_PNG_PATH):
        if path.exists():
            return QIcon(str(path))
    return QIcon()
