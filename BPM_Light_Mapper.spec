# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


ROOT = Path(SPECPATH)

datas = []
binaries = []
hiddenimports = [
    "audioread",
    "cffi",
    "lazy_loader",
    "librosa",
    "librosa.core",
    "librosa.feature",
    "librosa.feature.spectral",
    "librosa.onset",
    "numba",
    "numpy",
    "pyqtgraph",
    "scipy",
    "scipy.fft",
    "scipy.linalg",
    "scipy.signal",
    "sounddevice",
    "soundfile",
    "soxr",
]

hiddenimports += collect_submodules("lazy_loader")

datas += collect_data_files("PySide6")
binaries += collect_dynamic_libs("numpy")
binaries += collect_dynamic_libs("scipy")
binaries += collect_dynamic_libs("soundfile")

fixtures_dir = ROOT / "tests" / "audio" / "fixtures"
if fixtures_dir.exists():
    datas.append((str(fixtures_dir), "tests/audio/fixtures"))


a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "cupy",
        "IPython",
        "jupyter",
        "matplotlib",
        "matplotlib.tests",
        "numpy.tests",
        "OpenGL",
        "pandas",
        "pygame",
        "pytest",
        "scipy.tests",
        "tensorflow",
        "torch",
        "torchaudio",
        "torchvision",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BPM Light Mapper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BPM Light Mapper",
)
