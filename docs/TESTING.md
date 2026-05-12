# Testing

## Scope

The current testing approach focuses on signal-validation scaffolding rather than full UI automation.

Main goals:

- verify that BPM estimation is in the expected range
- check whether segment counts are plausible
- observe known failure cases

## Synthetic Validation

Synthetic validation is implemented in:

- [bpm_light_mapper/app/audio/synthetic_tests.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/synthetic_tests.py:1)

It generates controlled audio material for repeatable checks.

## Current Test Cases

### `click_120`

Purpose:

- baseline detection on a clean click track at 120 BPM

Expected:

- global BPM near 120
- 1 stable segment

### `click_128`

Purpose:

- baseline detection on a clean click track at 128 BPM

Expected:

- global BPM near 128
- 1 stable segment

### `tempo_changes`

Purpose:

- verify that multiple stable BPM regions can be separated

Pattern:

- 120 BPM
- 128 BPM
- 124 BPM

Expected:

- approximately 3 detected segments

### `silences`

Purpose:

- evaluate behavior around gaps and missing energy

Expected:

- no excessive micro-segmentation

### `half_time`

Purpose:

- expose ambiguity between felt tempo and technical beat spacing

Expected:

- warning-prone result
- often valid around either half-time or full-time candidate

## Running the Synthetic Tests

```bash
python -m bpm_light_mapper.app.audio.synthetic_tests
```

Expected outputs:

- generated WAV files in `synthetic_test_output/`
- JSON report in `synthetic_test_output/report.json`

## What to Inspect in the Report

- `detected_global_bpm`
- `global_bpm_error`
- `detected_segments`
- `segment_bpms`
- `warnings`

## Manual Testing Checklist

### Offline

- load WAV
- load FLAC
- load MP3 if backend support is available
- run analysis with default parameters
- increase and decrease onset sensitivity
- increase and decrease minimum BPM change threshold
- check beat offset application
- edit segment values in table
- export JSON
- export CSV
- export TXT

### Live

- verify device list loads
- start and stop stream cleanly
- confirm level meter reacts to input
- confirm BPM history graph updates
- test tap tempo
- test manual lock
- verify unstable input does not present falsely stable values

## Suggested Future Test Additions

- tempo ramp synthetic case
- swing groove case
- sparse kick / offbeat percussion case
- heavy syncopation case
- low-level noisy live-source simulation
- regression dataset from real show tracks

## Current Limitations

- no automated GUI tests yet
- no benchmark dataset from real songs yet
- no strict pass/fail thresholds committed yet
- current synthetic tests still need execution in an environment with write permission
