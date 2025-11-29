---
created: 2025-11-29
modified: 2025-11-29
status: DRAFT
---
# BOOT ROM Primitives Specification

This document specifies the hardcoded ROM primitives provided by the BOOT subsystem for use by BIOS and application modules.

## Design Philosophy

### Separation of Concerns

```
Synthesis Time (ROM)          Deployment Time (ENV)         Runtime (Registers)
────────────────────          ────────────────────          ───────────────────
- Waveform shapes             - Analog frontend config      - Percentage requests
- Percentage curves           - Voltage scaling factors     - Waveform selection
- Clock divider logic         - Calibration offsets         - Clock divider select
                              - Custom curves (if needed)
```

**Key Principle:** ROMs contain *normalized* data that is platform-agnostic. Deployment-time configuration transforms normalized values into hardware-specific outputs.

### Consistency Over Cleverness

Even when a waveform *could* be computed (e.g., triangle from counter), we store it as a LUT to guarantee:
- Identical timing characteristics across all waveform types
- Predictable BRAM access patterns
- No unexpected variations from arithmetic edge cases

## ROM Contents Overview

| Bank | ROM ID | Name | Entries | Bits | Bytes | Description |
|------|--------|------|---------|------|-------|-------------|
| 0 | 0 | `SIN_256` | 256 | 16 | 512 | Full sine cycle |
| 0 | 1 | `TRI_256` | 256 | 16 | 512 | Symmetric triangle |
| 0 | 2 | `SAW_UP_256` | 256 | 16 | 512 | Sawtooth rising |
| 0 | 3 | `SAW_DN_256` | 256 | 16 | 512 | Sawtooth falling |
| 0 | 4 | `SQR_50_256` | 256 | 16 | 512 | Square 50% duty |
| 0 | 5 | `SQR_25_256` | 256 | 16 | 512 | Square 25% duty |
| 0 | 6 | `SQR_10_256` | 256 | 16 | 512 | Square 10% duty |
| 0 | 7 | `STEP_16` | 256 | 16 | 512 | 16 discrete levels |
| **Subtotal** | | | | | **4096** | **Bank 0: Waveforms** |
| 1 | 8 | `PCT_LINEAR` | 101 | 16 | 202 | Linear 0-100% |
| 1 | 9 | `PCT_LOG` | 101 | 16 | 202 | Logarithmic curve |
| 1 | 10 | `PCT_SQRT` | 101 | 16 | 202 | Square root curve |
| 1 | 11 | `PCT_GAMMA22` | 101 | 16 | 202 | Gamma 2.2 curve |
| 1 | - | Reserved | 101×4 | 16 | 808 | Future curves |
| **Subtotal** | | | | | **~1616** | **Bank 1: Percentages** |
| **Total** | | | | | **~5712** | Fits in 2× 18Kb BRAM |

## Waveform LUTs (Bank 0)

### Value Encoding

All waveform LUTs use **16-bit signed** values:

```
+32767 = Maximum positive (≈ +5V at full scale)
     0 = Midpoint (≈ 0V)
-32768 = Maximum negative (≈ -5V at full scale)
```

### SIN_256 - Sinusoid

Full 360° sine cycle, 256 samples.

```
Entry[i] = round(32767 × sin(2π × i / 256))

Index:    0    32    64    96   128   160   192   224   255
Value:    0  23170 32767 23170     0 -23170 -32767 -23170    -201
Phase:    0°   45°   90°  135°  180°   225°   270°   315°   ~360°
```

**Use Cases:**
- AC test signals
- Phase relationship verification
- Audio/RF waveform generation

### TRI_256 - Triangle

Symmetric triangle wave, 256 samples.

```
Entry[i] =
  i < 128:  (i × 32767) / 127        -- Rising: 0 → +32767
  i >= 128: ((255-i) × 32767) / 127  -- Falling: +32767 → 0

Index:    0    64   127   128   192   255
Value:    0  16383 32767 32767 16383     0
```

**Note:** Triangle is unipolar (0 to +max). For bipolar, subtract 16384.

**Use Cases:**
- Slew rate testing
- Linear sweep generation
- PWM modulation source

### SAW_UP_256 - Sawtooth Rising

Linear ramp from minimum to maximum, 256 samples.

