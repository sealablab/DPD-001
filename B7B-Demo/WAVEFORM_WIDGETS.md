# Waveform Widget Demos

This directory contains prompt_toolkit-based waveform visualization demos that build on the BpB (Bits per Block) rendering proof of concept.

## New Files

| File | Description |
|------|-------------|
| [screensaver.py](screensaver.py) | Full-screen floating widget screensaver with DVD-logo style bouncing animation |
| [screensaver_repl.py](screensaver_repl.py) | Simple REPL wrapper that launches the screensaver via 'P' command |
| [screensaver_split.py](screensaver_split.py) | Split-screen REPL with embedded waveform widgets (no alternate screen) |

## File Details

### screensaver.py
Full-screen application with two floating waveform widgets that bounce around the screen. Features 20 FPS animation with scrolling waveforms. Uses prompt_toolkit's `FloatContainer` for positioning.

**Run:** `python screensaver.py`

### screensaver_repl.py
Command-line REPL with `RUN>` prompt. Commands B/R/L are stubs; P launches the full-screen screensaver. Press q/x/Escape to return to the REPL.

**Run:** `python screensaver_repl.py`

### screensaver_split.py
Integrated split-screen layout using `HSplit`/`VSplit` (not full-screen mode). Shows two waveform widgets in the top half, REPL in the bottom half, and a status bar with red FAULT indicator and inline animated waveform.

**Run:** `python screensaver_split.py`

## Architecture

All demos reuse the core BpB rendering logic:
- `sample_to_column()` - Maps 7-bit samples to character columns
- `render_waveform()` - Renders sample arrays as character grids
- Four renderer backends: Binary (1 BpB), ASCII (2 BpB), CP437 (2 BpB), Unicode (3 BpB)
