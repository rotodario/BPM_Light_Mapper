# Contributing

## Development Principles

- prefer maintainable modules over clever shortcuts
- do not hide uncertainty in BPM detection
- preserve manual correction workflows
- keep the UI responsive during analysis
- avoid destructive git operations

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Validation

Run the synthetic validator:

```bash
python -m bpm_light_mapper.app.audio.synthetic_tests
```

Expected outcome:

- generated synthetic WAV files
- JSON report with BPM error and segment counts

## Commit Scope Guidance

Prefer small commits grouped by concern:

- UI changes
- offline analysis changes
- live analysis changes
- export changes
- documentation changes

## Coding Notes

- use `apply_patch` for direct file edits when working through Codex
- keep comments short and purposeful
- favor explicit data models for anything exported or edited by the UI
