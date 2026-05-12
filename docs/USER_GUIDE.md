# User Guide

## Purpose

`BPM Light Mapper` is intended for lighting preproduction and live support.

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
8. Edit segments manually if needed.
9. Export the result to JSON, CSV or TXT.

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
   - timing values in ms
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
