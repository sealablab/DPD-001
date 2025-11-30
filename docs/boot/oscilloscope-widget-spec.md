---
created: 2025-11-30
status: DRAFT
author: Claude (design session)
---
# Oscilloscope Widget Specification

A lightweight, reusable text-based oscilloscope widget for the BIOS client shell.

## 1. Overview

### 1.1 Purpose

Provide a low-fidelity visual representation of waveform data within the terminal-based BIOS client. The widget renders a "local model" of what the FPGA DAC outputs look like, using data the client already knows (ROM primitives, uploaded ENV_BBUF contents).

### 1.2 Design Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Framework | `prompt_toolkit` only | No new console dependencies |
| Display width | 32-40 chars | Power-of-2 friendly decimation |
| Display height | 8-16 rows | Compact, stackable |
| Refresh rate | 20 Hz | Matches existing HVS monitor |
| Data range | 0.0 - 1.0 | Normalized, never negative |
| Max instances | 4+ | 2 inputs + 2 outputs + debug |

### 1.3 Non-Goals (Initial Version)

- Real-time oscilloscope streaming from hardware (future)
- XY/Lissajous mode
- Measurement cursors
- Zoom/pan controls

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BIOS Client Shell                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐       │
│  │ WaveformStore │───▶│  Decimator    │───▶│ TextRenderer  │       │
│  │               │    │               │    │               │       │
│  │ - rom_bank[]  │    │ - source_len  │    │ - width       │       │
│  │ - env_buf[]   │    │ - target_len  │    │ - height      │       │
│  │ - live_trace  │    │ - strategy    │    │ - char_set    │       │
│  └───────────────┘    └───────────────┘    └───────────────┘       │
│         ▲                                          │                │
│         │                                          ▼                │
│  ┌──────┴──────┐                         ┌─────────────────┐       │
│  │ HW Stream   │                         │ OscilloWidget   │       │
│  │ (future)    │                         │ (UIControl)     │       │
│  └─────────────┘                         └─────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **WaveformStore** | Holds normalized waveform data (ROM + ENV buffers) |
| **Decimator** | Reduces sample count to display width |
| **TextRenderer** | Converts samples to Unicode block art |
| **OscilloWidget** | `prompt_toolkit` UI integration |

## 3. Data Model

### 3.1 WaveformStore

```python
@dataclass
class WaveformStore:
    """Client-side waveform data mirror."""

    # ROM primitives (compile-time known, 128 samples each)
    # Keys: 0=SIN, 1=TRI, 2=SAW, 3=SQR_64, 4=SQR_32, 5=SQR_04, 6=NOISE, 7=DC
    rom_bank: Dict[int, np.ndarray]

    # ENV buffers (deployment-time loaded, up to 2048 samples each)
    # Index 0-3 corresponds to ENV_BBUF_0 through ENV_BBUF_3
    env_buf: List[Optional[np.ndarray]]  # len=4

    # Live trace buffer (future: streamed from oscilloscope)
    live_trace: Optional[np.ndarray] = None

    def get_waveform(self, source_id: int,
                     width_sel: int = 0,
                     shift: int = 0) -> np.ndarray:
        """
        Retrieve normalized waveform data.

        Args:
            source_id: 0-7 for ROM, 8-9 for ENV_BBUF_0/1
            width_sel: For ENV sources, 0=bank mode, 1-4=single waveform
            shift: Index offset (phase for single mode, slot for bank mode)

        Returns:
            np.ndarray of float32 in range [0.0, 1.0]
        """
        ...
```

### 3.2 Normalization

All waveform data is stored as `float32` in range `[0.0, 1.0]`.

**Conversion from hardware format:**
```python
# 16-bit signed values constrained to 0-32767 (unipolar)
normalized = raw_data.astype(np.float32) / 32767.0
```

### 3.3 ROM Waveform Definitions

Pre-computed at module load time. Must match `BOOT-ROM-primitives-spec.md`.

