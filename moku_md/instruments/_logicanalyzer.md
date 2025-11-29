---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_logicanalyzer.py
title: LogicAnalyzer
---

# Overview

The LogicAnalyzer module provides a high-level interface for controlling Moku's Logic Analyzer instrument. This instrument allows digital signal analysis, pattern generation, protocol decoding (UART, SPI, I2C, I2S, CAN), and triggering capabilities across multiple digital pins.

> [!info] Key Dependencies
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Enables multi-instrument mode support

# Classes

## LogicAnalyzer

Logic Analyzer instrument object for digital signal analysis and pattern generation.

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, connect_timeout, read_timeout, slot, multi_instrument)` - Initialize the Logic Analyzer instrument
- `for_slot(slot, multi_instrument)` - Class method to configure instrument in multi-instrument mode
- `set_source(source, strict)` - Set input source ('DigitalIO', 'AnalogInputs', 'SlotInput')
- `set_pin_mode(pin, state, strict)` - Configure individual pin mode ('X', 'I', 'PG1', 'PG2')
- `set_analog_mode(high, low, strict)` - Set high/low thresholds for analog inputs
- `set_pattern_generator(channel, patterns, overrides, baud_rate, divider, tick_count, repeat, iterations, strict)` - Configure pattern generator
- `set_trigger(pins, sources, advanced, mode, combination, nth_event, holdoff, strict)` - Configure trigger settings
- `set_timebase(t1, t2, roll_mode, strict)` - Set time window around trigger point
- `get_data(timeout, wait_reacquire, wait_complete, include_pins, measurements)` - Retrieve captured logic analyzer data
- `set_uart_decoder(channel, data_bit, lsb_first, data_width, uart_stop_width, uart_parity, uart_baud_rate, strict)` - Configure UART protocol decoder
- `set_spi_decoder(channel, data_bit, lsb_first, data_width, clock_bit, spi_cs, spi_cpol, spi_cpha, strict)` - Configure SPI protocol decoder
- `set_i2c_decoder(channel, data_bit, clock_bit, strict)` - Configure I2C protocol decoder
- `set_i2s_decoder(channel, clock_bit, word_select, data_bit, lsb_first, offset, data_width, strict)` - Configure I2S protocol decoder
- `set_can_decoder(channel, data_bit, baud_rate, lsb_first, strict)` - Configure CAN protocol decoder
- `set_parallel_bus_decoder(channel, sample_mode, data_width, clock_bit, strict)` - Configure parallel bus decoder
- `save_settings(filename)` - Save instrument settings to .mokuconf file
- `load_settings(filename)` - Load settings from .mokuconf file

```python
class LogicAnalyzer(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 17
    OPERATION_GROUP = "logicanalyzer"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False,
                 connect_timeout=15, read_timeout=30,
                 slot=None, multi_instrument=None, **kwargs):
        ...
```

> [!note] Pin States
> Available pin states:
> - **X** - Off, Pin is disabled
> - **I** - Input mode
> - **PG1** - Pattern Generator 1
> - **PG2** - Pattern Generator 2
>
> Pin overrides (for pattern generators):
> - **X** - Override disabled
> - **H** - High (pin set to 1)
> - **L** - Low (pin set to 0)

> [!note] Implementation Notes
> - The class inherits from both `MultiInstrumentSlottable` and `Moku`, enabling both standalone and multi-instrument operation modes
> - All configuration methods support a `strict` parameter to disable implicit conversions
> - The instrument operates through a session-based API with slot-based routing
> - Several deprecated methods exist (marked with `.. deprecated:: 3.1.1`): `set_pin()`, `get_pin()`, `set_pins()`, `get_pins()`, and generic `set_decoder()` have been replaced with more specific alternatives

# Key Methods Detail

## Configuration Methods

### set_source

```python
def set_source(source, strict=True):
    """Configure the input source for the Logic Analyzer"""
```

**Parameters:**
- `source` - Input source: 'DigitalIO', 'AnalogInputs', or 'SlotInput'
- `strict` - Disable implicit conversions (default: True)

### set_pin_mode

```python
def set_pin_mode(pin, state, strict=True):
    """Configure the mode for a specific pin"""
