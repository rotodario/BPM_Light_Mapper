# Live Mode

## Goal

The live mode is designed to be operationally useful for lighting, not cosmetically impressive.

It should help an operator answer:

- what BPM am I probably hearing now
- is it stable enough to trust
- has it changed recently
- what are the timing subdivisions in milliseconds

## Current Features

- input device selection
- live start and stop
- input level indicator
- rolling BPM estimation
- confidence display
- state display
- BPM history graph
- tap tempo
- manual tap lock
- beat-length subdivisions in ms

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
- confidence is moderate
- short-term variation is still noticeable

Operational advice:

- usable as a rough guide
- confirm with tap tempo or wait for a clearer section

### `locked`

Meaning:

- confidence is high enough
- recent BPM estimates are consistent

Operational advice:

- suitable for practical timing reference
- still monitor for real tempo changes

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

## Reading the Millisecond Values

For a given BPM:

- `1/1` = one beat
- `1/2` = half beat
- `1/4` = quarter beat
- `1/8` = eighth beat
- `1/16` = sixteenth beat

Formula:

```text
beat_ms = 60000 / BPM
```

Example at 128 BPM:

- `1/1` = 468.75 ms
- `1/2` = 234.38 ms
- `1/4` = 117.19 ms
- `1/8` = 58.59 ms
- `1/16` = 29.30 ms

## Limitations

- live BPM is inherently noisier than offline analysis
- breakdowns and ambience reduce confidence
- half-time vs double-time ambiguity still exists
- detection quality depends strongly on the selected input signal

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
- better lock retention logic
- more explicit live ambiguity warnings
- optional export or network hooks for external lighting tools
