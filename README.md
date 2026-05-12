# BPM Light Mapper

Aplicacion de escritorio en Python para mapear BPM de audio offline y detectar BPM en directo desde una entrada de audio.

## Objetivo

Pensada para preproduccion y operacion de iluminacion:

- BPM global con confianza
- Beat grid visual
- Zonas con cambios de tempo
- Correccion manual de segmentos
- Exportacion a JSON, CSV y TXT
- Deteccion live con estado `searching`, `unstable`, `locked`

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
- Medidor de nivel
- BPM rolling con historial
- Estado de bloqueo
- Tap tempo manual
- Tiempos utiles para iluminacion en BPM x y BPM /

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
