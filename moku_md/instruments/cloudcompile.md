---
publish: "true"
type: reference
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_cloudcompile.py
title: CloudCompile
tags: [moku, api, instrument, fpga, custom]
---

# Overview

This module implements the CloudCompile instrument class, which provides support for custom user-defined instruments created through Moku's cloud compilation service. The instrument loads custom bitstream packages (tar/tar.gz files) and provides a generic interface for controlling custom hardware implementations.

> [!info] Key Dependencies
> - `tarfile` - For extracting bitstream packages
> - `tempfile` - For temporary extraction of bitstream files
> - `pathlib.Path` - For file path handling
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Support for multi-instrument mode
> - `moku.exceptions` - Custom exception types

# Classes

## CloudCompile

A custom instrument interface that loads and controls user-defined FPGA bitstreams created through Moku's cloud compilation service.

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, bitstream, connect_timeout, read_timeout, slot, multi_instrument, **kwargs)` - Initializes the instrument with a bitstream package
- `for_slot(slot, multi_instrument, **kwargs)` - Class method for multi-instrument mode configuration
- `save_settings(filename)` - Saves current instrument settings to a .mokuconf file
- `load_settings(filename)` - Loads settings from a .mokuconf file
- `set_control(idx, value, strict)` - Sets a single control register value
- `set_controls(controls, strict)` - Sets multiple control registers at once
- `get_control(idx, strict)` - Reads a single control register value
- `get_controls()` - Reads all control registers
- `set_interpolation(channel, enable, strict)` - Enables/disables interpolation on a channel
- `get_interpolation(channel)` - Gets interpolation state for a channel
- `sync(mask, strict)` - Synchronization operation with mask parameter
- `summary()` - Returns instrument summary information

```python
class CloudCompile(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 255
    OPERATION_GROUP = "cloudcompile"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False, bitstream=None,
                 connect_timeout=15, read_timeout=30, slot=None,
                 multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - The `bitstream` parameter is **required** and must be a path to a valid tar or tar.gz file
> - The bitstream package is extracted to a temporary directory during initialization
> - Inherits from both `MultiInstrumentSlottable` and `Moku` to support standalone and multi-instrument modes
> - Uses INSTRUMENT_ID 255, which is reserved for custom cloud-compiled instruments
> - The control interface provides generic register access (idx-based) since custom instruments can have arbitrary control schemes

> [!warning] Important
> - The bitstream file must exist at the specified path or initialization will fail with `FileNotFoundError`
> - If the bitstream package is invalid, a `MokuException` is raised with guidance to check the package
> - The `strict` parameter (default True) disables implicit type conversions when set
> - Settings files must have `.mokuconf` extension for compatibility with Moku tools

# Platform-Specific Constants

Control register values require platform-specific conversion. **Important:** There are TWO different clocks:

| Platform | ADC/DAC Clock | MCC Fabric Clock | ADC Bits | Notes |
|----------|---------------|------------------|----------|-------|
| Moku:Go | 125 MHz | **31.25 MHz** (÷4) | 12-bit | Entry-level |
| Moku:Lab | 500 MHz | **125 MHz** (÷4) | 12-bit | |
| Moku:Pro | 1250 MHz | **312.5 MHz** (÷4) | 10-bit* | High-performance |
| Moku:Delta | 5000 MHz | **1250 MHz** (÷4) | 14-bit* | Flagship |

\* Blended ADC architecture (secondary high-resolution ADC available)

> [!warning] MCC Fabric Clock vs ADC Clock
> **CloudCompile uses the MCC Fabric Clock**, not the ADC/DAC sample rate. Timing registers (durations, delays) must be calculated using the fabric clock period.
>
> For comprehensive platform specs including ADC/DAC details, see [moku-models-v4](../../libs/moku-models-v4/) pydantic library.

| Platform | MCC Period | ADC Resolution (approx) |
|----------|------------|------------------------|
| Moku:Go | 32 ns | 1/6550.4 V/bit |
| Moku:Lab | 8 ns | 2/30000 V/bit |
| Moku:Pro | 3.2 ns | 1/29925 V/bit |
| Moku:Delta | 0.8 ns | 1/36440 V/bit |

**Runtime Platform Discovery:**
```python
description = moku.describe()
hardware = description['hardware']  # e.g., 'Moku:Go', 'Moku:Pro'

# Clock period lookup (seconds)
period_dict = {
    'Moku:Go': 32e-9,
    'Moku:Lab': 8e-9,
    'Moku:Pro': 3.2e-9,
    'Moku:Delta': 3.2e-9
}

# ADC resolution lookup (volts per bit)
resolution_dict = {
    'Moku:Go': 1/6550.4,
    'Moku:Lab': 2/30000,
    'Moku:Pro': 1/29925,
    'Moku:Delta': 1/36440
}
```

> [!tip] Example Reference
> See [BoxcarControlPanel.py:42-68](../../moku_trim_examples/mcc/HDLCoder/hdlcoder_boxcar/python/BoxcarControlPanel.py) for complete platform discovery and unit conversion.

# Control Register Patterns

## Basic Register Write with Unit Conversion

```python
# Convert physical units to register values
trigger_level_volts = 0.5
trigger_delay_ns = 100

# Write to control registers
mcc.set_control(0, int(trigger_level_volts / resolution))  # Voltage → ADC bits
mcc.set_control(1, int(trigger_delay_ns * 1e-9 / period))  # Time → clock cycles
```

## Multi-Channel Register Offset Pattern

For multi-channel designs, use arithmetic offsets between channels:

```python
# Dual-channel boxcar example: Channel 1 uses CR0-4, Channel 2 uses CR5-9
CHANNEL_OFFSET = 5

# Configure both channels with same settings
for channel in [0, 1]:
    base = channel * CHANNEL_OFFSET
    mcc.set_control(base + 0, trigger_level)
    mcc.set_control(base + 1, trigger_delay)
    mcc.set_control(base + 2, gate_width)
```

> [!tip] Example Reference
> See [DualBoxcarControlPanel.py](../../moku_trim_examples/mcc/HDLCoder/hdlcoder_boxcar/python/DualBoxcarControlPanel.py) for a complete dual-channel implementation with 16 control registers.

## Mode Register as Output Multiplexer

A common pattern uses a single control register to select output modes:

```python
# CR15 acts as output mode selector
match selected_mode:
    case 'Align':
        mcc.set_control(15, 15)   # Alignment mode
    case 'Output_Ch0':
        mcc.set_control(15, 7)    # Output channel 0
    case 'Output_Both':
        mcc.set_control(15, 4)    # Dual output
```

## Register Readback (Debugging)

```python
# Read all control register values (returns dict)
print(mcc.get_controls())  # {'control0': val, 'control1': val, ...}

# Read single register
val = mcc.get_control(0)
```

> [!warning] Readback Limitations
> `get_control()` returns the last-written value from the Moku firmware cache, NOT a live readback from FPGA fabric. For status registers that change dynamically, this may not reflect current hardware state.

# Functions

This module contains only the CloudCompile class and no standalone functions.

# See Also

- `moku.Moku` - Base instrument class
- `moku.MultiInstrumentSlottable` - Multi-instrument support mixin
- `moku.exceptions.MokuException` - Exception handling
- `moku.exceptions.NoInstrumentBitstream` - Bitstream loading errors
- [Moku Clock Domains Guide](../../docs/moku-clock-domains.md) - **Critical: ADC vs MCC clock domains**
- [moku-models-v4](../../libs/moku-models-v4/) - Pydantic platform models
- [Moku Cloud Compile Documentation](https://apis.liquidinstruments.com/cloudcompile.html)
- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/instruments/cloudcompile)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/cloudcompile.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/instruments/cloudcompile.md)
