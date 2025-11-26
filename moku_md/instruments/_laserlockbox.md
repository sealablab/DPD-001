---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_laserlockbox.py
title: LaserLockBox
---

# Overview

The LaserLockBox module provides a Python interface for controlling and configuring the Moku Laser Lock Box instrument. This instrument is designed for laser frequency stabilization and locking applications, featuring PID controllers, demodulation, filtering, and oscillator functionality.

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Enables multi-instrument mode operation
> - `moku.instruments._stream.StreamInstrument` - Provides data streaming capabilities
> - `moku.exceptions.StreamException` - Exception handling for streaming operations

# Classes

## LaserLockBox

Multi-functional laser lock box instrument for frequency stabilization and control applications.

**Inheritance:**
- `MultiInstrumentSlottable` - Supports slot-based multi-instrument operation
- `Moku` - Core Moku device functionality
- `StreamInstrument` - Data acquisition and streaming

**Key Configuration:**
- `INSTRUMENT_ID = 16`
- `OPERATION_GROUP = "laserlockbox"`

**Key Methods:**

### Initialization and Configuration
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Initialize connection to the instrument
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in a specific slot
- `save_settings(filename)` - Save instrument configuration to `.mokuconf` file
- `load_settings(filename)` - Load configuration from `.mokuconf` file
- `set_defaults()` - Reset instrument to default settings
- `summary()` - Get current instrument state summary

### Input/Output Configuration
- `set_frontend(channel, coupling, impedance, attenuation, gain, strict)` - Configure input channel frontend (AC/DC coupling, impedance, gain/attenuation)
- `set_digital_input_gain(digital_gain, strict)` - Set digital input gain (0dB, 24dB, 48dB)
- `set_output(channel, signal, output, gain_range, strict)` - Enable/disable output channels with gain range
- `set_output_offset(channel, offset, strict)` - Set DC offset for output channel
- `set_output_limit(channel, enable, low_limit, high_limit, strict)` - Configure voltage limiter on output
- `get_frontend(channel, strict)` - Query frontend configuration
- `get_output_offset(channel, strict)` - Query output offset
- `get_output_limit(channel, strict)` - Query output limit settings

### Oscillators and Signal Generation
- `set_aux_oscillator(enable, frequency, amplitude, phase_lock, output, strict)` - Configure auxiliary oscillator (1 MHz default)
- `set_scan_oscillator(enable, shape, frequency, amplitude, output, strict)` - Configure scan oscillator with various waveforms (ramp, triangle)
- `get_aux_oscillator()` - Query auxiliary oscillator settings
- `get_scan_oscillator()` - Query scan oscillator settings

### Demodulation and Phase-Locked Loop
- `set_demodulation(mode, frequency, phase, strict)` - Configure demodulation mode (Modulation, Internal, External, ExternalPLL, None)
- `set_pll(auto_acquire, frequency, frequency_multiplier, bandwidth, strict)` - Configure external PLL with bandwidth options (1Hz to 1MHz)
- `pll_reacquire()` - Trigger PLL reacquisition
- `get_pll()` - Query PLL settings
- `get_demodulation()` - Query demodulation settings

### Filtering
- `set_filter(shape, type, low_corner, high_corner, pass_band_ripple, stop_band_attenuation, order, strict)` - Configure standard filters (Lowpass, Bandstop) with multiple types (Butterworth, Chebyshev, Elliptic, Bessel, etc.)
- `set_custom_filter(scaling, coefficients, strict)` - Configure custom IIR filter with coefficient stages

### PID Control
- `set_pid_by_frequency(channel, prop_gain, int_crossover, diff_crossover, double_int_crossover, int_saturation, diff_saturation, invert, strict)` - Configure PID controller using frequency-based parameters with dual integrators and saturation limits
- `set_setpoint(setpoint, strict)` - Set the error signal setpoint voltage
- `get_setpoint()` - Query current setpoint

### Monitoring and Triggering
- `set_monitor(monitor_channel, source, strict)` - Route internal signals to monitor outputs (sources include filters, PID outputs, error signals, oscillators)
- `set_trigger(type, level, mode, edge, polarity, width, width_condition, nth_event, holdoff, hysteresis, auto_sensitivity, noise_reject, hf_reject, source, strict)` - Configure oscilloscope-style triggering (Edge or Pulse modes)
- `enable_conditional_trigger(enable, strict)` - Enable/disable conditional triggering
- `set_hysteresis(hysteresis_mode, value, strict)` - **Deprecated in v3.1.1** - Set trigger hysteresis (use `set_trigger` instead)

### Data Acquisition
- `set_timebase(t1, t2, strict)` - Configure time window for data acquisition relative to trigger
- `set_acquisition_mode(mode, strict)` - Set acquisition mode (Normal, Precision, DeepMemory, PeakDetect)
- `get_data(timeout, wait_reacquire, wait_complete, measurements)` - Acquire single data frame with optional measurements
- `get_samplerate()` - Query current sample rate
- `get_acquisition_mode()` - Query acquisition mode
- `get_timebase()` - Query timebase settings
- `enable_rollmode(roll, strict)` - Enable/disable roll mode for continuous display

### Data Logging
- `start_logging(duration, delay, file_name_prefix, comments, trigger_source, trigger_level, mode, rate, strict)` - Start data logging to instrument storage
- `stop_logging()` - Stop active logging session
- `logging_progress()` - Query logging progress
- `save_high_res_buffer(comments, timeout)` - Save high-resolution buffer to file

### Data Streaming
- `start_streaming(duration, mode, rate, trigger_source, trigger_level)` - Start real-time data streaming to host
- `stop_streaming()` - Stop active streaming session
- `get_chunk()` - Retrieve next raw data chunk from stream
- `get_stream_status()` - Query streaming status

```python
class LaserLockBox(MultiInstrumentSlottable, Moku, StreamInstrument):
    INSTRUMENT_ID = 16
    OPERATION_GROUP = "laserlockbox"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - All configuration methods accept a `strict` parameter (default `True`) to disable implicit conversions
> - Channel parameters are typically 1-indexed integers
> - Frequency ranges and parameter limits are enforced by the instrument
> - The class uses REST API calls via `self.session.post()` and `self.session.get()`
> - Streaming operations require managing `stream_id` and use V2 API endpoints

> [!warning] Important
> - Default read timeout is 30 seconds; increase via `session.read_timeout` for long operations
> - Streaming operations can raise `StreamException` on errors
> - The `set_hysteresis()` method is deprecated since v3.1.1; use `hysteresis` parameter in `set_trigger()` instead
> - File operations (save/load settings) expect `.mokuconf` extension for compatibility

> [!example] Typical Usage Pattern
> ```python
> # Initialize instrument
> llb = LaserLockBox(ip='192.168.1.100')
>
> # Configure input frontend
> llb.set_frontend(channel=1, coupling='DC', impedance='1MOhm', attenuation='0dB')
>
> # Set up demodulation and PLL
> llb.set_demodulation(mode='ExternalPLL', frequency=1e6)
> llb.set_pll(auto_acquire=True, bandwidth='1kHz')
>
> # Configure PID controller
> llb.set_pid_by_frequency(channel=1, prop_gain=10, int_crossover=1000)
> llb.set_setpoint(setpoint=0.5)
>
> # Start data acquisition
> data = llb.get_data(timeout=60, measurements=True)
> ```

# See Also

- `moku.Moku` - Base instrument class
- `moku.MultiInstrumentSlottable` - Multi-instrument mode interface
- `moku.instruments._stream.StreamInstrument` - Streaming functionality
- Related instruments: PID Controller, Lock-in Amplifier, Oscilloscope