```

**Parameters:**
- `pin` - Target pin number (integer)
- `state` - Pin state: 'X' (off), 'I' (input), 'PG1', or 'PG2'
- `strict` - Disable implicit conversions (default: True)

### set_analog_mode

```python
def set_analog_mode(high=1.25, low=0.75, strict=True):
    """Set voltage thresholds for analog input interpretation"""
```

**Parameters:**
- `high` - High threshold voltage (default: 1.25V)
- `low` - Low threshold voltage (default: 0.75V)
- `strict` - Disable implicit conversions (default: True)

## Pattern Generation

### set_pattern_generator

```python
def set_pattern_generator(channel, patterns, overrides=None, baud_rate=None,
                         divider=None, tick_count=8, repeat=True,
                         iterations=1, strict=True):
    """Configure pattern generator for digital signal output"""
```

**Parameters:**
- `channel` - Target pattern generator channel (1 or 2)
- `patterns` - List of pin/bit to pattern mappings
- `overrides` - Optional list of pin/bit to override mappings
- `baud_rate` - Baud rate for pattern output
- `divider` - Frequency divider (1 to 1e6), scales 125 MHz base frequency
- `tick_count` - Number of ticks per pattern
- `repeat` - Repeat pattern forever (default: True)
- `iterations` - Number of iterations when repeat=False (1-8192)
- `strict` - Disable implicit conversions (default: True)

> [!note] Pattern Generator Notes
> The base frequency is 125 MHz. Use the `divider` parameter to scale down to desired tick frequency. For example, divider=2 provides 62.5 MHz tick frequency.

## Triggering

### set_trigger

```python
def set_trigger(pins=None, sources=None, advanced=False, mode="Auto",
                combination="AND", nth_event=1, holdoff=0, strict=True):
    """Configure trigger conditions for data acquisition"""
```

**Parameters:**
- `pins` - Map of pin and edge trigger configurations
- `sources` - Map of pin/bit and edge trigger configurations
- `advanced` - Enable advanced triggering mode (default: False)
- `mode` - Trigger mode: 'Auto' or 'Normal'
- `combination` - Trigger combination: 'AND' or 'OR'
- `nth_event` - Number of trigger events to wait for (0-65535, default: 1)
- `holdoff` - Duration to hold off trigger post-event (1e-9 to 10 seconds)
- `strict` - Disable implicit conversions (default: True)

## Data Acquisition

### get_data

```python
def get_data(timeout=60, wait_reacquire=False, wait_complete=False,
             include_pins=None, measurements=False):
    """Retrieve captured logic analyzer data"""
```

**Parameters:**
- `timeout` - Wait timeout in seconds (default: 60)
- `wait_reacquire` - Wait until new dataframe is acquired (default: False)
- `wait_complete` - Wait until entire frame is available (default: False)
- `include_pins` - Optional list to filter result by specific pins
- `measurements` - Include measurements for each pin (default: False)

**Returns:** Data frame with digital signal captures

> [!warning] Important
> Default timeout for reading data is 10 seconds. This can be increased by setting the `read_timeout` property of the session object:
> ```python
> i.session.read_timeout = 100  # in seconds
> ```

### set_timebase

```python
def set_timebase(t1, t2, roll_mode=None, strict=True):
    """Configure the time window around trigger point"""
```

**Parameters:**
- `t1` - Time from trigger point to left of screen (can be negative)
- `t2` - Time from trigger point to right of screen (must be positive)
- `roll_mode` - Enable roll mode (optional)
- `strict` - Disable implicit conversions (default: True)

## Protocol Decoders

### set_uart_decoder

```python
def set_uart_decoder(channel, data_bit, lsb_first=True, data_width=8,
                     uart_stop_width=1, uart_parity="None",
                     uart_baud_rate=9600, strict=True):
    """Configure UART protocol decoder"""