```
Entry[i] = -32768 + (i × 65535) / 255

Index:    0    64   128   192   255
Value: -32768 -16384    0 16384 32767
```

**Use Cases:**
- DAC linearity verification
- Time-base generation
- Frequency sweep source

### SAW_DN_256 - Sawtooth Falling

Linear ramp from maximum to minimum, 256 samples.

```
Entry[i] = 32767 - (i × 65535) / 255

Index:    0    64   128   192   255
Value: 32767 16384    0 -16384 -32768
```

**Use Cases:**
- Reverse sweep
- Decay envelope
- Complementary signal generation

### SQR_50_256 - Square Wave (50% Duty)

Square wave, 50% duty cycle, 256 samples.

```
Entry[i] =
  i < 128:  +32767  -- High for first half
  i >= 128: -32768  -- Low for second half
```

**Use Cases:**
- Digital timing verification
- Rise/fall time testing
- Clock signal simulation

### SQR_25_256 - Pulse (25% Duty)

Pulse wave, 25% duty cycle, 256 samples.

```
Entry[i] =
  i < 64:   +32767  -- High for first quarter
  i >= 64:  -32768  -- Low for remaining 75%
```

**Use Cases:**
- Narrow pulse testing
- Trigger signal generation

### SQR_10_256 - Pulse (10% Duty)

Pulse wave, ~10% duty cycle, 256 samples.

```
Entry[i] =
  i < 26:   +32767  -- High for ~10%
  i >= 26:  -32768  -- Low for ~90%
```

**Use Cases:**
- Impulse-like signals
- Low duty cycle testing

### STEP_16 - Staircase (16 Levels)

16 discrete voltage levels, 16 samples per level.

```
Level[n] = -32768 + (n × 65535) / 15    for n = 0..15
Entry[i] = Level[i / 16]                for i = 0..255

Index:   0-15  16-31  32-47  ...  240-255
Level:      0      1      2  ...       15
Value: -32768 -28398 -24029  ...   +32767
```

**Use Cases:**
- DNL/INL testing
- ADC/DAC quantization verification
- Discrete level calibration

## Percentage LUTs (Bank 1)

### Value Encoding

All percentage LUTs use **16-bit unsigned** values:

```
    0 = 0%
65535 = 100%

Normalized output = LUT[percentage_index]
```

The percentage index range is **0 to 100** (101 valid entries). Indices 101-127 should clamp to 100%.

### PCT_LINEAR - Linear Percentage

Direct linear mapping from percentage to normalized value.

```
Entry[i] = round(65535 × i / 100)

Index:    0    25    50    75   100
Value:    0 16384 32768 49151 65535
```

**Use Cases:**
- Most common case (linear probes, standard DACs)
- Default curve when no special mapping needed

### PCT_LOG - Logarithmic Percentage

Logarithmic mapping for audio/perceptual applications.

```
Entry[i] = round(65535 × log10(1 + 9×i/100) / log10(10))
         = round(65535 × log10(1 + 0.09×i))

Index:    0    25    50    75   100
Value:    0 23171 39794 52876 65535
```

**Use Cases:**
- Audio volume control (perceived loudness)
- Light intensity (perceived brightness)

### PCT_SQRT - Square Root Percentage

Square root mapping for power-to-amplitude conversion.

```
Entry[i] = round(65535 × sqrt(i / 100))

Index:    0    25    50    75   100
Value:    0 32768 46341 56756 65535
```

**Use Cases:**
- Power percentage to amplitude conversion
- Energy-based scaling

### PCT_GAMMA22 - Gamma 2.2 Percentage

Gamma 2.2 curve for display/visual applications.

```
Entry[i] = round(65535 × (i / 100)^2.2)

Index:    0    25    50    75   100
Value:    0  3664 18350 43366 65535
```

**Use Cases:**
- Display calibration
- Perceptual luminance mapping

## Memory Architecture

### BRAM Allocation

