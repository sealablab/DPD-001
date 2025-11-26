# Moku API Architecture: Session, Multi-Instrument, and State Management

## Overview

This document describes the architectural relationships between the core Moku API components, with particular focus on session management, multi-instrument mode, and configuration state persistence. This is essential reading for implementing utilities that need to capture and restore complete hardware state.

## Core Components

### 1. RequestSession (session.py)

**Purpose**: Low-level HTTP communication layer for all Moku device interactions.

**Key Responsibilities**:
- Manages HTTP session with connection pooling
- Handles session key authentication (`Moku-Client-Key` header)
- Provides API v1 and v2 endpoint routing
- Parses responses and maps error codes to exceptions
- Supports file upload/download operations

**Critical Methods**:
```python
# API v1 endpoints (legacy)
session.get(group, operation)
session.post(group, operation, params)

# API v2 endpoints (newer)
session.post_to_v2(location, params)

# File operations
session.get_file(group, operation, local_path)  # Download
session.post_file(group, operation, data)        # Upload
```

**Session Key Management**:
- Automatically extracted from response headers
- Updated on every request via `update_sk(response)`
- Must be maintained across requests for authorization

### 2. Moku Base Class (__init__.py)

**Purpose**: Base class for all Moku device connections and ownership management.

**Key Responsibilities**:
- Device connection and ownership claiming
- Bitstream deployment and management
- Platform configuration for multi-instrument mode
- Common device operations (reboot, shutdown, etc.)

**Critical Methods**:
```python
# Connection management
moku = Moku(ip, force_connect, ignore_busy, persist_state)
moku.claim_ownership(force_connect, ignore_busy, persist_state)
moku.relinquish_ownership()

# Bitstream management
moku.upload_bitstream(name, bs_path)
moku.platform(platform_id)  # Configure for multi-instrument mode
```

**Platform IDs**:
- `platform_id=2`: 2-slot multi-instrument mode
- `platform_id=4`: 4-slot multi-instrument mode

### 3. MultiInstrumentSlottable Mixin (__init__.py)

**Purpose**: Common initialization pattern for all instruments that can operate in multi-instrument mode.

**Key Responsibilities**:
- Handles both standalone and multi-instrument initialization
- Manages slot-based routing for API calls
- Coordinates bitstream deployment for specific slots

**Initialization Pattern**:
```python
def _init_instrument(self, slot=None, multi_instrument=None, ...):
    if multi_instrument is None:
        # Standalone mode: always slot 1
        self.slot = 1
        super().__init__(ip=ip, ...)  # Call Moku.__init__
        self.upload_bitstream("01-000")           # Platform bitstream
        self.upload_bitstream(f"01-{self.id:03}-00")  # Instrument bitstream
    else:
        # Multi-instrument mode: use shared session
        self.slot = slot
        self.session = multi_instrument.session  # CRITICAL: Shared session
        self.platform_id = multi_instrument.platform_id
        # Bitstream handled by MultiInstrument.set_instrument()
```

**All Instruments Using This Pattern** (16 total):
- ArbitraryWaveformGenerator
- CloudCompile
- Datalogger
- DigitalFilterBox
- FIRFilterBox
- FrequencyResponseAnalyzer
- LaserLockBox
- LockInAmp
- LogicAnalyzer
- NeuralNetwork
- Oscilloscope
- Phasemeter
- PIDController
- SpectrumAnalyzer
- TimeFrequencyAnalyzer
- WaveformGenerator

### 4. MultiInstrument Class (_mim.py)

**Purpose**: Manages multi-instrument mode, allowing multiple instruments to run simultaneously in separate slots.

**Key Responsibilities**:
- Configures platform for multi-slot operation
- Manages instrument deployment to specific slots
- Handles signal routing between slots
- Provides slot-level configuration (frontend, output, DIO)

**Critical Methods**:
```python
# Initialize multi-instrument mode
mim = MultiInstrument(ip, platform_id=4)  # 4-slot platform

# Deploy instruments to slots
slot1_instrument = mim.set_instrument(slot=1, instrument=Oscilloscope)
slot2_instrument = mim.set_instrument(slot=2, instrument=WaveformGenerator)

# Get current slot assignments
instruments = mim.get_instruments()  # Returns list of instrument names per slot

# Configuration persistence
mim.save_configuration("setup.mokuconf")   # MIM-level config only
mim.load_configuration("setup.mokuconf")
```

