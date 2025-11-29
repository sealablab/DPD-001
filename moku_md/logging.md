---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/logging.py
title: logging
---

# Overview

This module provides logging configuration for the Moku library following Python library best practices. It uses a NullHandler by default to avoid unwanted log output, allowing library users to configure their own logging. The module provides convenience functions for common logging scenarios including debug logging enablement and context-based temporary logging.

> [!info] Key Dependencies
> - `logging` - Python's standard logging framework
> - `sys` - Used for stderr stream access
> - `typing` - Type hints for Optional parameters

# Classes

## LoggingContext

A context manager for temporarily enabling debug logging within a specific code block.

**Key Methods:**
- `__init__(level, format_string, stream)` - Initialize with optional logging configuration
- `__enter__()` - Enables debug logging and saves previous state
- `__exit__(exc_type, exc_val, exc_tb)` - Restores previous logging state

```python
class LoggingContext:
    def __init__(self, level: int = logging.DEBUG,
                 format_string: Optional[str] = None,
                 stream=None):
        ...
```

> [!example] Usage
> ```python
> with moku.logging.LoggingContext():
>     # Debug logging enabled here
>     moku_device.get_data()
> # Debug logging disabled after context
> ```

# Functions

## get_logger

```python
def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module within the moku package."""
```

Returns a logger instance for a specific module within the moku package hierarchy.

**Parameters:**
- `name` - Module name (e.g., 'session', 'instruments.oscilloscope')

**Returns:** Logger instance for the specified module (e.g., 'moku.session')

## enable_debug_logging

```python
def enable_debug_logging(level: int = logging.DEBUG,
                         format_string: Optional[str] = None,
                         stream=None) -> None:
```

Convenience function for library users to quickly enable debug output for the Moku library.

**Parameters:**
- `level` - Logging level (default: DEBUG)
- `format_string` - Custom format string (default: includes timestamp, level, module, message)
- `stream` - Output stream (default: stderr)

**Returns:** None

> [!warning] Important
> This should only be called by the application, not the library itself. The function removes any existing StreamHandler instances to avoid duplicate log messages.

> [!example] Usage
> ```python
> import moku.logging
> moku.logging.enable_debug_logging()
> # Now all moku operations will log debug information
> ```

## disable_debug_logging

```python
def disable_debug_logging() -> None:
    """Disable debug logging for the Moku library."""
```

Disables debug logging by removing all stream handlers and resetting to NullHandler only.

**Returns:** None

> [!note] Implementation Notes
> - Removes all StreamHandler instances from the logger
> - Ensures at least a NullHandler is present
> - Resets logging level to WARNING

# Module-level Configuration

> [!info] Logger Setup
> The module creates a package-level logger named 'moku' with:
> - A NullHandler attached by default (no output unless configured)
> - Propagation enabled (allows parent loggers to handle moku logs)
> - This follows best practices for Python libraries

# See Also

- Related to all moku instrument modules that use logging
- Integrates with Python's standard logging framework
