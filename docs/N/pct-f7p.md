---
created: 2025-12-01
modified: 2025-12-01 15:41:51
accessed: 2025-12-01 15:41:39
type: N
---
# [pct-f7p](docs/N/pct-f7p.md)

# Fixed-Point Percent Indexing

A scheme for human-friendly “percent” access to power-of-two wavetables, using 7-bit fixed-point representation internally.

-----

## The Problem

Humans think in 0–100%. Hardware likes powers of two. Storing 101 samples is awkward; storing 128 samples means “100%” doesn’t land on a clean index.

## The Solution

Redefine “percent” internally as a 7-bit value where:

```
0x00 (0)   = 0%
0x7F (127) = 100%
```

Conversion to/from human-readable percent happens only at the UI boundary.

-----

## Bit Layout

All samples use the BPB fault-bit scheme with MSB fixed to zero:

```
Bit:    7   6   5   4   3   2   1   0
      ┌───┬───────────────────────────┐
      │ 0 │      sample [6:0]         │
      └───┴───────────────────────────┘
        │   └──────────┬──────────────┘
        │              └── 7-bit value (0–127)
        └── Fault bit (always 0 for valid ROM data)
```

-----

## Conversion Functions

```python
import numpy as np

def human_to_native(percent: int) -> np.uint8:
    """Convert human 0–100 to native 0–127."""
    return np.uint8(np.clip(percent, 0, 100) * 127 // 100)

def native_to_human(native: np.uint8) -> int:
    """Convert native 0–127 to human 0–100."""
    return int(native * 100 // 127)
```

-----

## Wavetable Examples

### Linear Ramp

```python
def generate_linear(order: int = 7) -> np.ndarray:
    """
    Linear ramp from 0x00 to 0x7F.
    
    Args:
        order: Log₂ of table size (7 → 128 samples)
    
    Returns:
        uint8 array, MSB=0, values span 0–127
    """
    length = 1 << order
    return np.linspace(0, 127, length, dtype=np.uint8)

line = generate_linear()
# line[0]   = 0   (0%)
# line[64]  = 64  (50.4%)
# line[127] = 127 (100%)
```

### Sine Wave

```python
def generate_sine(order: int = 7) -> np.ndarray:
    """
    One period of sine, scaled to 0–127.
    
    Zero-crossing at index 0, peak at index 32 (for order=7).
    """
    length = 1 << order
    phase = np.linspace(0, 2 * np.pi, length, endpoint=False)
    normalized = np.sin(phase)                      # [-1, +1]
    scaled = ((normalized + 1) / 2 * 127)           # [0, 127]
    return scaled.astype(np.uint8)

sine = generate_sine()
# sine[0]   = 63  (zero crossing, middle value)
# sine[32]  = 127 (positive peak)
# sine[64]  = 63  (zero crossing)
# sine[96]  = 0   (negative peak)
```

### Cosine Wave

```python
def generate_cosine(order: int = 7) -> np.ndarray:
    """
    One period of cosine, scaled to 0–127.
    
    Peak at index 0, zero-crossing at index 32 (for order=7).
    """
    length = 1 << order
    phase = np.linspace(0, 2 * np.pi, length, endpoint=False)
    normalized = np.cos(phase)                      # [-1, +1]
    scaled = ((normalized + 1) / 2 * 127)           # [0, 127]
    return scaled.astype(np.uint8)

cosine = generate_cosine()
# cosine[0]  = 127 (positive peak)
# cosine[32] = 63  (zero crossing)
# cosine[64] = 0   (negative peak)
```

-----

## Percent-Indexed Access

```python
class WaveTable:
    """Power-of-two storage with percent-indexed access."""
    
    def __init__(self, samples: np.ndarray):
        self._data = samples
        self._mask = len(samples) - 1  # For index wrapping
    
    def at_native(self, index: np.uint8) -> np.uint8:
        """Direct access by native index (0–127)."""
        return self._data[index & self._mask]
    
    def at_percent(self, percent: int) -> np.uint8:
        """Access by human percent (0–100)."""
        native = human_to_native(percent)
        return self.at_native(native)


# Usage
wave = WaveTable(generate_sine())
wave.at_percent(0)    # → 63  (0%, zero crossing)
wave.at_percent(25)   # → 126 (25%, near peak)
wave.at_percent(50)   # → 63  (50%, zero crossing)
wave.at_percent(75)   # → 1   (75%, near trough)
wave.at_percent(100)  # → 63  (100%, wraps to ~0%)
```

-----

## Summary

|Representation|Range|Use                          |
|--------------|-----|-----------------------------|
|Human percent |0–100|UI display, user input       |
|Native percent|0–127|Internal storage, table index|

Convert at the boundary, use native everywhere else.