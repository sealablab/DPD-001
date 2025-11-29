---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_oscilloscope.py
title: Oscilloscope
---

# Overview

The Oscilloscope instrument provides time-domain views of voltages on analog inputs. It includes a built-in Waveform Generator that can control Moku analog outputs. The oscilloscope can display signals from the two analog inputs or loop back the signals being generated.

> [!info] Key Dependencies
> - `moku.Moku` - Base instrument class
> - `moku.MultiInstrumentSlottable` - Enables multi-instrument slot management

# Classes

## Oscilloscope

Digital oscilloscope with built-in waveform generator for Moku hardware platforms.

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Initialize oscilloscope connection
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in multi-instrument mode
- `save_settings(filename)` - Save instrument configuration to .mokuconf file
- `load_settings(filename)` - Load configuration from .mokuconf file
- `set_defaults()` - Reset to default settings
- `set_frontend(channel, impedance, coupling, range)` - Configure input channel frontend parameters
- `get_frontend(channel)` - Retrieve frontend configuration for a channel
- `set_source(channel, source)` - Set data source for a channel
- `set_sources(sources)` - Set multiple data sources at once
- `get_sources()` - Retrieve current source configuration
- `set_trigger(type, level, mode, edge, ...)` - Configure trigger settings with extensive options
- `set_timebase(t1, t2, max_length, frame_length)` - Configure time axis and data frame length
- `get_timebase()` - Retrieve current timebase settings
- `get_data(timeout, wait_reacquire, wait_complete, measurements)` - Acquire oscilloscope data frame
- `set_acquisition_mode(mode)` - Set acquisition mode (Normal, Precision, DeepMemory, PeakDetect)
- `get_acquisition_mode()` - Get current acquisition mode
- `get_samplerate()` - Retrieve current sample rate
- `generate_waveform(channel, type, amplitude, frequency, ...)` - Generate output waveform
- `sync_output_phase()` - Synchronize output phase
- `set_interpolation(interpolation)` - Set waveform interpolation method
- `get_interpolation()` - Get current interpolation setting
- `disable_input(channel)` - Disable an input channel
- `enable_rollmode(roll)` - Enable or disable roll mode display
- `set_input_attenuation(channel, attenuation)` - Set input attenuation factor
- `set_output_termination(channel, termination)` - Set output termination impedance
- `get_output_termination(channel)` - Get output termination setting
- `save_high_res_buffer(comments, timeout)` - Save high-resolution buffer with optional comments
- `osc_measurement(t1, t2, trigger_source, edge, level)` - Configure measurement parameters
- `summary()` - Get instrument summary information

```python
class Oscilloscope(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 1
    OPERATION_GROUP = "oscilloscope"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - All operations are performed via session.post() or session.get() REST API calls
> - The `strict` parameter (default True) disables implicit conversions and coercions
> - Data frames default to 1024 points but can be configured via set_timebase()
> - Actual frame length may vary based on timebase settings
> - Default read timeout is 10 seconds but can be adjusted via session.read_timeout

## Frontend Configuration

### set_frontend

```python
def set_frontend(self, channel, impedance, coupling, range, strict=True):
    """Configure analog input channel frontend parameters"""
```

Configures the analog frontend for an input channel.

**Parameters:**
- `channel` (integer) - Target channel number
- `impedance` (string) - Input impedance: '1MOhm' or '50Ohm'
- `coupling` (string) - Input coupling: 'AC' or 'DC'
- `range` (string) - Input voltage range: '100mVpp', '400mVpp', '1Vpp', '2Vpp', '4Vpp', '10Vpp', '40Vpp', '50Vpp'
- `strict` (boolean) - Disable implicit conversions (default: True)

**Returns:** API response from session

## Source Configuration

### set_source

```python
def set_source(self, channel, source, strict=True):
    """Set the data source for a channel"""
