# BPM Light Mapper Architecture

## Goal

`BPM Light Mapper` is a desktop tool for lighting preproduction and live operation. It focuses on:

- offline BPM mapping over time
- beat grid inspection
- editable tempo zones
- exportable tempo maps
- live BPM estimation with confidence and stability

The architecture prioritizes:

- analysis correctness over visual polish
- manual correction over false certainty
- modular code over a single large file
- UI responsiveness during analysis

## High-Level Structure

```text
bpm_light_mapper/
  main.py
  app/
    audio/
    export/
    models/
    ui/
    utils/
```

## Module Responsibilities

### `app/audio`

- `loader.py`
  - loads supported audio files
  - normalizes metadata
  - converts to mono for analysis
  - keeps sample-rate and channel information

- `beat_tracker.py`
  - computes onset envelope
  - detects beats
  - refines detected peak times against the waveform to reduce frame quantization error
  - estimates BPM from robust peak intervals
  - estimates beat consistency confidence

- `offline_analyzer.py`
  - orchestrates the full offline analysis flow
  - computes global BPM and candidate multiples/divisions
  - emits warnings for tempo ambiguity
  - builds the final `AnalysisResult`

- `tempo_map.py`
  - computes local tempo over sliding windows
  - groups windows into stable BPM segments
  - applies smoothing and minimum segment duration heuristics
  - converts overlapping analysis windows into non-overlapping displayed/exported segment boundaries

- `tempo_candidate_resolver.py`
  - scores half-time, detected and double-time candidates
  - calculates grid, onset and accent alignment metrics
  - reports half-time/double-time ambiguity without hiding alternatives

- `live_analyzer.py`
  - opens selected input device
  - writes incoming audio into a bounded ring buffer
  - performs rolling live tempo estimation in a worker thread
  - applies a narrow 3:2 subdivision guard for common 120 BPM electronic material misread near 80 BPM
  - prepares reduced min/max waveform data for live rendering
  - smooths BPM history
  - emits `searching`, `unstable`, `locked`
  - treats `locked` as operational BPM stability for lighting, while half/double-time certainty is exposed through candidates

- `synthetic_tests.py`
  - generates synthetic validation material
  - runs analysis against controlled cases
  - produces a report for BPM error and segment count

### `app/models`

- `segment.py`
  - editable BPM segment model

- `analysis_result.py`
  - aggregate analysis result for export and UI binding

- `tempo_candidate.py`
  - structured score model for related tempo candidates

### `app/ui`

- `main_window.py`
  - main orchestration layer
  - file loading
  - fixture loading via `Cargar Test`
  - launching analysis in a worker thread
  - segment editing actions
  - playback transport and playhead synchronization
  - waveform/table segment selection coordination
  - compact tabbed offline layout for segments/terminal and timing/export/advanced controls
  - export actions

- `waveform_widget.py`
  - waveform display
  - beat markers
  - segment overlays
  - BPM labels per zone
  - click-to-seek signal emission
  - selected-segment highlighting

- `segment_table.py`
  - editable table for segment start/end/BPM/notes/confirmation

- `live_panel.py`
  - live device selection
  - rolling BPM display
  - fixed-rate UI rendering with `QTimer`
  - optimized live waveform envelope from reduced min/max data
  - visual metronome derived from the displayed live BPM
  - tap tempo
  - manual lock
  - BPM x and BPM / lighting timing grid

- `theme.py`
  - central dark HUD palette
  - global QSS for Qt widgets
  - dark styling for menus and combo dropdown popups
  - shared style helpers for status and action controls

- `metric_card.py`, `status_badge.py`, `section_panel.py`, `timing_grid.py`, `metronome_indicator.py`
  - reusable HUD components for prominent BPM, confidence, status, timing and visual beat pulse displays

### `app/export`

- `export_json.py`
  - full structured export

- `export_csv.py`
  - technician-friendly segment export
  - optional TXT summary export

### `app/utils`

- formatting and logging helpers

### Packaging

- `BPM_Light_Mapper.spec`
  - PyInstaller `onedir` configuration for Windows distribution
  - collects Qt/audio/scientific Python dependencies and test fixtures

- `tools/build_windows.ps1`
  - repeatable Windows build entrypoint
  - installs runtime and build requirements before invoking PyInstaller

## Data Flow

### Offline

1. User loads an audio file.
2. `loader.py` reads audio and metadata.
3. `beat_tracker.py` computes onset envelope and beats.
4. `offline_analyzer.py` estimates global BPM and candidates.
5. `tempo_map.py` derives local BPM windows and merges them into segments.
6. Segment boundaries are normalized so zones are contiguous and non-overlapping.
7. `AnalysisResult` is sent back to the UI thread.
8. UI renders waveform, beat markers and segments.
9. User navigates with waveform clicks or segment table selection.
10. Playback playhead, selected zone and table row stay synchronized.
11. User edits segments manually if needed.
12. Export modules write JSON/CSV/TXT.

### Live

1. User selects an audio input.
2. `live_analyzer.py` opens a streaming input.
3. Rolling windows are converted to onset energy.
4. Tempo is estimated continuously.
5. Smoothed BPM, confidence and state are emitted to the UI.
6. `live_panel.py` shows BPM history, level and lighting timing equivalents.

## Heuristic Areas

The following parts are intentionally heuristic:

- half-time / double-time interpretation
- local tempo estimation per window
- confidence scoring
- segment split thresholding
- live-state classification

These are designed to be practical, not academically exact.

## Why Manual Correction Exists

Real music introduces failure cases:

- intros without clear transients
- sparse percussion
- heavy syncopation
- swing and groove
- tempo ramps
- breakdowns and fills
- half-time feel with full-time tempo

Because of this, manual correction is a first-class feature rather than an afterthought.

## Current Limitations

- no audible click/metronome preview yet
- no direct drag editing of segment boundaries on the waveform yet
- live mode is useful but still basic
- no beat-grid snapping tools yet
- no dedicated persistence format for manual edit history yet
- playback depends on codecs available to Qt Multimedia on the host machine

## Planned Direction

Near-term direction:

- click preview
- stronger segment editing UX
- better live lock behavior
- improved synthetic validation
- optional downbeat alignment tools
