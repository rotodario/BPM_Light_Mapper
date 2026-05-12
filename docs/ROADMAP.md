# BPM Light Mapper Roadmap

## Phase 1: Foundation

Status: mostly complete

- project structure
- offline analysis pipeline
- waveform and segment UI
- JSON/CSV/TXT export
- basic live mode
- synthetic validation scaffolding
- dark HUD UI foundation
- logging foundation

## Phase 2: Editing Workflow

Status: in progress

- audio playback inside the app
- waveform playhead and click-to-seek navigation
- synchronized waveform/table segment selection
- click/metronome preview over detected beats
- better segment creation workflow
- direct visual segment split/merge helpers
- downbeat offset and beat-grid alignment tools
- stronger warnings around half-time and double-time

## Phase 3: Precision Improvements

Status: planned

- improved confidence model
- beat-grid regularity diagnostics
- segment hysteresis refinement
- adaptive window sizing
- tempo ramp detection vs hard segment changes
- better handling for silence and breakdowns

## Phase 4: Live Utility

Status: in progress

- stronger live smoothing and lock logic
- manual hold / release BPM modes
- tap-tempo assisted lock
- change markers on live graph
- optional MIDI or OSC export hooks for external lighting workflows

## Phase 5: Production Readiness

Status: planned

- packaging for Windows desktop use
- saved project sessions
- recent files and autosave
- richer error diagnostics
- validation report improvements
- example assets and demo tempo maps

## Stretch Goals

- beat-grid snapping editor
- waveform zoom controls
- cue-sheet export profiles
- Ableton / DAW friendly timing exports
- plugin or scripting hook for custom lighting pipelines
