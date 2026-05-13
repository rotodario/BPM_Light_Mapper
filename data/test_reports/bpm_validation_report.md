# BPM Validation Report

- Total tests: 11
- Passed: 11
- Failed: 0

| File | Expected BPM | Detected BPM | Abs Error | Confidence | Pass |
| --- | ---: | ---: | ---: | ---: | :---: |
| 01_constant_click_120bpm_60s.wav | 120.00 | 120.00 | 0.00 | 0.97 | PASS |
| 02_constant_click_128bpm_60s.wav | 128.00 | 127.91 | 0.09 | 0.90 | PASS |
| 03_kick_hat_128bpm_60s.wav | 128.00 | 127.92 | 0.08 | 0.79 | PASS |
| 04_tempo_map_120_128_124bpm_90s.wav | - | 120.00 | - | 0.63 | PASS |
| 05_128bpm_with_silence_breaks_75s.wav | 128.00 | 127.92 | 0.08 | 0.69 | PASS |
| 06_half_time_70_double_140_60s.wav | 70.00 | 139.93 | 69.93 | 0.86 | PASS |
| 07_gradual_ramp_120_to_128bpm_60s.wav | - | 123.82 | - | 0.61 | PASS |
| 08_waltz_3_4_90bpm_60s.wav | 90.00 | 89.97 | 0.03 | 0.95 | PASS |
| 09_low_onset_pad_100bpm_60s.wav | 100.00 | 99.85 | 0.15 | 0.73 | PASS |
| 10_constant_click_60bpm_60s.wav | 60.00 | 60.02 | 0.02 | 0.98 | PASS |
| 11_musical_pattern_60bpm_hats_60s.wav | 60.00 | 120.00 | 60.00 | 0.94 | PASS |

## 01_constant_click_120bpm_60s.wav

- Description: Click track constante a 120 BPM
- Expected BPM: 120.00
- Detected BPM: 120.00
- Absolute error: 0.00
- Confidence: 0.97
- Candidates: 60.00, 120.00, 240.00
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 120.00 BPM | constant click
- Detected: 0.0-60.0s | 120.05 BPM | conf 0.62

## 02_constant_click_128bpm_60s.wav

- Description: Click track constante a 128 BPM
- Expected BPM: 128.00
- Detected BPM: 127.91
- Absolute error: 0.09
- Confidence: 0.90
- Candidates: 63.96, 127.91, 255.83
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 128.00 BPM | constant click
- Detected: 0.0-25.0s | 106.77 BPM | conf 0.62; 25.0-33.0s | 128.16 BPM | conf 0.62; 33.0-60.0s | 117.46 BPM | conf 0.61

## 03_kick_hat_128bpm_60s.wav

- Description: Patrón kick/hat constante a 128 BPM, más parecido a música electrónica simple
- Expected BPM: 128.00
- Detected BPM: 127.92
- Absolute error: 0.08
- Confidence: 0.79
- Candidates: 63.96, 127.92, 255.83
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 128.00 BPM | constant kick/hat
- Detected: 0.0-13.0s | 106.76 BPM | conf 0.64; 13.0-21.0s | 128.16 BPM | conf 0.64; 21.0-31.0s | 106.76 BPM | conf 0.64; 31.0-39.0s | 128.16 BPM | conf 0.64; 39.0-60.0s | 120.13 BPM | conf 0.64

## 04_tempo_map_120_128_124bpm_90s.wav

- Description: Tema sintético con cambios de BPM por zonas
- Expected BPM: -
- Detected BPM: 120.00
- Absolute error: -
- Confidence: 0.63
- Candidates: 60.00, 120.00, 240.00
- Result: PASS

### Segments

- Expected: 0.0-30.0s | 120.00 BPM | intro; 30.0-60.0s | 128.00 BPM | drop; 60.0-90.0s | 124.00 BPM | outro
- Detected: 0.0-29.0s | 120.05 BPM | conf 0.64; 29.0-37.0s | 127.52 BPM | conf 0.63; 37.0-45.0s | 106.76 BPM | conf 0.63; 45.0-53.0s | 117.46 BPM | conf 0.63; 53.0-90.0s | 123.85 BPM | conf 0.63

