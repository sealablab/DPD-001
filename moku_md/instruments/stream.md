---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/instruments/_stream.py
title: _stream
created: 2025-11-19
modified: 2025-11-19 15:41:39
accessed: 2025-11-29 17:22:30
---

# Overview

This module provides the base infrastructure for streaming data from Moku instruments. It implements a threading-based system that uses the `mokucli` command-line tool to establish data streams from Moku devices and provides both real-time data access and file-based recording capabilities.

> [!info] Key Dependencies
> - `socket` - TCP socket connections for streaming data
> - `subprocess.Popen` - Launching mokucli CLI processes
> - `threading.Thread` - Background thread management for CLI processes
> - `json` - Parsing streamed data
> - `moku.MOKU_CLI_PATH` - Path to the mokucli executable
> - `moku.utilities.check_mokucli_version` - Validation of CLI version
> - `moku.exceptions.StreamException` - Custom exception for stream errors

# Classes

## MokuCLIThread

Threading class responsible for running the mokucli command as a subprocess.

**Key Methods:**
- `__init__(command, error_event, start_evt=None)` - Initialize with command to execute and event objects
- `run()` - Execute the subprocess and wait for completion, setting error event if failures occur

```python
class MokuCLIThread(Thread):
    def __init__(self, command, error_event, start_evt=None):
        self.command = command
        self.start_evt = start_evt
        self.error_event = error_event
```

> [!note] Implementation Notes
> This thread signals when the subprocess has launched via `start_evt`, then waits for process completion. Any stderr output raises a `StreamException` and sets the error event.

## StreamInstrument

Base class for all streaming features. Any instrument supporting data streaming should inherit this class.

**Key Methods:**
- `__init__(mokuOS_version)` - Initialize stream configuration and events
- `start_streaming()` - Base method to verify if streaming is possible
- `get_stream_data() -> dict` - Get the next converted stream data frame
- `stream_to_file(name=None)` - Stream data to a file in CSV, NPY, or MAT format
- `_get_next_available_port()` - Static method to find an available TCP port
- `_reset_stream_config()` - Reset all stream-related instance variables
- `_connect()` - Connect to the TCP port with retry logic
- `_begin_streaming()` - Initialize the streaming subprocess and connection

```python
class StreamInstrument:
    def __init__(self, mokuOS_version):
        self.stream_id = None
        self.ip_address = None
        self.port = None
        self._socket_rdr = None
        self._running = False
        self._error_event = Event()
```

> [!note] Implementation Notes
> This class uses a TCP socket to receive JSON-formatted data from the mokucli subprocess. The socket connection is made to localhost on a dynamically allocated port, with the mokucli process forwarding data from the Moku device.

> [!warning] Important
> - Streaming must be started before calling `get_stream_data()` or `stream_to_file()`
> - The connection retry logic attempts 5 times with 0.5 second delays
> - Data streaming ends when "EOS\n" (End of Stream) is received
> - All streaming methods check `mokucli` version compatibility before execution

# Functions

## start_streaming

```python
def start_streaming(self):
    """
    Base class start_streaming, verifies if streaming is possible
    """
```

Validates that the mokucli CLI tool is available and at the correct version before allowing streaming to begin.

**Returns:** None

> [!note]
> This is a base implementation meant to be overridden by instrument subclasses that will configure their specific streaming parameters.

## stream_to_file

```python
def stream_to_file(self, name=None):
    """
    Streams the data to the file of desired format

    :type name: `string`
    :param name: Base name with one of csv, npy, mat extensions (defaults to csv)
    """
```

Launches a background process to stream data directly to a file.

**Parameters:**
- `name` - Optional filename with extension (.csv, .npy, or .mat). If not provided, generates a timestamped CSV filename in format `STREAM_DDMMYYYYHHMMSS.csv`

**Returns:** None (launches background thread)

> [!warning] Important
> Raises `StreamException` if no streaming session is in progress (stream_id is None)

## get_stream_data

```python
def get_stream_data(self):
    """
    Get the converted stream of data

    :raises StreamException: Indicates END OF STREAM
    """
```

Retrieves the next frame of streaming data as a parsed JSON object.

**Returns:** Dictionary containing the parsed stream data

> [!warning] Important
> - Raises `StreamException` if no streaming session is active
> - Raises `StreamException` with "End of stream" when stream terminates
> - Automatically starts the streaming connection on first call if not already running
> - Blocks until data is available on the socket

# See Also

- `moku.exceptions.StreamException` - Exception raised for streaming errors
- `moku.utilities.check_mokucli_version` - CLI version validation
- Instrument-specific classes that inherit from `StreamInstrument`
