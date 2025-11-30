---
publish: "true"
type: reference
date: 2025-11-17
path_to_py_file: /Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku/finder.py
title: Finder
tags:
  - moku
  - api
  - discovery
created: 2025-11-25
modified: 2025-11-25 19:33:58
accessed: 2025-11-29 17:23:00
---

# Overview

This module provides network discovery functionality for Moku devices using Zeroconf/mDNS service discovery. It allows applications to find and enumerate Moku hardware on the local network by listening for `_moku._tcp.local.` service broadcasts.

> [!info] Key Dependencies
> - `zeroconf` - Used for mDNS/Zeroconf service discovery and browsing
> - `logging` - Provides logging capabilities for error handling
> - `time` - Used for timeout management during device discovery
> - `collections.namedtuple` - Defines the MokuInfo data structure

# Data Structures

## MokuInfo

A named tuple containing information about a discovered Moku device.

**Fields:**
- `name` - Device name
- `netver` - Network protocol version
- `fwver` - Firmware version
- `hwver` - Hardware version
- `serial` - Device serial number
- `colour` - Device color identifier
- `bootmode` - Current boot mode of the device
- `ipv4_addr` - IPv4 address
- `ipv6_addr` - IPv6 address (currently not implemented)

# Classes

## Finder

Discovers and tracks Moku devices on the local network using Zeroconf service discovery.

**Key Methods:**
- `__init__(on_add=None, on_remove=None)` - Initializes the finder with optional callbacks
- `add_service(zeroconf, service_type, name)` - Called when a Moku device is discovered
- `remove_service(zeroconf, service_type, name)` - Called when a Moku device is removed
- `update_service(zeroconf, service_type, name)` - Called when a Moku service is updated (currently no-op)
- `start()` - Starts the service browser
- `close()` - Closes the Zeroconf connection
- `find_all(timeout=5, filter=None)` - Finds all Moku devices on the network

```python
class Finder(object):
    def __init__(self, on_add=None, on_remove=None):
        self.moku_list = []
        self.finished = False
        self.filter = None
        self.timeout = 5
        self.zero_conf = Zeroconf(ip_version=IPVersion.V4Only)
        self.browser = None
        self.on_add = on_add
        self.on_remove = on_remove
```

> [!note] Implementation Notes
> - The Finder class implements the listener interface for Zeroconf's ServiceBrowser
> - Supports multiple network protocol versions (0.2, 0.4, 0.5) with version-specific parsers
> - Currently only supports IPv4 discovery (IPv6 is TODO)
> - Uses callbacks (`on_add`, `on_remove`) for asynchronous device discovery events

### Version-Specific Parsers

The Finder includes three private parsing methods to handle different network protocol versions:

- `_parse_02(info)` - Parses Moku device info for network protocol version 0.2
- `_parse_04(info)` - Parses Moku device info for network protocol version 0.4
- `_parse_05(info)` - Parses Moku device info for network protocol version 0.5

Each parser extracts device properties from the Zeroconf service info and returns a MokuInfo instance. The parsers differ in how they access properties from the service info dictionary (e.g., `device.fw_version` vs `fwver`).

> [!warning] Important
> - The `find_all()` method blocks for up to the specified timeout period
> - Error handling silently logs parsing errors and continues discovery
> - The browser must be properly closed using `close()` to release network resources

### Usage Pattern

```python
# Blocking discovery
finder = Finder()
devices = finder.find_all(timeout=10)
for device in devices:
    print(f"Found {device.name} at {device.ipv4_addr}")

# Asynchronous discovery with callbacks
def on_device_found(name, info):
    print(f"Device added: {name}")

def on_device_removed(name):
    print(f"Device removed: {name}")

finder = Finder(on_add=on_device_found, on_remove=on_device_removed)
finder.start()
# ... do other work ...
finder.close()
```

# See Also

- Related modules: `moku` package for device communication
- `zeroconf` package documentation for service discovery details
- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/finder)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/finder.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/finder.md)
