---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_fra.py
title: FrequencyResponseAnalyzer
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:21:35
---

# Overview

The Frequency Response Analyzer (FRA) instrument measures the transfer function of a system by generating a swept sine wave and measuring the system response on the input. This module provides the Python API for configuring and controlling the FRA instrument on Moku devices.

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Enables multi-instrument mode support

> [!note] API Reference
> For complete API documentation, see https://apis.liquidinstruments.com/reference/fra

# Classes

## FrequencyResponseAnalyzer

Main instrument class for the Frequency Response Analyzer. Inherits from both `MultiInstrumentSlottable` and `Moku` to support standalone and multi-instrument modes.

**Key Methods:**

### Initialization and Configuration
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Initialize and connect to the instrument
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in multi-instrument mode
- `save_settings(filename)` - Save instrument settings to `.mokuconf` file
- `load_settings(filename)` - Load previously saved `.mokuconf` settings
- `set_defaults()` - Reset instrument to default settings
- `summary()` - Get instrument status summary

### Frontend Configuration
- `set_frontend(channel, impedance, coupling, range, strict=True)` - Configure input channel settings
- `get_frontend(channel)` - Retrieve current frontend settings for a channel

### Sweep Configuration
- `set_sweep(start_frequency, stop_frequency, num_points, averaging_time, averaging_cycles, settling_time, settling_cycles, dynamic_amplitude, linear_scale, strict=True)` - Configure frequency sweep parameters
- `get_sweep()` - Retrieve current sweep configuration
- `start_sweep(single=False, strict=True)` - Start frequency sweep (single or continuous)
- `stop_sweep()` - Stop ongoing sweep
- `fra_measurement(channel, mode, start_frequency, stop_frequency, averaging_duration, averaging_cycles, output_amplitude, strict=True)` - Configure complete FRA measurement
- `measurement_mode(mode, strict=True)` - Set FRA measurement mode

### Output Configuration
- `set_output(channel, amplitude, offset, enable_amplitude, enable_offset, strict=True)` - Configure output channel amplitude and offset
- `get_output(channel)` - Retrieve output channel settings
- `disable_output(channel, strict=True)` - Disable output on specified channel
- `set_output_phase(channel, phase, strict=True)` - Set output phase for a channel
- `set_output_termination(channel, termination, strict=True)` - Set output termination (HiZ or 50Ohm)
- `get_output_termination(channel)` - Get output termination setting
- `set_harmonic_multiplier(multiplier, strict=True)` - Set harmonic multiplier (1-15) for frequency
- `get_harmonic_multiplier()` - Get current harmonic multiplier

### Data Acquisition
- `get_data(timeout=60, wait_reacquire=False, wait_complete=False)` - Retrieve measurement data

### Deprecated Methods
- `set_output_load(channel, load, strict=True)` - Deprecated in v3.1.1, use `set_output_termination` instead
- `get_output_load(channel)` - Deprecated in v3.1.1, use `get_output_termination` instead

```python
class FrequencyResponseAnalyzer(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 9
    OPERATION_GROUP = "fra"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - All configuration methods include a `strict` parameter (default: `True`) that disables implicit conversions and coercions
> - Sweep points are automatically rounded to the nearest power of 2
> - The instrument can operate in standalone mode (via IP or serial) or as part of a multi-instrument setup (via slot)
> - Default data read timeout is 60 seconds but can be extended via session.read_timeout property

> [!warning] Important
> - When using `get_data()`, ensure sufficient timeout is set for long sweeps. Default is 60 seconds but can be increased via `instrument.session.read_timeout`
> - Configuration files must use `.mokuconf` extension for compatibility with other Moku tools
> - Deprecated methods `set_output_load` and `get_output_load` will be removed in future versions - use termination methods instead

# Configuration Parameters

## Frontend Settings

**Impedance Options:**
- `1MOhm` - High impedance input
- `50Ohm` - 50 Ohm terminated input

**Coupling Options:**
- `AC` - AC coupling
- `DC` - DC coupling

**Range Options:**
- `100mVpp`, `400mVpp`, `1Vpp`, `2Vpp`, `4Vpp`, `10Vpp`, `40Vpp`, `50Vpp`

## Measurement Modes

- `In` - Input only measurement
- `InOut` - Input-output transfer function (default)
- `InIn1` - Dual input measurement

## Sweep Parameters

- **Frequency Range:** 1e-3 Hz to 20 MHz
- **Averaging Time:** 1e-6 to 10 seconds per point
- **Averaging Cycles:** 1 to 1,048,576 cycles per point
- **Settling Time:** 1e-6 to 10 seconds per point
- **Settling Cycles:** 1 to 1,048,576 cycles per point
- **Scale:** Logarithmic (default) or Linear
- **Harmonic Multiplier:** 1 to 15

## Output Parameters

- **Amplitude Range:** 2e-3 Vpp to 10 Vpp (for FRA measurements) or -5V to 5V (general)
- **Offset Range:** -5V to 5V
- **Termination:** `HiZ` (High impedance) or `50Ohm`

# Usage Example

```python
from moku.instruments import FrequencyResponseAnalyzer

# Connect to the instrument
fra = FrequencyResponseAnalyzer('192.168.1.100', force_connect=True)

# Configure frontend
fra.set_frontend(channel=1, impedance='1MOhm', coupling='DC', range='1Vpp')

# Set up sweep
fra.set_sweep(
    start_frequency=100,      # 100 Hz
    stop_frequency=1e6,       # 1 MHz
    num_points=512,
    averaging_time=1e-3,
    averaging_cycles=3,
    linear_scale=False        # Logarithmic sweep
)

# Configure output
fra.set_output(channel=1, amplitude=1.0, offset=0)

# Start sweep and get data
fra.start_sweep(single=True)
data = fra.get_data(timeout=120, wait_complete=True)
```

# See Also

- Moku base class for core instrument functionality
- MultiInstrumentSlottable for multi-instrument mode capabilities
- Official API documentation: https://apis.liquidinstruments.com/reference/fra
