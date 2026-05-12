# BPM Validation Report

- Total tests: 9
- Passed: 9
- Failed: 0

| File | Expected BPM | Detected BPM | Abs Error | Confidence | Pass |
| --- | ---: | ---: | ---: | ---: | :---: |
| 01_constant_click_120bpm_60s.wav | 120.00 | 120.00 | 0.00 | 1.00 | PASS |
| 02_constant_click_128bpm_60s.wav | 128.00 | 128.00 | 0.00 | 1.00 | PASS |
| 03_kick_hat_128bpm_60s.wav | 128.00 | 128.00 | 0.00 | 0.50 | PASS |
| 04_tempo_map_120_128_124bpm_90s.wav | - | 123.99 | - | 0.50 | PASS |
| 05_128bpm_with_silence_breaks_75s.wav | 128.00 | 128.00 | 0.00 | 0.25 | PASS |
| 06_half_time_70_double_140_60s.wav | 70.00 | 140.00 | 70.00 | 1.00 | PASS |
| 07_gradual_ramp_120_to_128bpm_60s.wav | - | 124.04 | - | 0.50 | PASS |
| 08_waltz_3_4_90bpm_60s.wav | 90.00 | 90.00 | 0.00 | 1.00 | PASS |
| 09_low_onset_pad_100bpm_60s.wav | 100.00 | 114.49 | 14.49 | 0.24 | PASS |

## 01_constant_click_120bpm_60s.wav

- Description: Click track constante a 120 BPM
- Expected BPM: 120.00
- Detected BPM: 120.00
- Absolute error: 0.00
- Confidence: 1.00
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 120.00 BPM | constant click
- Detected: 0.0-60.0s | 120.00 BPM | conf 0.61

## 02_constant_click_128bpm_60s.wav

- Description: Click track constante a 128 BPM
- Expected BPM: 128.00
- Detected BPM: 128.00
- Absolute error: 0.00
- Confidence: 1.00
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 128.00 BPM | constant click
- Detected: 0.0-60.0s | 128.00 BPM | conf 0.61

## 03_kick_hat_128bpm_60s.wav

- Description: Patrón kick/hat constante a 128 BPM, más parecido a música electrónica simple
- Expected BPM: 128.00
- Detected BPM: 128.00
- Absolute error: 0.00
- Confidence: 0.50
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 128.00 BPM | constant kick/hat
- Detected: 0.0-60.0s | 128.00 BPM | conf 0.61

## 04_tempo_map_120_128_124bpm_90s.wav

- Description: Tema sintético con cambios de BPM por zonas
- Expected BPM: -
- Detected BPM: 123.99
- Absolute error: -
- Confidence: 0.50
- Result: PASS

### Segments

- Expected: 0.0-30.0s | 120.00 BPM | intro; 30.0-60.0s | 128.00 BPM | drop; 60.0-90.0s | 124.00 BPM | outro
- Detected: 0.0-29.0s | 120.38 BPM | conf 0.61; 29.0-63.0s | 127.98 BPM | conf 0.61; 63.0-90.0s | 123.98 BPM | conf 0.61

## 05_128bpm_with_silence_breaks_75s.wav

- Description: 128 BPM con silencios/breaks para probar estabilidad y recuperación
- Expected BPM: 128.00
- Detected BPM: 128.00
- Absolute error: 0.00
- Confidence: 0.25
- Result: PASS
- Notes: no false segments detected during silence

### Segments

- Expected: 0.0-20.0s | 128.00 BPM | active audio; 28.0-50.0s | 128.00 BPM | active audio; 57.0-75.0s | 128.00 BPM | active audio
- Detected: 0.0-75.0s | 128.00 BPM | conf 0.56

## 06_half_time_70_double_140_60s.wav

- Description: Caso ambiguo: pulso fuerte a 70 BPM pero subdivisión marcada a 140 BPM
- Expected BPM: 70.00
- Detected BPM: 140.00
- Absolute error: 70.00
- Confidence: 1.00
- Result: PASS
- Notes: global BPM is ambiguous by design

### Segments

- Expected: 0.0-60.0s | 70.00 BPM | half-time/double-time ambiguity
- Detected: 0.0-60.0s | 140.00 BPM | conf 0.61

## 07_gradual_ramp_120_to_128bpm_60s.wav

- Description: Ramp gradual de 120 a 128 BPM, para probar que no todo son segmentos bruscos
- Expected BPM: -
- Detected BPM: 124.04
- Absolute error: -
- Confidence: 0.50
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 124.00 BPM | gradual tempo ramp
- Detected: 0.0-49.0s | 123.55 BPM | conf 0.61; 49.0-60.0s | 127.39 BPM | conf 0.61

## 08_waltz_3_4_90bpm_60s.wav

- Description: Compás 3/4 a 90 BPM, para comprobar que no se confunde con acento de compás
- Expected BPM: 90.00
- Detected BPM: 90.00
- Absolute error: 0.00
- Confidence: 1.00
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 90.00 BPM | waltz meter
- Detected: 0.0-60.0s | 90.00 BPM | conf 0.61

## 09_low_onset_pad_100bpm_60s.wav

- Description: Pad con transitorios débiles a 100 BPM. Caso difícil: debería dar baja confianza.
- Expected BPM: 100.00
- Detected BPM: 114.49
- Absolute error: 14.49
- Confidence: 0.24
- Result: PASS
- Notes: low confidence as expected

### Segments

- Expected: 0.0-60.0s | 100.00 BPM | low onset confidence test
- Detected: 0.0-60.0s | 114.49 BPM | conf 0.66
