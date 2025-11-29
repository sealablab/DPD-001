---
publish: "true"
type: reference
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/session.py
title: session
tags: [moku, api, networking]
---

# Overview

This module provides HTTP session management for communicating with the Moku API Server. It handles request/response cycles, error handling, session key management, and response parsing for both v1 and v2 API endpoints.

> [!info] Key Dependencies
> - `requests.Session` - HTTP session management with connection pooling
> - `moku.exceptions` - Custom exception types for API error handling
> - `moku.logging` - Logging infrastructure for debugging and monitoring
> - `json` - Response parsing and serialization
> - `functools.wraps` - Decorator implementation

# Classes

## RequestSession

Base HTTP Requests class for managing communication with Moku devices over HTTP API.

**Key Methods:**
- `__init__(ip, connect_timeout, read_timeout, **kwargs)` - Initialize session with IP address and timeout configuration
- `update_sk(response)` - Update session key from response headers
- `url_for(group, operation)` - Generate API v1 URL for given group and operation
- `url_for_v2(location)` - Generate API v2 URL for given location
- `timeout_headers(rt_increase=0)` - Returns timeout tuple for HTTP requests
- `get(group, operation)` - Execute GET request to API v1 endpoint
- `post(group, operation, params=None)` - Execute POST request to API v1 endpoint
- `post_raw_json(group, operation, data)` - Execute POST with raw JSON data
- `post_to_v2(location, params=None)` - Execute POST request to API v2 endpoint
- `post_to_v2_raw(location, params=None)` - Execute raw POST to API v2 endpoint
- `get_file(group, operation, local_path)` - Download file from Moku to local path
- `post_file(group, operation, data)` - Upload file to Moku
- `delete_file(group, operation)` - Delete file from Moku
- `resolve(response)` - Parse and validate HTTP response, raising exceptions on errors

```python
class RequestSession:
    json_headers = {"Content-type": "application/json"}
    sk_name = "Moku-Client-Key"  # session key name

    def __init__(self, ip, connect_timeout, read_timeout, **kwargs):
        self.ip_address = ip
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.rs = Session()
        # support arbitrary session arguments
```

> [!note] Implementation Notes
> - Automatically manages session keys via the `Moku-Client-Key` header
> - Supports custom session attributes via `session_*` keyword arguments
> - Uses separate connect and read timeout values for fine-grained control
> - All decorated methods use `handle_response` for consistent error handling
> - Automatically adjusts read timeout for long-running operations (e.g., get_data)

> [!warning] Important
> - API v2 methods raise `MokuException` for non-200 status codes
> - Session keys are automatically updated and must be maintained across requests
> - File operations stream data in 8KB chunks to manage memory

# Functions

## handle_response

```python
def handle_response(func):
    """
    Decorator which parses the response returned
    by Moku API Server
    """
```

Decorator that wraps HTTP request methods to automatically parse and validate responses.

**Parameters:**
- `func` - The HTTP request function to wrap (get, post, etc.)

**Returns:** The parsed response data from `resolve()` method

> [!note] Implementation Notes
> This decorator is applied to all main HTTP methods (get, post, post_raw_json, post_file, delete_file) to ensure consistent response handling and error checking.

## RequestSession._handle_error

```python
@staticmethod
def _handle_error(code, messages):
```

Static method that maps API error codes to specific exception types.

**Parameters:**
- `code` - Error code string from API response
- `messages` - Error message(s) from API response

**Raises:**
- `NoPlatformBitstream` - When platform bitstream is missing
- `NoInstrumentBitstream` - When instrument bitstream is missing
- `InvalidParameterException` - When parameters are invalid
- `InvalidRequestException` - When request is malformed
- `NetworkError` - When network issues occur
- `UnexpectedChangeError` - When unexpected state changes occur
- `MokuException` - Generic exception for unhandled error codes

## RequestSession.echo_warnings

```python
@staticmethod
def echo_warnings(messages):
    """Prints any warnings received from Moku"""
```

Static method that logs and prints warning messages from the device.

**Parameters:**
- `messages` - List of warning message strings (or None)

## RequestSession._normalize_nan_inf

```python
@staticmethod
def _normalize_nan_inf(arg):
    return {"-inf": -float("inf"), "inf": float("inf"), "nan": float("nan")}[arg]
```

Static method that converts string representations of special float values to Python float objects.

**Parameters:**
- `arg` - String representation ("nan", "inf", or "-inf")

**Returns:** Python float object (nan, inf, or -inf)

## RequestSession._check_and_normalize_nan_inf

```python
def _check_and_normalize_nan_inf(self, content):
```

Parses JSON content with special handling for NaN and infinity values.

**Parameters:**
- `content` - JSON string content to parse

**Returns:** Parsed JSON object with normalized special float values

> [!note] Implementation Notes
> This method first attempts normal JSON parsing. If that fails due to non-standard NaN/Inf values, it replaces them with quoted strings and re-parses using `parse_constant` to normalize them.

# See Also

- `moku.exceptions` - Custom exception types used by this module
- `moku.logging` - Logging utilities for debugging
- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/session)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/session.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/session.md)
- Moku API documentation for endpoint specifications
