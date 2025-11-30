---
publish: "true"
type: reference
created: 2025-11-29
modified: 2025-11-29 18:14:00
tags:
  - moku
  - cloudcompile
  - clock
  - timing
  - critical
accessed: 2025-11-29 18:17:56
---

# Moku Clock Domains: A Critical Guide for CloudCompile Developers

> [!danger] Critical Knowledge Gap
> This document addresses a **poorly documented** aspect of Moku CloudCompile development: the distinction between **ADC/DAC sample rate clocks** and **MCC fabric clocks**. Confusing these leads to timing errors that are difficult to diagnose.

## The Two Clock Domains

Every Moku platform has **two distinct clock domains** that CloudCompile developers must understand:

| Clock Domain | Purpose | Where Used |
|--------------|---------|------------|
| **ADC/DAC Clock** | Analog-to-digital conversion, sample rate | Physical I/O, waveform generation, data acquisition |
| **MCC Fabric Clock** | FPGA fabric timing, CloudCompile logic | Control registers, timing counters, FSM transitions |

**The critical insight: These are NOT the same frequency!**

## Platform Clock Reference

| Platform | ADC/DAC Clock | MCC Fabric Clock | Ratio | MCC Period |
|----------|---------------|------------------|-------|------------|
| **Moku:Go** | 125 MHz | **31.25 MHz** | ÷4 | 32 ns |
| **Moku:Lab** | 500 MHz | **125 MHz** | ÷4 | 8 ns |
| **Moku:Pro** | 1250 MHz | **312.5 MHz** | ÷4 | 3.2 ns |
| **Moku:Delta** | 5000 MHz | **312.5 MHz** | ÷16 | 3.2 ns |

> [!warning] The MCC fabric clock is NOT the ADC sample rate!
> Most documentation (including official Liquid Instruments specs) emphasizes the ADC/DAC sample rates. CloudCompile timing registers use the **MCC fabric clock**, which is typically 4x slower.

## Official Datasheets: MCC Clock is Undocumented

> [!danger] Critical Gap in Official Documentation
> After reviewing all four official Liquid Instruments datasheets (Moku:Go, Moku:Lab, Moku:Pro, Moku:Delta), the **MCC fabric clock is not mentioned anywhere**.

### What the Datasheets Document

| Platform | Datasheet Version | ADC Sample Rate | DAC Sample Rate | MCC Clock? |
|----------|-------------------|-----------------|-----------------|------------|
| Moku:Go | v24-0815 | 125 MSa/s | 125 MSa/s | **NOT MENTIONED** |
| Moku:Lab | v24-0412 | 500 MSa/s | 1 GSa/s | **NOT MENTIONED** |
| Moku:Pro | v24-1015 | 1.25-5 GSa/s | 1.25 GSa/s | **NOT MENTIONED** |
| Moku:Delta | v25-0820 | 5 GSa/s | 10 GSa/s | **NOT MENTIONED** |

The datasheets focus exclusively on:
- ADC/DAC sample rates (emphasized in marketing)
- Analog bandwidth (-3 dB points)
- Input/output voltage ranges
- Noise performance specifications
- Slot-to-slot interconnect bandwidth (12.5-80 Gb/s)

### What is NOT Documented

The following are **completely absent** from official datasheets:
- FPGA fabric clock frequency
- MCC/CloudCompile timing clock
- The ÷4 (or ÷16 for Delta) ratio between ADC and fabric clocks
- Any reference to 31.25 MHz (Go), 125 MHz (Lab), or 312.5 MHz (Pro/Delta) for MCC

### Implications for CloudCompile Developers

This means:
1. **You cannot find MCC timing info in official specs** - datasheets won't help
2. **The only authoritative source is example code** - specifically `BoxcarControlPanel.py`
3. **Third-party developers will likely use wrong clock** - 125 MHz is prominently advertised for Moku:Go
4. **4x timing errors are virtually guaranteed** - until you discover this undocumented detail

