---
created: 2025-12-01
modified: 2025-12-01 16:53:38
accessed: 2025-12-01 16:53:38
---
# [B7B-README](B7B-Demo/B7B-README.md)

A self-contained utility for **terminal waveform rendering** using Unicode block characters. This project validates the core hypothesis that 3 LSBs map cleanly to Unicode eighth-blocks, with graceful vertical scaling for higher bit depths.

## Core Hypothesis

The [BpB Bits per Block](docs/N/BpB%20Bits%20per%20Block.md) encoding has a key property: the **three least-significant bits** of any sample map directly to Unicode eighth-block characters (`U+2581`–`U+2588`):

```
3 LSBs → 8 levels → ▁▂▃▄▅▆▇█
```

For samples with more than 3 bits of resolution, vertical space **doubles** per additional bit:

| Sample Bits | Blocks per Bar | Use Case |
|-------------|----------------|----------|
| 3           | 1              | Status line / minimal |
| 4           | 2              | Detailed status |
| 5           | 4              | Minimum widget |
| 6           | 8              | Medium widget |
| 7           | 16             | Full 8-bit resolution |

See: [BpB Analog Notes](docs/N/BpB-Analog-notes.jpeg) for the original sketch.

## Goals

1. **Validate the 3-LSB → Unicode mapping** with numpy arrays
2. **Demonstrate graceful degradation** from 7-bit samples down to 3-bit
3. **Render Lin/Sin/Cos wavetables** at various vertical resolutions
4. **Keep it minimal** — no fancy terminal libraries (yet)

Future work may integrate with [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) or similar, but this experiment uses only `print()` and basic ANSI.

## Key Concepts

- [BpB Bits per Block](docs/N/BpB%20Bits%20per%20Block.md) — The encoding scheme (fault bit, state bits, guard bits)
- [fixed-f7p](docs/N/fixed-f7p.md) — 7-bit fixed-point percent indexing for wavetables
- [HVS-encoding-scheme](docs/HVS-encoding-scheme.md) — Related analog voltage encoding for FPGA debug
- [BOOT-ROM-WAVE-TABLE](docs/N/BOOT-ROM-WAVE-TABLE.md) — Hardware wavetable context

## Directory Layout

```
B7B-Demo/
├── B7B-README.md           # This file
├── REQUIREMENTS.md         # Detailed requirements spec
├── docs/
│   └── design-notes.md     # Design decisions and rationale
├── src/
│   ├── bpb/                # BpB encoding/decoding
│   │   └── codec.py        # encode/decode functions
│   ├── render/             # Terminal rendering
│   │   └── blocks.py       # Unicode block rendering
│   ├── wavetables/         # Waveform generation
│   │   └── generators.py   # lin/sin/cos generators
│   └── README.md           # Module documentation
└── examples/
    └── demo.py             # Interactive demo script
```

## Quick Start

```bash
cd B7B-Demo
python examples/demo.py
```

## Requirements

- Python 3.10+
- numpy
- A terminal with Unicode support (most modern terminals)

## See Also

- [BpB Bits per Block](docs/N/BpB%20Bits%20per%20Block.md)
- [fixed-f7p](docs/N/fixed-f7p.md)
- [ENV-BBUF](docs/N/ENV-BBUF.md) — Hardware buffer context
