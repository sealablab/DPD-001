---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_waveformgenerator.py
title: WaveformGenerator
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:22:48
---

# Overview

The WaveformGenerator module provides control over Moku's Waveform Generator instrument, which generates Sine, Square, Ramp, Pulse, Noise, and DC waveforms. The output waveforms support frequency, phase, and amplitude modulation, with modulation sources including internally-generated sinewaves, analog input channels, or other output channels.

> [!info] Key Dependencies
> - `moku.Moku` - Base instrument class
> - `moku.MultiInstrumentSlottable` - Support for multi-instrument mode
> - Communicates with hardware via session-based REST API calls

# Classes

## WaveformGenerator

Multi-instrument compatible waveform generator that provides comprehensive signal generation capabilities including basic waveforms, modulation, burst mode, and sweep mode.

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Initialize connection to Moku device
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in multi-instrument mode
- `generate_waveform(channel, type, amplitude, frequency, offset, phase, **kwargs)` - Generate a waveform with specified parameters
- `set_modulation(channel, type, source, depth, frequency)` - Configure waveform modulation
- `disable_modulation(channel)` - Disable modulation on a channel
- `set_burst_mode(channel, source, mode, **kwargs)` - Configure burst mode operation
- `set_sweep_mode(channel, source, stop_frequency, sweep_time, trigger_level)` - Configure frequency sweep
- `set_output_termination(channel, termination)` - Set output impedance (HiZ or 50Ohm)
- `get_output_termination(channel)` - Get current output termination
- `set_frontend(channel, impedance, coupling, range)` - Configure input frontend settings
- `get_frontend(channel)` - Get current frontend configuration
- `sync_phase()` - Synchronize phase across channels
- `manual_trigger()` - Manually trigger all configured channels
- `save_settings(filename)` - Save configuration to .mokuconf file
- `load_settings(filename)` - Load configuration from .mokuconf file
- `summary()` - Get instrument summary information
- `set_defaults()` - Reset instrument to default settings

```python
class WaveformGenerator(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 4
    OPERATION_GROUP = "waveformgenerator"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - Inherits from both `MultiInstrumentSlottable` and `Moku` base classes
> - All operations use REST API endpoints via `self.session.post()` or `self.session.get()`
> - Supports `strict` mode to disable implicit conversions and coercions
> - Can be used in standalone mode or as part of a multi-instrument configuration
> - Documentation available at: https://apis.liquidinstruments.com/reference/waveformgenerator

# Functions

## generate_waveform

```python
def generate_waveform(channel, type, amplitude=1, frequency=10000,
                      offset=0, phase=0, duty=None, symmetry=None,
                      dc_level=None, edge_time=None, pulse_width=None,
                      strict=True):
    """Generate waveform with specified parameters"""
```

Configures and generates a waveform on the specified channel with comprehensive parameter control.

**Parameters:**
- `channel` (integer) - Target output channel
- `type` (string) - Waveform type: 'Off', 'Sine', 'Square', 'Ramp', 'Pulse', 'Noise', 'DC'
- `amplitude` (number, default=1) - Peak-to-peak amplitude [4e-3V, 10V]
- `frequency` (number, default=10000) - Waveform frequency [1e-3Hz, 20e6Hz]
- `offset` (number, default=0) - DC offset applied to waveform [-5V, 5V]
- `phase` (number, default=0) - Phase offset [0Deg, 360Deg]
- `duty` (number, optional) - Duty cycle percentage [0%, 100%] (Square wave only)
- `symmetry` (number, optional) - Fraction of cycle rising [0%, 100%]
- `dc_level` (number, optional) - DC level (DC waveform only)
- `edge_time` (number, optional) - Edge time [16e-9, pulse width] (Pulse wave only)
- `pulse_width` (number, optional) - Pulse width (Pulse wave only)
- `strict` (boolean, default=True) - Disable all implicit conversions and coercions

**Returns:** API response from waveform generation command

> [!warning] Important
> Different waveform types use different subset of parameters. For example, `duty` is only valid for Square waves, while `edge_time` and `pulse_width` are only for Pulse waves.

## set_modulation

```python
def set_modulation(channel, type, source, depth=0, frequency=10000000,
                   strict=True):
    """Configure modulation for a channel"""
