---
created: 2025-12-01
modified: 2025-12-01 15:42:45
accessed: 2025-12-01 16:05:29
type: N
---

# [BpB Bits per Block](docs/N/BpB%20Bits%20per%20Block.md)

# BPB: Bits Per Block Encoding Scheme

A compact, MSB-first encoding for streaming sample data that gracefully degrades from high-resolution DAC/ADC chains down to minimal 8-bit representations—while embedding fault diagnostics directly in the data stream.

-----

## Core Principle: MSB-First Significance

The encoding follows a strict hierarchy from most-significant to least-significant bits:

```
MSB                                                      LSB
 │                                                        │
 ▼                                                        ▼
[F][S S S S S S][G G G]
 │  └─────┬─────┘ └─┬─┘
 │        │        └── Guard band / noise margin
 │        └── State bits (magnitude or FSM state)
 └── Fault/Sign bit (discriminant)
```

**Key property:** You can truncate bits from the right and still retain the most important information. This mirrors how other efficient encodings work—IEEE 754 floats (sign → exponent → mantissa), UTF-8 (prefix → payload), progressive JPEG, IP subnets.

-----

## The Fault Bit as Tagged Union

From a C programmer’s perspective, the sign bit acts as a discriminant in a tagged union:

```c
#include <stdint.h>

/* 
 * The sign bit determines interpretation of the remaining bits.
 * This is a "sum type" encoded in a single byte.
 */
typedef union {
    int8_t raw;
    
    struct {
        uint8_t magnitude : 7;  /* Sample value: 0–127 */
        uint8_t is_fault  : 1;  /* 0 = valid sample */
    } sample;
    
    struct {
        uint8_t state     : 6;  /* FSM state at time of fault */
        uint8_t reserved  : 1;  /* Noise margin / severity */
        uint8_t is_fault  : 1;  /* 1 = fault code */
    } fault;
    
} bpb_word_t;


/* Decode with explicit discriminant check */
void decode(bpb_word_t word) {
    if (word.raw < 0) {
        /* Fault path: word.fault.state is "where were we?" */
        printf("FAULT in state %d\n", word.fault.state);
    } else {
        /* Valid sample: word.sample.magnitude is the data */
        printf("Sample: %d\n", word.sample.magnitude);
    }
}
```

This is analogous to:

- POSIX `ssize_t` returning `-1` for errors
- Tagged pointers in VM implementations
- Rust’s `Result<T, E>` encoded in a machine word

-----

## Bit Field Layout by Resolution

The scheme scales across word sizes while maintaining the MSB-first hierarchy:

### 8-bit (Minimal Viable)

```
Bit:    7   6   5   4   3   2   1   0
      ┌───┬───┬───┬───┬───┬───┬───┬───┐
      │ F │     STATE [5:0]     │ G │ G │
      └───┴───┴───┴───┴───┴───┴───┴───┘
        │   └────────┬────────┘   └─┬─┘
        │            │              └── 2-bit guard band
        │            └── 6-bit state (64 states)
        └── Fault flag

Valid sample: F=0, bits[6:0] = 7-bit magnitude
Fault code:   F=1, bits[5:0] = state ID, bits[6] = severity/spare
```

### 16-bit (Typical Operation)

```
Bit:   15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
      ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
      │ F │            STATE / MAGNITUDE            │   GUARD / EXT   │
      └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘

Valid sample: F=0, bits[14:0] = 15-bit magnitude
Fault code:   F=1, bits[5:0] = state, bits[14:6] = extended diagnostics
```

-----

## Digital vs. Analog Sources

A key insight: when the source is a digital FSM (no ADC), the “noise” bits aren’t noisy—they’re deterministic zeros or available for other use.

```
From FSM (digital):    [F][S S S S S S][0 0 0]
                        │  └── deterministic  └── literally zero
                        └── fault flag

From ADC (analog):     [F][M M M M M M][N N N]  
                        │  └── signal        └── thermal/quantization noise
                        └── fault flag
```

