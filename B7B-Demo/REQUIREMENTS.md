---
created: 2025-12-01
modified: 2025-12-01 17:02:25
status: DRAFT
accessed: 2025-12-01 17:03:04
---
# [REQUIREMENTS](B7B-Demo/REQUIREMENTS.md)

Detailed requirements for the B7B-Demo terminal waveform renderer.

## Overview

This utility validates the hypothesis that Unicode block characters provide a natural, gracefully-degrading representation for low-resolution sample data. The core insight is that the **3 least-significant bits** of any sample map directly to the 8 Unicode eighth-block characters.

The end goal is **three renderer backends** with graceful degradation:

| Renderer | Encoding | Levels | Bits | Target Environment |
|----------|----------|--------|------|--------------------|
| Unicode  | UTF-8    | 9      | 3    | Modern terminals (Phase 1) |
| CP437    | 8-bit    | 5      | ~2   | DOS/retro terminals |
| ASCII    | 7-bit    | 8      | 3    | Universal fallback |

**Phase 1 focuses exclusively on the Unicode renderer.** CP437 and ASCII are specified here for completeness but implementation is deferred.

---

## Constraints

### C1: No Fancy Terminal Libraries (Phase 1)

For the initial implementation:
- Use only `print()` and basic ANSI escape codes
- No curses, blessed, rich, textual, or prompt-toolkit
- This constraint allows us to validate the core rendering logic before adding complexity

**Rationale**: We need to understand the fundamental behavior before introducing framework abstractions. Future phases may evaluate prompt-toolkit or similar.

### C2: NumPy Only

- NumPy is the only required dependency
- All waveform data stored as `np.ndarray` with appropriate dtype
- Vectorized operations preferred over Python loops

### C3: Pure Python 3.10+

- No compiled extensions
- Type hints throughout
- Dataclasses for configuration

---

## Functional Requirements

### FR1: Unicode Block Character Mapping

The 3 LSBs of any sample value map to Unicode eighth-block characters:

```
Binary  Decimal  Character  Unicode
000     0        (space)    U+0020
001     1        ▁          U+2581
010     2        ▂          U+2582
011     3        ▃          U+2583
100     4        ▄          U+2584
101     5        ▅          U+2585
110     6        ▆          U+2586
111     7        ▇          U+2587
(full)  8        █          U+2588
```

**Note**: The full block (█) represents overflow/saturation beyond 3 bits.

### FR2: Vertical Scaling by Bit Depth

For samples with more than 3 bits of resolution, vertical space **doubles** per additional bit:

| Sample Bits | Vertical Blocks | Formula |
|-------------|-----------------|---------|
| 3           | 1               | 2^(3-3) = 1 |
| 4           | 2               | 2^(4-3) = 2 |
| 5           | 4               | 2^(5-3) = 4 |
| 6           | 8               | 2^(6-3) = 8 |
| 7           | 16              | 2^(7-3) = 16 |

The rendering algorithm:
1. Split the sample value into "full blocks" (upper bits) and "partial block" (lower 3 bits)
2. Render full blocks as `█`
3. Render the partial block using the 3-LSB mapping
4. Fill remaining rows with spaces

### FR3: Wavetable Generation

Generate standard wavetables as 7-bit unsigned samples (0–127):

**Linear Ramp**
```python
# samples[i] = i for i in 0..127
```

**Sine Wave**
```python
# One period, zero-crossing at index 0, peak at index 32
# samples[i] = round(63.5 + 63.5 * sin(2π * i / 128))
```

**Cosine Wave**
```python
# One period, peak at index 0
# samples[i] = round(63.5 + 63.5 * cos(2π * i / 128))
```

### FR4: Horizontal Rendering

Render a waveform buffer as a horizontal bar chart:
- Each sample becomes one column
- Columns are rendered bottom-to-top
- Output is printed top-to-bottom (reverse order)

Example (3-bit, 8 samples):
```
    █
   ▆█▆
  ▄█ █▄
 ▂█   █▂
█       █
```

### FR5: Graceful Degradation

