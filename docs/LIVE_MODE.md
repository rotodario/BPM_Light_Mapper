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
- tap tempo
- manual tap lock
- BPM x and BPM / timing grid for lighting divisions
- dark HUD panel optimized for visibility from a control position
- non-blocking live startup so device errors should return to the UI instead of freezing it

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
- better lock retention logic
- more explicit live ambiguity warnings
- optional export or network hooks for external lighting tools
- lower-level backend diagnostics per audio device