**Important Notes**:
- `MultiInstrument` extends `Moku` (has its own session)
- Each instrument in a slot shares the same `session` instance
- `save_configuration()` only saves MIM-level settings (connections, frontend, DIO)
- **Individual instruments must be saved separately**

### 5. CloudCompile (_cloudcompile.py)

**Purpose**: Special instrument for deploying custom FPGA bitstreams compiled via Liquid Instruments' cloud service.

**Key Difference**:
- Requires custom bitstream package path at initialization
- Extracts tarball to temporary directory
- Passes `bs_path` to `_init_instrument()` for custom bitstream deployment

**Usage**:
```python
# Standalone mode
cc = CloudCompile(ip, bitstream="path/to/custom.tar.gz")

# Multi-instrument mode
cc = mim.set_instrument(slot=2, instrument=CloudCompile, bitstream="path/to/custom.tar.gz")
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Your Code                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MultiInstrument (MIM)                     │
│  - platform_id: 2 or 4                                      │
│  - session: RequestSession                                  │
│  - save_configuration() ← MIM-level only                    │
│  - get_instruments() → ["Oscilloscope", "", "PIDController"]│
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  Slot 1  │        │  Slot 2  │        │  Slot 3  │
    │   Osc    │        │  Empty   │        │   PID    │
    └──────────┘        └──────────┘        └──────────┘
          │                                       │
          │              (shared session)         │
          ▼                                       ▼
┌──────────────────┐                    ┌──────────────────┐
│  Oscilloscope    │                    │  PIDController   │
│  - slot: 1       │                    │  - slot: 3       │
│  - session: MIM  │                    │  - session: MIM  │
│  - save_settings()│                   │  - save_settings()│
└──────────────────┘                    └──────────────────┘
          │                                       │
          └───────────────────┬───────────────────┘
                              ▼
                    ┌──────────────────┐
                    │  RequestSession  │
                    │  - ip_address    │
                    │  - session_key   │
                    │  - HTTP methods  │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Moku Device    │
                    │   HTTP API       │
                    └──────────────────┘
```

## API Routing Patterns

### Standalone Mode
```python
oscilloscope = Oscilloscope(ip="192.168.1.100")
oscilloscope.save_settings("osc.mokuconf")

# API call routing:
# session.get_file(group="oscilloscope", operation="save_settings", ...)
# → GET http://192.168.1.100/api/oscilloscope/save_settings
```

### Multi-Instrument Mode
```python
mim = MultiInstrument(ip="192.168.1.100", platform_id=4)
osc = mim.set_instrument(slot=1, instrument=Oscilloscope)
osc.save_settings("osc.mokuconf")

# API call routing:
# session.get_file(group="slot1/oscilloscope", operation="save_settings", ...)
# → GET http://192.168.1.100/api/slot1/oscilloscope/save_settings
```

**Key Pattern**: In multi-instrument mode, the API group is prefixed with `slot{N}/`

## Configuration State Management

### Two-Level Configuration Hierarchy

#### Level 1: MultiInstrument Configuration
**What it saves**:
- Signal routing/connections between slots
- Frontend configuration (impedance, coupling, attenuation)
- Output configuration (gain)
- DIO configuration (direction mapping)

**Methods**:
```python
mim.save_configuration("mim_config.mokuconf")
mim.load_configuration("mim_config.mokuconf")
```

**Important**: This does NOT save individual instrument settings!

#### Level 2: Per-Instrument Configuration
**What it saves**:
- All instrument-specific parameters
- Trigger settings
- Acquisition settings
- Waveform parameters
- Filter configurations
- etc.

**Methods** (available on all 16 slottable instruments):
```python
instrument.save_settings("instrument_config.mokuconf")
instrument.load_settings("instrument_config.mokuconf")
```