The renderer must support downsampling:
- A 7-bit sample can be rendered at 7, 6, 5, 4, or 3-bit resolution
- Downsampling is achieved by right-shifting the sample value
- Information is lost, but the visual shape is preserved

Example (sine wave at different resolutions):
```
7-bit (16 rows): Full detail, smooth curves
5-bit (4 rows):  Coarse but recognizable
3-bit (1 row):   Minimal, but still shows shape
```

### FR6: Fault Bit Handling

Per the [BpB encoding](docs/N/BpB%20Bits%20per%20Block.md):
- Bit 7 (MSB) is the fault flag
- If fault=1, render a distinct visual indicator (e.g., `│` or `X`)
- Fault samples should stand out visually from valid samples

---

## Character Map Specifications (AUTHORITATIVE)

Each renderer defines a **character map** — an ordered sequence of characters representing increasing "fill levels" from empty to full.

### Design Principles

1. **Clean power-of-2 math**: Unicode uses exactly 8 levels (3 bits) for clean vertical scaling
2. **Space for zero**: Index 0 is space (empty cell), not underscore
3. **Separate fill character**: Full blocks (█) are the fill character for stacked rows, NOT part of the char_map

### Summary Table

| Encoding | Char Map | Levels | Bits | Fill Char | Fault Char |
|----------|----------|--------|------|-----------|------------|
| Unicode  | ` ▁▂▃▄▅▆▇` | 8 | 3.0 | `█` | `×` (U+00D7) |
| CP437    | ` ▄` | 2 | 1.0 | `█` | `×` (dec 158) |
| ASCII    | ` -` | 2 | 1.0 | `#` | `x` (0x78) |

**Power-of-2 effective resolution** (Unicode):
```
Rows × Levels = Effective Levels = Bits
   1 ×    8   =      8           = 3 bits
   2 ×    8   =     16           = 4 bits
   4 ×    8   =     32           = 5 bits
   8 ×    8   =     64           = 6 bits
  16 ×    8   =    128           = 7 bits
```

**Fault character rationale**: The multiplication sign `×` is visually distinct ("X marks the error") and consistent across Unicode/CP437. ASCII degrades gracefully to lowercase `x`.

---

### CM1: Unicode Character Map

**Status**: AUTHORITATIVE

**Full map** — 8 levels (3 bits exactly):

| Index | Char | Codepoint | Name |
|-------|------|-----------|------|
| 0     | ` `  | U+0020    | SPACE (empty) |
| 1     | `▁`  | U+2581    | LOWER ONE EIGHTH BLOCK |
| 2     | `▂`  | U+2582    | LOWER ONE QUARTER BLOCK |
| 3     | `▃`  | U+2583    | LOWER THREE EIGHTHS BLOCK |
| 4     | `▄`  | U+2584    | LOWER HALF BLOCK |
| 5     | `▅`  | U+2585    | LOWER FIVE EIGHTHS BLOCK |
| 6     | `▆`  | U+2586    | LOWER THREE QUARTERS BLOCK |
| 7     | `▇`  | U+2587    | LOWER SEVEN EIGHTHS BLOCK |

```python
UNICODE_MAP = " ▁▂▃▄▅▆▇"  # len=8, index 0-7 (3 bits)
UNICODE_FILL = "█"         # U+2588 for stacked full rows
```

**Fault character**: `×` (U+00D7 MULTIPLICATION SIGN)

**Key insight**: Using space (not underscore) for zero-level enables clean 8-level = 3-bit encoding. The full block `█` is separate as the fill character.

---

### CM2: CP437 Character Map

**Status**: AUTHORITATIVE

2 levels (1 bit), using space and half-block:

| Index | Char | CP437 Dec | Name |
|-------|------|-----------|------|
| 0     | ` `  | 32        | SPACE (empty) |
| 1     | `▄`  | 220       | LOWER HALF BLOCK |

```python
CP437_MAP = " ▄"    # len=2, index 0-1 (1 bit)
CP437_FILL = "█"    # dec 219 for stacked full rows
```

