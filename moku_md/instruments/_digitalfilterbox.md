---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_digitalfilterbox.py
title: DigitalFilterBox
---

# Overview

The Digital Filter Box instrument provides interactive design and generation of infinite impulse response (IIR) digital filters with configurable sampling rates. It supports multiple filter shapes (lowpass, highpass, bandpass, bandstop) and filter types (Butterworth, Chebyshev, Elliptic, and more).

> [!info] Key Dependencies
> - `moku.Moku` - Base instrument class
> - `moku.MultiInstrumentSlottable` - Multi-instrument mode support
> - `moku.instruments._stream.StreamInstrument` - Data streaming capabilities
> - `moku.exceptions.StreamException` - Stream error handling

# Classes

## DigitalFilterBox

A multi-channel digital filter instrument that can design and apply various types of IIR filters to input signals in real-time.

**Key Methods:**
- `__init__(ip=None, serial=None, force_connect=False, ...)` - Initialize connection to the instrument
- `for_slot(slot, multi_instrument)` - Configure instrument for multi-instrument mode
- `set_filter(channel, sample_rate, shape, type, ...)` - Configure filter parameters
- `set_custom_filter(channel, sample_rate, scaling, coefficients)` - Apply custom filter coefficients
- `set_frontend(channel, coupling, impedance, attenuation, gain)` - Configure input frontend
- `set_control_matrix(channel, input_gain1, input_gain2)` - Configure input mixing matrix
- `enable_output(channel, signal, output, gain_range)` - Enable and configure outputs
- `set_monitor(monitor_channel, source)` - Configure monitor outputs
- `set_trigger(type, level, mode, edge, ...)` - Configure oscilloscope-style triggering
- `get_data(timeout, wait_reacquire, wait_complete, measurements)` - Retrieve oscilloscope data
- `start_streaming(duration, mode, rate, ...)` - Start data streaming
- `stop_streaming()` - Stop data streaming
- `get_chunk()` - Get next chunk from streaming session
- `start_logging(duration, delay, ...)` - Start data logging to device
- `stop_logging()` - Stop data logging
- `save_settings(filename)` - Save configuration to .mokuconf file
- `load_settings(filename)` - Load configuration from .mokuconf file

```python
class DigitalFilterBox(MultiInstrumentSlottable, Moku, StreamInstrument):
    INSTRUMENT_ID = 6
    OPERATION_GROUP = "digitalfilterbox"

    def __init__(self, ip=None, serial=None, force_connect=False, ...):
        ...
```

> [!note] Implementation Notes
> - Supports up to 4 independent filter channels
> - Sample rates range from 61.04kHz to 39.06MHz
> - Filter order is configurable (default: 8)
> - Custom filters use coefficient arrays with 6-coefficient stages
> - Each coefficient must be in range [-4.0, 4.0]
> - Inherits streaming capabilities from StreamInstrument

## Configuration Methods

### Frontend Configuration

**`set_frontend(channel, coupling, impedance, attenuation, gain)`**

Configures the analog input frontend for a specific channel.

**Parameters:**
- `channel` (int) - Target channel (1-4)
- `coupling` (str) - Input coupling: 'AC' or 'DC'
- `impedance` (str) - Input impedance: '1MOhm' or '50Ohm'
- `attenuation` (str, optional) - Input attenuation: '-20dB', '0dB', '14dB', '20dB', '32dB', '40dB'
- `gain` (str, optional) - Input gain: '20dB', '0dB', '-14dB', '-20dB', '-32dB', '-40dB'
- `strict` (bool) - Disable implicit conversions (default: True)

**`get_frontend(channel)`** - Returns current frontend configuration

### Signal Path Configuration

**`set_control_matrix(channel, input_gain1, input_gain2)`**

Configures the input mixing matrix for a channel.

**Parameters:**
- `channel` (int) - Target channel
- `input_gain1` (float) - ADC input gain for Channel 1 [-20, 20] dB
- `input_gain2` (float) - ADC input gain for Channel 2 [-20, 20] dB

**`set_input_offset(channel, offset)`** / **`get_input_offset(channel)`**

Set or get input DC offset [-5V, 5V].

**`set_output_offset(channel, offset)`** / **`get_output_offset(channel)`**

Set or get output DC offset [-5V, 5V].