**API Implementation Pattern**:
```python
def save_settings(self, filename):
    if hasattr(self, 'slot'):
        # Multi-instrument mode
        group = f"slot{self.slot}/{self.operation_group}"
    else:
        # Standalone mode (or legacy)
        group = self.operation_group

    self.session.get_file(group, "save_settings", filename)
```

## Complete State Capture Utility: Implementation Guide

### Goal
Capture the complete state of a Moku device in multi-instrument mode so it can be restored later.

### Required Steps

#### 1. Connect and Verify Multi-Instrument Mode

```python
from moku.instruments import MultiInstrument

def capture_state(ip_address, output_dir):
    # Connect to device
    mim = MultiInstrument(ip=ip_address, platform_id=4)  # Adjust platform_id

    # Verify/get current configuration
    instruments = mim.get_instruments()
    print(f"Current slots: {instruments}")
    # Example output: ["Oscilloscope", "", "PIDController", "WaveformGenerator"]
```

#### 2. Save MultiInstrument Configuration

```python
    # Save MIM-level configuration
    mim_config_path = f"{output_dir}/mim_config.mokuconf"
    mim.save_configuration(mim_config_path)
    print(f"Saved MIM config to {mim_config_path}")
```

#### 3. Iterate Through Active Slots and Save Each Instrument

**Challenge**: You need to instantiate the correct instrument class for each slot.

**Solution**: Use dynamic imports and the instrument list from `get_instruments()`

```python
from moku import instruments
import inspect

def get_instrument_class(instrument_name):
    """Get instrument class from name string"""
    # Get all classes from instruments module
    for name, obj in inspect.getmembers(instruments, inspect.isclass):
        if name == instrument_name:
            return obj
    raise ValueError(f"Unknown instrument: {instrument_name}")

def capture_all_instrument_states(mim, output_dir):
    """Capture state of all instruments in all slots"""
    instrument_list = mim.get_instruments()

    for slot_num, instrument_name in enumerate(instrument_list, start=1):
        if instrument_name == "":
            print(f"Slot {slot_num}: Empty")
            continue

        print(f"Slot {slot_num}: {instrument_name}")

        # Get instrument class
        InstrumentClass = get_instrument_class(instrument_name)

        # Create instrument reference using for_slot class method
        instrument = InstrumentClass.for_slot(slot=slot_num, multi_instrument=mim)

        # Save instrument settings
        config_path = f"{output_dir}/slot{slot_num}_{instrument_name}.mokuconf"
        instrument.save_settings(config_path)
        print(f"  Saved to {config_path}")
```

#### 4. Create Metadata File

```python
import json
from datetime import datetime

def save_metadata(mim, instruments, output_dir):
    """Save metadata about the capture"""
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "device_ip": mim.session.ip_address,
        "serial_number": mim.serial_number(),
        "mokuos_version": mim.mokuos_version(),
        "platform_id": mim.platform_id,
        "slots": [
            {"slot": i+1, "instrument": name}
            for i, name in enumerate(instruments)
            if name != ""
        ]
    }

    with open(f"{output_dir}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
```

### Complete Implementation


