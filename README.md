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
2. Ajustar parametros de analisis
3. Ejecutar `Analizar`
4. Revisar waveform, beats y segmentos
5. Corregir manualmente en la tabla o con botones de edicion
6. Exportar a JSON, CSV o TXT

## Modo live

- Seleccion de dispositivo de entrada
- Medidor de nivel
- BPM rolling con historial
- Estado de bloqueo
- Tap tempo manual
- Tiempos utiles para iluminacion en BPM x y BPM /

## Validacion sintetica

Genera senales sinteticas y ejecuta un analisis basico:

```bash
python -m bpm_light_mapper.app.audio.synthetic_tests
```

Esto crea un reporte con:

- error de BPM global
- deteccion de zonas esperadas
- tolerancia de tempo en casos de half-time y silencios

## Limitaciones conocidas

- Puede haber ambiguedad half-time / double-time
- Intros suaves, breaks o percusion difusa reducen confianza
- La segmentacion es heuristica y necesita correccion manual en material complejo
- El modo live prioriza estabilidad util para operacion, no precision de laboratorio
