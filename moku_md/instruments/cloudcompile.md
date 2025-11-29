---
publish: "true"
type: reference
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_cloudcompile.py
title: CloudCompile
tags: [moku, api, instrument, fpga, custom]
---

# Overview

This module implements the CloudCompile instrument class, which provides support for custom user-defined instruments created through Moku's cloud compilation service. The instrument loads custom bitstream packages (tar/tar.gz files) and provides a generic interface for controlling custom hardware implementations.

> [!info] Key Dependencies
> - `tarfile` - For extracting bitstream packages
> - `tempfile` - For temporary extraction of bitstream files
> - `pathlib.Path` - For file path handling
> - `moku.Moku` - Base Moku instrument class
> - `moku.MultiInstrumentSlottable` - Support for multi-instrument mode
> - `moku.exceptions` - Custom exception types

# Classes

## CloudCompile

A custom instrument interface that loads and controls user-defined FPGA bitstreams created through Moku's cloud compilation service.

**Key Methods:**
- `__init__(ip, serial, force_connect, ignore_busy, persist_state, bitstream, connect_timeout, read_timeout, slot, multi_instrument, **kwargs)` - Initializes the instrument with a bitstream package
- `for_slot(slot, multi_instrument, **kwargs)` - Class method for multi-instrument mode configuration
- `save_settings(filename)` - Saves current instrument settings to a .mokuconf file
- `load_settings(filename)` - Loads settings from a .mokuconf file
- `set_control(idx, value, strict)` - Sets a single control register value
- `set_controls(controls, strict)` - Sets multiple control registers at once
- `get_control(idx, strict)` - Reads a single control register value
- `get_controls()` - Reads all control registers
- `set_interpolation(channel, enable, strict)` - Enables/disables interpolation on a channel
- `get_interpolation(channel)` - Gets interpolation state for a channel
- `sync(mask, strict)` - Synchronization operation with mask parameter
- `summary()` - Returns instrument summary information

```python
class CloudCompile(MultiInstrumentSlottable, Moku):
    INSTRUMENT_ID = 255
    OPERATION_GROUP = "cloudcompile"

    def __init__(self, ip=None, serial=None, force_connect=False,
                 ignore_busy=False, persist_state=False, bitstream=None,
                 connect_timeout=15, read_timeout=30, slot=None,
                 multi_instrument=None, **kwargs):
        ...
```

> [!note] Implementation Notes
> - The `bitstream` parameter is **required** and must be a path to a valid tar or tar.gz file
> - The bitstream package is extracted to a temporary directory during initialization
> - Inherits from both `MultiInstrumentSlottable` and `Moku` to support standalone and multi-instrument modes
> - Uses INSTRUMENT_ID 255, which is reserved for custom cloud-compiled instruments
> - The control interface provides generic register access (idx-based) since custom instruments can have arbitrary control schemes

> [!warning] Important
> - The bitstream file must exist at the specified path or initialization will fail with `FileNotFoundError`
> - If the bitstream package is invalid, a `MokuException` is raised with guidance to check the package
> - The `strict` parameter (default True) disables implicit type conversions when set
> - Settings files must have `.mokuconf` extension for compatibility with Moku tools

# Functions

This module contains only the CloudCompile class and no standalone functions.

# See Also

- `moku.Moku` - Base instrument class
- `moku.MultiInstrumentSlottable` - Multi-instrument support mixin
- `moku.exceptions.MokuException` - Exception handling
- `moku.exceptions.NoInstrumentBitstream` - Bitstream loading errors
- [Moku Cloud Compile Documentation](https://apis.liquidinstruments.com/cloudcompile.html)
- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/instruments/cloudcompile)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/instruments/cloudcompile.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/instruments/cloudcompile.md)
