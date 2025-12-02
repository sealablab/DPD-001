---
created: 2025-12-01
modified: 2025-12-01
---
# [README](B7B-Demo/src/README.md)

Source modules for B7B-Demo terminal waveform renderer.

## Module Structure

```
src/
├── bpb/              # BpB encoding/decoding
│   ├── __init__.py
│   └── codec.py      # Encode/decode BpB words
├── render/           # Terminal rendering
│   ├── __init__.py
│   └── blocks.py     # Unicode block rendering
├── wavetables/       # Waveform generation
│   ├── __init__.py
│   └── generators.py # Lin/Sin/Cos generators
└── README.md         # This file
```

## bpb/ — BpB Codec

Implements the [BpB Bits per Block](docs/N/BpB%20Bits%20per%20Block.md) encoding.

**Key types:**
- `decode_word(raw: np.int8)` → `(is_fault, value, guard)`
- `encode_sample(magnitude: np.uint8)` → `np.int8`
- `encode_fault(state: np.uint8)` → `np.int8`

**Design note:** The codec is stateless and vectorizable. Fault detection is simply `raw < 0`.

## render/ — Block Rendering

Maps sample values to Unicode block characters for terminal display.

**Key constants:**
```python
BLOCK_CHARS = " ▁▂▃▄▅▆▇█"  # 9 chars: space + 8 blocks
```

**Key functions:**
- `sample_to_column(value: np.uint8, height: int)` → list of chars
- `render_waveform(samples: np.ndarray, height: int)` → list of strings

**The core algorithm:**
1. Right-shift sample to get "full blocks" count
2. Mask lower 3 bits for "partial block" character
3. Build column bottom-to-top
4. Transpose columns to rows for printing

## wavetables/ — Waveform Generators

Standard wavetables for testing and demonstration.

**Key functions:**
- `generate_linear(length=128)` — Ramp from 0 to 127
- `generate_sine(length=128)` — One period, scaled 0–127
- `generate_cosine(length=128)` — One period, scaled 0–127

All generators return `np.ndarray` with dtype `uint8`.

## Usage Example

```python
import numpy as np
from wavetables.generators import generate_sine
from render.blocks import render_waveform

# Generate a sine wave
wave = generate_sine(64)  # 64 samples

# Render at different heights
for height in [1, 2, 4, 8]:
    print(f"\n=== Height {height} ===")
    for row in render_waveform(wave, height):
        print(row)
```

## See Also

- [REQUIREMENTS](REQUIREMENTS.md) — Detailed functional requirements
- [BpB Bits per Block](docs/N/BpB%20Bits%20per%20Block.md) — Encoding spec


