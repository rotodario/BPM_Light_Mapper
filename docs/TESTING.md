# Testing

## Scope

The current testing approach focuses on signal-validation scaffolding rather than full UI automation.

Main goals:

- verify that BPM estimation is in the expected range
- check whether segment counts are plausible
- observe known failure cases

## Synthetic Validation

Primary fixture validation is implemented in:

- [tools/validate_test_audios.py](/F:/Descargas/bpm_detec/tools/validate_test_audios.py:1)

It loads committed WAV fixtures from:

- [tests/audio/fixtures](/F:/Descargas/bpm_detec/tests/audio/fixtures/README_TEST_AUDIO.md:1)

Ground truth lives in:

- [tests/audio/fixtures/ground_truth.json](/F:/Descargas/bpm_detec/tests/audio/fixtures/ground_truth.json:1)

The older generator is still available in:

- [bpm_light_mapper/app/audio/synthetic_tests.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/synthetic_tests.py:1)

It generates controlled audio material for repeatable checks when new fixtures are needed.

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

Run the committed fixture validation:

```bash
python tools/validate_test_audios.py
```

Expected output:

- console summary with pass/fail
- Markdown report at `data/test_reports/bpm_validation_report.md`

Run the generator-only script:

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

The validation runner also checks:

- click tracks stay within strict BPM thresholds
- tempo-map fixtures detect at least 2 of 3 expected zones
- detected zones do not overlap
- silence fixtures do not create false fully-silent segments
- half-time/double-time ambiguity is warned instead of hidden
- low-onset material reports low confidence

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
- committed fixtures are synthetic, not a replacement for real show-track validation
- report quality depends on the ground truth metadata staying current
