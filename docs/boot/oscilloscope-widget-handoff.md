# Oscilloscope Widget Implementation Handoff

This document provides context for an LLM assistant to help implement the oscilloscope widget.

---

## Quick Context

You are helping implement a **text-based oscilloscope widget** for a terminal-based BIOS client. The widget renders waveform data as Unicode art using `prompt_toolkit`.

**Key files to read first:**
1. `docs/design/oscilloscope-widget-spec.md` - Full specification (READ THIS)
2. `py_tools/boot_shell.py` - Existing shell to integrate with
3. `py_tools/boot_constants.py` - HVS and state constants
4. `docs/bootup-proposal/BOOT-ROM-primitives-spec.md` - ROM waveform definitions

---

## Implementation Prompt

Use this prompt to start an implementation session:

---

### SYSTEM CONTEXT

I'm implementing a text-based oscilloscope widget for a terminal application. The design spec is in `docs/design/oscilloscope-widget-spec.md`.

**Constraints:**
- Framework: `prompt_toolkit` only (no curses, textual, rich, etc.)
- Dependencies: `numpy` is available, no new packages
- Display: 32-40 chars wide, 8-16 rows tall
- Data range: 0.0 to 1.0 (normalized, never negative)
- Refresh: 20 Hz
- Must support 4+ simultaneous widget instances

**The widget renders a "local model" of FPGA waveform output.** The client has local copies of:
- ROM waveforms (8 × 128 samples each: SIN, TRI, SAW, SQR_64, SQR_32, SQR_04, NOISE, DC)
- ENV_BBUF contents (4 × up to 2048 samples, uploaded at deployment)

### TASK

Help me implement the oscilloscope widget in stages:

**Stage 1: Core rendering (`py_tools/oscillo/renderer.py`)**
- `TextRenderer` class with `render()` and `render_sparkline()` methods
- Use Unicode block characters: `" ▁▂▃▄▅▆▇█"`
- Input: numpy array of floats (0.0-1.0), length matching display width
- Output: list of strings (one per row)

**Stage 2: Decimation (`py_tools/oscillo/decimator.py`)**
- `decimate(data, target_len, strategy)` function
- Strategies: subsample, peak, average
- Power-of-2 friendly (128→32 = /4, 2048→32 = /64)

**Stage 3: ROM data (`py_tools/oscillo/rom_data.py`)**
- Pre-computed normalized waveforms matching `BOOT-ROM-primitives-spec.md`
- Dict mapping ID (0-7) to numpy array

**Stage 4: Store (`py_tools/oscillo/store.py`)**
- `WaveformStore` dataclass holding ROM + ENV buffers
- `get_waveform(source_id, width_sel, shift)` method

**Stage 5: Widget (`py_tools/oscillo/widget.py`)**
- `OscilloWidget(UIControl)` for prompt_toolkit
- `update()` method to refresh from store
- `create_content()` for prompt_toolkit rendering

**Stage 6: Integration (`py_tools/boot_shell.py`)**
- Add oscilloscope to existing shell
- Toggle visibility with hotkey
- 20Hz update in existing or new thread

### WORKING STYLE

- Implement one stage at a time
- Show me the code, explain key decisions
- I'll test and give feedback before moving on
- Keep files small and focused

---

## File Structure

Create these files:

```
py_tools/
├── oscillo/
│   ├── __init__.py           # Package exports
│   ├── renderer.py           # Stage 1: TextRenderer
│   ├── decimator.py          # Stage 2: Decimation
│   ├── rom_data.py           # Stage 3: ROM waveforms
│   ├── store.py              # Stage 4: WaveformStore
│   └── widget.py             # Stage 5: OscilloWidget
└── boot_shell.py             # Stage 6: Integration (modify existing)
```

---

## Code Style Reference

Match the existing codebase style. Example from `boot_constants.py`:

```python
"""
Module docstring with clear purpose.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


# Constants with clear naming
HVS_PRE_STATE_UNITS = 197


@dataclass
class SomeClass:
    """Docstring explaining purpose."""

    field: int
    optional_field: Optional[str] = None

    def method(self) -> int:
        """One-line docstring."""
        return self.field * 2
```

---

## Rendering Example

Expected output for SIN wave (32×8):

```
        ▄▆█▇▅▃▁
      ▃▆        ▁▃▅▇█▆▄▂
    ▂▅                  ▂▄▆█▇▅
  ▁▄                        ▁▃
 ▂
▄
                              ▂
                              ▅
```

Expected sparkline (single row):
```
▁▂▄▆█▆▄▂▁▁▂▄▆█▆▄▂
```

---

## Key Algorithms

### Rendering (Stage 1)

```
For display of width=W columns and height=H rows:
  effective_resolution = H × 8  (using block characters)

For each column x:
  sample = data[x]                      # 0.0 to 1.0
  v_pos = sample × (H × 8 - 1)          # vertical position
  row = H - 1 - floor(v_pos / 8)        # which row (0=top)
  level = floor(v_pos) % 8              # sub-row level (0-7)
  grid[row][x] = VBLOCKS[level + 1]     # place character
```

### Decimation (Stage 2)

```python
def decimate_peak(data: np.ndarray, target: int) -> np.ndarray:
    """Take max of each window."""
    ratio = len(data) // target
    trimmed = data[:target * ratio]
    return trimmed.reshape(target, ratio).max(axis=1)
```

### ROM Generation (Stage 3)

```python
def gen_sin() -> np.ndarray:
    """SIN: Full cycle, 128 samples, normalized to [0, 1]."""
    x = np.linspace(0, 2 * np.pi, 128, endpoint=False)
    return (0.5 + 0.5 * np.sin(x)).astype(np.float32)
```

---

## Testing Commands

```bash
# After implementing each stage, test with:
cd /home/user/DPD-001

# Stage 1-3: Quick visual test
python -c "
from py_tools.oscillo.rom_data import ROM_WAVEFORMS
from py_tools.oscillo.decimator import decimate
from py_tools.oscillo.renderer import TextRenderer

r = TextRenderer(40, 10)
data = ROM_WAVEFORMS[0]  # SIN
dec = decimate(data, 40)
for line in r.render(dec, label='SIN'):
    print(line)
"

# Stage 5: Widget standalone test
python -c "
from py_tools.oscillo.widget import OscilloWidget
from py_tools.oscillo.store import WaveformStore

store = WaveformStore.with_rom_bank()
w = OscilloWidget(store, source_id=0, label='TEST')
w.update()
# inspect w._cached_lines
"
```

---

## Notes for Implementation

1. **Thread safety**: `WaveformStore` will be accessed from update thread and UI thread. Use a lock.

2. **Sparkline mode**: Essential for compact status bar display. Single row, width matched to content.

3. **Border option**: `render(border=True)` should add box drawing characters around the waveform.

4. **Label placement**: Top-left corner, inside border if present.

5. **Empty state**: If no data available, render a flat line at 0 or display placeholder text.

---

## Success Criteria

- [ ] `TextRenderer.render()` produces clean Unicode output
- [ ] `TextRenderer.render_sparkline()` produces single-line output
- [ ] Decimation handles all power-of-2 cases correctly
- [ ] ROM waveforms match the spec visually
- [ ] Widget integrates with prompt_toolkit layout
- [ ] 20Hz refresh doesn't cause flickering or lag
- [ ] Can display 4 widgets simultaneously

---

## References

- `docs/design/oscilloscope-widget-spec.md` - Full specification
- `docs/bootup-proposal/BOOT-ROM-primitives-spec.md` - ROM waveform math
- `docs/bootup-proposal/BIOS-interface-spec.md` - BIOS channel model
- `py_tools/boot_shell.py` - Existing shell (lines 130-200 for HVS thread pattern)