### Source Files (Local Copies)

```
libs/moku-models-v4/datasheets/
├── Datasheet-MokuGo.pdf      # v24-0815 - Only mentions 125 MSa/s
├── Datasheet-MokuLab.pdf     # v24-0412 - Only mentions 500 MSa/s
├── Datasheet-MokuPro.pdf     # v24-1015 - Only mentions 1.25-5 GSa/s
└── Datasheet-MokuDelta.pdf   # v25-0820 - Only mentions 5 GSa/s
```

## Evidence: Official Liquid Instruments Examples

### Source: `moku_trim_examples/mcc/HDLCoder/hdlcoder_boxcar/python/BoxcarControlPanel.py`

```python
# Lines 42-47 - Official MCC timing periods
period_dict = {
    'Moku:Go': 32e-9,      # 32 ns = 31.25 MHz (NOT 125 MHz!)
    'Moku:Lab': 8e-9,      # 8 ns = 125 MHz (NOT 500 MHz!)
    'Moku:Pro': 3.2e-9,    # 3.2 ns = 312.5 MHz (NOT 1.25 GHz!)
    'Moku:Delta': 3.2e-9   # 3.2 ns = 312.5 MHz
}

# Usage: Convert time to MCC clock cycles
trg_delay_bits = math.ceil(trg_delay_ns * 1e-9 / period)
mcc.set_control(1, trg_delay_bits)
```

### Source: `moku_trim_examples/mcc/Moderate/SweptPulse/MokuGo/mim_mgo_wg_mcc.py`

```python
# Line 49-50 - Explicit 31.25 MHz for Moku:Go
# Calculate control register values based on clock frequency of Moku:Go
freqControl = int(31250000/float(PRF))  # 31.25 MHz, NOT 125 MHz!
```

### Source: `moku_trim_examples/mcc/Moderate/SweptPulse/MokuPro/mim_mpro_wg_mcc_la_osc.py`

```python
# Line 61 - Explicit 312.5 MHz for Moku:Pro
freqControl = int(312500000/float(PRF))  # 312.5 MHz, NOT 1.25 GHz!
```

## Common Pitfalls

### Pitfall 1: Using ADC Clock Instead of MCC Clock

**Wrong (4x timing error):**
```python
# Using ADC sample rate for timing calculations
CLK_FREQ = 125_000_000  # 125 MHz - WRONG for MCC on Moku:Go!
delay_cycles = int(delay_us * 1e-6 * CLK_FREQ)
mcc.set_control(1, delay_cycles)  # Delay will be 4x shorter than expected!
```

**Correct:**
```python
# Using MCC fabric clock
MCC_CLK_FREQ = 31_250_000  # 31.25 MHz - Correct for Moku:Go MCC
delay_cycles = int(delay_us * 1e-6 * MCC_CLK_FREQ)
mcc.set_control(1, delay_cycles)  # Correct timing
```

### Pitfall 2: Hardcoding Platform-Specific Clocks

**Wrong:**
```python
# Hardcoded for one platform - breaks on others
CLOCK_PERIOD = 32e-9  # Only correct for Moku:Go!
```

**Correct:**
```python
# Query platform at runtime
description = moku.describe()
hardware = description['hardware']

period_dict = {
    'Moku:Go': 32e-9,
    'Moku:Lab': 8e-9,
    'Moku:Pro': 3.2e-9,
    'Moku:Delta': 3.2e-9
}
CLOCK_PERIOD = period_dict[hardware]
```

### Pitfall 3: Confusing VHDL Simulation vs Hardware Clocks

**Issue:** VHDL testbenches (CocoTB/GHDL) may use different clock frequencies than real hardware.

**Symptoms:**
- Simulation passes, hardware fails
- Timing looks correct in simulation, 4x off on device
- FSM transitions work in sim but timeout on hardware

**Solution:** Explicitly document and verify clock assumptions:

