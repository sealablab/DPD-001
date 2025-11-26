---
publish: "true"
type: reference
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_mim.py
title: MultiInstrument
tags: [moku, api, instrument, multi-instrument, platform]
---

# Overview

This module implements the Multi-Instrument Mode (MIM) for Moku devices, allowing multiple instruments to run simultaneously on a single Moku platform. The `MultiInstrument` class extends the base `Moku` class to provide slot-based instrument management and inter-instrument connectivity.

> [!info] Key Dependencies
> - `moku.Moku` - Base class for Moku device interaction
> - `moku.exceptions.MokuException` - Exception handling for Moku operations
> - `moku.utilities.find_moku_by_serial` - Device discovery by serial number
> - `moku.instruments` - Available instrument types for slot assignment
> - `inspect` - Runtime introspection for validating instrument classes

# Classes

## MultiInstrument

Multi-Instrument Mode controller for Moku platforms. This class manages multiple instruments running in separate slots on a single Moku device.

**Key Methods:**
- `__init__(ip, serial, platform_id, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, **kwargs)` - Initialize Multi-Instrument Mode with platform configuration
- `set_instrument(slot, instrument, **kwargs) -> instrument` - Load and configure an instrument in a specific slot
- `save_configuration(filename)` - Save current MIM configuration to a .mokuconf file
- `load_configuration(filename)` - Load MIM configuration from a .mokuconf file
- `set_connections(connections)` - Configure signal routing between instruments and I/O
- `set_frontend(channel, impedance, coupling, attenuation, gain, strict)` - Configure input channel frontend settings
- `set_output(channel, output_gain, strict)` - Configure output channel settings
- `set_dio(direction, direction_map, strict)` - Configure digital I/O port directions
- `sync()` - Synchronize instrument states
- `get_connections()` - Retrieve current signal routing configuration
- `get_instruments()` - List all instruments loaded in slots
- `get_frontend(channel)` - Get current frontend configuration for a channel
- `get_output(channel)` - Get current output configuration for a channel
- `get_dio(port)` - Get digital I/O port configuration

```python
class MultiInstrument(Moku):
    def __init__(
        self,
        ip=None,
        serial=None,
        platform_id=None,
        force_connect=False,
        ignore_busy=False,
        persist_state=False,
        connect_timeout=15,
        read_timeout=30,
        **kwargs,
    ):
        ...
```

> [!warning] Important
> The `platform_id` parameter is required and cannot be empty. It defines the number of available instrument slots. Either `ip` or `serial` must be provided to identify the target Moku device.

> [!note] Implementation Notes
> - The operation group is set to "mim" for all API calls
> - Empty slots are automatically filled with placeholder bitstreams when setting an instrument
> - Configuration files use the `.mokuconf` extension
> - Slot numbers are 1-indexed and must be within the range [1, platform_id]

# Methods

## set_instrument

```python
def set_instrument(slot, instrument, **kwargs):
    """Load an instrument into a specific slot"""
```

Assigns an instrument class to a specific slot on the multi-instrument platform. Validates that the slot number is within the platform's capacity and that the instrument is a valid type.

**Parameters:**
- `slot` - Integer slot number (1-indexed, must be <= platform_id)
- `instrument` - Instrument class from the moku.instruments module
- `**kwargs` - Additional configuration parameters passed to the instrument

**Returns:** Configured instrument instance for the specified slot

> [!warning] Slot Validation
> Raises an exception if the slot number is invalid for the platform or if the instrument type is not recognized. Empty slots are automatically populated with placeholder bitstreams.

## save_configuration

```python
def save_configuration(filename):
    """Save Multi-Instrument Mode configuration to file"""
```

Writes the current MIM configuration to a `.mokuconf` file. This saves the multi-instrument platform settings but does not include individual instrument configurations.

**Parameters:**
- `filename` - Path to save the configuration file (should have .mokuconf extension)

> [!note] Configuration Scope
> This method only saves MIM-level configuration. Each instrument must be saved individually using its own save method.

## load_configuration

```python
def load_configuration(filename):
    """Load a Multi-Instrument Mode configuration from file"""
```

Loads a previously saved `.mokuconf` configuration file to restore MIM settings.

**Parameters:**
- `filename` - Path to the .mokuconf configuration file to load

## set_connections

```python
def set_connections(connections):
    """Configure signal routing between slots and I/O"""
```

Establishes connections between instrument slots and physical I/O channels, enabling signal routing within the multi-instrument platform.

**Parameters:**
- `connections` - List of connection mappings specifying source and destination points

## set_frontend

```python
def set_frontend(channel, impedance, coupling, attenuation=None, gain=None, strict=True):
    """Configure input channel frontend parameters"""
```

Sets the frontend configuration for an input channel, including impedance, coupling, and attenuation.

**Parameters:**
- `channel` - Integer channel number to configure
- `impedance` - Input impedance ('1MOhm' or '50Ohm')
- `coupling` - Input coupling mode ('AC' or 'DC')
- `attenuation` - Optional attenuation level ('-20dB', '0dB', '14dB', '20dB', '32dB', '40dB')
- `gain` - Optional gain setting
- `strict` - Boolean to disable implicit conversions (default: True)

## set_output

```python
def set_output(channel, output_gain, strict=True):
    """Configure output channel settings"""
```

Sets the output configuration for a channel.

**Parameters:**
- `channel` - Integer channel number to configure
- `output_gain` - Output gain level ('0dB' or '14dB')
- `strict` - Boolean to disable implicit conversions (default: True)

## set_dio

```python
def set_dio(direction=None, direction_map=None, strict=True):
    """Configure digital I/O port directions"""
```

Configures the direction (input/output) for digital I/O ports.

**Parameters:**
- `direction` - List of DIO directions (0 for input, 1 for output); defaults to all inputs
- `direction_map` - Alternative list-based mapping of DIO directions
- `strict` - Boolean to disable implicit conversions (default: True)

## get_connections

```python
def get_connections():
    """Retrieve current signal routing configuration"""
```

Returns the current connection mappings between instrument slots and I/O channels.

**Returns:** Connection configuration data

## get_instruments

```python
def get_instruments():
    """List all instruments loaded in slots"""
```

Returns a list of instruments currently loaded in each slot.

**Returns:** List of instrument names or empty strings for empty slots

## get_frontend

```python
def get_frontend(channel):
    """Get frontend configuration for a channel"""
```

Retrieves the current frontend settings for a specified input channel.

**Parameters:**
- `channel` - Integer channel number to query

**Returns:** Frontend configuration including impedance, coupling, and attenuation

## get_output

```python
def get_output(channel):
    """Get output configuration for a channel"""
```

Retrieves the current output settings for a specified channel.

**Parameters:**
- `channel` - Integer channel number to query

**Returns:** Output configuration including gain settings

## get_dio

```python
def get_dio(port=None):
    """Get digital I/O port configuration"""
```

Retrieves the configuration for digital I/O ports.

**Parameters:**
- `port` - Optional integer port number to query specific port

**Returns:** DIO port direction configuration

## sync

```python
def sync():
    """Synchronize instrument states"""
```

Synchronizes the state across all instruments in the multi-instrument platform.

**Returns:** Synchronization status

# See Also

- `moku.Moku` - Base class for device interaction
- `moku.instruments` - Available instrument types for slot assignment
- [Moku Multi-Instrument Mode Documentation](https://apis.liquidinstruments.com/multiinstrument.html)
- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/instruments/mim)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/mim.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/instruments/mim.md)
