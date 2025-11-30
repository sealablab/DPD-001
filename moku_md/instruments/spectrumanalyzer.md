---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_spectrumanalyzer.py
title: SpectrumAnalyzer
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:22:21
---

# Overview

The SpectrumAnalyzer module provides a Python interface for controlling Liquid Instruments' Spectrum Analyzer instrument. This instrument performs frequency-domain analysis of input signals with features including switchable window functions, configurable resolution bandwidth (RBW), and multiple averaging modes.

> [!info] Key Dependencies
> - `moku.Moku` - Base instrument class providing core functionality
> - `moku.MultiInstrumentSlottable` - Mixin for multi-instrument support allowing operation in slotted configurations

# Classes

## SpectrumAnalyzer

Spectrum Analyzer instrument object that provides frequency-domain analysis capabilities for input signals.

**Inheritance:** Inherits from `MultiInstrumentSlottable` and `Moku`

**Key Methods:**
- `__init__(ip=None, serial=None, force_connect=False, ...)` - Initialize and connect to a Spectrum Analyzer instrument
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in multi-instrument mode
- `save_settings(filename)` - Save current instrument configuration to `.mokuconf` file
- `load_settings(filename)` - Load instrument configuration from `.mokuconf` file
- `set_frontend(channel, impedance, coupling, range, strict=True)` - Configure input channel frontend settings
- `get_frontend(channel)` - Retrieve current frontend settings for a channel
- `sa_output(channel, amplitude, frequency, strict=True)` - Configure output signal generation
- `set_rbw(mode, rbw_value=5000, strict=True)` - Set resolution bandwidth mode and value
- `get_rbw()` - Get current resolution bandwidth settings
- `set_span(frequency1, frequency2, strict=True)` - Set frequency span for analysis
- `get_span()` - Get current frequency span
- `sa_measurement(channel, frequency1, frequency2, rbw='Auto', rbw_value=5000, window='BlackmanHarris', strict=True)` - Configure comprehensive spectrum analysis measurement
- `set_window(window, strict=True)` - Set window function for FFT analysis
- `get_window()` - Get current window function
- `disable_output(channel, strict=True)` - Disable signal output on a channel
- `set_output_termination(channel, termination, strict=True)` - Configure output termination impedance
- `get_output_termination(channel)` - Get current output termination setting
- `set_averaging(target_duration=0.1, strict=True)` - Configure frame averaging duration
- `enable_xcorr(channel_a, channel_b, strict=True)` - Enable cross-correlation between two channels
- `disable_xcorr()` - Disable cross-correlation
- `get_data(timeout=60, wait_reacquire=False, wait_complete=True, units='dBm', psdUnits=False, measurements=False, strict=True)` - Retrieve spectrum data from the instrument
- `summary()` - Get instrument status summary
- `set_defaults()` - Reset instrument to default settings

```python
class SpectrumAnalyzer(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 2
    OPERATION_GROUP = "spectrumanalyzer"

    def __init__(
        self,
        ip=None,
        serial=None,
        force_connect=False,
        ignore_busy=False,
        persist_state=False,
        connect_timeout=15,
        read_timeout=30,
        slot=None,
        multi_instrument=None,
        **kwargs,
    ):
        ...
```

> [!note] Implementation Notes
> - The `strict` parameter (default `True`) disables implicit conversions and coercions when set
> - All session operations use the pattern `f"slot{self.slot}/{self.operation_group}"` for API routing
> - The instrument can operate standalone or in multi-instrument slotted configurations

## Key Configuration Parameters

### Frontend Settings (`set_frontend`)

**Parameters:**
- `channel` (integer) - Target input channel
- `impedance` (string) - Input impedance: `'1MOhm'` or `'50Ohm'`
- `coupling` (string) - Input coupling: `'AC'` or `'DC'`
- `range` (string) - Input range: `'100mVpp'`, `'400mVpp'`, `'1Vpp'`, `'2Vpp'`, `'4Vpp'`, `'10Vpp'`, `'40Vpp'`, `'50Vpp'`

### Resolution Bandwidth (`set_rbw`)

**Parameters:**
- `mode` (string) - RBW mode: `'Auto'`, `'Manual'`, or `'Minimum'`
- `rbw_value` (number) - RBW value in Hz (only used in Manual mode, default: 5000)

### Window Functions (`set_window`)

**Supported Windows:**
`'BlackmanHarris'` (default), `'FlatTop'`, `'Rectangular'`, `'Bartlett'`, `'Hamming'`, `'Hann'`, `'Nuttall'`, `'Gaussian'`, `'Kaiser'`

### Frequency Span (`set_span`)

**Parameters:**
- `frequency1` (number) - Left-most frequency [0Hz to 30MHz]
- `frequency2` (number) - Right-most frequency [0Hz to 30MHz]

### Output Configuration (`sa_output`)

**Parameters:**
- `channel` (integer) - Target output channel
- `amplitude` (number) - Waveform peak-to-peak amplitude
- `frequency` (number) - Signal frequency [0Hz to 30MHz]

### Cross-Correlation (`enable_xcorr`)

**Parameters:**
- `channel_a` (string) - First channel: `'Input1'`, `'Input2'`, `'Input3'`, `'Input4'`, `'InputA'`, `'InputB'`, `'InputC'`, `'InputD'`
- `channel_b` (string) - Second channel (same options as channel_a)

> [!note] Cross-Correlation
> Cross-correlation enables analysis of phase and amplitude relationships between two input channels

### Data Acquisition (`get_data`)

**Parameters:**
- `timeout` (number) - Wait timeout in seconds (default: 60)
- `wait_reacquire` (boolean) - Wait until new dataframe is reacquired
- `wait_complete` (boolean) - Wait until entire frame is available
- `units` (string) - Data units: `'dBm'` (default), `'Vrms'`, `'Vpp'`, `'dBV'`
- `psdUnits` (boolean) - Use power spectral density units
- `measurements` (boolean) - Include available measurements for each channel

**Returns:** Spectrum data frame with frequency and amplitude information

> [!warning] Important
> The default read timeout is controlled by `session.read_timeout` (default 30s). For longer acquisitions, increase this value before calling `get_data()`. Example: `instrument.session.read_timeout = 100`

### Comprehensive Measurement (`sa_measurement`)

Configures a complete spectrum analysis measurement with all key parameters in a single call.

**Parameters:**
- `channel` (integer) - Target input channel
- `frequency1` (number) - Start frequency [0Hz to 30MHz]
- `frequency2` (number) - Stop frequency [0Hz to 30MHz]
- `rbw` (string) - Resolution bandwidth mode: `'Auto'` (default), `'Manual'`, `'Minimum'`
- `rbw_value` (number) - RBW value for Manual mode (default: 5000)
- `window` (string) - Window function (default: `'BlackmanHarris'`)

> [!info] Configuration Files
> Settings can be saved to `.mokuconf` files using `save_settings()` and loaded with `load_settings()`. These files are compatible with Liquid Instruments' desktop application.

# See Also

- [Liquid Instruments API Reference](https://apis.liquidinstruments.com/reference/specan)
- Related instruments: Oscilloscope, Waveform Generator, Data Logger
- Base classes: `moku.Moku`, `moku.MultiInstrumentSlottable`
