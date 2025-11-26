---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/utilities.py
title: utilities
---

# Overview

This module provides utility functions for Moku device discovery, CLI version checking, configuration management, and bitstream path resolution. It handles platform-specific configuration directories and version-specific bitstream file locations.

> [!info] Key Dependencies
> - `packaging.specifiers.SpecifierSet` - For version compatibility checking
> - `.exceptions` - Custom exceptions (InvalidParameterRange, MokuException, MokuNotFound, NoInstrumentBitstream)
> - `.finder.Finder` - Device discovery functionality
> - `.version.COMPAT_MOKUCLI` - CLI version compatibility specification
> - `pathlib.Path` - Cross-platform path handling
> - `platform` - OS detection for platform-specific paths

# Functions

## find_moku_by_serial

```python
def find_moku_by_serial(serial):
    """Find a Moku device by its serial number and return its IP address"""
```

Discovers a Moku device on the network using its serial number.

**Parameters:**
- `serial` - The serial number of the Moku device to find

**Returns:** The IPv4 address of the device

> [!warning] Important
> Raises `MokuNotFound` if no device with the specified serial number is found within the 10-second timeout period.

## check_mokucli_version

```python
def check_mokucli_version(cli_path):
    """Verify that the mokucli tool is installed and compatible"""
```

Validates that the mokucli command-line tool is available and meets version requirements.

**Parameters:**
- `cli_path` - Path to the mokucli executable

**Returns:** None (raises exceptions on failure)

> [!warning] Important
> - Raises `MokuException` if mokucli cannot be found at the specified path
> - Raises `InvalidParameterRange` if the installed version is incompatible with the current API
> - Checks version against `COMPAT_MOKUCLI` specifier from the version module
> - Provides instructions for downloading and configuring mokucli via the MOKU_CLI_PATH environment variable

## get_config_dir

```python
def get_config_dir() -> Path:
    """Get the platform-specific configuration directory.

    This path resolution should exactly match the logic in mokucli.

    Corrolary: If you change this, change it in mokucli as well.
    """
```

Returns the appropriate configuration directory based on the operating system.

**Returns:** Path object pointing to the Moku configuration directory

> [!note] Implementation Notes
> - **Windows**: `%APPDATA%\Moku` (or `%USERPROFILE%\Moku` if APPDATA is not set)
> - **macOS**: `~/Library/Application Support/Moku`
> - **Linux/Other**: `$XDG_CONFIG_HOME/moku` (or `~/.config/moku` if XDG_CONFIG_HOME is not set)
> - This logic must remain synchronized with mokucli implementation

## get_version_info

```python
def get_version_info(mokuOS_version):
    """Load version information from JSON file"""
```

Retrieves version-specific configuration data for a given MokuOS version.

**Parameters:**
- `mokuOS_version` - The MokuOS version string to look up

**Returns:** Dictionary containing version information loaded from JSON

> [!warning] Important
> Raises `NoInstrumentBitstream` if the version file does not exist at `{config_dir}/data/versions/{mokuOS_version}.json`

## get_bitstream_path

```python
def get_bitstream_path(mokuOS_version, hardware):
    """Resolve the filesystem path to instrument bitstreams for a specific hardware and OS version"""
```

Constructs the path to instrument bitstream files for a specific hardware platform and MokuOS version.

**Parameters:**
- `mokuOS_version` - The MokuOS version string
- `hardware` - The hardware platform identifier (one of: "mokupro", "mokugo", "mokulab", "mokudelta")

**Returns:** Path object pointing to the bitstream directory

> [!note] Implementation Notes
> Hardware directory mapping:
> - `mokupro` -> `mokupro`
> - `mokugo` -> `mokugo`
> - `mokulab` -> `moku20`
> - `mokudelta` -> `mokuaf`
>
> The path structure is: `{config_dir}/data/instruments/{version_instruments}/{hw_dir}`

> [!warning] Important
> Raises `NoInstrumentBitstream` if the resolved bitstream path does not exist

# See Also

- `.finder` - Device discovery implementation
- `.exceptions` - Custom exception definitions
- `.version` - Version compatibility specifications
