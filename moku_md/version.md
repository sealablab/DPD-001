---
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/version.py
title: version
---

# Overview

This module defines version compatibility constants for the Moku library. It specifies the supported proxy version and compatible versions for both MokuOS and MokuCLI, which are used to ensure proper communication and compatibility between the Moku Python library and the Moku hardware/software ecosystem.

> [!info] Key Dependencies
> No external dependencies - this module only defines constants

# Constants

## SUPPORTED_PROXY_VERSION

```python
SUPPORTED_PROXY_VERSION = 2.0
```

The proxy protocol version supported by this version of the Moku library. Proxy 2.0 first appeared in MokuOS 4.0.1. This is used for compatibility checking when communicating with Moku devices.

## COMPAT_MOKUOS

```python
COMPAT_MOKUOS = ">=4.0.1"
```

Specifies the compatible MokuOS versions. Currently used only for error messages, while the actual compatibility check uses the proxy version.

**Format:** Version constraint string (e.g., ">=4.0.1")

## COMPAT_MOKUCLI

```python
COMPAT_MOKUCLI = ">=4.0.1"
```

Specifies the compatible MokuCLI versions. This is used to enforce compatibility with the Moku command-line interface.

**Format:** Version constraint string (e.g., ">=4.0.1")

> [!note] Implementation Notes
> The proxy version (SUPPORTED_PROXY_VERSION) is the primary mechanism for compatibility checking, while the version strings (COMPAT_MOKUOS and COMPAT_MOKUCLI) are used for user-facing error messages and CLI compatibility enforcement.

# See Also

- This module is typically imported by core Moku connection and initialization code
- Version compatibility affects communication with Moku devices and CLI tools
