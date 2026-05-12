# BPM Light Mapper Status

## Implemented

- modular Python project structure
- desktop UI with PySide6
- offline file loading for WAV/FLAC/AIFF and MP3 fallback path
- global BPM estimation
- beat detection
- local BPM window analysis
- tempo-zone segmentation with contiguous non-overlapping boundaries
- segment table editing
- add/delete/split/merge segment actions
- manual beat offset application
- embedded playback transport with play/stop
- waveform playhead and click-to-seek navigation
- bidirectional selection between waveform position and segment table
- JSON/CSV/TXT export
- live device listing
- live BPM estimation with rolling history
- live confidence and state labels
- tap tempo and manual lock
- dark HUD UI theme for offline and live operation
- dark styled dropdowns for test loading and live input selection
- application logging for analysis and live diagnostics
- synthetic test generator script
- committed synthetic audio fixtures and validation runner
- Markdown BPM validation report generation

## Not Implemented Yet

- click/metronome preview
- draggable segment boundary editing
- explicit beat audition
- persistent project save/load
- advanced confidence diagnostics UI

## Current Focus

- reduce analysis stalls on long or unusual audio
- keep UI responsive while loading, analyzing and running live input
- improve waveform/timeline editing ergonomics
- expand validation from synthetic fixtures toward real show-track regression cases