**`set_input_gain(channel, gain)`** / **`get_input_gain(channel)`**

Set or get input gain [-40dB, 40dB].

**`set_output_gain(channel, gain)`** / **`get_output_gain(channel)`**

Set or get output gain [-40dB, 40dB].

### Filter Design

**`set_filter(channel, sample_rate, shape, type, low_corner, high_corner, pass_band_ripple, stop_band_attenuation, order)`**

Design and apply a standard IIR filter.

**Parameters:**
- `channel` (int) - Target channel (1-4)
- `sample_rate` (str) - Filter sample rate: '3.906MHz', '488.3kHz', '61.04kHz', '39.06MHz', '4.883MHz', '305.2kHz', '15.625MHz', '1.9531MHz', '122.07kHz'
- `shape` (str) - Filter shape: 'Lowpass', 'Highpass', 'Bandpass', 'Bandstop' (default: 'Lowpass')
- `type` (str) - Filter type: 'Butterworth', 'ChebyshevI', 'ChebyshevII', 'Elliptic', 'Cascaded', 'Bessel', 'Gaussian', 'Legendre' (default: 'Butterworth')
- `low_corner` (float, optional) - Low corner frequency in Hz
- `high_corner` (float, optional) - High corner frequency in Hz
- `pass_band_ripple` (float, optional) - Passband ripple in dB (for Chebyshev/Elliptic)
- `stop_band_attenuation` (float, optional) - Stopband attenuation in dB (for Chebyshev/Elliptic)
- `order` (int) - Filter order (default: 8)

**`set_custom_filter(channel, sample_rate, scaling, coefficients)`**

Apply a custom filter defined by coefficient stages.

**Parameters:**
- `channel` (int) - Target channel
- `sample_rate` (str) - Same options as set_filter
- `scaling` (float) - Output scaling factor (default: 1)
- `coefficients` (list) - List of filter stages, each with 6 coefficients in range [-4.0, 4.0]

> [!warning] Important
> Custom filter coefficients must be carefully designed to ensure filter stability. Each coefficient must be in the range [-4.0, 4.0].

### Output Configuration

**`enable_output(channel, signal, output, gain_range)`**

Enable and configure channel outputs.

**Parameters:**
- `channel` (int) - Target channel
- `signal` (bool) - Enable output signal (default: True)
- `output` (bool) - Enable physical output (default: True)
- `gain_range` (str) - Output gain range (default: '0dB')

**`set_monitor(monitor_channel, source)`**

Configure what signal appears on monitor outputs.

**Parameters:**
- `monitor_channel` (int) - Monitor channel number
- `source` (str) - Signal source: 'None', 'Input1', 'Filter1', 'Output1', 'Input2', 'Filter2', 'Output2', 'Input3', 'Filter3', 'Output3', 'Input4', 'Filter4', 'Output4'

## Data Acquisition Methods

### Triggering

**`set_trigger(type, level, mode, edge, polarity, width, ...)`**

Configure oscilloscope-style triggering for data acquisition.

**Parameters:**
- `type` (str) - Trigger type: 'Edge' or 'Pulse' (default: 'Edge')
- `level` (float) - Trigger level in volts [-5V, 5V] (default: 0)
- `mode` (str) - Trigger mode: 'Auto' or 'Normal' (default: 'Auto')
- `edge` (str) - Edge selection: 'Rising', 'Falling', 'Both' (default: 'Rising')
- `polarity` (str) - Pulse polarity: 'Positive' or 'Negative' (Pulse mode only)
- `width` (float) - Pulse width in seconds [26e-3, 10] (default: 0.0001)
- `width_condition` (str) - Width condition: 'GreaterThan' or 'LessThan'
- `nth_event` (int) - Number of trigger events to wait [0, 65535] (default: 1)
- `holdoff` (float) - Holdoff time in seconds [1e-9, 10] (default: 0)
- `hysteresis` (float) - Trigger hysteresis (default: 1e-3)
- `auto_sensitivity` (bool, optional) - Auto/manual hysteresis
- `noise_reject` (bool) - Enable noise rejection (default: False)
- `hf_reject` (bool) - Enable high-frequency rejection (default: False)
- `source` (str) - Trigger source: 'ProbeA', 'ProbeB', 'ProbeC', 'ProbeD', 'External' (default: 'ProbeA')