```

**Parameters:**
- `channel` - Target decoder channel
- `data_bit` - Bit index for data line (0-15)
- `lsb_first` - Bit order, LSB first (default: True)
- `data_width` - Number of data bits: 5-9 (default: 8)
- `uart_stop_width` - Number of stop bits: 1-2 (default: 1)
- `uart_parity` - Parity: 'None', 'Even', or 'Odd'
- `uart_baud_rate` - Baud rate (default: 9600)
- `strict` - Disable implicit conversions (default: True)

### set_spi_decoder

```python
def set_spi_decoder(channel, data_bit, lsb_first=False, data_width=8,
                    clock_bit=None, spi_cs=None, spi_cpol=0,
                    spi_cpha=0, strict=True):
    """Configure SPI protocol decoder"""
```

**Parameters:**
- `channel` - Target decoder channel
- `data_bit` - Bit index for data line (1-16)
- `lsb_first` - Bit order, LSB first (default: False, i.e., MSB first)
- `data_width` - Number of data bits: 5-9 (default: 8)
- `clock_bit` - Bit index for clock signal (1-16)
- `spi_cs` - Chip select bit index (1-16)
- `spi_cpol` - Clock polarity: 0 (low) or 1 (high)
- `spi_cpha` - Clock phase: 0 (leading edge) or 1 (trailing edge)
- `strict` - Disable implicit conversions (default: True)

### set_i2c_decoder

```python
def set_i2c_decoder(channel, data_bit, clock_bit, strict=True):
    """Configure I2C protocol decoder"""
```

**Parameters:**
- `channel` - Target decoder channel
- `data_bit` - Bit index for data line (SDA) (0-15)
- `clock_bit` - Bit index for clock signal (SCL) (0-15)
- `strict` - Disable implicit conversions (default: True)

### set_i2s_decoder

```python
def set_i2s_decoder(channel, clock_bit, word_select, data_bit,
                    lsb_first=True, offset=1, data_width=8, strict=True):
    """Configure I2S protocol decoder"""
```

**Parameters:**
- `channel` - Target decoder channel
- `clock_bit` - Bit index for clock signal (0-15)
- `word_select` - Bit index for word select signal (0-15)
- `data_bit` - Bit index for data line (0-15)
- `lsb_first` - Bit order (default: True)
- `offset` - Right shift offset: 0-1 (default: 1)
- `data_width` - Number of data bits: 5-9 (default: 8)
- `strict` - Disable implicit conversions (default: True)

### set_can_decoder

```python
def set_can_decoder(channel, data_bit, baud_rate=500000,
                    lsb_first=False, strict=True):
    """Configure CAN protocol decoder"""
```

**Parameters:**
- `channel` - Target decoder channel
- `data_bit` - Bit index for receive (Rx) signal (1-16)
- `baud_rate` - Baud rate (default: 500000)
- `lsb_first` - Bit order (default: False, i.e., MSB first)
- `strict` - Disable implicit conversions (default: True)

### set_parallel_bus_decoder

```python
def set_parallel_bus_decoder(channel, sample_mode, data_width,
                             clock_bit, strict=True):
    """Configure parallel bus decoder"""
```

**Parameters:**
- `channel` - Target decoder channel
- `sample_mode` - Sample mode: "Rising", "Falling", or "Both"
- `data_width` - Number of data bits
- `clock_bit` - Clock bit index
- `strict` - Disable implicit conversions (default: True)

## Settings Management

### save_settings

```python
def save_settings(filename):
    """Save instrument settings to a .mokuconf file"""
```

**Parameters:**
- `filename` - Path to save the .mokuconf file

### load_settings

```python
def load_settings(filename):
    """Load previously saved .mokuconf settings file"""
```

**Parameters:**
- `filename` - Path to the .mokuconf configuration file to load

## Deprecated Methods

> [!warning] Deprecated Methods
> The following methods are deprecated as of version 3.1.1 and should not be used in new code:
> - `set_pin()` - Use `set_pin_mode()` instead
> - `get_pin()` - Use `get_pin_mode()` instead
> - `set_pins()` - Use `set_pin_mode()` for each pin instead
> - `get_pins()` - Use `get_pin_mode()` instead
> - `set_decoder()` - Use specific decoder methods: `set_uart_decoder()`, `set_spi_decoder()`, `set_i2c_decoder()`, etc.

# See Also

- [Moku Logic Analyzer API Documentation](https://apis.liquidinstruments.com/reference/logicanalyzer)
- Related modules: `moku.Moku`, `moku.MultiInstrumentSlottable`
