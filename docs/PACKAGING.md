# Packaging

## Goal

The recommended Windows delivery format is a PyInstaller `onedir` build:

```text
dist/BPM Light Mapper/BPM Light Mapper.exe
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

```powershell
.\tools\build_windows.ps1 -Clean
```

If PowerShell blocks script execution on the machine, run it with a temporary execution-policy bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows.ps1 -Clean
```

Output:

```text
dist\BPM Light Mapper\BPM Light Mapper.exe
```

## What Is Bundled

The spec file includes:

- project Python modules
- PySide6 data/plugins collected by PyInstaller hooks
- `librosa`, `numpy`, `scipy`, `sounddevice`, `soundfile`, `pyqtgraph`
- test audio fixtures for the `Cargar Test` dropdown

## Build Failure Notes

The build script now stops if PyInstaller fails or if the expected executable is not created.

If folders are created but there is no executable, inspect the PyInstaller error above the final lines. Common causes:

- mixed global/user Python packages
- old compiled packages incompatible with the installed NumPy
- optional packages such as `matplotlib`, `torch`, `pygame` being collected accidentally
- PowerShell execution policy blocking the script

The project spec excludes optional packages that are not used by BPM Light Mapper to avoid pulling broken or huge dependencies into the bundle.

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

3. Test the executable from `dist\BPM Light Mapper`:

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
   dist\BPM Light Mapper
   ```

Do not distribute only the `.exe` from the folder unless you switch to a tested `onefile` build.

## Onefile Note

`onefile` can be attempted later, but it is not the default because audio/Qt plugins and scientific Python packages are more fragile when extracted to a temporary runtime directory.
