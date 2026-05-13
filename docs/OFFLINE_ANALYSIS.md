# Offline Analysis

## Goal

Offline analysis builds a tempo map for a whole audio file rather than reporting a single BPM number and stopping there.

This is the core value for lighting preproduction.

## Pipeline Overview

1. file load
2. mono conversion for analysis
3. musical onset envelope extraction from spectral flux bands
4. BPM candidate estimation from autocorrelation/tempogram evidence
5. musical half/double-time scoring
6. beat-grid construction and onset snapping
7. local tempo estimation in sliding windows
8. segment grouping and smoothing
9. manual correction in UI
10. export

## Step-by-Step

### 1. File Load

Handled by:

- [loader.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/loader.py:11)

Responsibilities:

- read waveform
- preserve metadata
- normalize to a mono analysis signal

## 2. Musical Onset Envelope

Handled by:

- [offline_rhythm_analyzer.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/offline_rhythm_analyzer.py:1)

Purpose:

- estimate per-frame musical onset strength
- emphasize transient/percussive changes instead of raw waveform amplitude
- reduce the influence of sustained vocals, pads, bass and reverb tails

Why it matters:

- tempo estimation is more reliable from rhythmic energy than from raw waveform amplitude

Current approach:

- normalize the full mono analysis signal
- compute an STFT once for the file
- derive positive spectral flux in several bands:
  - low band for kick-like movement
  - mid band for snare, claps and body transients
  - high band for hats and sharp attacks
  - broadband/transient envelopes for general rhythmic changes
- combine and normalize those envelopes into one offline onset envelope

This is deliberately separate from Live, which must stay causal and low latency.

## 3. BPM Candidates

Handled by:

- [offline_rhythm_analyzer.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/offline_rhythm_analyzer.py:1)

Output:

- primary BPM candidate
- half-time and double-time alternatives
- candidate confidence components
- diagnostic summary

Current approach:

- compute autocorrelation over the combined onset envelope
- extract several candidate periodicities, not only one maximum
- refine autocorrelation lag with sub-frame interpolation
- score each candidate by:
  - onset/grid alignment
  - accent alignment
  - interval stability
  - tempogram strength
- prefer musically plausible candidates without hiding ambiguity

## 3.1 Beat Grid

After choosing a BPM, the offline analyzer builds a regular beat grid and snaps each beat to a nearby strong onset when that improves alignment. This keeps the grid stable while still allowing small timing deviations in material that is not perfectly quantized.

The first beat is stored as the estimated downbeat anchor when available.

## 4. Global BPM

Handled by:

- [offline_analyzer.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/offline_analyzer.py:42)

The global BPM is derived from the onset representation and summarized as:

- primary BPM
- candidate related BPMs
- confidence
- estimated downbeat
- diagnostic summary
- warnings

This is intentionally not treated as the whole truth for the song.

## 4.1 Tempo Candidate Resolver

After a primary BPM is detected, the app evaluates related tempo candidates:

- half-time: `bpm / 2`
- detected: `bpm`
- double-time: `bpm * 2`

Each candidate stores:

- beat interval in milliseconds
- grid alignment score
- onset alignment score
- accent score
- confidence
- whether it is inside the configured BPM range

If multiple candidates score well, the analysis warns about possible half-time/double-time ambiguity.
This is important for material where a musical 60 BPM groove contains hats or other intermediate transients that make 120 BPM look technically plausible.

## 5. Local BPM Windows

Handled by:

- [tempo_map.py](/F:/Descargas/bpm_detec/bpm_light_mapper/app/audio/tempo_map.py:33)

Method:

- analyze overlapping windows through time
- compute local BPM from the local onset envelope, not from the global beat grid
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
