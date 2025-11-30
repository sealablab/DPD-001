---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_lockinamp.py
title: LockInAmp
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:21:46
---

# Overview

The LockInAmp instrument provides dual-phase demodulation (XY/Rθ) capabilities with an integrated oscilloscope and data logger. This instrument is part of the Moku multi-instrument platform and supports lock-in amplifier functionality for precision signal measurement and analysis.

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument functionality
> - `moku.MultiInstrumentSlottable` - Multi-instrument slot management
> - `moku.instruments._stream.StreamInstrument` - Streaming data capabilities
> - `moku.exceptions.StreamException` - Exception handling for streaming operations

# Classes

## LockInAmp

A lock-in amplifier instrument that performs dual-phase demodulation with oscilloscope and logging capabilities.

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Initialize the instrument with connection parameters
- `for_slot(slot, multi_instrument)` - Configure instrument at given slot in multi-instrument mode
- `save_settings(filename)` - Save instrument settings to a .mokuconf file
- `load_settings(filename)` - Load previously saved .mokuconf settings
- `set_frontend(channel, coupling, impedance, attenuation, gain)` - Configure input channel frontend settings
- `get_frontend(channel)` - Retrieve frontend settings for a channel
- `set_demodulation(mode, frequency, phase)` - Configure demodulation mode and parameters
- `get_demodulation()` - Retrieve current demodulation settings
- `set_filter(corner_frequency, slope)` - Configure low-pass filter
- `get_filter()` - Retrieve filter settings
- `set_monitor(monitor_channel, source)` - Configure monitor channel routing
- `set_outputs(main, aux, main_offset, aux_offset)` - Configure main and auxiliary outputs
- `get_outputs()` - Retrieve output configuration
- `set_aux_output(frequency, amplitude)` - Configure auxiliary oscillator
- `get_aux_output()` - Retrieve auxiliary oscillator settings
- `set_gain(main, aux, main_invert, aux_invert, main_gain_range, aux_gain_range)` - Configure output gains
- `get_gain()` - Retrieve gain settings
- `set_polar_mode(range)` - Configure polar coordinate range
- `get_polar_theta_range()` - Retrieve polar theta range
- `set_pll(auto_acquire, frequency, frequency_multiplier, bandwidth)` - Configure phase-locked loop
- `get_pll()` - Retrieve PLL settings
- `use_pid(channel)` - Enable/configure PID controller
- `set_by_frequency(prop_gain, int_crossover, diff_crossover, int_saturation, diff_saturation, invert)` - Configure PID parameters by frequency
- `pll_reacquire()` - Force PLL to reacquire lock
- `set_trigger(type, level, mode, edge, polarity, width, width_condition, nth_event, holdoff, hysteresis, auto_sensitivity, noise_reject, hf_reject, source)` - Configure oscilloscope trigger
- `set_timebase(t1, t2)` - Configure oscilloscope timebase
- `set_hysteresis(hysteresis_mode, value)` - Configure trigger hysteresis (deprecated)
- `enable_rollmode(roll)` - Enable/disable oscilloscope roll mode
- `get_data(timeout, wait_reacquire, wait_complete, measurements)` - Retrieve oscilloscope data
- `save_high_res_buffer(comments, timeout)` - Save high-resolution buffer
- `set_acquisition_mode(mode)` - Configure acquisition mode
- `get_samplerate()` - Retrieve current sample rate
- `get_acquisition_mode()` - Retrieve acquisition mode
- `get_timebase()` - Retrieve timebase settings
- `logging_progress()` - Get data logging progress
- `start_logging(duration, delay, file_name_prefix, comments, trigger_source, trigger_level, mode, rate)` - Start data logging
- `stop_logging()` - Stop data logging
- `start_streaming(duration, mode, rate, trigger_source, trigger_level)` - Start streaming data
- `stop_streaming()` - Stop streaming data
- `get_chunk()` - Get next raw chunk from streaming session
- `get_stream_status()` - Get streaming status

```python
class LockInAmp(MultiInstrumentSlottable, Moku, StreamInstrument):
    """
    LockInAmp instrument object.

    The LockInAmp instrument supports dual-phase
    demodulation (XY/Rθ) with integrated oscilloscope
    and data logger

    Read more at https://apis.liquidinstruments.com/reference/lia
    """
    INSTRUMENT_ID = 8
    OPERATION_GROUP = "lockinamp"
```

