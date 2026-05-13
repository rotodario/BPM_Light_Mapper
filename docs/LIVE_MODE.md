# Live Mode

## Goal

The live mode is designed to be operationally useful for lighting, not cosmetically impressive.

It should help an operator answer:

- what BPM am I probably hearing now
- is it stable enough to trust
- has it changed recently
- what are the timing equivalents in BPM for useful lighting divisions

## Current Features

- input device selection
- live start and stop
- input level indicator
- rolling BPM estimation
- confidence display
- state display
- BPM history graph
- optimized live waveform envelope
- tap tempo
- manual tap lock
- BPM x and BPM / timing grid for lighting divisions
- dark HUD panel optimized for visibility from a control position
- non-blocking live startup so device errors should return to the UI instead of freezing it
- half-time / detected / double-time candidate display and selection
- preferred BPM range presets for slow, normal and fast material

## Runtime Architecture

The live path is designed like a real-time instrument panel:

```text
audio input -> ring buffer -> DSP blocks -> reduced visual state -> fixed-rate UI render
```

Key rules:

- the audio callback only converts input to mono and writes blocks into the ring buffer
- BPM analysis runs in a worker thread at a lower stable rate
- waveform/level visual data is reduced in a separate visual loop
- the UI renders from the latest processed state with a fixed `QTimer`
- the waveform uses min/max columns instead of drawing every sample
- buffers and histories have bounded sizes

This means the UI should remain responsive even if BPM analysis is temporarily expensive.

## Half-Time / Double-Time

Live mode evaluates candidate tempos around the detected value:

- half-time
- detected
- double-time

Use the candidate buttons when the useful lighting clock differs from the detected rhythmic subdivision.
For example, a 60 BPM groove with hats can produce a strong 120 BPM detection; selecting half-time keeps the display and timing grid aligned to 60 BPM.

## Detection States

### `searching`

Meaning:

- not enough stable evidence yet
- low confidence
- weak or inconsistent transients

Operational advice:

- do not trust this BPM for programming decisions without manual confirmation

### `unstable`

Meaning:

- a BPM estimate exists
- confidence is low/moderate or short-term variation is still noticeable

Operational advice:

- usable as a rough guide
- confirm with tap tempo or wait for a clearer section

### `locked`

Meaning:

- input level is present
- recent BPM estimates are consistent
- confidence is high enough to trust the clock operationally

Operational advice:

- suitable for practical timing reference
- still monitor for real tempo changes

Important:

- `locked` does not mean the app has solved the musical half-time/double-time question with absolute certainty
- a drum groove can be locked while still showing valid half/detected/double candidates
- use the candidate buttons when the lighting clock should follow a different subdivision

### `manual-lock`

Meaning:

- tap tempo is overriding the displayed BPM

Operational advice:

- useful when detection becomes unreliable
- remember it is a manual reference, not a live measurement

## Recommended Use in Lighting

### Chases and Movement

Use the displayed BPM plus beat subdivisions to derive:

- sweep timing
- movement accents
- chase stepping rate

### Strobes and Bumps

Use:

- `1/4`
- `1/8`
- `1/16`

These are often the quickest practical values for effect timing.

### During Unstable Sources

Examples:

- audience mics
- monitor feeds
- sparse intros
- speech sections

Recommended approach:

1. watch confidence and state
2. tap manually if needed
3. engage `Lock TAP` if you need a stable working reference

## Reading the BPM Equivalents

The timing grid shows the base BPM multiplied and divided by common lighting factors:

- `1x`
- `2x`
- `4x`
- `8x`
- `16x`

and the corresponding `/` column for lower-rate equivalents.

This is useful when you want to program chases, strobes or bumps against a faster or slower clock without doing the mental math live.

## Limitations

- live BPM is inherently noisier than offline analysis
- breakdowns and ambience reduce confidence
- half-time vs double-time ambiguity still exists
- detection quality depends strongly on the selected input signal
- device drivers can still fail or block at OS/backend level; app logs are the first place to inspect these cases

## Good Input Sources

Prefer:

- direct mixer feed
- music bus
- clean playback output

Avoid if possible:

- room microphone
- heavily compressed or distorted monitoring signal
- speech-heavy mixed feeds

## Planned Improvements

- stronger change markers
- expose raw BPM / locked BPM / confidence diagnostics in the UI
- more explicit live ambiguity warnings
- optional export or network hooks for external lighting tools
- lower-level backend diagnostics per audio device
