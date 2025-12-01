---
created: 2025-11-29
modified: 2025-11-30 16:23:16
status: PROPOSED
accessed: 2025-11-30 17:41:10
---
# BIOS Interface Specification

This document specifies the BIOS module's control register and output interface.

## Design Philosophy: The Effects Pedal Model

BIOS signal generation follows a **guitar pedal board** metaphor:

```
┌─────────┐   ┌───────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│  Wave   │ → │  Gain &   │ → │ Shift  │ → │ Stride │ → │ Effect │ → Output
│  ROM    │   │  Center   │   │        │   │        │   │        │
└─────────┘   └───────────┘   └────────┘   └────────┘   └────────┘
   source       amplitude       index       playback      pedal
               + position       offset       speed
```

Each output channel has its own signal chain with one effect slot.

## Waveform Sources

| ID | Name | Width | Description |
|----|------|-------|-------------|
| 0 | SIN | 128 | Sinusoid (use shift for COS) |
| 1 | TRI | 128 | Symmetric triangle |
| 2 | SAW | 128 | Sawtooth rising (use FLIP effect for falling) |
| 3 | SQR_64_128 | 128 | Square: 64 high, 64 low |
| 4 | SQR_32_128 | 128 | Square: 32 high, 96 low |
| 5 | SQR_04_128 | 128 | Square: 4 high, 124 low |
| 6 | NOISE | 128 | White noise (deterministic LFSR) |
| 7 | DC | 128 | Constant high (canvas for effects) |
| 8 | ENV_0 | variable | Custom waveform from ENV_BBUF_0 |
| 9 | ENV_1 | variable | Custom waveform from ENV_BBUF_1 |
| 10-15 | (reserved) | | |

**Note:** ROM sources (0-7) have fixed 128-sample width. ENV sources (8-9) use width_sel for variable width.

## CR_BIOS - Control Registers

Since interface clarity matters more than bit packing, BIOS uses multiple control words.

### CR_BIOS_ENABLE - Global Enables

```
Bit | Name          | Description
----|---------------|------------------------------------------
 0  | output_enable | Master output gate (0=muted, 1=active)
 1  | out1_enable   | OutputA enable
 2  | out2_enable   | OutputB enable
 3  | input_enable  | Master input gate (behavior TBD)
 4  | in1_enable    | InputA enable (behavior TBD)
 5  | in2_enable    | InputB enable (behavior TBD)
7:6 | (reserved)    |
```

### CR_BIOS_OUT1 - Output 1 Channel Strip

```
Bit   | Name        | Description
------|-------------|------------------------------------------
 3:0  | wave_sel    | Waveform source (0-7 ROM, 8-9 ENV_BBUF)
 7:4  | amplitude   | Gain/attenuation (0=full, 15=silent)
11:8  | center      | DC position (0=floor, 8=mid, 15=ceiling)
15:12 | shift       | LUT index offset (0-15 × 8 samples)
17:16 | stride      | Playback speed (0=×1, 1=×2, 2=×4, 3=×8)
21:18 | effect_sel  | Effect pedal (0=bypass, see table)
25:22 | effect_param| Effect intensity/threshold
28:26 | width_sel   | Samples per cycle for ENV sources (0=128, 4=2048)
31:29 | (reserved)  |
```

### CR_BIOS_OUT2 - Output 2 Channel Strip

Same layout as CR_BIOS_OUT1.

## Per-Channel Fields

### wave_sel [3:0] - Source Waveform

Selects the waveform source.

| Value | Source | Width | Notes |
|-------|--------|-------|-------|
| 0-7 | ROM | 128 (fixed) | See ROM waveform table |
| 8 | ENV_BBUF_0 | from width_sel | Custom waveform |
| 9 | ENV_BBUF_1 | from width_sel | Custom waveform |
| 10-15 | (reserved) | | |

For ROM sources, width is always 128 samples and width_sel is ignored.

### amplitude [7:4] - Gain Control

Attenuation via right-shift. The waveform is first converted to signed (centered at 0), then scaled.