```vhdl
-- In VHDL entity header:
-- Clock Frequency: 125 MHz (Moku:Go ADC clock)
-- Note: MCC fabric clock is 31.25 MHz for timing registers!
generic (
    CLK_FREQ_HZ : integer := 125000000  -- ADC clock for I/O timing
    -- MCC_CLK_FREQ_HZ : integer := 31250000  -- For control register timing
);
```

### Pitfall 4: Register Propagation Delays

**Issue:** After `set_control()`, there's a network propagation delay before the value reaches the FPGA.

**Wrong:**
```python
mcc.set_control(0, arm_value)
# Immediately read state - may see old value!
data = osc.get_data()
```

**Correct:**
```python
mcc.set_control(0, arm_value)
await asyncio.sleep(0.01)  # 10ms minimum propagation delay
data = osc.get_data(wait_reacquire=True)  # Wait for new frame
```

## ADC Resolution Reference

For voltage-to-register conversions, ADC resolution also varies by platform:

| Platform | ADC Bits | Resolution (V/bit) | Bits/Volt |
|----------|----------|-------------------|-----------|
| Moku:Go | 12-bit | 1/6550.4 | ~6550 |
| Moku:Lab | 12-bit | 2/30000 | ~15000 |
| Moku:Pro | 10-bit* | 1/29925 | ~29925 |
| Moku:Delta | 14-bit* | 1/36440 | ~36440 |

\* Blended ADC architecture (primary ADC; secondary high-resolution ADC available)

**Voltage to register conversion:**
```python
resolution_dict = {
    'Moku:Go': 1/6550.4,
    'Moku:Lab': 2/30000,
    'Moku:Pro': 1/29925,
    'Moku:Delta': 1/36440
}
resolution = resolution_dict[hardware]

# Convert voltage to register value
trigger_level_volts = 0.5
trigger_level_bits = int(trigger_level_volts / resolution)
mcc.set_control(0, trigger_level_bits)
```

## Portable Clock Utility Pattern

```python
"""
Platform-aware clock utilities for Moku CloudCompile.
"""

class MokuClockConfig:
    """Platform-specific clock and ADC configuration."""

    # MCC fabric clock periods (seconds)
    MCC_PERIOD = {
        'Moku:Go': 32e-9,      # 31.25 MHz
        'Moku:Lab': 8e-9,      # 125 MHz
        'Moku:Pro': 3.2e-9,    # 312.5 MHz
        'Moku:Delta': 3.2e-9   # 312.5 MHz
    }

    # ADC resolution (volts per bit)
    ADC_RESOLUTION = {
        'Moku:Go': 1/6550.4,
        'Moku:Lab': 2/30000,
        'Moku:Pro': 1/29925,
        'Moku:Delta': 1/36440
    }

    def __init__(self, moku_instance):
        """Initialize from connected Moku device."""
        description = moku_instance.describe()
        self.hardware = description['hardware']
        self.period = self.MCC_PERIOD[self.hardware]
        self.resolution = self.ADC_RESOLUTION[self.hardware]
        self.mcc_freq_hz = 1.0 / self.period

    def time_to_cycles(self, seconds: float) -> int:
        """Convert time (seconds) to MCC clock cycles."""
        return int(seconds / self.period)

    def us_to_cycles(self, microseconds: float) -> int:
        """Convert microseconds to MCC clock cycles."""
        return self.time_to_cycles(microseconds * 1e-6)

    def ns_to_cycles(self, nanoseconds: float) -> int:
        """Convert nanoseconds to MCC clock cycles."""
        return self.time_to_cycles(nanoseconds * 1e-9)

    def volts_to_bits(self, volts: float) -> int:
        """Convert voltage to ADC register value."""
        return int(volts / self.resolution)


# Usage:
# clock = MokuClockConfig(moku_instance)
# delay_cycles = clock.us_to_cycles(100)  # Platform-aware conversion
# mcc.set_control(1, delay_cycles)
```

## Why This Matters for BIOS/Boot Development