The guard band bits naturally absorb LSB uncertainty from analog sources, while providing spare capacity for digital sources.

-----

## Configurable State Bits

The number of state bits is configurable (compile-time default: 6), allowing the encoding to adapt to different FSM complexities:

|State Bits|Max States|Guard Bits (8-bit)|Use Case                         |
|----------|----------|------------------|---------------------------------|
|3         |8         |4                 |Trivial FSM, maximum noise margin|
|4         |16        |3                 |Simple protocol, good margin     |
|5         |32        |2                 |Moderate complexity              |
|6         |64        |1                 |Complex FSM (default)            |

-----

## NumPy Implementation

### Basic Types and Constants

```python
import numpy as np
from dataclasses import dataclass
from enum import IntEnum
from typing import NamedTuple


# Configuration: compile-time equivalent
STATE_BITS: int = 6
GUARD_BITS: int = 7 - STATE_BITS  # Remaining bits in 8-bit word

# Derived masks
STATE_MASK: np.uint8 = np.uint8((1 << STATE_BITS) - 1)
GUARD_MASK: np.uint8 = np.uint8((1 << GUARD_BITS) - 1)


class DecodeResult(NamedTuple):
    """Result of decoding a BPB word."""
    is_fault: bool
    value: np.uint8      # magnitude if valid, state if fault
    guard: np.uint8      # guard band bits (noise or spare)
```

### Single-Word Decode

```python
def decode_word(raw: np.int8) -> DecodeResult:
    """
    Decode a single BPB-encoded byte.
    
    Bit layout (STATE_BITS=6):
        [F][S₅ S₄ S₃ S₂ S₁ S₀][G]
         7   6  5  4  3  2  1   0
    
    Args:
        raw: Signed 8-bit value from wire
        
    Returns:
        DecodeResult with fault flag, value, and guard bits
    """
    is_fault = raw < 0
    
    # Extract fields regardless of fault status
    unsigned = np.uint8(raw & 0x7F)  # Strip sign bit
    guard = unsigned & GUARD_MASK
    value = (unsigned >> GUARD_BITS) & STATE_MASK
    
    return DecodeResult(is_fault, value, guard)


def encode_sample(magnitude: np.uint8) -> np.int8:
    """Encode a valid sample (fault=0)."""
    if magnitude > 127:
        raise ValueError("Magnitude must fit in 7 bits")
    return np.int8(magnitude)


def encode_fault(state: np.uint8, guard: np.uint8 = 0) -> np.int8:
    """Encode a fault code with FSM state."""
    if state > STATE_MASK:
        raise ValueError(f"State must fit in {STATE_BITS} bits")
    if guard > GUARD_MASK:
        raise ValueError(f"Guard must fit in {GUARD_BITS} bits")
    
    payload = (state << GUARD_BITS) | guard
    # Set the sign bit by using negative value
    return np.int8(-128 + payload)  # 0x80 | payload
```

### Vectorized Buffer Operations

```python
def decode_buffer(buf: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Decode an entire buffer of BPB words.
    
    Args:
        buf: Array of int8 values
        
    Returns:
        Tuple of (fault_mask, values, guard_bits) as uint8 arrays
    """
    # Vectorized fault detection
    faults = buf < 0
    
    # Vectorized field extraction
    unsigned = (buf & 0x7F).astype(np.uint8)
    guards = unsigned & GUARD_MASK
    values = (unsigned >> GUARD_BITS) & STATE_MASK
    
    return faults, values, guards


def partition_buffer(buf: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Separate valid samples from fault codes.
    
    Returns:
        (valid_samples, fault_states) - masked arrays or indices
    """
    faults, values, guards = decode_buffer(buf)
    
    valid_mask = ~faults
    valid_samples = values[valid_mask]
    fault_states = values[faults]
    
    return valid_samples, fault_states
```

### Configurable State Width

