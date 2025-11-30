---
publish: "true"
type: reference
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/__init__.py
title: moku
tags:
  - moku
  - api
  - core
created: 2025-11-25
modified: 2025-11-29 17:23:01
accessed: 2025-11-29 17:19:07
---

# Overview
@Claude: What do you think about utilizing these (formerly) '__init__' files and turn them into 'README.md's (either figuritavely or literally). 

@Claude: What do you think about 'anonymizing' the path_to_py frontmatter so that it is relative to the pip module (natural). 


This is the main initialization module for the Moku Python package. It provides the core classes and functionality for connecting to and controlling Liquid Instruments Moku devices. The module handles device connection, ownership management, bitstream deployment, and provides a base class for all instruments.

> [!info] Key Dependencies
> - **RequestSession** (moku.session) - Handles HTTP communication with Moku devices
> - **mokucli** - External command-line utility for bitstream management (required)
> - **exceptions** (moku.exceptions) - Custom exception types for error handling
> - **utilities** - Helper functions for version checking, configuration, and bitstream paths
> - **logging** - Module-level logging support
> - **json, tarfile, subprocess, pathlib** - Standard library utilities for file and process management

> [!note] Environment Variables
> - **MOKU_CLI_PATH** - Override path to mokucli executable
> - **MOKU_DATA_PATH** - Override default data path for bitstreams and configuration

# Classes

## MultiInstrumentSlottable

A mixin class that handles common instrument initialization patterns for multi-instrument capable devices.

**Key Methods:**
- `_init_instrument(ip=None, serial=None, force_connect=False, ignore_busy=False, persist_state=False, connect_timeout=15, read_timeout=30, slot=None, multi_instrument=None, bs_path=None, **kwargs)` - Common initialization logic for all instruments

```python
class MultiInstrumentSlottable:
    """Mixin to handle common instrument initialization pattern for multi-instrument capable devices.

    Must mix in to a class that also extends Moku in order to get bitstream upload implementation.
    """

    INSTRUMENT_ID = None
    OPERATION_GROUP = None
```

> [!note] Implementation Notes
> - Subclasses must define `INSTRUMENT_ID` and `OPERATION_GROUP` class attributes
> - Supports both standalone mode (single instrument) and multi-instrument mode (multiple slots)
> - In standalone mode, always uses slot 1
> - Handles automatic bitstream upload based on instrument ID and slot number
> - Supports custom bitstream paths via `bs_path` parameter

## Moku

The base class for all Moku devices. Handles connection management, ownership claiming, bitstream deployment, and provides methods for device configuration and control.

**Key Methods:**
- `__init__(ip, force_connect=False, ignore_busy=False, persist_state=False, connect_timeout=15, read_timeout=30, **kwargs)` - Initialize connection to a Moku device
- `claim_ownership(force_connect=True, ignore_busy=False, persist_state=False)` - Claim exclusive ownership of the device
- `relinquish_ownership()` - Release ownership of the device
- `upload_bitstream(name, bs_path=None)` - Upload instrument bitstream to device
- `platform(platform_id)` - Configure platform for multi-instrument operation
- `set_connect_timeout(value)` - Set connection timeout for requests
- `set_read_timeout(value)` - Set read timeout for requests
- `__enter__()` / `__exit__()` - Context manager support for automatic cleanup

```python
class Moku:
    """
    Moku base class. This class does all the heavy lifting required to
    deploy and control instruments.
    """

    def __init__(
        self,
        ip,
        force_connect=False,
        ignore_busy=False,
        persist_state=False,
        connect_timeout=15,
        read_timeout=30,
        **kwargs,
    ) -> None:
        ...
```

> [!warning] Version Compatibility
> The module enforces strict version compatibility between:
> - MokuOS version running on the device
> - Python package version
> - mokucli utility version
>
> Mismatches will raise `IncompatibleMokuException` or `IncompatiblePackageException`

**Device Information Methods:**
- `name()` - Get device name
- `serial_number()` - Get device serial number
- `summary()` - Get device summary
- `describe()` - Get detailed device description
- `calibration_date()` - Get last calibration date
- `mokuos_version()` - Get MokuOS version
- `firmware_version()` - Deprecated, use `mokuos_version()` instead

**Power Supply Methods:**
- `get_power_supplies()` - Get all power supply states
- `get_power_supply(id)` - Get specific power supply state
- `set_power_supply(id, enable=True, voltage=3, current=0.1)` - Configure power supply

**Clock Configuration Methods:**
- `get_external_clock()` - Get external clock configuration
- `set_external_clock(enable=True)` - Enable/disable external reference clock
- `get_blended_clock()` - Get blended clock configuration
- `set_blended_clock(freq_ref_enable=None, freq_ref_frequency=None, sync_ref_enable=None, sync_ref_source=None, strict=True)` - Configure blended clock with external frequency and sync references

**File Management Methods:**
- `upload(target, file_name, data)` - Upload files to device (bitstreams, ssd, logs, persist, media)
- `download(target, file_name, local_path)` - Download files from device
- `delete(target, file_name)` - Delete files from device
- `list(target)` - List files in target directory

**Advanced Configuration Methods:**
- `modify_hardware(data=None)` - Raw access to hardware state (use with caution)
- `modify_calibration(data=None)` - Query or update calibration coefficients
- `set_configuration(data=None)` - Update device/network configuration
- `get_configuration()` - Retrieve device/network configuration

**Power Management Methods:**
- `shutdown()` - Shutdown the device
- `reboot()` - Reboot the device

> [!note] Context Manager Support
> The Moku class supports Python's context manager protocol (`with` statement), automatically relinquishing ownership when exiting the context. This ensures proper cleanup even if exceptions occur.

> [!warning] Bitstream Management
> Bitstreams are automatically managed by default. If a required bitstream is not present on the device or has a checksum mismatch, it will be uploaded from the local data path. Ensure mokucli is properly installed and bitstreams are downloaded using `mokucli instrument download`.

# Functions

This module does not define standalone functions. All functionality is encapsulated in the `Moku` and `MultiInstrumentSlottable` classes.

# Module-Level Configuration

The module performs initialization at import time:

```python
# Locate mokucli executable
MOKU_CLI_PATH = environ.get("MOKU_CLI_PATH", which("mokucli"))

# Determine data path for bitstreams
MOKU_DATA_PATH = environ.get("MOKU_DATA_PATH") or
                 Path(mokucli_output).parent.joinpath("data")
```

> [!warning] mokucli Requirement
> If mokucli cannot be found in PATH or via MOKU_CLI_PATH environment variable, a warning is issued. The package may not function correctly without mokucli, particularly for bitstream operations.

# See Also

- **moku.session** - RequestSession class for HTTP communication
- **moku.exceptions** - Custom exception classes
- **moku.utilities** - Helper functions for configuration and version checking
- **moku.logging** - Logging configuration
- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/__init__)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/__init__.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/__init__.md)