**`set_hysteresis(hysteresis_mode, value)`** - Deprecated in 3.1.1, use `hysteresis` parameter of `set_trigger` instead.

### Timebase

**`set_timebase(t1, t2)`**

Configure the time window for data acquisition.

**Parameters:**
- `t1` (float) - Time from trigger to left of screen (can be negative)
- `t2` (float) - Time from trigger to right of screen (must be positive)

**`get_timebase()`** - Returns current timebase configuration

**`enable_rollmode(roll)`**

Enable or disable roll mode for continuous data display.

**Parameters:**
- `roll` (bool) - Enable roll mode (default: True)

### Acquisition Modes

**`set_acquisition_mode(mode)`**

Set the data acquisition mode.

**Parameters:**
- `mode` (str) - Acquisition mode: 'Normal', 'Precision', 'DeepMemory', 'PeakDetect' (default: 'Normal')

**`get_acquisition_mode()`** - Returns current acquisition mode

**`get_samplerate()`** - Returns current sample rate

### Data Retrieval

**`get_data(timeout, wait_reacquire, wait_complete, measurements)`**

Retrieve oscilloscope data frame.

**Parameters:**
- `timeout` (int) - Timeout in seconds (default: 60)
- `wait_reacquire` (bool) - Wait for new data frame (default: False)
- `wait_complete` (bool) - Wait for complete frame (default: False)
- `measurements` (bool) - Include channel measurements (default: False)

**Returns:** Dictionary containing time series data and optional measurements

> [!info] Timeout Configuration
> Default read timeout is 10 seconds. Increase via `instrument.session.read_timeout = 100` for longer operations.

**`save_high_res_buffer(comments, timeout)`**

Save high-resolution buffer data.

**Parameters:**
- `comments` (str) - Optional comments (default: "")
- `timeout` (int) - Timeout in seconds (default: 60)

## Data Streaming

**`start_streaming(duration, mode, rate, trigger_source, trigger_level)`**

Start continuous data streaming.

**Parameters:**
- `duration` (int, optional) - Duration in seconds
- `mode` (str) - Acquisition mode: 'Normal', 'Precision', 'DeepMemory', 'PeakDetect' (default: 'Normal')
- `rate` (float, optional) - Acquisition rate
- `trigger_source` (str, optional) - Trigger source: 'ProbeA', 'ProbeB', 'ProbeC', 'ProbeD', 'External'
- `trigger_level` (float, optional) - Trigger level [-5V, 5V]

**Returns:** Dictionary with stream_id

**`stop_streaming()`**

Stop the active streaming session.

**`get_chunk()`**

Retrieve the next raw data chunk from the active stream.

**Returns:** Raw binary data chunk

**`get_stream_status()`**

Get the current status of the streaming session.

## Data Logging

**`start_logging(duration, delay, file_name_prefix, comments, trigger_source, trigger_level, mode, rate)`**

Start logging data to device storage.

**Parameters:**
- `duration` (int) - Logging duration in seconds (default: 60)
- `delay` (int) - Start delay in seconds (default: 0)
- `file_name_prefix` (str) - Optional filename prefix (default: "")
- `comments` (str) - Optional comments (default: "")
- `trigger_source` (str, optional) - Trigger source
- `trigger_level` (float, optional) - Trigger level [-5V, 5V]
- `mode` (str) - Acquisition mode (default: 'Normal')
- `rate` (float, optional) - Acquisition rate

**`stop_logging()`**

Stop the active logging session.

**`logging_progress()`**

Get the current logging progress status.

## Configuration Management

**`save_settings(filename)`**

Save current instrument settings to a .mokuconf file.

**Parameters:**
- `filename` (str or file-like) - Path to save configuration

**`load_settings(filename)`**

Load instrument settings from a .mokuconf file.

**Parameters:**
- `filename` (str or file-like) - Path to configuration file

**`set_defaults()`**

Reset instrument to default settings.

**`summary()`**

Get a summary of current instrument configuration.

# See Also

- [Moku API Reference](https://apis.liquidinstruments.com/reference/dfb)
- Related instruments: `_oscilloscope.py`, `_stream.py`
- Base classes: `Moku`, `MultiInstrumentSlottable`, `StreamInstrument`