```python
@dataclass
class BPBConfig:
    """Runtime-configurable BPB parameters."""
    state_bits: int = 6
    word_bits: int = 8
    
    def __post_init__(self):
        self.guard_bits = (self.word_bits - 1) - self.state_bits
        self.state_mask = np.uint8((1 << self.state_bits) - 1)
        self.guard_mask = np.uint8((1 << self.guard_bits) - 1)
        self.max_states = 1 << self.state_bits
        
        if self.guard_bits < 0:
            raise ValueError("Not enough bits for requested state width")
    
    def decode(self, raw: np.int8) -> DecodeResult:
        """Decode using this configuration."""
        is_fault = raw < 0
        unsigned = np.uint8(raw & 0x7F)
        guard = unsigned & self.guard_mask
        value = (unsigned >> self.guard_bits) & self.state_mask
        return DecodeResult(is_fault, value, guard)


# Usage with different configurations
config_simple = BPBConfig(state_bits=4)   # 16 states, 3 guard bits
config_default = BPBConfig(state_bits=6)  # 64 states, 1 guard bit
config_16bit = BPBConfig(state_bits=6, word_bits=16)  # 64 states, 9 guard bits
```

-----

## Unicode Block Rendering

The lower 3 bits of a sample map directly to Unicode eighth-block characters for oscilloscope-style display:

```python
# U+2581 through U+2588
BLOCK_CHARS = " ▁▂▃▄▅▆▇█"

def sample_to_blocks(magnitude: np.uint8, rows: int) -> list[str]:
    """
    Render a sample as vertical bar using Unicode blocks.
    
    Args:
        magnitude: 7-bit sample value (0–127)
        rows: Display height (1, 2, 4, 8, or 16)
    
    Returns:
        List of characters, bottom to top
    """
    # Scale to available resolution
    bits_needed = int(np.log2(rows)) + 3  # rows = 2^n, plus 3 for sub-block
    scaled = magnitude >> (7 - bits_needed)
    
    sub_block = scaled & 0b111        # Which eighth?
    full_blocks = scaled >> 3         # How many full blocks?
    
    result = []
    for row in range(rows):
        if row < full_blocks:
            result.append('█')        # Full block
        elif row == full_blocks:
            result.append(BLOCK_CHARS[sub_block])
        else:
            result.append(' ')        # Empty
    
    return result


def render_fault(state: np.uint8, rows: int) -> list[str]:
    """Render a fault as a distinct visual pattern."""
    mid = rows // 2
    return ['│' if i != mid else f'{state:02d}' for i in range(rows)]
```

-----

## Graceful Degradation

The MSB-first design means higher-resolution data can be truncated for lower-resolution displays without losing critical information:

```python
def downsample(word_16bit: np.int16) -> np.int8:
    """
    Truncate 16-bit word to 8-bit, preserving fault flag and MSBs.
    
    16-bit: [F][14 bits of data    ]
     8-bit: [F][top 7 bits of data ]
    """
    if word_16bit < 0:
        # Preserve fault + top 6 state bits + 1 guard
        state_and_guard = (abs(word_16bit) >> 8) & 0x7F
        return np.int8(-128 + state_and_guard)
    else:
        # Preserve top 7 magnitude bits
        return np.int8(word_16bit >> 8)
```

This property enables:

- Bandwidth adaptation (send fewer bits over constrained links)
- Display scaling (render at terminal’s actual resolution)
- Storage tiering (archive at reduced precision)

-----

## Summary

|Property                |Benefit                                        |
|------------------------|-----------------------------------------------|
|MSB-first significance  |Truncation preserves meaning                   |
|Sign bit as discriminant|Tagged union in one byte                       |
|Configurable state width|Adapts to FSM complexity                       |
|Guard band bits         |Absorbs noise (ADC) or provides spare (digital)|
|Direct Unicode mapping  |3 LSBs → ⅛-block resolution                    |

The encoding treats the data stream as self-describing: a negative value *is* a fault, and its magnitude *is* the diagnostic context.



![img](docs/N/BpB-Analog-notes.jpeg)