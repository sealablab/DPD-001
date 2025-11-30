---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_datalogger.py
title: Datalogger
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:21:19
---

# Overview

The Datalogger instrument provides file logging of time-series voltage data from the Moku device. It includes a built-in Waveform Generator that can control the analog outputs, allowing simultaneous data acquisition and signal generation.

Read more at https://apis.liquidinstruments.com/reference/datalogger

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Enables multi-instrument mode operation
> - `moku.instruments._stream.StreamInstrument` - Provides streaming capabilities
> - `moku.exceptions.StreamException` - Exception handling for streaming operations
> - `json` - JSON parsing for stream data

# Classes

## Datalogger

Multi-functional instrument combining data logging and waveform generation capabilities. Supports both file-based logging and real-time streaming of voltage data across multiple channels.

**Key Methods:**

### Initialization & Configuration
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument, **kwargs)` - Initialize the Datalogger instrument
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in multi-instrument mode
- `save_settings(filename)` - Save instrument configuration to `.mokuconf` file
- `load_settings(filename)` - Load configuration from `.mokuconf` file

### Input Configuration
- `set_frontend(channel, impedance, coupling, range, strict=True)` - Configure input channel parameters
- `get_frontend(channel)` - Retrieve current frontend configuration
- `enable_input(channel, enable=True, strict=True)` - Enable or disable input channel
- `disable_channel(channel, disable=True, strict=True)` - **Deprecated**: Use `enable_input` instead

### Acquisition Settings
- `set_acquisition_mode(mode='Normal', strict=True)` - Set acquisition mode (Normal, Precision, DeepMemory, PeakDetect)
- `get_acquisition_mode()` - Get current acquisition mode
- `set_samplerate(sample_rate, strict=True)` - Set sampling rate (10 Hz to 1 MHz)
- `get_samplerate()` - Get current sampling rate

### Logging Operations
- `start_logging(duration=60, delay=0, file_name_prefix='', comments='', trigger_source=None, trigger_level=None, strict=True, sample_rate=None)` - Start logging session
- `stop_logging()` - Stop active logging session
- `logging_progress()` - Check progress of current logging session
- `summary()` - Get logging session summary

### Waveform Generation
- `generate_waveform(channel, type, amplitude=1, frequency=10000, offset=0, phase=0, duty=None, symmetry=None, dc_level=None, edge_time=None, pulse_width=None, strict=True)` - Generate output waveforms (Sine, Square, Ramp, Pulse, Noise, DC)
- `sync_output_phase()` - Synchronize phase of output channels

### Output Configuration
- `set_output_termination(channel, termination, strict=True)` - Set output termination (HiZ or 50Ohm)
- `get_output_termination(channel)` - Get current output termination
- `set_output_load(channel, load, strict=True)` - **Deprecated**: Use `set_output_termination` instead
- `get_output_load(channel)` - **Deprecated**: Use `get_output_termination` instead

### Streaming Operations
- `start_streaming(duration=None, sample_rate=None, trigger_source=None, trigger_level=None)` - Start real-time data streaming
- `stop_streaming()` - Stop active streaming session
- `get_chunk()` - Retrieve next raw data chunk from stream
- `get_stream_status()` - Get current streaming status

```python
class Datalogger(MultiInstrumentSlottable, Moku, StreamInstrument):
    INSTRUMENT_ID = 7
    OPERATION_GROUP = "datalogger"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - Supports both standalone and multi-instrument modes via slot parameter
> - All setter methods include a `strict` parameter to disable implicit conversions
> - Channel numbering varies by model (ChannelA/B/C/D or Input1/2/3/4)
> - Operations use POST/GET requests to device API endpoints

> [!warning] Important
> - When using `start_logging()`, it is recommended **not** to relinquish ownership of the device until the logging session is completed
> - Streaming uses `stream_id` to track active sessions
> - The `get_chunk()` method may raise `StreamException` if streaming fails or encounters errors

> [!example] Frontend Configuration
> Input range options: `100mVpp`, `400mVpp`, `1Vpp`, `2Vpp`, `4Vpp`, `10Vpp`, `40Vpp`, `50Vpp`
>
> Input impedance: `1MOhm` or `50Ohm`
>
> Input coupling: `AC` or `DC`

> [!example] Waveform Types
> Supported waveform types: `Off`, `Sine`, `Square`, `Ramp`, `Pulse`, `Noise`, `DC`
>
> Frequency range: 1 mHz to 20 MHz
>
> Amplitude range: 4 mV to 10 V peak-to-peak

# Functions

This module contains only a class definition and no top-level functions.

# See Also

- `moku.Moku` - Base instrument class
- `moku.instruments._stream.StreamInstrument` - Streaming functionality
- `moku.MultiInstrumentSlottable` - Multi-instrument mode support
- Liquid Instruments API Documentation: https://apis.liquidinstruments.com/reference/datalogger
