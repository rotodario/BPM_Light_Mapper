# Offline Analysis

## Goal

Offline analysis builds a tempo map for a whole audio file rather than reporting a single BPM number and stopping there.

This is the core value for lighting preproduction.

## Pipeline Overview

1. file load
2. mono conversion for analysis
3. onset envelope extraction
4. beat detection
5. global tempo estimation
6. local tempo estimation in sliding windows
7. segment grouping and smoothing
8. manual correction in UI
9. export

## Step-by-Step

### 1. File Load

Handled by:

- [loader.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/loader.py:11)

Responsibilities:

- read waveform
- preserve metadata
- normalize to a mono analysis signal

## 2. Onset Envelope

Handled by:

- [beat_tracker.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/beat_tracker.py:7)

Purpose:

- estimate per-frame onset strength
- capture rhythmic energy over time

Why it matters:

- tempo estimation is more reliable from rhythmic energy than from raw waveform amplitude

## 3. Beat Detection

Handled by:

- [beat_tracker.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/beat_tracker.py:7)

Output:

- estimated beat times
- base tempo estimate

These beats are visualized in the timeline and later included in exports.

Current approach:

- detect onset peaks independently from the first tempo estimate
- estimate BPM from robust intervals between peaks
- refine peak positions against the waveform to reduce frame quantization error
- keep half-time/double-time candidates visible instead of pretending there is only one answer

## 4. Global BPM

Handled by:

- [offline_analyzer.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/offline_analyzer.py:42)

The global BPM is derived from the onset representation and summarized as:

- primary BPM
- candidate related BPMs
- confidence
- warnings

This is intentionally not treated as the whole truth for the song.

## 5. Local BPM Windows

Handled by:

- [tempo_map.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/tempo_map.py:33)

Method:

- analyze overlapping windows through time
- compute local BPM for each valid window
- estimate local confidence

This allows the app to detect tempo changes and stable sections.

## 6. Segment Grouping

The app does not create a new segment for every local fluctuation.

It uses practical constraints:

- minimum BPM change to justify a split
- minimum segment duration
- smoothing across nearby windows

This avoids absurd micro-segments caused by noise.

Important boundary rule:

- analysis windows may overlap, but exported/displayed segments must not
- grouped tempo runs are converted into contiguous boundaries using window centers
- this prevents visual zones like `0-34`, `24-68`, `58-90` from overlapping on the timeline

## Key Parameters

### Window (s)

Controls:

- how much material is used for each local tempo estimate

Smaller values:

- faster reaction
- less stability

Larger values:

- more stability
- less responsiveness to quick changes

### Hop (s)

Controls:

- spacing between local analysis windows

Smaller values:

- more temporal detail
- more computation

### Minimum BPM Change

Controls:

- how different the local BPM must be before a new zone is created

Lower values:

- more segments
- more sensitivity to drift

Higher values:

- fewer segments
- more conservative splitting

### Minimum Segment Duration

Controls:

- shortest practical zone allowed after grouping

This is important for avoiding noise-driven fragmentation.

### Onset Sensitivity

Controls:

- how strongly onset activity influences analysis

Useful when material is:

- too soft
- too transient-heavy

### BPM Min / Max

Controls:

- allowed search range

Use tighter bounds when you know the music style in advance.

## Manual Review Guidance

After analysis, check:

- are beat markers visually plausible
- do segment boundaries match musical structure
- are detected BPM shifts real or just transient changes
- does the result confuse half-time and full-time feel

If not:

- adjust parameters
- reanalyze
- manually edit the resulting zones

## Typical Failure Cases

- ambient intros
- fills and breaks
- rubato sections
- extreme syncopation
- half-time groove against full-time clock
- weak drum presence in the mix

## Why This Still Helps

Even when imperfect, the offline map is useful because it gives:

- tempo families
- likely beat spacing
- rough structural segmentation
- editable timing references for programming

That is much more useful for lighting work than a single BPM number with fake certainty.