```

Sets which signal source is routed to a display channel.

**Parameters:**
- `channel` (integer) - Target channel number
- `source` (string) - Source selection: 'None', 'Input1', 'Input2', 'Input3', 'Input4', 'Output1', 'Output2', 'Output3', 'Output4'
- `strict` (boolean) - Disable implicit conversions (default: True)

**Returns:** API response from session

## Trigger Configuration

### set_trigger

```python
def set_trigger(self, type="Edge", level=0, level_low=0, level_high=0.1,
                mode="Auto", edge="Rising", polarity="Positive",
                width=0.0001, width_condition="LessThan", nth_event=1,
                holdoff=0, hysteresis=1e-3, auto_sensitivity=True,
                noise_reject=False, hf_reject=False, source="Input1",
                strict=True):
    """Configure oscilloscope trigger parameters"""
```

Comprehensive trigger configuration with support for Edge, Pulse, and Runt trigger modes.

**Parameters:**
- `type` (string) - Trigger type: 'Edge', 'Pulse', 'Runt'
- `level` (number) - Trigger level voltage [-5V to 5V]
- `level_low` (number) - Low trigger level for Runt mode [-5V to 5V]
- `level_high` (number) - High trigger level for Runt mode [-5V to 5V]
- `mode` (string) - Trigger mode: 'Auto' or 'Normal'
- `edge` (string) - Edge selection: 'Rising', 'Falling', 'Both'
- `polarity` (string) - Pulse polarity: 'Positive' or 'Negative'
- `width` (number) - Pulse width [26e-3 to 10 seconds]
- `width_condition` (string) - Width condition: 'GreaterThan' or 'LessThan'
- `nth_event` (integer) - Number of trigger events before triggering [0-65535]
- `holdoff` (number) - Trigger holdoff duration [1e-9 to 10 seconds]
- `hysteresis` (number) - Absolute hysteresis around trigger (default: 0.001)
- `auto_sensitivity` (boolean) - Auto or manual hysteresis mode
- `noise_reject` (boolean) - Enable hysteresis for noise rejection
- `hf_reject` (boolean) - Enable low-pass filter for HF noise rejection
- `source` (string) - Trigger source: 'ChannelA', 'ChannelB', 'ChannelC', 'ChannelD', 'Input1-4', 'Output1-4', 'External'
- `strict` (boolean) - Disable implicit conversions (default: True)

**Returns:** API response from session

> [!note] Trigger Modes
> - **Edge mode**: Triggers on rising, falling, or both edges
> - **Pulse mode**: Triggers on pulse width conditions (width parameter required)
> - **Runt mode**: Triggers on runt pulses between level_low and level_high

## Timebase Configuration

### set_timebase

```python
def set_timebase(self, t1, t2, max_length=1024, frame_length=None, strict=True):
    """Configure time axis and data acquisition window"""
```

Sets the time window relative to the trigger point and maximum data frame length.

**Parameters:**
- `t1` (number) - Time from trigger to left edge of screen (can be negative for on-screen trigger)
- `t2` (number) - Time from trigger to right edge of screen (must be positive)
- `max_length` (number) - Maximum number of points to return via get_data() (default: 1024)
- `frame_length` (number) - Deprecated, use max_length instead
- `strict` (boolean) - Disable implicit conversions (default: True)

**Returns:** API response from session

> [!warning] Frame Length Variability
> The actual frame length may be less than max_length and can vary based on timebase settings. Code should handle variable frame lengths.

## Data Acquisition

### get_data

```python
def get_data(self, timeout=60, wait_reacquire=False,
             wait_complete=False, measurements=False):
    """Retrieve oscilloscope data frame"""
