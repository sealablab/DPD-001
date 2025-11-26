---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_pidcontroller.py
title: PIDController
---

# Overview

The PIDController module provides a dual-channel PID (Proportional-Integral-Derivative) controller instrument for voltage-input, voltage-output signals. It supports both independent and MIMO (Multiple-Input Multiple-Output) control configurations with features including double-integrator capability, configurable integrator saturation (anti-windup), and differentiator saturation.

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku device class
> - `moku.MultiInstrumentSlottable` - Enables multi-instrument mode support
> - `moku.instruments._stream.StreamInstrument` - Provides streaming capabilities
> - `moku.exceptions.StreamException` - Exception handling for streaming operations
> - `json` - For parsing streaming data responses

# Classes

## PIDController

Dual-channel PID controller instrument with independent or MIMO control modes. Inherits from `MultiInstrumentSlottable`, `Moku`, and `StreamInstrument` to provide comprehensive control and data acquisition capabilities.

**Key Configuration Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Initialize PID controller connection
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in multi-instrument mode
- `set_frontend(channel, impedance, coupling, attenuation, gain)` - Configure input frontend settings
- `set_control_matrix(channel, input_gain1, input_gain2)` - Configure input gain matrix for MIMO control
- `set_by_frequency(channel, prop_gain, int_crossover, diff_crossover, double_int_crossover, int_saturation, diff_saturation)` - Configure PID parameters by frequency
- `set_by_gain(channel, overall_gain, prop_gain, int_gain, diff_gain, int_corner, diff_corner)` - Configure PID parameters by gain values
- `set_by_gain_and_section(channel, section, overall_gain, prop_gain, int_gain, diff_gain, int_corner, diff_corner)` - Configure PID parameters by section

**Output Control Methods:**
- `enable_output(channel, signal, output)` - Enable/disable output signal and output
- `set_output_gain(channel, gain)` - Set output gain (default "0dB")
- `get_output_gain(channel)` - Retrieve current output gain
- `set_output_offset(channel, offset)` - Set output DC offset (-5V to 5V)
- `get_output_offset(channel)` - Retrieve current output offset
- `set_output_limit(channel, enable, low_limit, high_limit)` - Configure voltage limiter
- `get_output_limit(channel)` - Retrieve voltage limit settings

**Input Control Methods:**
- `enable_input(channel, enable)` - Enable/disable input signal
- `set_input_offset(channel, offset)` - Set input DC offset (-5V to 5V)
- `get_input_offset(channel)` - Retrieve current input offset

**Monitoring Methods:**
- `set_monitor(monitor_channel, source)` - Configure monitoring channel source (Input1-4, Control1-4, Output1-4)
- `get_frontend(channel)` - Retrieve frontend configuration
- `get_control_matrix(channel)` - Retrieve control matrix settings

**Trigger and Timebase Methods:**
- `set_trigger(type, level, mode, edge, polarity, width, width_condition, nth_event, holdoff, hysteresis, auto_sensitivity, noise_reject, hf_reject, source)` - Configure trigger settings
- `set_timebase(t1, t2)` - Set timebase window relative to trigger
- `get_timebase()` - Retrieve timebase settings
- `set_hysteresis(hysteresis_mode, value)` - **Deprecated**: Use `hysteresis` parameter of `set_trigger` instead
- `enable_rollmode(roll)` - Enable/disable roll mode

**Data Acquisition Methods:**
- `get_data(timeout, wait_reacquire, wait_complete, measurements)` - Retrieve data frame with optional measurements
- `save_high_res_buffer(comments, timeout)` - Save high-resolution buffer to file
- `set_acquisition_mode(mode)` - Set acquisition mode (Normal, Precision, DeepMemory, PeakDetect)
- `get_acquisition_mode()` - Retrieve current acquisition mode
- `get_samplerate()` - Get current sample rate

**Streaming Methods:**
- `start_streaming(duration, mode, rate, trigger_source, trigger_level)` - Start streaming data
- `stop_streaming()` - Stop streaming session
- `get_chunk()` - Get next raw chunk from streaming session
- `get_stream_status()` - Get current streaming status

**Logging Methods:**
- `start_logging(duration, delay, file_name_prefix, comments, trigger_source, trigger_level, mode, rate)` - Start data logging
- `stop_logging()` - Stop data logging
- `logging_progress()` - Get logging progress status

**Settings Management:**
- `save_settings(filename)` - Save instrument configuration to `.mokuconf` file
- `load_settings(filename)` - Load configuration from `.mokuconf` file
- `summary()` - Get instrument summary
- `set_defaults()` - Reset to default settings

```python
class PIDController(MultiInstrumentSlottable, Moku, StreamInstrument):
    INSTRUMENT_ID = 5
    OPERATION_GROUP = "pidcontroller"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - The `strict` parameter (default `True`) disables implicit conversions and coercions when set
> - Supports dual-channel operation with independent or MIMO control modes
> - All session operations use the pattern: `f"slot{self.slot}/{self.operation_group}"`
> - Streaming operations set `self.stream_id` and `self.ip_address` during initialization

> [!warning] Important
> - Default timeout for reading data is 10 seconds but can be increased via `i.session.read_timeout` property
> - The `set_hysteresis()` method is deprecated since version 3.1.1 - use the `hysteresis` parameter in `set_trigger()` instead
> - When streaming, the `get_chunk()` method raises `StreamException` if stream ID is invalid or connection fails

> [!info] API Reference
> Full API documentation available at: https://apis.liquidinstruments.com/reference/pid

# Functions

No top-level functions are defined in this module. All functionality is encapsulated within the `PIDController` class.

# See Also

- `moku.Moku` - Base instrument class
- `moku.MultiInstrumentSlottable` - Multi-instrument mode support
- `moku.instruments._stream.StreamInstrument` - Streaming functionality base class
- Related instruments in `moku.instruments` package