If you're developing boot sequences or BIOS-like functionality for CloudCompile:

1. **ROM table timing** - Waveform lookup table indices must increment at MCC clock rate
2. **FSM transition timing** - State machine delays use MCC cycles, not ADC cycles
3. **Control register latching** - SYNC_SAFE gating operates on MCC clock edges
4. **HVS encoding timing** - Voltage state encoding updates at MCC rate

## DPD Project Note

> [!warning] DPD Clock Configuration Review Needed
> The DPD project's `py_tools/clk_utils.py` currently defaults to 125 MHz:
> ```python
> DEFAULT_CLK_FREQ_HZ = 125_000_000  # 125 MHz
> ```
>
> This is the **ADC clock**, not the **MCC fabric clock** (31.25 MHz for Moku:Go).
>
> **Recommendation:** Review whether DPD timing calculations should use MCC fabric clock (31.25 MHz) instead of ADC clock (125 MHz). A 4x timing error would cause:
> - Pulses 4x shorter than expected
> - Timeouts 4x faster than expected
> - FSM transitions 4x faster than expected

## Source Materials

### Official Liquid Instruments Examples (AUTHORITATIVE for MCC Clock)
- `moku_trim_examples/mcc/HDLCoder/hdlcoder_boxcar/python/BoxcarControlPanel.py` - **Platform period dictionary** (lines 42-47)
- `moku_trim_examples/mcc/Moderate/SweptPulse/MokuGo/mim_mgo_wg_mcc.py` - Moku:Go 31.25 MHz usage (line 49)
- `moku_trim_examples/mcc/Moderate/SweptPulse/MokuPro/mim_mpro_wg_mcc_la_osc.py` - Moku:Pro 312.5 MHz usage (line 61)

### Official Datasheets (DO NOT contain MCC clock info)
- `libs/moku-models-v4/datasheets/Datasheet-MokuGo.pdf` (v24-0815) - ADC/DAC only
- `libs/moku-models-v4/datasheets/Datasheet-MokuLab.pdf` (v24-0412) - ADC/DAC only
- `libs/moku-models-v4/datasheets/Datasheet-MokuPro.pdf` (v24-1015) - ADC/DAC only
- `libs/moku-models-v4/datasheets/Datasheet-MokuDelta.pdf` (v25-0820) - ADC/DAC only

### Platform Hardware Specifications
- `libs/moku-models-v4/docs/MOKU_PLATFORM_SPECIFICATIONS.md` - ADC/DAC specs from datasheets
- `libs/moku-models-v4/moku_models/platforms/` - Pydantic platform models (uses ADC clock)

### DPD Project
- `py_tools/clk_utils.py` - Current clock utility (uses 125 MHz)
- `rtl/DPD_main.vhd` - VHDL clock frequency comments

## Summary

| What | Use This Clock |
|------|----------------|
| `set_control()` timing values | **MCC Fabric Clock** (31.25 MHz for Go) |
| Oscilloscope sample rate | ADC/DAC Clock (125 MHz for Go) |
| Waveform generator frequency | ADC/DAC Clock (125 MHz for Go) |
| VHDL counter increments | **MCC Fabric Clock** |
| FSM state timing | **MCC Fabric Clock** |
| `get_data()` timestamps | ADC/DAC Clock |

**When in doubt: Query the platform at runtime and use the appropriate clock!**

---

## See Also

- [CloudCompile Documentation](../moku_md/instruments/cloudcompile.md) - Platform constants and register patterns
- [MIM Documentation](../moku_md/instruments/mim.md) - Platform reference table
- [moku-models-v4](../libs/moku-models-v4/) - Pydantic platform models
- [Hardware Debug Checklist](hardware-debug-checklist.md) - Debugging timing issues

---
**Last Updated**: 2025-11-29
**Status**: AUTHORITATIVE - Based on official Liquid Instruments examples and datasheet review
**Datasheet Review**: All 4 official datasheets (v24-v25) confirmed to NOT document MCC fabric clock