**Fault character**: `×` (CP437 dec 158 MULTIPLICATION SIGN)

**Rationale**: Simplified to 2 levels (1 bit) for consistent power-of-2 math. Higher resolution achieved through more rows.

---

### CM3: ASCII Character Map

**Status**: AUTHORITATIVE

2 levels (1 bit), using space and dash:

| Index | Char | Hex  | Name |
|-------|------|------|------|
| 0     | ` `  | 0x20 | SPACE (empty) |
| 1     | `-`  | 0x2D | HYPHEN-MINUS (mid-height) |

```python
ASCII_MAP = " -"    # len=2, index 0-1 (1 bit)
ASCII_FILL = "#"    # 0x23 NUMBER SIGN for stacked full rows
```

**Fault character**: `x` (0x78 LATIN SMALL LETTER X)

**Rationale**: Simplified to 2 levels (1 bit) for consistent power-of-2 math. The hash `#` provides dense fill for stacked rows.

---

## API Requirements

### AR1: Core Rendering Function

```python
def render_waveform(
    samples: np.ndarray,    # uint8 array, 7-bit values (bit 7 ignored or fault)
    height: int = 1,        # Number of vertical blocks (1, 2, 4, 8, or 16)
) -> list[str]:
    """
    Render a waveform as a list of strings (top to bottom).

    Args:
        samples: Array of 7-bit sample values
        height: Vertical resolution in blocks (must be power of 2)

    Returns:
        List of strings, one per row, ready for print()
    """
```

### AR2: Block Character Lookup

```python
BLOCK_CHARS: str = " ▁▂▃▄▅▆▇█"

def sample_to_char(value_3bit: int) -> str:
    """Map a 3-bit value (0–7) to a block character."""
    return BLOCK_CHARS[value_3bit]
```

### AR3: Wavetable Generators

```python
def generate_linear(length: int = 128) -> np.ndarray:
    """Generate linear ramp 0–127."""

def generate_sine(length: int = 128) -> np.ndarray:
    """Generate one period of sine, scaled to 0–127."""

def generate_cosine(length: int = 128) -> np.ndarray:
    """Generate one period of cosine, scaled to 0–127."""
```

---

## Test Requirements

### TR1: Character Mapping Verification

Verify that all 8 levels render correctly:
```python
for i in range(8):
    assert sample_to_char(i) == BLOCK_CHARS[i]
```

### TR2: Vertical Scaling Correctness

For each height (1, 2, 4, 8, 16):
- A sample value of 0 should render as all `_` (underscore baseline markers)
- A sample value of max should render as all full blocks (fill character)
- Intermediate values should have correct number of full blocks + partial
- Empty space above the waveform uses literal space (U+0020), not underscore

### TR3: Waveform Shape Preservation

Render sine wave at 7-bit and 3-bit resolution:
- Both should show recognizable sinusoidal shape
- Peak/trough positions should match

---

## Phased Roadmap

### Phase 1: Unicode Renderer (Current)

- Core rendering with Unicode block characters
- Wavetable generation (lin/sin/cos)
- Vertical scaling (1–16 blocks)
- Basic `print()` output
- No external dependencies beyond NumPy

### Phase 2: Alternative Renderers

- CP437 renderer (finalize character map)
- ASCII renderer (finalize character map)
- Renderer abstraction layer (swap backends)
- Encoding auto-detection

### Phase 3: Interactive Features

- **prompt-toolkit integration**: Proper widget with keyboard handling
- **Color**: ANSI color for positive/negative, fault indication
- **Scrolling/zooming**: Navigate large waveforms
- **Dual-axis**: Side-by-side waveform comparison
- **Animation**: Real-time waveform playback

---

## See Also

- [B7B-README](B7B-README.md) — Project overview
- [BpB Bits per Block](docs/N/BpB%20Bits%20per%20Block.md) — Encoding scheme
- [BpB Analog Notes](docs/N/BpB-Analog-notes.jpeg) — Original sketch
- [fixed-f7p](docs/N/fixed-f7p.md) — Percent indexing scheme