| Value | Attenuation | Output Range |
|-------|-------------|--------------|
| 0 | ×1 (full) | ±16383 |
| 1 | ×0.5 | ±8191 |
| 4 | ×0.0625 | ±1023 |
| 15 | ×0.00003 | ±0 (silent) |

### center [11:8] - DC Position

Where to position the waveform in the output range. The scaled waveform oscillates around this point.

| Value | Center Voltage | Description |
|-------|----------------|-------------|
| 0 | 0 | Floor (risks clipping negative) |
| 8 | 16384 | Midpoint (safe for full-scale) |
| 15 | 30720 | Ceiling (risks clipping high) |

**Center model:** `output = center_voltage + scaled_waveform`

For a full-scale waveform (amplitude=0), center=8 keeps output in valid 0-32767 range.

### shift [15:12] - Index Offset

Offsets the LUT read address. Each increment shifts by 8 samples.

| Value | Sample Offset | Phase (for SIN) |
|-------|---------------|-----------------|
| 0 | 0 | 0° |
| 4 | 32 | 90° (= COS) |
| 8 | 64 | 180° |
| 12 | 96 | 270° |

**Implementation:** `addr = (base_addr + shift × 8) mod width`

For ROM sources, width is always 128. For ENV sources, width is determined by width_sel.

### stride [17:16] - Playback Speed

How many samples to skip per clock tick.

| Value | Stride | Effect |
|-------|--------|--------|
| 0 | ×1 | Normal playback |
| 1 | ×2 | Double speed (octave up) |
| 2 | ×4 | Quadruple speed |
| 3 | ×8 | 8× speed |

**Implementation:** `addr_increment = 1 << stride`

### effect_sel [21:18] - Effect Pedal

Which effect to apply after the base signal chain.

| Value | Effect | Description |
|-------|--------|-------------|
| 0x0 | BYPASS | Clean signal (no effect) |
| 0x1 | FLIP | Mirror around center |
| 0x2 | RECTIFY | Fold negative half upward |
| 0x3 | CLIP | Hard limit at threshold |
| 0x4 | FOLD | Wavefolder at threshold |
| 0x5 | QUANTIZE | Reduce bit depth |
| 0x6 | NOISE | Add white noise |
| 0x7 | GATE | Zero below threshold |
| 0x8-0xF | (reserved) | Future effects |

### effect_param [25:22] - Effect Intensity

Effect-specific parameter (0-15).

| Effect | Param Meaning |
|--------|---------------|
| BYPASS | (ignored) |
| FLIP | (ignored) |
| RECTIFY | 0=full-wave, 1=half-positive, 2=half-negative |
| CLIP | Threshold level (0=no clip, 15=heavy) |
| FOLD | Fold point (0=center, 15=extreme) |
| QUANTIZE | Output bits (0=1-bit, 15=16-bit) |
| NOISE | Mix level (0=none, 15=full noise) |
| GATE | Threshold (0=no gate, 15=aggressive) |

### width_sel [28:26] - ENV Buffer Mode

Specifies how to interpret the ENV_BBUF. Ignored for ROM sources (0-7).

| Value | Mode | Description |
|-------|------|-------------|
| 0 | **Bank mode** | 16 × 128-sample waveforms (like ROM) |
| 1 | Single 256 | One 256-sample waveform |
| 2 | Single 512 | One 512-sample waveform |
| 3 | Single 1024 | One 1024-sample waveform |
| 4 | Single 2048 | One 2048-sample waveform (full buffer) |
| 5-7 | (reserved) | |

**Bank mode (width_sel=0):**
- Buffer contains 16 waveforms × 128 samples × 16-bit = 4KB
- `shift` field selects which waveform (0-15), NOT phase offset
- ROM-compatible: use as drop-in replacement for ROM waveforms
- Like a "font character table" — load your own waveform bank

**Single waveform mode (width_sel=1-4):**
- Buffer contains one high-resolution waveform
- `shift` field controls phase offset (normal behavior)