```
┌─────────────────────────────────────────────────────────────┐
│                    BOOT ROM BANK 0                          │
│                 (Waveforms - 4KB)                           │
│  ┌─────────┬─────────┬─────────┬─────────┐                 │
│  │ SIN_256 │ TRI_256 │SAW_UP   │SAW_DN   │  0x000 - 0x7FF  │
│  │ 512B    │ 512B    │ 512B    │ 512B    │                 │
│  ├─────────┼─────────┼─────────┼─────────┤                 │
│  │ SQR_50  │ SQR_25  │ SQR_10  │ STEP_16 │  0x800 - 0xFFF  │
│  │ 512B    │ 512B    │ 512B    │ 512B    │                 │
│  └─────────┴─────────┴─────────┴─────────┘                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    BOOT ROM BANK 1                          │
│                 (Percentages - 2KB)                         │
│  ┌───────────┬───────────┬───────────┬───────────┐         │
│  │PCT_LINEAR │ PCT_LOG   │ PCT_SQRT  │PCT_GAMMA22│         │
│  │ 202B      │ 202B      │ 202B      │ 202B      │         │
│  ├───────────┴───────────┴───────────┴───────────┤         │
│  │              Reserved (808B)                   │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Addressing Scheme

**Waveform Access:**
```vhdl
-- 3-bit waveform select + 8-bit sample index
wave_addr <= wave_sel(2 downto 0) & sample_idx(7 downto 0);
wave_data <= WAVE_ROM(to_integer(unsigned(wave_addr)));
```

**Percentage Access:**
```vhdl
-- 2-bit curve select + 7-bit percentage index
pct_addr <= curve_sel(1 downto 0) & pct_idx(6 downto 0);
pct_data <= PCT_ROM(to_integer(unsigned(pct_addr)));
```

## pct_scaler Module

### Purpose

The `pct_scaler` module transforms a percentage request (0-100) into a hardware-specific voltage value using:
1. Hardcoded percentage LUT (curve shape)
2. Deployment-time scale and offset (voltage range)

### Interface

```vhdl
entity boot_pct_scaler is
    port (
        Clk         : in  std_logic;

        -- Percentage request (0-100, clamped internally)
        pct_idx     : in  std_logic_vector(6 downto 0);

        -- Curve selection
        curve_sel   : in  std_logic_vector(1 downto 0);
        -- "00" = LINEAR, "01" = LOG, "10" = SQRT, "11" = GAMMA22

        -- Deployment-time configuration (from ENV_BBUF or CR)
        v_scale     : in  unsigned(15 downto 0);  -- Full-scale output value
        v_offset    : in  signed(15 downto 0);    -- Zero-point offset

        -- Scaled output (valid 1 cycle after pct_idx changes)
        voltage_out : out signed(15 downto 0)
    );
end entity;
```

### Operation

```
1. Lookup: raw = PCT_LUT[curve_sel][pct_idx]    -- 0 to 65535
2. Scale:  scaled = (raw × v_scale) >> 16       -- 0 to v_scale
3. Offset: output = scaled + v_offset           -- Final voltage
```

### Timing

| Cycle | Action |
|-------|--------|
| 0 | pct_idx presented |
| 1 | LUT output valid, multiply starts |
| 2 | voltage_out valid |

**Latency: 2 clock cycles** (can be pipelined for throughput)

### Usage Pattern

```vhdl
-- In application shim layer
process(Clk)
begin
    if rising_edge(Clk) then
        if intensity_pct_changed = '1' then
            -- Trigger new calculation (happens automatically)
            pct_request <= intensity_pct;
        end if;

        -- Latch result when valid
        if pct_valid = '1' then
            intensity_voltage_reg <= pct_scaler_output;
        end if;
    end if;
end process;

