---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_phasemeter.py
title: Phasemeter
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:22:07
---

# Overview

The Phasemeter instrument is used to measure the amplitude and change in phase of periodic input signals. Using the auto-acquire feature, it can automatically lock to input frequencies in the range of 2-200MHz and track phase with a bandwidth of 10kHz.

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Support for multi-instrument mode
> - `moku.instruments._stream.StreamInstrument` - Streaming data functionality
> - `moku.exceptions.StreamException` - Exception handling for streaming operations

# Classes

## Phasemeter

A comprehensive instrument for measuring phase and amplitude of periodic signals with auto-acquisition capabilities.

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Initialize Phasemeter instrument with connection parameters
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in multi-instrument mode
- `save_settings(filename)` - Save instrument settings to `.mokuconf` file
- `load_settings(filename)` - Load previously saved settings from `.mokuconf` file
- `summary()` - Get instrument summary
- `set_defaults()` - Reset to default settings
- `reacquire()` - Trigger reacquisition of signal
- `set_frontend(channel, impedance, coupling, range, strict)` - Configure input channel frontend settings
- `get_frontend(channel)` - Retrieve frontend configuration for specified channel
- `set_acquisition_speed(speed, strict)` - Set data acquisition rate
- `get_acquisition_speed()` - Get current acquisition speed
- `set_pm_loop(channel, auto_acquire, frequency, bandwidth, strict)` - Configure phase meter loop settings
- `get_pm_loop(channel)` - Get phase meter loop configuration
- `get_auto_acquired_frequency(channel, strict)` - Retrieve the auto-acquired frequency for a channel
- `generate_output(channel, signal, amplitude, frequency, frequency_multiplier, phase, offset, phase_locked, scaling, output_range, strict)` - Generate output signal
- `sync_output_phase()` - Synchronize output phase across channels
- `disable_output(channel, strict)` - Disable output on specified channel
- `enable_input(channel, enable, strict)` - Enable or disable input signal on channel
- `disable_input(channel)` - Deprecated method to disable input (use `enable_input` instead)
- `zero_phase(channel)` - Reset phase measurement to zero for specified channel
- `enable_freewheeling(enable, strict)` - Enable or disable freewheeling mode
- `enable_single_input(enable, strict)` - Route first input signal to all phasemeter channels
- `set_phase_wrap(value, strict)` - Configure phase wrapping at specific values
- `set_auto_reset(value, strict)` - Configure automatic phase reset threshold
- `get_data(timeout, wait_reacquire)` - Retrieve measurement data frame
- `start_logging(duration, delay, file_name_prefix, comments, strict, acquisition_speed)` - Begin data logging to file
- `stop_logging()` - Stop current logging session
- `logging_progress()` - Check progress of active logging session
- `start_streaming(duration, acquisition_speed)` - Start streaming measurement data
- `stop_streaming()` - Stop active streaming session
- `get_stream_status()` - Check status of streaming session
- `get_chunk()` - Retrieve next raw chunk from streaming session

```python
class Phasemeter(MultiInstrumentSlottable, Moku, StreamInstrument):
    """
    Phasemeter instrument object.

    The Phasemeter instrument is used to measure the
    amplitude and change in phase of periodic input
    signals. Using the auto-acquire feature, it can
    automatically lock to input frequencies in the
    range of 2-200MHz and track phase with a
    bandwidth of 10kHz.
    """

    INSTRUMENT_ID = 3
    OPERATION_GROUP = "phasemeter"
```

> [!note] Implementation Notes
> - Inherits from `MultiInstrumentSlottable`, `Moku`, and `StreamInstrument` for full functionality
> - Supports both standalone and multi-instrument slot configurations
> - All API operations use the session interface with slot-based routing
> - Most setter methods include a `strict` parameter to disable implicit conversions

> [!warning] Important
> - The `disable_input` method is deprecated since version 3.1.1 - use `enable_input` instead
> - Default timeout for `get_data` is 60 seconds, but can be increased via `session.read_timeout`
> - Streaming operations require proper initialization of `stream_id` and `ip_address` attributes

# Key Features

## Frontend Configuration

Configure input impedance, coupling, and range for each channel:

**Impedance Options:** `1MOhm`, `50Ohm`
**Coupling Options:** `AC`, `DC`
**Range Options:** `100mVpp`, `400mVpp`, `1Vpp`, `2Vpp`, `4Vpp`, `10Vpp`, `40Vpp`, `50Vpp`

## Acquisition Speed

Configurable data acquisition rates from 30Hz to 152kHz:
`30Hz`, `37Hz`, `119Hz`, `150Hz`, `477Hz`, `596Hz`, `1.9kHz`, `2.4kHz`, `15.2kHz`, `19.1kHz`, `122kHz`, `152kHz`

## Phase Meter Loop

- Auto-acquire mode for automatic frequency locking (2-200MHz range)
- Manual frequency setting
- Configurable bandwidth: `1Hz`, `10Hz`, `100Hz`, `1kHz`, `10kHz`, `100kHz`, `1MHz`

## Output Signal Generation

Generate various output signal types:
- `Sine` - Standard sine wave
- `Phase` - Phase-derived signal
- `FrequencyOffset` - Frequency offset signal
- `Amptitude` - Amplitude-derived signal

**Output Range Options:** `2Vpp`, `10Vpp`

## Phase Management

- Phase wrapping at configurable thresholds: `Off`, `1pi`, `2pi`, `4pi`
- Auto-reset functionality at phase thresholds
- Zero phase calibration
- Phase synchronization across outputs

## Data Acquisition

Multiple methods for retrieving measurement data:
- **Immediate Data**: `get_data()` for single frame acquisition
- **Logging**: Save data to files with configurable duration and metadata
- **Streaming**: Real-time data streaming with chunk-based retrieval

> [!example] Usage Pattern
> ```python
> # Initialize phasemeter
> pm = Phasemeter(ip='192.168.1.100')
>
> # Configure frontend
> pm.set_frontend(channel=1, impedance='50Ohm',
>                 coupling='AC', range='1Vpp')
>
> # Set up phase meter loop with auto-acquire
> pm.set_pm_loop(channel=1, auto_acquire=True,
>                bandwidth='10kHz')
>
> # Get measurement data
> data = pm.get_data(timeout=10)
> ```

# See Also

- [Moku API Documentation](https://apis.liquidinstruments.com/reference/phasemeter)
- Related instruments: `_stream.StreamInstrument`
- Base classes: `Moku`, `MultiInstrumentSlottable`