**Implementation:**
```vhdl
if width_sel = 0 then
    -- Bank mode: shift selects waveform slot (0-15), 128 samples each
    base_addr <= shift & "0000000";  -- shift × 128
    wrap_width <= 128;
else
    -- Single mode: one waveform, shift is phase offset
    base_addr <= shift & "000";      -- shift × 8 (phase)
    wrap_width <= 128 << width_sel;  -- 256, 512, 1024, or 2048
end if;

index <= (base_addr + phase_counter) mod wrap_width;
```

**Use cases:**

| width_sel | shift | Behavior |
|-----------|-------|----------|
| 0 (bank) | 0 | Waveform slot 0 (samples 0-127) |
| 0 (bank) | 7 | Waveform slot 7 (samples 896-1023) |
| 0 (bank) | 15 | Waveform slot 15 (samples 1920-2047) |
| 4 (single) | 0 | Full 2048-sample waveform, no phase shift |
| 4 (single) | 4 | Full 2048-sample waveform, 32-sample phase shift |

## Transform Pipeline

Per-channel signal flow:

```
1. ROM Lookup
   raw = WAVE_ROM[wave_sel][(index + shift×8) mod 128]

2. Convert to Signed (center at zero)
   signed_wave = raw - 16384                    // ±16383 range

3. Apply Stride
   index += (1 << stride)                       // Advance read pointer

4. Apply Amplitude
   scaled = signed_wave >> amplitude            // Attenuate

5. Apply Center
   centered = (center × 2048) + scaled          // Position in output range

6. Apply Effect
   effected = EFFECT[effect_sel](centered, effect_param)

7. Clamp to Valid Range
   output = clamp(effected, 0, 32767)           // Unipolar safety
```

## Effect Implementations

### FLIP
```
output = (center × 2048) - scaled
```
Reflects the waveform around the center point.

### RECTIFY
```
if param == 0:  output = abs(centered - center×2048) + center×2048  // Full-wave
if param == 1:  output = max(centered, center×2048)                  // Half-positive
if param == 2:  output = min(centered, center×2048)                  // Half-negative
```

### CLIP
```
threshold = (15 - param) × 2048
output = clamp(centered, center×2048 - threshold, center×2048 + threshold)
```

### FOLD
```
threshold = (15 - param) × 2048
while output > center×2048 + threshold or output < center×2048 - threshold:
    output = reflect at boundary
```

### QUANTIZE
```
bits = param + 1                    // 1 to 16 bits
mask = 0xFFFF << (16 - bits)
output = centered & mask
```

### NOISE
```
noise = LFSR_next() >> 1            // 0 to 32767
mix = param / 15
output = centered × (1 - mix) + noise × mix
```

### GATE
```
threshold = param × 2048
if abs(centered - center×2048) < threshold:
    output = center × 2048          // Gate to center
else:
    output = centered
```

## ENV_BBUF Custom Waveforms

### Data Format

ENV_BBUF waveforms use the same format as ROM waveforms:
- **16-bit signed** values with **unipolar constraint** (0 to 32767)
- Contiguous samples, no header
- Loaded via LOADER module at deployment time

### Single Waveform Mode (width_sel=1-4)

```
ENV_BBUF_n memory layout (single high-resolution waveform):
┌─────────────────────────────────────────────────┐
│ Sample 0    │ Sample 1    │ ... │ Sample N-1   │
│ (16-bit)    │ (16-bit)    │     │ (16-bit)     │
└─────────────────────────────────────────────────┘

Width determines N:
  width_sel=1: N=256  (512 bytes)
  width_sel=2: N=512  (1024 bytes)
  width_sel=3: N=1024 (2048 bytes)
  width_sel=4: N=2048 (4096 bytes = full buffer)
```

In single waveform mode, `shift` controls phase offset as usual.

### Bank Mode (width_sel=0) - "Font Character Table"

When `width_sel=0`, the ENV buffer acts like a custom ROM bank:

```
ENV_BBUF_n as waveform bank (16 × 128 samples):
┌────────┬────────┬────────┬────────┬─────┬──────────┐
│ Slot 0 │ Slot 1 │ Slot 2 │ Slot 3 │ ... │ Slot 15  │
│ 256B   │ 256B   │ 256B   │ 256B   │     │ 256B     │
└────────┴────────┴────────┴────────┴─────┴──────────┘
    ↑
 shift=0    shift=1   shift=2   shift=3      shift=15
```

**Key behavior:**
- `shift` field selects which waveform slot (0-15), NOT phase offset
- Each slot is 128 samples, same as ROM waveforms
- Enables real-time waveform switching via control register updates
- No phase control in bank mode (trade-off for slot selection)

**Use case:** Load 16 custom waveforms at deployment time, then select between them at runtime via `shift` field — no slow network round-trip needed to change waveforms.

### Python Generation Example

```python
import numpy as np

def gen_custom_waveform(width=2048):
    """Generate a custom waveform for ENV_BBUF."""
    # Example: complex multi-harmonic waveform
    t = np.linspace(0, 2*np.pi, width, endpoint=False)
    wave = np.sin(t) + 0.5*np.sin(2*t) + 0.25*np.sin(3*t)
    # Normalize to 0-32767 range
    wave = (wave - wave.min()) / (wave.max() - wave.min())
    return (wave * 32767).astype(np.int16)

def save_for_loader(waveform, filename):
    """Save waveform as raw binary for LOADER."""
    waveform.tofile(filename)
```

## Design Decisions

### Playback Rate
Base playback rate controlled by **global clock divider** in BOOT module.
Stride provides per-channel speed multiplication on top of global rate.

### OutputC Behavior
OutputC **always** produces HVS-encoded BIOS state. Not configurable.

### Input Behavior
Input enables [5:3] reserved for future functionality:
- Loopback / passthrough testing
- Threshold triggering
- Input mixing with generated waveforms
- Level monitoring

## Example Configurations

### Dual Sine, Centered (safest default)
```
CR_BIOS_ENABLE = 0x07  (output + out1 + out2 enabled)
CR_BIOS_OUT1 = wave=SIN(0), amp=0, center=8, shift=0, stride=0, effect=BYPASS
CR_BIOS_OUT2 = wave=SIN(0), amp=0, center=8, shift=0, stride=0, effect=BYPASS
```

### I/Q Quadrature (SIN + COS via shift)
```
CR_BIOS_OUT1 = wave=SIN, center=8, shift=0   // SIN at 0°
CR_BIOS_OUT2 = wave=SIN, center=8, shift=4   // SIN at 90° = COS
```

### Inverted Sawtooth (SAW + FLIP)
```
CR_BIOS_OUT1 = wave=SAW, center=8, effect=FLIP
```

### Clipped Sine (soft square)
```
CR_BIOS_OUT1 = wave=SIN, center=8, effect=CLIP, param=10
```

### Rectified Sine (pulsing DC)
```
CR_BIOS_OUT1 = wave=SIN, center=4, effect=RECTIFY, param=0
```

### Bit-crushed Noise
```
CR_BIOS_OUT1 = wave=NOISE, center=8, effect=QUANTIZE, param=2  // 3-bit
```

### Custom High-Resolution Waveform (ENV_BBUF)
```
CR_BIOS_OUT1 = wave=ENV_0(8), center=8, width_sel=4  // 2048-sample custom from ENV_BBUF_0
CR_BIOS_OUT2 = wave=ENV_1(9), center=8, width_sel=2  // 512-sample custom from ENV_BBUF_1
```

### ENV Waveform with Effects
```
CR_BIOS_OUT1 = wave=ENV_0(8), center=8, width_sel=4, stride=2, effect=CLIP, param=8
// 2048-sample custom waveform, 4× speed, clipped
```

## See Also

- [BOOT-ROM-primitives-spec.md](docs/boot/BOOT-ROM-WAVES-prop.md) - Waveform definitions
- [boot-process-terms.md](../boot-process-terms.md) - Naming conventions