-- DAC always reads from registered value
OutputB <= std_logic_vector(intensity_voltage_reg);
```

## Clock Divider

### CR0 Bit Allocation

```
CR0[20:17] = CLK_DIV_SEL (4 bits)
CR0[16]    = CLK_DIV_LOADER_BYPASS (1 bit)
```

**Updated CR0 Map:**
```
CR0[31:29] - RUN gate (R/U/N)
CR0[28:25] - Module select (P/B/L/R)
CR0[24]    - RET
CR0[23:22] - LOADER buffer count
CR0[21]    - LOADER data strobe
CR0[20:17] - CLK_DIV_SEL         ← NEW
CR0[16]    - CLK_DIV_LOADER_BYPASS ← NEW
CR0[15:0]  - Reserved
```

### Divider Values

| CLK_DIV_SEL | Divider | Effective Freq | Period | Use Case |
|-------------|---------|----------------|--------|----------|
| 0000 | /1 | 125.00 MHz | 8 ns | Normal operation |
| 0001 | /2 | 62.50 MHz | 16 ns | |
| 0010 | /4 | 31.25 MHz | 32 ns | |
| 0011 | /8 | 15.63 MHz | 64 ns | |
| 0100 | /16 | 7.81 MHz | 128 ns | |
| 0101 | /32 | 3.91 MHz | 256 ns | |
| 0110 | /64 | 1.95 MHz | 512 ns | |
| 0111 | /128 | 977 kHz | 1.02 μs | |
| 1000 | /256 | 488 kHz | 2.05 μs | Scope-friendly |
| 1001 | /512 | 244 kHz | 4.10 μs | |
| 1010 | /1024 | 122 kHz | 8.19 μs | |
| 1011 | /2048 | 61.0 kHz | 16.4 μs | |
| 1100 | /4096 | 30.5 kHz | 32.8 μs | Audio-rate |
| 1101 | /8192 | 15.3 kHz | 65.5 μs | |
| 1110 | /16384 | 7.63 kHz | 131 μs | Slow debug |
| 1111 | /32768 | 3.81 kHz | 262 μs | Crawl mode |

### Scope

The clock divider generates a `ClkEn_divided` signal that gates:
- BOOT FSM
- BIOS module
- PROG modules

**LOADER Exception:** When `CLK_DIV_LOADER_BYPASS = 1` (default), LOADER receives undivided `ClkEn`. This preserves the blind handshake timing protocol.

### Interface

```vhdl
-- In BOOT_TOP
signal clk_div_sel     : std_logic_vector(3 downto 0);
signal clk_div_counter : unsigned(14 downto 0);
signal clk_div_tick    : std_logic;
signal ClkEn_divided   : std_logic;

-- Free-running counter (always runs at full speed)
process(Clk)
begin
    if rising_edge(Clk) then
        clk_div_counter <= clk_div_counter + 1;
    end if;
end process;

-- Generate tick at selected division rate
process(clk_div_sel, clk_div_counter)
begin
    case clk_div_sel is
        when "0000" => clk_div_tick <= '1';  -- /1
        when "0001" => clk_div_tick <= clk_div_counter(0);
        when "0010" => clk_div_tick <= clk_div_counter(1) and not clk_div_counter(0);
        -- ... (full decode table)
        when others => clk_div_tick <= '1';
    end case;
end process;

-- Gated enable
ClkEn_divided <= ClkEn and clk_div_tick;
```

## VHDL Package Integration

### New Package: forge_rom_pkg.vhd

```vhdl
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

package forge_rom_pkg is

    -- Waveform ROM types
    type wave_lut_t is array(0 to 255) of signed(15 downto 0);
    type wave_bank_t is array(0 to 7) of wave_lut_t;

    -- Percentage ROM types
    type pct_lut_t is array(0 to 100) of unsigned(15 downto 0);
    type pct_bank_t is array(0 to 3) of pct_lut_t;

    -- ROM IDs
    constant WAVE_SIN      : natural := 0;
    constant WAVE_TRI      : natural := 1;
    constant WAVE_SAW_UP   : natural := 2;
    constant WAVE_SAW_DN   : natural := 3;
    constant WAVE_SQR_50   : natural := 4;
    constant WAVE_SQR_25   : natural := 5;
    constant WAVE_SQR_10   : natural := 6;
    constant WAVE_STEP_16  : natural := 7;

    constant PCT_LINEAR    : natural := 0;
    constant PCT_LOG       : natural := 1;
    constant PCT_SQRT      : natural := 2;
    constant PCT_GAMMA22   : natural := 3;

    -- Curve select encoding
    constant CURVE_LINEAR  : std_logic_vector(1 downto 0) := "00";
    constant CURVE_LOG     : std_logic_vector(1 downto 0) := "01";
    constant CURVE_SQRT    : std_logic_vector(1 downto 0) := "10";
    constant CURVE_GAMMA22 : std_logic_vector(1 downto 0) := "11";

    -- ROM contents (generated - see forge_rom_gen.py)
    constant WAVE_ROM : wave_bank_t;
    constant PCT_ROM  : pct_bank_t;

end package forge_rom_pkg;
```

### forge_common_pkg.vhd Additions

```vhdl
-- Add to existing package:

----------------------------------------------------------------------------
-- Clock Divider (CR0[20:16])
----------------------------------------------------------------------------
constant CLK_DIV_SEL_HI      : natural := 20;
constant CLK_DIV_SEL_LO      : natural := 17;
constant CLK_DIV_BYPASS_BIT  : natural := 16;

-- Divider select values
constant CLK_DIV_1     : std_logic_vector(3 downto 0) := "0000";
constant CLK_DIV_2     : std_logic_vector(3 downto 0) := "0001";
constant CLK_DIV_4     : std_logic_vector(3 downto 0) := "0010";
constant CLK_DIV_8     : std_logic_vector(3 downto 0) := "0011";
constant CLK_DIV_16    : std_logic_vector(3 downto 0) := "0100";
constant CLK_DIV_32    : std_logic_vector(3 downto 0) := "0101";
constant CLK_DIV_64    : std_logic_vector(3 downto 0) := "0110";
constant CLK_DIV_128   : std_logic_vector(3 downto 0) := "0111";
constant CLK_DIV_256   : std_logic_vector(3 downto 0) := "1000";
constant CLK_DIV_512   : std_logic_vector(3 downto 0) := "1001";
constant CLK_DIV_1024  : std_logic_vector(3 downto 0) := "1010";
constant CLK_DIV_2048  : std_logic_vector(3 downto 0) := "1011";
constant CLK_DIV_4096  : std_logic_vector(3 downto 0) := "1100";
constant CLK_DIV_8192  : std_logic_vector(3 downto 0) := "1101";
constant CLK_DIV_16384 : std_logic_vector(3 downto 0) := "1110";
constant CLK_DIV_32768 : std_logic_vector(3 downto 0) := "1111";

-- Helper function
function get_clk_div_sel(cr0 : std_logic_vector(31 downto 0))
    return std_logic_vector;
```

## Python ROM Generation

A Python script generates the ROM contents for synthesis:

```python
# py_tools/forge_rom_gen.py

import numpy as np

def gen_sin_256():
    """Full sine cycle, 256 entries, 16-bit signed."""
    x = np.linspace(0, 2*np.pi, 256, endpoint=False)
    return np.round(32767 * np.sin(x)).astype(np.int16)

def gen_tri_256():
    """Symmetric triangle, 256 entries, 16-bit signed (0 to +max)."""
    up = np.linspace(0, 32767, 128)
    down = np.linspace(32767, 0, 128, endpoint=False)
    return np.concatenate([up, down]).astype(np.int16)

def gen_pct_linear():
    """Linear percentage, 101 entries, 16-bit unsigned."""
    return np.round(65535 * np.arange(101) / 100).astype(np.uint16)

def gen_pct_log():
    """Logarithmic percentage, 101 entries, 16-bit unsigned."""
    x = np.arange(101)
    return np.round(65535 * np.log10(1 + 9*x/100)).astype(np.uint16)

def gen_vhdl_rom_package():
    """Generate forge_rom_pkg_body.vhd with ROM contents."""
    # ... implementation ...
```

## Open Questions

1. **Waveform polarity:** Should TRI_256 be bipolar (-32768 to +32767) or unipolar (0 to +32767)?
   - Current: Unipolar (matches typical ramp/sweep use case)
   - Alternative: Bipolar (matches SIN for consistency)

2. **Percentage overflow:** What happens for pct_idx > 100?
   - Current: Clamp to 100%
   - Alternative: Modulo (wrap around)
   - Alternative: Assert fault

3. **Clock divider default:** What should CLK_DIV_SEL default to on reset?
   - Current: 0000 (/1, no division)
   - This is the safest default

4. **BRAM inference vs instantiation:** Should ROMs be inferred or explicitly instantiated?
   - Inference is more portable
   - Instantiation gives more control over placement

## See Also

- [BOOT-FSM-spec.md](../BOOT-FSM-spec.md) - BOOT state machine (AUTHORITATIVE)
- [forge_common_pkg.vhd](../../rtl/forge_common_pkg.vhd) - CR0 bit definitions
- [boot-process-terms.md](../boot-process-terms.md) - Naming conventions
- [HVS-encoding-scheme.md](../HVS-encoding-scheme.md) - Voltage encoding
