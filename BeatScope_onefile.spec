# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs


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

binaries += collect_dynamic_libs("numpy")
binaries += collect_dynamic_libs("scipy")
binaries += collect_dynamic_libs("soundfile")

brand_assets_dir = ROOT / "BeatScope_brand_assets"
if brand_assets_dir.exists():
    datas.append((str(brand_assets_dir), "BeatScope_brand_assets"))

app_icon = brand_assets_dir / "beatscope.ico"
splash_image = brand_assets_dir / "beatscope_splash.png"


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
        "babel",
        "certifi",
        "docutils",
        "IPython",
        "jupyter",
        "lxml",
        "matplotlib",
        "matplotlib.tests",
        "numpy.tests",
        "OpenGL",
        "pandas",
        "PIL",
        "PyQt5",
        "PyQt6",
        "pygame",
        "pytest",
        "requests",
        "sklearn",
        "scipy.tests",
        "sphinx",
        "tensorflow",
        "torch",
        "torchaudio",
        "torchvision",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "tkinter",
        "urllib3",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
splash = Splash(
    str(splash_image),
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(34, 378),
    text_size=13,
    text_color="#EAF4FF",
) if splash_image.exists() else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    *([splash] if splash is not None else []),
    [],
    name="BeatScope",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(app_icon) if app_icon.exists() else None,
)