> [!note] Implementation Notes
> - Inherits from MultiInstrumentSlottable, Moku, and StreamInstrument
> - All setter methods include a `strict` parameter (default True) to disable implicit conversions
> - Methods communicate with the instrument via session.post() and session.get() calls
> - Supports both standalone and multi-instrument slot operation modes

> [!info] Reference Documentation
> Complete API documentation available at: https://apis.liquidinstruments.com/reference/lia

## Frontend Configuration

**Input Coupling Options:**
- AC or DC coupling per channel

**Input Impedance Options:**
- 1MOhm or 50Ohm

**Attenuation/Gain Options:**
- Attenuation: -20dB, 0dB, 14dB, 20dB, 32dB, 40dB
- Gain: 20dB, 0dB, -14dB, -20dB, -32dB, -40dB

## Demodulation Modes

**Available Modes:**
- Internal - Use internal oscillator
- External - Use external reference signal
- ExternalPLL - Use external signal with PLL tracking
- None - Disable demodulation

> [!note] Frequency Range
> Demodulation frequency parameter accepts numeric values representing frequency in Hz (default: 1MHz)

## Filter Configuration

**Slope Options:**
- Slope6dB (default)
- Higher slopes available (specific options depend on firmware)

**Corner Frequency:**
- Configurable low-pass filter corner frequency

## Output Configuration

**Main Output Options:**
- X, Y, R, Theta, Offset, None

**Auxiliary Output Options:**
- Y, Theta, Demod, Aux, Offset, None

**Gain Control:**
- Independent gain control for main and auxiliary channels
- Inversion capability for each channel
- Gain range selection (Pro models only)

## Polar Mode

**Available Ranges:**
- 2Vpp
- 7.5mVpp
- 25uVpp

## PLL Configuration

**Bandwidth Options:**
- 1Hz, 10Hz, 100Hz, 1kHz, 10kHz, 100kHz, 1MHz

**Features:**
- Auto-acquire mode for automatic frequency detection
- Manual frequency specification when auto-acquire is disabled
- Configurable frequency multiplier

## PID Controller

**Target Channels:**
- Off - Disable PID
- Main - Apply to main output
- Aux - Apply to auxiliary output

**Frequency-Based Parameters:**
- Proportional gain: -60dB to 60dB
- Integrator crossover: 31.25e-3Hz to 312.5e3Hz
- Differentiator crossover: 312.5e-3Hz to 3.125e6Hz
- Integrator saturation: -60dB to 60dB
- Differentiator saturation: -60dB to 60dB

## Oscilloscope Features

**Trigger Types:**
- Edge - Trigger on rising/falling/both edges
- Pulse - Trigger on pulse width conditions

**Trigger Sources:**
- ProbeA, ProbeB, ProbeC, ProbeD, External

**Trigger Modes:**
- Auto - Automatically trigger if no event occurs
- Normal - Wait for trigger event

**Acquisition Modes:**
- Normal - Standard acquisition
- Precision - Higher precision sampling
- DeepMemory - Extended memory depth
- PeakDetect - Capture peak values

> [!warning] Trigger Configuration
> When using Pulse mode, the edge parameter specifies pulse polarity (rising=positive, falling=negative). The 'both' option is invalid for pulse triggers.

## Data Acquisition

**get_data() Parameters:**
- `timeout` - Wait time in seconds (default: 60)
- `wait_reacquire` - Wait for new dataframe acquisition
- `wait_complete` - Wait for entire frame to be available
- `measurements` - Include channel measurements when True

> [!important] Timeout Configuration
> Default read timeout is 10 seconds. Increase via: `instrument.session.read_timeout = 100`

## Streaming

**Streaming Workflow:**
1. Call `start_streaming()` with desired parameters
2. Repeatedly call `get_chunk()` to retrieve data
3. Monitor status with `get_stream_status()`
4. Call `stop_streaming()` when finished

**Stream Parameters:**
- Duration, mode, rate, trigger source, trigger level

> [!note] Stream Management
> The instrument maintains stream_id and ip_address internally during active streaming sessions

## Data Logging

**Logging Features:**
- Configurable duration and delay
- Optional trigger source and level
- File name prefix and comments support
- Multiple acquisition modes supported
- Configurable acquisition rate

**Progress Monitoring:**
- Use `logging_progress()` to check logging status

> [!warning] Deprecated Method
> `set_hysteresis()` is deprecated since version 3.1.1. Use the `hysteresis` parameter of `set_trigger()` instead.

# See Also

- Related instruments: Oscilloscope, DataLogger
- Parent classes: Moku, MultiInstrumentSlottable, StreamInstrument
- Exception handling: StreamException
