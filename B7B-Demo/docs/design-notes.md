---
created: 2025-12-01
modified: 2025-12-01
---
# [design-notes](B7B-Demo/docs/design-notes.md)

Design decisions and rationale for B7B-Demo.

## Why Unicode Block Characters?

Unicode provides a set of eighth-block characters that fill a terminal cell from bottom to top:

```
U+2581  ▁  LOWER ONE EIGHTH BLOCK      (1/8)
U+2582  ▂  LOWER ONE QUARTER BLOCK     (2/8)
U+2583  ▃  LOWER THREE EIGHTHS BLOCK   (3/8)
U+2584  ▄  LOWER HALF BLOCK            (4/8)
U+2585  ▅  LOWER FIVE EIGHTHS BLOCK    (5/8)
U+2586  ▆  LOWER THREE QUARTERS BLOCK  (6/8)
U+2587  ▇  LOWER SEVEN EIGHTHS BLOCK   (7/8)
U+2588  █  FULL BLOCK                  (8/8)
```

**Key insight**: These 8 levels map perfectly to 3 bits. Add a space for "zero" and you get 9 levels (which is slightly more than 3 bits can represent, but 0–7 + full is ergonomic).

## The Doubling Property

From the [analog notes](docs/N/BpB-Analog-notes.jpeg):

> "For every bit after '3', we use the following formula: num_blocks = 2^n"

This gives us:

| Extra Bits (n) | Blocks | Total Sample Bits |
|----------------|--------|-------------------|
| 0              | 1      | 3                 |
| 1              | 2      | 4                 |
| 2              | 4      | 5                 |
| 3              | 8      | 6                 |
| 4              | 16     | 7                 |

**Why this works**: The upper bits determine "which block row" we're in. The lower 3 bits determine "how full" that row is. It's exactly like reading a ruler: whole units + fractional part.

## MSB-First Graceful Degradation

The [BpB encoding](docs/N/BpB%20Bits%20per%20Block.md) is designed MSB-first:

```
[Fault][MSBs ... → ... LSBs]
```

This means you can truncate from the right and still preserve meaning:
- 7-bit sample → 5-bit sample: just right-shift by 2
- Shape is preserved, resolution is lost

This mirrors other efficient encodings:
- IEEE 754 floats: sign → exponent → mantissa
- UTF-8: prefix → payload
- Progressive JPEG: coarse → fine

## Why No Terminal Libraries (Phase 1)?

Several reasons:

1. **Validation**: We need to confirm the rendering math works before adding complexity
2. **Portability**: `print()` works everywhere; curses/blessed don't
3. **Debuggability**: Raw strings are easier to inspect than widget abstractions
4. **Future flexibility**: We haven't decided between prompt-toolkit, textual, rich, etc.

Phase 2 will evaluate:
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) — Full TUI framework
- [rich](https://rich.readthedocs.io/) — Pretty printing with layout
- [textual](https://textual.textualize.io/) — Modern TUI apps

## The Fault Bit Convention

Per [BpB](docs/N/BpB%20Bits%20per%20Block.md):
- Bit 7 (MSB) = 1 means "fault"
- This works naturally with signed int8: negative = fault

In rendering, faults should be visually distinct:
- Option 1: `│` vertical bar (different character class)
- Option 2: `X` or `?` (obvious error)
- Option 3: Color (red background) — but requires ANSI

Phase 1 will use `│` for simplicity.

## Rendering Algorithm

For a single sample with value `v` at height `h`:

```python
def sample_to_column(v: int, h: int) -> list[str]:
    """
    v: 7-bit sample value (0–127)
    h: height in blocks (1, 2, 4, 8, or 16)
    """
    # How many bits determine "which row"?
    row_bits = int(log2(h))  # 0, 1, 2, 3, or 4

    # Scale sample to available resolution
    # For h=1: we use 3 bits (the LSBs)
    # For h=16: we use all 7 bits
    bits_used = 3 + row_bits
    scaled = v >> (7 - bits_used)

    # Split into full blocks and partial
    partial = scaled & 0b111        # lower 3 bits
    full_count = scaled >> 3        # upper bits

    # Build column bottom-to-top
    column = []
    for row in range(h):
        if row < full_count:
            column.append('█')
        elif row == full_count:
            column.append(BLOCK_CHARS[partial])
        else:
            column.append(' ')

    return column  # [bottom, ..., top]
```

Then transpose columns to rows for printing:
```python
def render_waveform(samples, height):
    columns = [sample_to_column(s, height) for s in samples]
    # Transpose and reverse (top row first)
    rows = [''.join(row) for row in zip(*columns)]
    return rows[::-1]
```

## See Also

- [B7B-README](B7B-README.md) — Project overview
- [REQUIREMENTS](REQUIREMENTS.md) — Detailed requirements
- [BpB Bits per Block](docs/N/BpB%20Bits%20per%20Block.md) — Encoding spec
