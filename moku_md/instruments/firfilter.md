---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_firfilter.py
title: FIRFilterBox
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:21:28
---

# Overview

The FIRFilterBox module provides an instrument object for designing and implementing finite impulse response (FIR) filters on Moku hardware. It supports lowpass, highpass, bandpass, and bandstop filter configurations with fine-tuning capabilities in both frequency and time domains. The instrument provides four frequency response shapes, five common impulse responses, and up to eight window functions.

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Multi-instrument mode support
> - `moku.instruments._stream.StreamInstrument` - Streaming data acquisition capabilities
> - `moku.exceptions.StreamException` - Stream error handling
> - `json` - JSON data parsing for streaming

# Classes

## FIRFilterBox

A multi-slottable instrument class for FIR filter design and implementation on Moku devices.

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Constructor for initializing the FIR filter instrument
- `for_slot(slot, multi_instrument)` - Class method to configure instrument for a specific slot in multi-instrument mode
- `save_settings(filename)` - Save current instrument configuration to .mokuconf file
- `load_settings(filename)` - Load previously saved .mokuconf settings
- `set_by_frequency(channel, sample_rate, coefficient_count, shape, low_corner, high_corner, window, window_width, kaiser_order)` - Configure filter by frequency domain parameters
- `set_by_time(channel, sample_rate, coefficient_count, response, response_width, window, window_width, kaiser_order)` - Configure filter by time domain impulse response
- `set_custom_kernel_coefficients(channel, sample_rate, coefficients)` - Set custom FIR filter coefficients
- `set_frontend(channel, coupling, impedance, attenuation, gain)` - Configure input channel frontend
- `set_control_matrix(channel, input_gain1, input_gain2)` - Set ADC input gain matrix
- `enable_output(channel, signal, output, gain_range)` - Enable/disable output channels
- `set_trigger(type, level, mode, edge, polarity, width, width_condition, nth_event, holdoff, hysteresis, auto_sensitivity, noise_reject, hf_reject, source)` - Configure trigger settings
- `get_data(timeout, wait_reacquire, wait_complete, measurements)` - Retrieve data frames from instrument
- `start_streaming(duration, mode, rate, trigger_source, trigger_level)` - Start streaming data acquisition
- `stop_streaming()` - Stop streaming data acquisition
- `get_chunk()` - Get next raw chunk from streaming session

```python
class FIRFilterBox(MultiInstrumentSlottable, Moku, StreamInstrument):
    """
    FIRFilterBox instrument object.

    The FIRFilterBox instrument object allows design and
    implemention of lowpass, highpass, bandpass, and
    bandstop finite impulse response (FIR) filters. It
    allows fine tuning of filter's response in the
    frequency and time domains. It provides four frequency
    response shapes, five common impulse responses,
    and up to eight window functions

    Read more at https://apis.liquidinstruments.com/reference/fir
    """

    INSTRUMENT_ID = 10
    OPERATION_GROUP = "firfilter"
```

> [!note] Implementation Notes
> - Inherits from MultiInstrumentSlottable for multi-instrument rack support
> - Can be used standalone or as part of a multi-instrument configuration
> - All setter methods include a `strict` parameter to disable implicit conversions
> - Session-based communication with Moku hardware via HTTP POST/GET requests
> - Supports both trigger-based and streaming data acquisition modes

> [!warning] Filter Configuration
> - Sample rates are constrained to predefined values (e.g., '15.63MHz', '7.813MHz', etc.)
> - Filter shapes include: 'Lowpass', 'Highpass', 'Bandpass', 'Bandstop'
> - Window functions include: 'None', 'Bartlett', 'Hann', 'Hamming', 'Blackman', 'Nuttall', 'Tukey', 'Kaiser'
> - Impulse responses include: 'Rectangular', 'Sinc', 'Triangular', 'Gaussian'
> - Custom coefficients must be normalized to range [-1.0, 1.0]

> [!info] Frequency Domain Configuration
> The `set_by_frequency()` method allows configuring filters by specifying:
> - Filter shape (lowpass, highpass, bandpass, bandstop)
> - Corner frequencies (low_corner, high_corner)
> - Coefficient count (default 201)
> - Window function and parameters

> [!info] Time Domain Configuration
> The `set_by_time()` method allows configuring filters by specifying:
> - Impulse response shape (Sinc, Rectangular, Triangular, Gaussian)
> - Response width parameter
> - Window function and parameters

> [!info] Input/Output Configuration
> - Input coupling: 'AC' or 'DC'
> - Input impedance: '1MOhm' or '50Ohm'
> - Attenuation/Gain ranges: '-40dB' to '40dB'
> - Input/Output offset range: -5V to 5V
> - Input/Output gain range: -5dB to 5dB

> [!info] Trigger Configuration
> - Trigger types: 'Edge', 'Pulse'
> - Trigger modes: 'Auto', 'Normal'
> - Trigger sources: 'ProbeA', 'ProbeB', 'ProbeC', 'ProbeD', 'External'
> - Level range: -5V to 5V
> - Supports noise rejection and high-frequency filtering
> - Configurable hysteresis for noise immunity

> [!info] Data Acquisition Modes
> - **Normal**: Standard acquisition mode
> - **Precision**: Higher precision sampling
> - **DeepMemory**: Extended memory depth
> - **PeakDetect**: Peak detection mode
> - Roll mode available for continuous viewing
> - Supports both triggered and streaming acquisition

> [!warning] Streaming Usage
> - Must call `start_streaming()` before reading chunks
> - Use `get_chunk()` to retrieve raw streaming data
> - Always call `stop_streaming()` when finished
> - Stream exceptions raised on errors
> - Stream ID automatically managed by the class

> [!info] Logging Capability
> - `start_logging()` - Begin data logging to file
> - `logging_progress()` - Check logging status
> - `stop_logging()` - Stop active logging session
> - Supports configurable duration, delay, and trigger parameters
> - Optional file name prefix and comments

# See Also

- [Moku API Documentation](https://apis.liquidinstruments.com/reference/fir)
- Related instruments: `_oscilloscope.py`, `_stream.py`
- Base classes: `Moku`, `MultiInstrumentSlottable`, `StreamInstrument`