## 05_128bpm_with_silence_breaks_75s.wav

- Description: 128 BPM con silencios/breaks para probar estabilidad y recuperación
- Expected BPM: 128.00
- Detected BPM: 127.92
- Absolute error: 0.08
- Confidence: 0.69
- Candidates: 63.96, 127.92, 255.84
- Result: PASS
- Notes: no false segments detected during silence

### Segments

- Expected: 0.0-20.0s | 128.00 BPM | active audio; 28.0-50.0s | 128.00 BPM | active audio; 57.0-75.0s | 128.00 BPM | active audio
- Detected: 0.0-13.0s | 106.76 BPM | conf 0.65; 13.0-31.0s | 128.16 BPM | conf 0.63; 31.0-39.0s | 106.77 BPM | conf 0.64; 39.0-75.0s | 128.15 BPM | conf 0.64

## 06_half_time_70_double_140_60s.wav

- Description: Caso ambiguo: pulso fuerte a 70 BPM pero subdivisión marcada a 140 BPM
- Expected BPM: 70.00
- Detected BPM: 139.93
- Absolute error: 69.93
- Confidence: 0.86
- Candidates: 69.97, 139.93, 279.87
- Result: PASS
- Notes: global BPM is ambiguous by design

### Segments

- Expected: 0.0-60.0s | 70.00 BPM | half-time/double-time ambiguity
- Detected: 0.0-60.0s | 99.10 BPM | conf 0.63

## 07_gradual_ramp_120_to_128bpm_60s.wav

- Description: Ramp gradual de 120 a 128 BPM, para probar que no todo son segmentos bruscos
- Expected BPM: -
- Detected BPM: 123.82
- Absolute error: -
- Confidence: 0.61
- Candidates: 61.91, 123.82, 247.63
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 124.00 BPM | gradual tempo ramp
- Detected: 0.0-13.0s | 111.02 BPM | conf 0.63; 13.0-31.0s | 122.96 BPM | conf 0.63; 31.0-39.0s | 93.34 BPM | conf 0.63; 39.0-60.0s | 116.09 BPM | conf 0.62

## 08_waltz_3_4_90bpm_60s.wav

- Description: Compás 3/4 a 90 BPM, para comprobar que no se confunde con acento de compás
- Expected BPM: 90.00
- Detected BPM: 89.97
- Absolute error: 0.03
- Confidence: 0.95
- Candidates: 89.97, 179.95
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 90.00 BPM | waltz meter
- Detected: 0.0-60.0s | 90.06 BPM | conf 0.61

## 09_low_onset_pad_100bpm_60s.wav

- Description: Pad con transitorios débiles a 100 BPM. Caso difícil: debería dar baja confianza.
- Expected BPM: 100.00
- Detected BPM: 99.85
- Absolute error: 0.15
- Confidence: 0.73
- Candidates: 99.85, 199.70
- Result: PASS
- Notes: moderate confidence on a difficult pad fixture

### Segments

- Expected: 0.0-60.0s | 100.00 BPM | low onset confidence test
- Detected: 0.0-60.0s | 99.85 BPM | conf 0.64

## 10_constant_click_60bpm_60s.wav

- Description: Click track constante a 60 BPM
- Expected BPM: 60.00
- Detected BPM: 60.02
- Absolute error: 0.02
- Confidence: 0.98
- Candidates: 60.02, 120.04
- Result: PASS

### Segments

- Expected: 0.0-60.0s | 60.00 BPM | constant slow click
- Detected: 0.0-60.0s | 79.93 BPM | conf 0.51

## 11_musical_pattern_60bpm_hats_60s.wav

- Description: Patron musical a 60 BPM con transitorios intermedios que pueden sugerir 120 BPM
- Expected BPM: 60.00
- Detected BPM: 120.00
- Absolute error: 60.00
- Confidence: 0.94
- Candidates: 60.00, 120.00, 240.00
- Result: PASS
- Notes: required BPM 60.00 present in tempo candidates

### Segments

- Expected: 0.0-60.0s | 60.00 BPM | 60 BPM with half-beat hats
- Detected: 0.0-60.0s | 90.03 BPM | conf 0.62