```

Returns a dictionary containing the acquired data frame and timebase information.

**Parameters:**
- `timeout` (number) - Wait timeout in seconds (default: 60)
- `wait_reacquire` (boolean) - Wait until new dataframe is acquired
- `wait_complete` (boolean) - Wait until entire frame is available
- `measurements` (boolean) - Include measurement data for each channel

**Returns:** Dictionary with data frame and timebase information

> [!warning] Important
> Default timeout for reading data is 10 seconds. For longer acquisitions, increase the read timeout:
> ```python
> oscilloscope.session.read_timeout = 100  # seconds
> ```

## Acquisition Modes

### set_acquisition_mode

```python
def set_acquisition_mode(self, mode="Normal", strict=True):
    """Set oscilloscope acquisition mode"""
```

Configures the data acquisition mode.

**Parameters:**
- `mode` (string) - Acquisition mode: 'Normal', 'Precision', 'DeepMemory', 'PeakDetect'
- `strict` (boolean) - Disable implicit conversions (default: True)

**Returns:** API response from session

## Waveform Generation

### generate_waveform

```python
def generate_waveform(self, channel, type, amplitude=1, frequency=10000,
                      offset=0, phase=0, duty=None, symmetry=None,
                      dc_level=None, edge_time=None, pulse_width=None,
                      strict=True):
    """Generate output waveform on specified channel"""
```

Configures the built-in waveform generator for output signals.

**Parameters:**
- `channel` (integer) - Target output channel
- `type` (string) - Waveform type: 'Off', 'Sine', 'Square', 'Ramp', 'Pulse', 'Noise', 'DC'
- `amplitude` (number) - Peak-to-peak amplitude [4e-3V to 10V]
- `frequency` (number) - Waveform frequency [1e-3Hz to 20MHz]
- `offset` (number) - DC offset [-5V to 5V]
- `phase` (number) - Phase offset [0 to 360 degrees]
- `duty` (number) - Duty cycle [0-100%] (Square wave only)
- `symmetry` (number) - Rise fraction [0-100%] (Ramp wave)
- `dc_level` (number) - DC level (DC waveform only)
- `edge_time` (number) - Edge time [16e-9 to pulse_width] (Pulse wave only)
- `pulse_width` (number) - Pulse width (Pulse wave only)
- `strict` (boolean) - Disable implicit conversions (default: True)

**Returns:** API response from session

> [!note] Waveform Types
> Different waveform types use different parameters:
> - **Square**: Uses duty parameter
> - **Ramp**: Uses symmetry parameter
> - **Pulse**: Uses edge_time and pulse_width parameters
> - **DC**: Uses dc_level parameter
> - **Sine/Noise**: Use standard amplitude/frequency parameters

## Output Configuration

### set_output_termination

```python
def set_output_termination(self, channel, termination, strict=True):
    """Configure output termination impedance"""
```

Sets the output termination impedance for a channel.

**Parameters:**
- `channel` (integer) - Target channel number
- `termination` (string) - Termination setting: 'HiZ' or '50Ohm'
- `strict` (boolean) - Disable implicit conversions (default: True)

**Returns:** API response from session

## Configuration Management

### save_settings

```python
def save_settings(self, filename):
    """Save current instrument configuration to file"""
```

Saves all instrument settings to a .mokuconf file for later restoration.

**Parameters:**
- `filename` (FileDescriptorOrPath) - Path to save .mokuconf file

> [!note] File Format
> Files should have `.mokuconf` extension for compatibility with Moku desktop tools

### load_settings

```python
def load_settings(self, filename):
    """Load instrument configuration from file"""
```

Loads a previously saved .mokuconf file into the instrument.

**Parameters:**
- `filename` (FileDescriptorOrPath) - Path to .mokuconf file to load

## Deprecated Methods

### set_hysteresis

> [!warning] Deprecated in v3.1.1
> Use the `hysteresis` parameter of `set_trigger()` instead.

### set_output_load / get_output_load

> [!warning] Deprecated in v3.1.1
> Use `set_output_termination()` and `get_output_termination()` instead.

# See Also

- [Moku API Documentation](https://apis.liquidinstruments.com/reference/oscilloscope)
- Related instruments: WaveformGenerator, SpectrumAnalyzer
