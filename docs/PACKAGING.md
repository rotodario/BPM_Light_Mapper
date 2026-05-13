# Packaging

## Goal

The recommended Windows delivery format is a PyInstaller `onedir` build:

```text
dist/BeatScope/BeatScope.exe
```

This is more reliable than a single-file executable for this app because it depends on:

- PySide6 Qt plugins
- PortAudio through `sounddevice`
- libsndfile through `soundfile`
- dynamic imports used by `librosa`, `scipy`, `numba` and `lazy_loader`

The user still launches one `.exe`, but the full folder must be distributed.

## Build Environment

Use the same Python major/minor version you want to support on the target machine.
For Windows release builds, use Windows.

Recommended:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

## Build Command

Recommended `onedir` build:

```powershell
.\tools\build_windows.ps1 -Clean
```

or:

```bat
build_onedir.bat
```

If PowerShell blocks script execution on the machine, run it with a temporary execution-policy bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows.ps1 -Clean
```

Output:

```text
dist\BeatScope\BeatScope.exe
```

## Onefile Build

`onefile` is available as a convenience build:

```powershell
.\tools\build_windows.ps1 -Clean -Onefile
```

or:

```bat
build_onefile.bat
```

Output:

```text
dist\BeatScope.exe
```

This uses [BeatScope_onefile.spec](../BeatScope_onefile.spec), embeds the BeatScope icon, uses `BeatScope_brand_assets/beatscope_splash.png` for the PyInstaller splash screen, and bundles `BeatScope_brand_assets` so the logo and PNG/ICO resources are available through the same `_MEIPASS` resource helper used by the app.

Keep `onedir` as the recommended release build until `onefile` has been tested on clean Windows machines. Scientific/audio stacks plus Qt plugins can be more fragile when extracted to PyInstaller's temporary runtime directory.

## What Is Bundled

The spec file includes:

- project Python modules
- PySide6 data/plugins collected by PyInstaller hooks
- `librosa`, `numpy`, `scipy`, `sounddevice`, `soundfile`, `pyqtgraph`
- BeatScope brand assets and application icon
- PyInstaller splash image when `BeatScope_brand_assets/beatscope_splash.png` exists
- runtime splash status text with the current-year author credit from the app branding module

Synthetic test WAV fixtures are not bundled in production builds by default. They are useful during development and validation, but add significant size to the executable folder. In packaged builds, `Cargar Test` will simply report that the fixture folder is not available.

## Build Failure Notes

The build script now stops if PyInstaller fails or if the expected executable is not created.

If folders are created but there is no executable, inspect the PyInstaller error above the final lines. Common causes:

- mixed global/user Python packages
- old compiled packages incompatible with the installed NumPy
- optional packages such as `matplotlib`, `torch`, `pygame` being collected accidentally
- PowerShell execution policy blocking the script

The project spec excludes optional packages that are not used by BeatScope to avoid pulling broken or huge dependencies into the bundle.
The current explicit exclusions are limited to unrelated notebook/ML/plotting/test stacks, optional documentation/network/image packages pulled by third-party hooks, alternate Qt bindings, Tkinter and Qt WebEngine modules. BeatScope still bundles the libraries it actually uses for UI, audio, DSP and plotting.

## What Is Not Guaranteed By Packaging

Packaging does not bypass host system limits:

- LIVE input requires working Windows audio drivers
- microphone/input privacy permissions must allow access
- exclusive-mode ASIO/WASAPI routing can still block devices
- Qt Multimedia playback depends on codecs available to Qt/Windows
- antivirus software may scan or quarantine unsigned executables

For the most reliable playback tests, use WAV or FLAC.

## Release Checklist

1. Run fixture validation:

   ```powershell
   python tools\validate_test_audios.py
   ```

2. Build:

   ```powershell
   .\tools\build_windows.ps1 -Clean
   ```

3. Test the executable from `dist\BeatScope`:

   - open app
   - use `Cargar Test`
   - load an external WAV
   - run analysis
   - export JSON/CSV/TXT
   - open LIVE tab
   - confirm input devices list
   - start/stop LIVE cleanly

4. Zip the full folder:

   ```text
   dist\BeatScope
   ```

Do not distribute only the `.exe` from the folder unless you switch to a tested `onefile` build.

## Onefile Note

`onefile` is supported through `.\tools\build_windows.ps1 -Clean -Onefile`, but it is not the default because audio/Qt plugins and scientific Python packages are more fragile when extracted to a temporary runtime directory.
