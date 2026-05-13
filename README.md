# BeatScope

Aplicacion de escritorio en Python para analisis profesional de tempo y BPM offline y en directo.

## Objetivo

Pensada para preproduccion y operacion de iluminacion:

- BPM global con confianza
- candidatos half-time / detected / double-time
- Beat grid visual
- Pipeline offline separado del Live con spectral flux multibanda, tempogram, diagnostico y beat grid
- Metronomo visual offline/live con LED balistico para validar el pulso sin generar click audible
- Zonas con cambios de tempo
- Correccion manual de segmentos
- Exportacion a JSON, CSV y TXT
- Deteccion live con estado `searching`, `unstable`, `locked`
- `LOCKED` en live prioriza estabilidad operativa para iluminacion; half/double-time se resuelve con candidatos seleccionables
- Guardia live para evitar lecturas 3:2 tipo `120 BPM -> 80 BPM` en material electronico estable
- Rango LIVE amplio por defecto `35-240` para que `Use main` no fuerce 60/70 BPM a double-time
- Filtro LIVE de rebotes de click para que metronomos lentos no caigan en double-time
- Branding BeatScope con logo, icono de aplicacion, splash de carga y footer de autoria dinamico

## Stack

- Python 3.10+
- PySide6
- pyqtgraph
- numpy / scipy
- librosa / soundfile
- sounddevice

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecucion

```bash
python main.py
```

## Ejecutable Windows

Build recomendado con PyInstaller en formato carpeta (`onedir`). Es el modo principal porque abre mas rapido que `onefile` y evita extracciones temporales grandes en cada arranque:

```powershell
.\tools\build_windows.ps1 -Clean
```

Tambien se puede usar el wrapper:

```bat
build_onedir.bat
```

Si PowerShell bloquea scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows.ps1 -Clean
```

Salida:

```text
dist\BeatScope\BeatScope.exe
```

Distribuye la carpeta completa `dist\BeatScope`, no solo el `.exe`.
Ver detalles y checklist en [docs/PACKAGING.md](docs/PACKAGING.md).

Build opcional `onefile`:

```powershell
.\tools\build_windows.ps1 -Clean -Onefile
```

o:

```bat
build_onefile.bat
```

Salida:

```text
dist\BeatScope.exe
```

El tamano grande del ejecutable/carpeta es normal: BeatScope incluye Qt, audio, DSP numerico y graficos.

## Branding y assets

Los assets publicos viven en `BeatScope_brand_assets/`. La aplicacion carga desde ahi el logo, icono y splash, con fallback seguro si falta algun archivo. El footer y los textos del splash muestran el ano actual dinamicamente junto a `Jose Osuna` y `www.joseosuna.com`.

## Formatos soportados

- WAV
- FLAC
- AIFF
- MP3

Nota: el soporte MP3 depende del backend disponible en tu entorno (`soundfile` o `audioread` via `librosa`).

## Flujo offline

1. Cargar audio
2. Opcional: usar `Cargar Test` para abrir fixtures WAV desde `tests/audio/fixtures`
3. Ajustar parametros de analisis
4. Ejecutar `Analizar`
5. Revisar waveform, beats y segmentos
6. Corregir manualmente en la tabla o con botones de edicion
7. Exportar a JSON, CSV o TXT

La UI offline esta organizada como panel tecnico:

- waveform y beat grid arriba
- `Segmentos` y `Terminal` en pestanas
- `Indicadores` en columna propia
- `Timing`, `Exportacion` y `Advanced` en pestanas laterales

## Modo live

- Seleccion de dispositivo de entrada
- Medidor de nivel dBFS con RMS, peak hold e indicador de clip
- BPM rolling con historial
- Estado de bloqueo
- Tap tempo manual
- Tiempos utiles para iluminacion en BPM x y BPM /
- seleccion de candidato half-time / detected / double-time para usar el clock mas util en iluminacion

## Validacion sintetica

Fixtures versionados y validacion con criterios pass/fail:

```bash
python tools/validate_test_audios.py
```

El reporte Markdown se escribe en:

```text
data/test_reports/bpm_validation_report.md
```

Tambien existe un generador de senales sinteticas:

```bash
python -m bpm_light_mapper.app.audio.synthetic_tests
```

La validacion cubre:

- error de BPM global
- deteccion de zonas esperadas sin solapes
- tolerancia de tempo en casos de half-time y silencios
- baja confianza en material con transitorios debiles

## Limitaciones conocidas

- Puede haber ambiguedad half-time / double-time
- Intros suaves, breaks o percusion difusa reducen confianza
- La segmentacion es heuristica y necesita correccion manual en material complejo
- El modo live prioriza estabilidad util para operacion, no precision de laboratorio
