from __future__ import annotations


try:
    import pyi_splash
except Exception:
    pyi_splash = None


def splash_update(text: str) -> None:
    if pyi_splash is None:
        return
    try:
        pyi_splash.update_text(text)
    except Exception:
        pass


def splash_close() -> None:
    if pyi_splash is None:
        return
    try:
        pyi_splash.close()
    except Exception:
        pass