| ID | Name | Formula | Notes |
|----|------|---------|-------|
| 0 | SIN | `0.5 + 0.5 * sin(2πi/128)` | Full cycle |
| 1 | TRI | Linear up 0→1, down 1→0 | Symmetric |
| 2 | SAW | `i / 127` | Rising ramp |
| 3 | SQR_64_128 | 1.0 for i<64, else 0.0 | 50% duty |
| 4 | SQR_32_128 | 1.0 for i<32, else 0.0 | 25% duty |
| 5 | SQR_04_128 | 1.0 for i<4, else 0.0 | Narrow pulse |
| 6 | NOISE | Deterministic LFSR | Seed: 0xACE1 |
| 7 | DC | All 1.0 | Constant high |

## 4. Decimation

### 4.1 Strategy

Power-of-2 decimation for clean scaling:

| Source | Target: 32 | Target: 64 | Target: 128 |
|--------|------------|------------|-------------|
| 128    | /4         | /2         | /1          |
| 256    | /8         | /4         | /2          |
| 512    | /16        | /8         | /4          |
| 1024   | /32        | /16        | /8          |
| 2048   | /64        | /32        | /16         |

### 4.2 Decimation Algorithms

```python
class DecimationStrategy(Enum):
    SUBSAMPLE = "subsample"  # Pick every Nth sample (fast, may alias)
    PEAK = "peak"            # Max value in window (preserves peaks)
    MINMAX = "minmax"        # Track min+max (envelope display)
    AVERAGE = "average"      # Mean of window (smoothing)
```

**Recommended default:** `PEAK` - preserves visual character of waveform.

### 4.3 Implementation

```python
def decimate(data: np.ndarray, target_len: int,
             strategy: DecimationStrategy = DecimationStrategy.PEAK) -> np.ndarray:
    """
    Reduce waveform to target length.

    Args:
        data: Source waveform, normalized [0.0, 1.0]
        target_len: Desired output length (should be power of 2)
        strategy: Decimation algorithm

    Returns:
        Decimated waveform of length target_len
    """
    source_len = len(data)
    if source_len <= target_len:
        # Upsample or return as-is (pad with last value)
        return np.pad(data, (0, target_len - source_len),
                      mode='edge')[:target_len]

    ratio = source_len // target_len

    if strategy == DecimationStrategy.SUBSAMPLE:
        return data[::ratio][:target_len]

    elif strategy == DecimationStrategy.PEAK:
        # Reshape and take max of each window
        trimmed = data[:target_len * ratio]
        return trimmed.reshape(target_len, ratio).max(axis=1)

    elif strategy == DecimationStrategy.AVERAGE:
        trimmed = data[:target_len * ratio]
        return trimmed.reshape(target_len, ratio).mean(axis=1)

    # ... MINMAX returns tuple of (min, max) arrays
```

## 5. Text Rendering

### 5.1 Character Set

Unicode block elements for vertical waveform display:

```python
# 9 levels: empty through full block
VBLOCKS = " ▁▂▃▄▅▆▇█"

# Index 0 = empty (0/8 of cell filled)
# Index 8 = full block (8/8 of cell filled)
```

### 5.2 Rendering Algorithm

For a display of `width` columns and `height` rows:

```
Effective vertical resolution = height × 8 levels

For each column x (0 to width-1):
    sample = data[x]                    # 0.0 to 1.0
    v_pos = sample × (height × 8 - 1)   # 0 to (height×8 - 1)

    row = height - 1 - floor(v_pos / 8) # Which row (0=top)
    level = floor(v_pos) mod 8          # Sub-row level (0-7)

    grid[row][x] = VBLOCKS[level + 1]   # +1 because 0 is empty

    # Clear cells above and below
    for r in range(height):
        if r != row:
            grid[r][x] = ' '
```

### 5.3 Example Output

SIN wave, 32×8 display:

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

### 5.4 Sparkline Mode

For compact single-line display (e.g., in status bar):