```

Enables and configures modulation on a waveform channel.

**Parameters:**
- `channel` (integer) - Target output channel
- `type` (string) - Modulation type: 'Amplitude', 'Frequency', 'Phase', 'PulseWidth'
- `source` (string) - Modulation source: 'Input1-4', 'InputA-D', 'Output1-4', 'OutputA-B', 'Internal'
- `depth` (number, default=0) - Modulation depth (meaning depends on type): percentage, frequency deviation/volt, or phase shift/volt
- `frequency` (number, default=10000000) - Internal sine wave frequency [0Hz, 50e6Hz] (ignored for ADC/DAC sources)
- `strict` (boolean, default=True) - Disable implicit conversions

**Returns:** API response from modulation configuration

> [!note] Implementation Notes
> The modulation source can be another output channel, allowing creation of complex nested modulation patterns.

## set_burst_mode

```python
def set_burst_mode(channel, source, mode, trigger_level=0,
                   burst_cycles=3, burst_duration=0.1, burst_period=1,
                   input_range=None, strict=True):
    """Configure burst mode operation"""
```

Configures burst mode for generating triggered waveform bursts.

**Parameters:**
- `channel` (integer) - Target output channel
- `source` (string) - Trigger source: 'Input1-4', 'InputA-D', 'Output1-4', 'OutputA-B', 'Internal', 'External'
- `mode` (string) - Burst mode: 'Gated', 'Start', 'NCycle'
- `trigger_level` (number, default=0) - Trigger threshold [-5V, 5V]
- `burst_cycles` (number, default=3) - Number of signal repetitions [1, 1e6] (NCycle mode only)
- `burst_duration` (number, default=0.1) - Duration of burst [1 cycle period, 1e3 seconds]
- `burst_period` (number) - Period between bursts
- `input_range` (string, optional) - Input range: '400mVpp', '1Vpp', '4Vpp', '10Vpp', '40Vpp', '50Vpp'
- `strict` (boolean, default=True) - Disable implicit conversions

**Returns:** API response from burst mode configuration

## set_sweep_mode

```python
def set_sweep_mode(channel, source, stop_frequency=30000000,
                   sweep_time=1, trigger_level=0, strict=True):
    """Configure frequency sweep mode"""
```

Configures linear frequency sweep from the base frequency to the stop frequency.

**Parameters:**
- `channel` (integer) - Target output channel
- `source` (string) - Trigger source: 'Input1-4', 'InputA-D', 'Output1-4', 'OutputA-B', 'Internal', 'External'
- `stop_frequency` (number, default=30000000) - End frequency of sweep [100Hz, 20e6Hz]
- `sweep_time` (number, default=1) - Duration of sweep [1 cycle period, 1e3 seconds]
- `trigger_level` (number, default=0) - Trigger threshold [-5V, 5V]
- `strict` (boolean, default=True) - Disable implicit conversions

**Returns:** API response from sweep mode configuration

## set_output_termination

```python
def set_output_termination(channel, termination, strict=True):
    """Set output termination impedance"""
```

Configures the output termination impedance for a channel.

**Parameters:**
- `channel` (integer) - Target output channel
- `termination` (string) - Output termination: 'HiZ' (high impedance) or '50Ohm'
- `strict` (boolean, default=True) - Disable implicit conversions

**Returns:** API response from termination configuration

> [!note] Implementation Notes
> Replaces the deprecated `set_output_load` method (deprecated since v3.1.1).

## set_frontend

```python
def set_frontend(channel, impedance, coupling, range, strict=True):
    """Configure input frontend settings"""
```

Configures the analog input frontend parameters for a channel.

**Parameters:**
- `channel` (integer) - Target input channel
- `impedance` (string) - Input impedance: '1MOhm' or '50Ohm'
- `coupling` (string) - Input coupling: 'AC' or 'DC'
- `range` (string) - Input range: '100mVpp', '400mVpp', '1Vpp', '2Vpp', '4Vpp', '10Vpp', '40Vpp', '50Vpp'
- `strict` (boolean, default=True) - Disable implicit conversions

**Returns:** API response from frontend configuration

## save_settings / load_settings

```python
def save_settings(filename):
    """Save instrument settings to a .mokuconf file"""

def load_settings(filename):
    """Load instrument settings from a .mokuconf file"""
```

Persist and restore complete instrument configurations.

**Parameters:**
- `filename` (FileDescriptorOrPath) - Path to .mokuconf file

**Returns:** None (save_settings), API response (load_settings)

> [!note] Implementation Notes
> Configuration files use the `.mokuconf` extension and are compatible with the Moku desktop application.

## sync_phase

```python
def sync_phase():
    """Synchronize phase across all output channels"""
```

Aligns the phase of all output channels to ensure synchronized operation.

**Returns:** API response from phase synchronization

## manual_trigger

```python
def manual_trigger():
    """Manually trigger all channels configured for manual triggering"""
```

Initiates a software trigger for all channels configured in manual trigger mode.

**Returns:** API response from trigger command

# See Also

- Official API Documentation: https://apis.liquidinstruments.com/reference/waveformgenerator
- Base classes: `moku.Moku`, `moku.MultiInstrumentSlottable`
- Related instruments: Oscilloscope, Spectrum Analyzer
