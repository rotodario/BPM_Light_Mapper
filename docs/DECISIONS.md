# Architectural Decisions

## ADR-001: PySide6 for Desktop UI

Decision:

- use `PySide6` as the main desktop UI toolkit

Reasoning:

- better long-term desktop UX than Tkinter for this use case
- suitable for threaded workflows
- integrates well with `pyqtgraph`

Tradeoff:

- heavier dependency footprint

## ADR-002: pyqtgraph for Waveform and Live Graphs

Decision:

- use `pyqtgraph` for timeline-style visualizations

Reasoning:

- lightweight and responsive for waveform-like plotting
- better interactivity path than embedding matplotlib for this app

Tradeoff:

- custom editing UX still needs to be built manually

## ADR-003: librosa for Offline Tempo Analysis

Decision:

- use `librosa` as the main offline DSP helper

Reasoning:

- mature onset and beat utilities
- practical feature set for initial implementation
- allows building heuristics around a stable base

Tradeoff:

- tempo estimation still requires app-level interpretation

## ADR-004: Manual Correction as a Core Feature

Decision:

- manual editability is part of the core architecture, not a fallback

Reasoning:

- real-world lighting preparation cannot trust automatic segmentation alone
- user needs editable zones, notes and confirmations

Tradeoff:

- more UI complexity

## ADR-005: Confidence Instead of False Precision

Decision:

- expose confidence and state, not only BPM

Reasoning:

- more honest for ambiguous material
- improves operator trust

Tradeoff:

- confidence is heuristic and must be explained clearly in the UI and docs