```python
def render_sparkline(data: np.ndarray) -> str:
    """Single-line mini waveform using block heights."""
    return "".join(VBLOCKS[min(8, int(s * 8))] for s in data)

# Example: "▁▂▄▆█▆▄▂▁▁▂▄▆█▆▄▂"
```

### 5.5 Renderer Class

```python
class TextRenderer:
    """Render waveform as Unicode text."""

    VBLOCKS = " ▁▂▃▄▅▆▇█"

    def __init__(self, width: int = 32, height: int = 8):
        self.width = width
        self.height = height

    def render(self, data: np.ndarray,
               label: str = "",
               border: bool = True) -> List[str]:
        """
        Render waveform to list of strings.

        Args:
            data: Decimated waveform (length should match self.width)
            label: Optional label for top-left corner
            border: Draw box around waveform

        Returns:
            List of strings, one per row (including border if enabled)
        """
        ...

    def render_sparkline(self, data: np.ndarray) -> str:
        """Single-line compact representation."""
        ...
```

## 6. prompt_toolkit Integration

### 6.1 OscilloWidget (UIControl)

```python
from prompt_toolkit.layout import UIControl, UIContent

class OscilloWidget(UIControl):
    """prompt_toolkit control for oscilloscope display."""

    def __init__(self,
                 store: WaveformStore,
                 source_id: int = 0,
                 width: int = 32,
                 height: int = 8,
                 label: str = ""):
        self.store = store
        self.source_id = source_id
        self.width_sel = 0
        self.shift = 0
        self.renderer = TextRenderer(width, height)
        self.label = label
        self._cached_lines: List[str] = []

    def update(self):
        """Refresh waveform from store. Call at 20Hz."""
        data = self.store.get_waveform(
            self.source_id, self.width_sel, self.shift)
        decimated = decimate(data, self.renderer.width)
        self._cached_lines = self.renderer.render(decimated, self.label)

    def create_content(self, width: int, height: int) -> UIContent:
        """prompt_toolkit UIControl interface."""
        def get_line(i: int) -> List[Tuple[str, str]]:
            if i < len(self._cached_lines):
                return [("", self._cached_lines[i])]
            return []

        return UIContent(
            get_line=get_line,
            line_count=len(self._cached_lines)
        )

    def set_source(self, source_id: int, width_sel: int = 0, shift: int = 0):
        """Change displayed waveform source."""
        self.source_id = source_id
        self.width_sel = width_sel
        self.shift = shift
```

### 6.2 Layout Options

**Option A: Float Overlay (Toggle with hotkey)**

```python
from prompt_toolkit.layout import Float, FloatContainer

# In BootShell.__init__:
self.oscillo_panel = HSplit([
    OscilloWidget(store, 0, label="OUT-A"),
    OscilloWidget(store, 1, label="OUT-B"),
])

self.layout = Layout(
    FloatContainer(
        content=self.main_container,
        floats=[
            Float(
                content=Window(self.oscillo_panel),
                right=1, top=1,
            )
        ]
    )
)
```

**Option B: Split Pane**

```python
from prompt_toolkit.layout import VSplit, HSplit

self.layout = Layout(
    VSplit([
        # Left: command area
        self.command_container,
        # Right: oscilloscope stack
        HSplit([
            Window(OscilloWidget(store, 0, label="OUT-A")),
            Window(OscilloWidget(store, 1, label="OUT-B")),
        ], width=40),
    ])
)
```

**Option C: Bottom Toolbar Sparklines**

```python
def _get_bottom_toolbar(self):
    sparkline_a = self.renderer.render_sparkline(self.get_outa_data())
    sparkline_b = self.renderer.render_sparkline(self.get_outb_data())
    return HTML(f"◉ BIOS │ {sparkline_a} A │ {sparkline_b} B")
```

## 7. Thread Model

### 7.1 Update Loop

Extend existing `HVSMonitor` or create unified display thread:

```python
class DisplayUpdateThread(threading.Thread):
    """Unified 20Hz display update thread."""

    def __init__(self,
                 state: ShellState,
                 widgets: List[OscilloWidget],
                 app: Optional[Application] = None):
        super().__init__(daemon=True)
        self.state = state
        self.widgets = widgets
        self.app = app
        self.poll_interval = 1.0 / 20.0  # 20 Hz
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            try:
                # Update HVS state (existing logic)
                self._update_hvs()

                # Update all oscilloscope widgets
                for widget in self.widgets:
                    widget.update()

                # Request UI refresh
                if self.app:
                    self.app.invalidate()

            except Exception:
                pass  # Fail silently, continue polling

            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False
```

### 7.2 Thread Safety

- `WaveformStore` access should be protected with a `threading.Lock`
- Widget `update()` acquires lock, copies data, releases lock
- UI rendering uses cached copy (no lock held during render)

## 8. File Organization

```
py_tools/
├── oscillo/
│   ├── __init__.py           # Package exports
│   ├── store.py              # WaveformStore class
│   ├── decimator.py          # Decimation strategies
│   ├── renderer.py           # TextRenderer class
│   ├── widget.py             # OscilloWidget (prompt_toolkit)
│   └── rom_data.py           # Pre-computed ROM waveforms
├── boot_shell.py             # Updated with oscilloscope integration
└── boot_constants.py         # (unchanged)
```

## 9. Status Indicator

Compact one-line state display (separate from oscilloscope):

```python
class StatusIndicator:
    """One-line status with colored state indicator."""

    FAULT_STYLE = "bg:#aa0000 #ffffff bold"
    OK_STYLE = "bg:#005500 #ffffff"

    CONTEXT_STYLES = {
        "BOOT": "#888888",
        "BIOS": "#aa8800",
        "LOAD": "#0088aa",
        "PROG": "#aa00aa",
    }

    def render(self, state: ShellState) -> FormattedText:
        """Generate formatted status text."""
        is_fault = state.hvs_is_fault
        ctx_name = self._extract_context(state.hvs_state_name)
        phase = self._extract_phase(state.hvs_state_name)

        parts = []

        # Indicator dot
        if is_fault:
            parts.append((self.FAULT_STYLE, " ● "))
        else:
            parts.append((self.OK_STYLE, " ◉ "))

        # Context/phase
        ctx_style = self.CONTEXT_STYLES.get(ctx_name, "")
        parts.append((ctx_style, f" {ctx_name}/P{phase} "))

        return FormattedText(parts)
```

## 10. Testing Strategy

### 10.1 Unit Tests

- `test_decimator.py`: Verify decimation algorithms
- `test_renderer.py`: Verify character output for known inputs
- `test_store.py`: Verify ROM generation matches spec

### 10.2 Visual Tests

Interactive script to preview rendering:

```python
# py_tools/oscillo/demo.py
if __name__ == "__main__":
    store = WaveformStore.with_rom_bank()
    renderer = TextRenderer(width=40, height=10)

    for wave_id, name in enumerate(["SIN", "TRI", "SAW", ...]):
        data = store.get_waveform(wave_id)
        decimated = decimate(data, 40)
        lines = renderer.render(decimated, label=name)
        print(f"\n{name}:")
        for line in lines:
            print(line)
```

## 11. Future Extensions

1. **Live oscilloscope stream**: Add hardware data source
2. **XY mode**: Plot channel A vs B for Lissajous
3. **Trigger line**: Visual threshold indicator
4. **Zoom/pan**: Keyboard navigation
5. **Measurement cursors**: Delta-T, amplitude markers
6. **Color themes**: Configurable palette

## 12. Dependencies

**Required (already in project):**
- `prompt_toolkit`
- `numpy`
- `threading` (stdlib)
- `dataclasses` (stdlib)

**No new dependencies.**

## 13. References

- `py_tools/boot_shell.py` - Existing shell implementation
- `py_tools/boot_constants.py` - HVS and state constants
- `docs/bootup-proposal/BOOT-ROM-primitives-spec.md` - ROM waveform definitions
- `docs/bootup-proposal/BIOS-interface-spec.md` - BIOS channel model
