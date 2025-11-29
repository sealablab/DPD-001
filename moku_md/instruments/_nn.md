---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_nn.py
title: NeuralNetwork
---

# Overview

The Neural Network instrument enables running feed-forward, multi-layer neural networks on serial and parallel input signals. This instrument can only operate in multi-instrument mode and provides functionality for configuring inputs/outputs, uploading neural network models in .linn JSON format, and managing network inference settings.

> [!info] Key Dependencies
> - `json` - For parsing .linn neural network configuration files
> - `pathlib.Path` - For file path handling
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Multi-instrument slot support
> - `moku.exceptions` - Custom exception handling

# Classes

## NeuralNetwork

Multi-instrument capable neural network inference engine for real-time signal processing.

**Key Methods:**
- `__init__(multi_instrument, slot=None, **kwargs)` - Constructor (requires multi-instrument mode)
- `for_slot(slot, multi_instrument)` - Class method to configure instrument at specific slot
- `save_settings(filename)` - Save instrument configuration to .mokuconf file
- `load_settings(filename)` - Load previously saved .mokuconf configuration
- `set_input_sample_rate(sample_rate, strict=True)` - Configure input sampling rate
- `set_input(channel, low_level, high_level, strict=True)` - Set voltage range for input channel
- `set_output(channel, enabled, low_level=None, high_level=None, strict=True)` - Configure output channel range
- `upload_network(linn)` - Upload neural network model in .linn JSON format
- `describe_network()` - Get description of currently loaded network
- `summary()` - Get instrument summary information
- `set_defaults()` - Reset to default settings

```python
class NeuralNetwork(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 128
    OPERATION_GROUP = "neuralnetwork"

    def __init__(self, multi_instrument, slot=None, **kwargs):
        # Neural Network can only run in multi-instrument mode
        if multi_instrument is None:
            raise MokuException(...)
```

> [!warning] Multi-Instrument Only
> The Neural Network instrument can ONLY be run in multi-instrument mode. Attempting to instantiate it without a multi_instrument parameter will raise a MokuException.

> [!note] Implementation Notes
> - The constructor has a different parameter order than other instruments for backwards compatibility
> - Uses `multi_instrument` as the first positional argument
> - All operations are performed via the session API using slot-based routing: `slot{self.slot}/{self.operation_group}`

# Methods

## save_settings

```python
def save_settings(self, filename):
    """
    Save instrument settings to a file. The file name should have
    a `.mokuconf` extension to be compatible with other tools.

    :type filename: FileDescriptorOrPath
    :param filename: The path to save the `.mokuconf` file to.
    """
```

Saves the current instrument configuration to a .mokuconf file for later restoration or use with desktop applications.

## load_settings

```python
def load_settings(self, filename):
    """
    Load a previously saved `.mokuconf` settings file into the instrument.
    To create a `.mokuconf` file, either use `save_settings` or the desktop app.

    :type filename: FileDescriptorOrPath
    :param filename: The path to the `.mokuconf` configuration to load
    """
```

Restores instrument settings from a previously saved .mokuconf file.

## set_input_sample_rate

```python
def set_input_sample_rate(self, sample_rate, strict=True):
    """Set the input samplerate"""
```

Configures the sampling rate for input signals.

**Parameters:**
- `sample_rate` (number) - Input sample rate in Hz
- `strict` (boolean) - Disable all implicit conversions and coercions (default: True)

## set_input

```python
def set_input(self, channel, low_level, high_level, strict=True):
    """Set the voltage range for a given input"""
```

Configures the voltage range for a specific input channel.

**Parameters:**
- `channel` (integer) - Target input channel number
- `low_level` (number) - Minimum voltage level
- `high_level` (number) - Maximum voltage level
- `strict` (boolean) - Disable implicit conversions (default: True)

## set_output

```python
def set_output(self, channel, enabled, low_level=None, high_level=None, strict=True):
    """Set the output range for a given output"""
```

Configures a specific output channel including enable state and voltage range.

**Parameters:**
- `channel` (integer) - Target output channel number
- `enabled` (boolean) - Enable or disable the output channel
- `low_level` (number, optional) - Minimum voltage level
- `high_level` (number, optional) - Maximum voltage level
- `strict` (boolean) - Disable implicit conversions (default: True)

## upload_network

```python
def upload_network(self, linn):
    """Upload a neural network in .linn JSON format."""
```

Uploads a neural network model to the instrument for inference.

**Parameters:**
- `linn` (dict or path) - Either a dictionary containing linn data or absolute path to a .linn file

**Returns:** Response from the upload operation

> [!note] File Format
> The .linn format is a JSON-based neural network specification. The method accepts either a pre-loaded dictionary or a file path string. If a path is provided, it validates the file exists before loading.

## describe_network

```python
def describe_network():
    """Provide a description of the currently loaded network"""
```

Returns information about the neural network model currently loaded on the instrument.

**Returns:** Description of the loaded network structure and configuration

## set_defaults

```python
def set_defaults():
    """Set the Neural Network to sane defaults"""
```

Resets the instrument to default configuration settings.

## summary

```python
def summary():
    """summary."""
```

Retrieves current instrument status and configuration summary.

**Returns:** Dictionary containing instrument state information

# See Also

- `moku.Moku` - Base instrument class
- `moku.MultiInstrumentSlottable` - Multi-instrument slot management
- `moku.exceptions.MokuException` - Exception handling
- `moku.exceptions.InvalidParameterException` - Parameter validation errors
