# BeatScope - Test Audio Pack

Audios sintéticos para probar detección de BPM, beat grid, segmentación por zonas y casos difíciles.

## Archivos

01_constant_click_120bpm_60s.wav
- Caso fácil: click constante a 120 BPM.
- Debe detectar 120 BPM con mucha confianza.

02_constant_click_128bpm_60s.wav
- Caso fácil: click constante a 128 BPM.
- Debe detectar 128 BPM con mucha confianza.

03_kick_hat_128bpm_60s.wav
- Patrón kick/hat a 128 BPM, más parecido a música electrónica simple.
- Debe detectar 128 BPM.

04_tempo_map_120_128_124bpm_90s.wav
- Cambios por zonas:
  00:00 - 00:30 = 120 BPM
  00:30 - 01:00 = 128 BPM
  01:00 - 01:30 = 124 BPM
- Sirve para validar la segmentación temporal.

05_128bpm_with_silence_breaks_75s.wav
- 128 BPM con silencios:
  00:00 - 00:20 activo
  00:20 - 00:28 silencio
  00:28 - 00:50 activo
  00:50 - 00:57 silencio
  00:57 - 01:15 activo
- Sirve para probar que el algoritmo no se vuelva loco en breaks.

06_half_time_70_double_140_60s.wav
- Caso ambiguo.
- Pulso fuerte a 70 BPM, subdivisión a 140 BPM.
- El programa debería mostrar posible half-time/double-time.

07_gradual_ramp_120_to_128bpm_60s.wav
- Rampa gradual de 120 a 128 BPM.
- Sirve para comprobar que el programa no fuerce todo a zonas bruscas.

08_waltz_3_4_90bpm_60s.wav
- Compás 3/4 a 90 BPM.
- Sirve para comprobar que no confunde acento de compás con tempo.

09_low_onset_pad_100bpm_60s.wav
- Caso difícil: pad con transitorios débiles a 100 BPM.
- Idealmente debería detectar con baja confianza o avisar de señal poco clara.

## Archivos de referencia

ground_truth.json
- Verdad esperada en formato estructurado.

ground_truth_segments.csv
- Segmentos esperados en CSV.

## Recomendación

Copia esta carpeta dentro del repo:

tests/audio/fixtures/

Luego crea un script tipo:

python tools/validate_test_audios.py

que analice todos los WAV, compare contra ground_truth.json y genere un reporte de error:
- error absoluto BPM
- segmentos detectados
- segmentos perdidos
- half-time/double-time detectado
- confidence media
