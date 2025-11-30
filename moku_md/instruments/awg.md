---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_awg.py
title: ArbitraryWaveformGenerator
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:21:13
---

# Overview

The Arbitrary Waveform Generator (AWG) instrument module provides control over Moku's AWG functionality. This instrument takes a time-series of voltage values and generates the corresponding waveform at the DACs (Digital-to-Analog Converters) at a configurable rate.

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Mixin for multi-instrument slot support
>
> **API Reference:** https://apis.liquidinstruments.com/reference/awg

# Classes

## ArbitraryWaveformGenerator

Main instrument class for controlling the Arbitrary Waveform Generator. Inherits from both `MultiInstrumentSlottable` and `Moku` to support both standalone and multi-instrument configurations.

**Class Attributes:**
- `INSTRUMENT_ID = 15` - Unique instrument identifier
- `OPERATION_GROUP = "awg"` - API operation group name

**Key Methods:**

- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument, **kwargs)` - Constructor for connecting to AWG instrument
- `for_slot(slot, multi_instrument)` - Class method to configure instrument at given slot in multi-instrument mode
- `summary()` - Get instrument summary information
- `save_settings(filename)` - Save instrument settings to a `.mokuconf` file
- `load_settings(filename)` - Load previously saved `.mokuconf` settings file
- `set_defaults()` - Reset instrument to default settings
- `set_frontend(channel, impedance, coupling, range, strict)` - Configure input frontend parameters
- `get_frontend(channel)` - Get current frontend configuration
- `enable_output(channel, enable, strict)` - Enable or disable output channel
- `sync_phase()` - Synchronize phase across channels
- `generate_waveform(channel, sample_rate, lut_data, frequency, amplitude, phase, offset, interpolation, strict)` - Generate arbitrary waveform from lookup table data
- `set_output_termination(channel, termination, strict)` - Set output termination impedance
- `get_output_termination(channel)` - Get current output termination setting
- `disable_modulation(channel, strict)` - Disable modulation on specified channel
- `pulse_modulate(channel, dead_cycles, dead_voltage, strict)` - Configure pulse modulation
- `burst_modulate(channel, trigger_source, trigger_mode, burst_cycles, trigger_level, input_range, strict)` - Configure burst modulation with triggering
- `manual_trigger()` - Manually trigger all channels configured for manual triggering

```python
class ArbitraryWaveformGenerator(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 15
    OPERATION_GROUP = "awg"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Connection Options
> The instrument can be connected via IP address or serial number. It supports both standalone and multi-instrument configurations through the `slot` and `multi_instrument` parameters.

### Configuration Methods

**Frontend Configuration:**
- Controls input impedance (1MOhm/50Ohm), coupling (AC/DC), and range (100mVpp to 50Vpp)
- Use `set_frontend()` and `get_frontend()` for input channel configuration

**Output Configuration:**
- Controls output enable/disable state per channel
- Output termination can be set to HiZ or 50Ohm
- Use `enable_output()`, `set_output_termination()`, and `get_output_termination()`

### Waveform Generation

**`generate_waveform` Method:**

```python
def generate_waveform(
    channel, sample_rate, lut_data=None, frequency=None,
    amplitude=None, phase=0, offset=0,
    interpolation=False, strict=True
)
```

**Parameters:**
- `channel` (integer) - Target output channel
- `sample_rate` (string) - Output sample rate from '15.625Ms' to '1.25Gs' or 'Auto'
- `lut_data` (list) - Lookup table coefficients in range [-1.0, 1.0]
- `frequency` (number) - Waveform frequency [1e-3Hz, 10e6Hz]
- `amplitude` (number) - Peak-to-peak amplitude [4e-3V, 10V]
- `phase` (number) - Phase offset [0Deg, 360Deg]
- `offset` (number) - DC offset [-5V, 5V]
- `interpolation` (boolean) - Enable linear interpolation of LUT entries
- `strict` (boolean) - Disable implicit conversions and coercions

**Returns:** API response from session

> [!info] Sample Rate Selection
> If sample rate is set to 'Auto', the fastest output rate for the given data length will be automatically chosen. This is the recommended setting in most circumstances.

### Modulation Methods

**Pulse Modulation:**
```python
def pulse_modulate(channel, dead_cycles=10, dead_voltage=0, strict=True)
```
Configures pulse modulation with dead time between cycles.

**Burst Modulation:**
```python
def burst_modulate(
    channel, trigger_source, trigger_mode,
    burst_cycles=1, trigger_level=0,
    input_range=None, strict=True
)
```
Configures burst modulation with various trigger sources (Input1-4, InputA-D, External) and modes (Start, NCycle).

**Manual Triggering:**
```python
def manual_trigger()
```
Triggers all channels configured for manual triggering.

> [!warning] Deprecated Methods
> - `set_output_load()` - Deprecated since v3.1.1, use `set_output_termination()` instead
> - `get_output_load()` - Deprecated since v3.1.1, use `get_output_termination()` instead

### Settings Management

**Save/Load Configuration:**
- `save_settings(filename)` - Saves current configuration to `.mokuconf` file
- `load_settings(filename)` - Loads configuration from `.mokuconf` file

> [!note] File Compatibility
> The `.mokuconf` files are compatible with other Moku tools including the desktop application.

# Functions

No module-level functions are defined in this file. All functionality is encapsulated within the `ArbitraryWaveformGenerator` class.

# See Also

- Base class: `moku.Moku`
- Multi-instrument support: `moku.MultiInstrumentSlottable`
- Official API documentation: https://apis.liquidinstruments.com/reference/awg
