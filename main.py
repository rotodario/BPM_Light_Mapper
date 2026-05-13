import ctypes
import sys
from typing import Optional


def _claim_single_instance() -> Optional[object]:
    if sys.platform != "win32":
        return None
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "BeatScope_SingleInstance_Mutex")
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(
            None,
            "BeatScope ya se esta iniciando o ya esta abierto.",
            "BeatScope",
            0x40,
        )
        raise SystemExit(0)
    return mutex


_BEATSCOPE_MUTEX = _claim_single_instance()


if __name__ == "__main__":
    from bpm_light_mapper.main import main

    raise SystemExit(main())