```python
#!/usr/bin/env python3
"""
Moku State Capture Utility

Captures the complete configuration state of a Moku device in multi-instrument mode.
"""

import json
import inspect
from pathlib import Path
from datetime import datetime
from moku.instruments import MultiInstrument
from moku import instruments


def get_instrument_class(instrument_name):
    """Get instrument class from name string"""
    for name, obj in inspect.getmembers(instruments, inspect.isclass):
        if name == instrument_name:
            return obj
    raise ValueError(f"Unknown instrument: {instrument_name}")


def capture_moku_state(ip_address, platform_id, output_dir):
    """
    Capture complete state of Moku device in multi-instrument mode.

    Args:
        ip_address: IP address of Moku device
        platform_id: Platform ID (2 or 4 for number of slots)
        output_dir: Directory to save configuration files

    Returns:
        Dictionary with capture results
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Connect to device
    print(f"Connecting to Moku at {ip_address}...")
    mim = MultiInstrument(ip=ip_address, platform_id=platform_id)

    # Get current instrument configuration
    instrument_list = mim.get_instruments()
    print(f"Current configuration: {instrument_list}")

    results = {
        "mim_config": None,
        "instrument_configs": [],
        "metadata": None
    }

    # Save MIM-level configuration
    mim_config_path = output_path / "mim_config.mokuconf"
    mim.save_configuration(str(mim_config_path))
    results["mim_config"] = str(mim_config_path)
    print(f"✓ Saved MIM config to {mim_config_path}")

    # Save each instrument's configuration
    for slot_num, instrument_name in enumerate(instrument_list, start=1):
        if instrument_name == "":
            print(f"  Slot {slot_num}: Empty")
            continue

        print(f"  Slot {slot_num}: {instrument_name}")

        try:
            # Get instrument class and create reference
            InstrumentClass = get_instrument_class(instrument_name)
            instrument = InstrumentClass.for_slot(slot=slot_num, multi_instrument=mim)

            # Save settings
            config_path = output_path / f"slot{slot_num}_{instrument_name}.mokuconf"
            instrument.save_settings(str(config_path))

            results["instrument_configs"].append({
                "slot": slot_num,
                "instrument": instrument_name,
                "config_file": str(config_path)
            })

            print(f"    ✓ Saved to {config_path}")

        except Exception as e:
            print(f"    ✗ Error saving {instrument_name}: {e}")
            results["instrument_configs"].append({
                "slot": slot_num,
                "instrument": instrument_name,
                "error": str(e)
            })

    # Save metadata
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "device_ip": ip_address,
        "serial_number": mim.serial_number(),
        "mokuos_version": mim.mokuos_version(),
        "platform_id": platform_id,
        "slots": [
            {"slot": i+1, "instrument": name}
            for i, name in enumerate(instrument_list)
        ]
    }

    metadata_path = output_path / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    results["metadata"] = str(metadata_path)
    print(f"✓ Saved metadata to {metadata_path}")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python capture_state.py <IP_ADDRESS> [PLATFORM_ID] [OUTPUT_DIR]")
        print("Example: python capture_state.py 192.168.1.100 4 ./backup")
        sys.exit(1)

    ip = sys.argv[1]
    platform = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    output = sys.argv[3] if len(sys.argv) > 3 else f"./moku_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    results = capture_moku_state(ip, platform, output)
    print(f"\n✓ Complete state captured to {output}")
```

## State Restoration

To restore a captured state:

```python
def restore_moku_state(ip_address, backup_dir):
    """Restore Moku state from backup directory"""
    backup_path = Path(backup_dir)

    # Load metadata
    with open(backup_path / "metadata.json") as f:
        metadata = json.load(f)

    platform_id = metadata["platform_id"]

    # Connect and restore MIM configuration
    mim = MultiInstrument(ip=ip_address, platform_id=platform_id)
    mim.load_configuration(str(backup_path / "mim_config.mokuconf"))

    # Restore each instrument
    for slot_info in metadata["slots"]:
        if slot_info["instrument"] == "":
            continue

        slot = slot_info["slot"]
        instrument_name = slot_info["instrument"]

        # Deploy instrument to slot
        InstrumentClass = get_instrument_class(instrument_name)
        instrument = mim.set_instrument(slot=slot, instrument=InstrumentClass)

        # Load settings
        config_file = backup_path / f"slot{slot}_{instrument_name}.mokuconf"
        instrument.load_settings(str(config_file))

        print(f"✓ Restored {instrument_name} to slot {slot}")
```

## Key Takeaways

1. **Session Sharing**: All instruments in multi-instrument mode share the same `RequestSession` instance
2. **Two-Level Config**: MIM config and per-instrument configs are separate
3. **API Routing**: Multi-instrument mode prefixes API groups with `slot{N}/`
4. **All 16 Instruments**: Have `save_settings()` and `load_settings()` methods
5. **Dynamic Access**: Use `get_instruments()` to discover active slots, then use `for_slot()` class method
6. **Complete State**: Requires saving both MIM config AND all instrument configs

## See Also

- [session.md](session.md) - RequestSession implementation details
- [__init__.md](moku_md/__init__.md) - Moku base class and MultiInstrumentSlottable mixin
- [instruments/_mim.md](./instruments/_mim.md) - MultiInstrument class details
- [instruments/_cloudcompile.md](./instruments/_cloudcompile.md) - CloudCompile special case
