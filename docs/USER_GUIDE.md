# User Guide

## Purpose

`BeatScope` is intended for lighting preproduction and live support.

Typical use cases:

- mapping BPM changes across a song
- checking beat alignment before programming cues
- identifying stable tempo sections for chases and effects
- validating tempo assumptions before a show
- estimating live BPM from an input feed

## Main Workflows

### Offline Analysis

1. Open the app.
2. Click `Cargar audio`.
3. Select a supported audio file.
4. Review the file metadata shown at the top.
5. Adjust analysis parameters if needed.
6. Click `Analizar`.
7. Review:
   - global BPM
   - alternate BPM candidates
   - confidence
   - beat markers
   - detected tempo segments
8. Use the waveform playhead to inspect positions:
   - click on the waveform to move playback to that time
   - the matching segment is selected in the table
   - selecting a row in the segment table moves the playhead to that zone
9. Edit segments manually if needed.
10. Export the result to JSON, CSV or TXT.

For quick regression checks, use `Cargar Test` next to `Cargar Audio`.
It opens a dropdown with the WAV fixtures from `tests/audio/fixtures` and loads the selected file through the same offline pipeline.

### Offline Layout

The offline workspace is intentionally compact:

- the top area contains waveform, beat grid, tempo zones and playhead
- the lower-left panel has tabs for `Segmentos` and `Terminal`
- `Indicadores` stays in its own column for constant visibility
- the right column has tabs for `Timing`, `Exportacion` and `Advanced`

### Live Analysis

1. Open the `LIVE` tab.
2. Refresh devices if required.
3. Select the desired audio input.
4. Click `Iniciar LIVE`.
5. Watch:
   - current BPM
   - confidence
   - state
   - input level
   - BPM history
   - BPM x and BPM / timing grid
6. Use `Tap Tempo` when live detection is unstable.
7. Use `Lock TAP` to temporarily hold a manual BPM reference.
8. Click `Parar LIVE` when done.

## Reading the BPM Output

### Global BPM

The global BPM is the broad estimate for the entire file.

Use it for:

- quick cue timing
- rough programming reference
- identifying likely tempo family

Do not assume it is enough when the song changes tempo.

### Alternate BPM Candidates

The app shows likely related values such as:

- half-time
- main estimate
- double-time

Example:

- `70.00 / 140.00`

This is important because many tracks can feel like one while technically matching the other.

### Confidence

Confidence is not a promise of correctness.

It is a practical indicator based on:

- beat regularity
- onset energy consistency
- stability of detected timing

Interpretation:

- high confidence: likely stable and usable
- medium confidence: verify visually and by ear
- low confidence: treat as provisional

## Segment Editing

The segment table is part of the core workflow.

Current operations:

- add zone
- delete zone
- split zone
- merge with next zone
- edit start
- edit end
- edit BPM
- mark confirmed
- add notes

Recommended use:

- keep algorithmic detections as a draft
- confirm the sections you trust
- annotate musical structure such as `intro`, `drop`, `break`, `solo`, `final`

## Waveform and Timeline Navigation

The waveform is the main offline workspace.

What it shows:

- audio amplitude in cyan
- beat markers as thin vertical lines
- tempo zones as translucent regions
- BPM labels inside each detected zone
- non-overlapping tempo zones generated from contiguous analysis boundaries
- a red playhead for the current playback/inspection position

Navigation behavior:

- clicking the waveform moves the playhead and selects the segment at that time
- selecting a segment row moves the playhead to that segment start
- the selected segment is highlighted on the waveform
- `Play` and `Stop` control the loaded audio when the local Qt multimedia backend supports the file codec

If playback does not start for an MP3 or other compressed file, the analysis can still work; install suitable codecs or test with WAV/FLAC for the most predictable playback path.

## Beat Offset

If the first detected beat is not where the real downbeat should be:

1. change `Offset beats (s)`
2. apply the offset
3. verify the beat markers again

This helps when the BPM is correct but the beat grid starts slightly early or late.

## Export Options

### JSON

Best for:

- full archival
- later tooling
- custom integrations

Includes:

- file info
- BPM results
- segments
- beats
- warnings
- parameters

### CSV

Best for:

- spreadsheet review
- cue planning
- lightweight import into other tools

### TXT

Best for:

- technician handoff
- quick show notes
- simple readable summaries

## Recommended Workflow for Lighting

For preproduction:

1. run offline analysis
2. inspect segment boundaries
3. confirm stable sections
4. annotate structure
5. export CSV or TXT for programming references

For live:

1. use live BPM as a guidance tool
2. verify stability state before trusting values
3. use tap lock when the source is noisy or sparse

## Known Limits

- automatic detection can misread half-time and double-time
- sparse intros and atmospheric sections reduce confidence
- live mode is helpful but should not replace operator judgement
- swing and tempo ramps need careful review
- click/metronome audition is not implemented yet
