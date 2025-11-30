---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_tfa.py
title: TimeFrequencyAnalyzer
created: 2025-11-19
modified: 2025-11-29 17:22:29
accessed: 2025-11-29 17:22:29
---

# Overview

The Time-Frequency Analyzer (TFA) instrument measures intervals between configurable start and stop events with sub-nanosecond precision, computes histograms of interval duration losslessly and in real-time, and saves high-resolution event timestamps to a file.

> [!info] Key Dependencies
> - `Moku` - Base class for Moku instruments
> - `MultiInstrumentSlottable` - Mixin for multi-instrument support, enables the instrument to run in a specific slot alongside other instruments

# Classes

## TimeFrequencyAnalyzer

A precision timing instrument that analyzes intervals between events and generates real-time histograms.

**Key Attributes:**
- `INSTRUMENT_ID = 11` - Unique identifier for the TFA instrument
- `OPERATION_GROUP = "tfa"` - API operation group name

**Key Methods:**

### Configuration Methods
- `__init__(ip=None, serial=None, force_connect=False, ignore_busy=False, persist_state=False, connect_timeout=15, read_timeout=30, slot=None, multi_instrument=None, **kwargs)` - Initialize and connect to the instrument
- `for_slot(slot, multi_instrument)` - Class method to create an instance for a specific slot in multi-instrument mode
- `set_defaults()` - Reset instrument to default settings
- `save_settings(filename)` - Save current instrument configuration to a `.mokuconf` file
- `load_settings(filename)` - Load previously saved configuration from a `.mokuconf` file

### Frontend Configuration
- `set_frontend(channel, impedance, coupling, range, strict=True)` - Configure input channel parameters (impedance: '1MOhm'/'50Ohm', coupling: 'AC'/'DC', range: '100mVpp' to '50Vpp')
- `get_frontend(channel)` - Retrieve current frontend configuration for a channel

### Acquisition Configuration
- `set_acquisition_mode(mode='Continuous', gate_source=None, gate_threshold=None, window_length=None, strict=True)` - Set acquisition mode ('Continuous', 'Windowed', or 'Gated')
- `get_acquisition_mode()` - Retrieve current acquisition mode settings
- `set_interpolation(mode='Linear', strict=True)` - Configure interpolation mode ('None' or 'Linear')
- `get_interpolation()` - Retrieve current interpolation settings

### Event Detection
- `set_event_detector(id, source, threshold=0, edge='Rising', holdoff=0.0, strict=True)` - Configure an event detector with source channel, threshold, edge type ('Rising', 'Falling', 'Both'), and holdoff time
- `get_event_detector(id)` - Retrieve configuration of a specific event detector

### Interval Analysis
- `set_interval_analyzer(id, start_event_id, stop_event_id, enable=True, strict=True)` - Configure an interval analyzer to measure time between start and stop events
- `get_interval_analyzer(id)` - Retrieve configuration of a specific interval analyzer
- `set_histogram(start_time, stop_time, strict=True)` - Set histogram time range for interval measurements

### Output Generation
- `generate_output(channel, signal_type, scaling, zero_point=0, output_range=None, invert=False, strict=True)` - Generate output signal based on interval or count data (signal_type: 'Interval'/'Count', output_range: '2Vpp'/'10Vpp')
- `disable_output(channel, strict=True)` - Disable output generation on a specific channel

### Data Logging
- `start_logging(event_ids, duration=60, file_name_prefix='', comments='', delay=0, quantity='EventTimestamp', strict=True)` - Start logging event timestamps to file with configurable duration and delay
- `stop_logging()` - Stop the current logging session
- `logging_progress()` - Check the progress of the current logging session

### Data Acquisition
- `get_data(timeout=60, strict=True)` - Retrieve acquired histogram and interval data (note: default session read_timeout is 10s, can be increased via `session.read_timeout`)
- `clear_data()` - Clear accumulated data buffers
- `summary()` - Get a summary of current instrument state

```python
class TimeFrequencyAnalyzer(MultiInstrumentSlottable, Moku):
    """Measure intervals between configurable start and stop events
    with sub-ns precision, compute histograms of interval duration
    losslessly and in real-time, and save high-resolution event
    timestamps to a file."""

    INSTRUMENT_ID = 11
    OPERATION_GROUP = "tfa"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - All configuration methods accept a `strict` parameter (default `True`) which disables implicit conversions and coercions
> - The instrument uses a slot-based architecture allowing it to run alongside other instruments
> - All operations are performed via HTTP POST/GET requests to the instrument's session endpoint using the pattern `slot{slot}/{operation_group}`
> - Event detectors and interval analyzers are identified by numerical IDs

> [!warning] Important
> - When using `get_data()`, the default timeout for reading data is 10 seconds. For longer acquisition periods, increase the timeout by setting `instrument.session.read_timeout` to a higher value (in seconds)
> - Settings files must have a `.mokuconf` extension to be compatible with other Liquid Instruments tools
> - Channel naming varies by device - options include 'ChannelA/B/C/D', 'Input1/2/3/4', 'Output1/2/3/4', and 'External'

> [!example] Typical Workflow
> 1. Configure input frontends with `set_frontend()`
> 2. Set up event detectors with `set_event_detector()`
> 3. Configure interval analyzers to measure time between events with `set_interval_analyzer()`
> 4. Set histogram range with `set_histogram()`
> 5. Start acquisition and retrieve data with `get_data()`
> 6. Optionally log event timestamps to file with `start_logging()`

# See Also

- [Liquid Instruments TFA API Reference](https://apis.liquidinstruments.com/reference/tfa)
- Related modules: `moku.Moku`, `moku.MultiInstrumentSlottable`
