---
publish: "true"
type: reference
created: 2025-11-29
modified: 2025-11-29 17:22:04
tags:
  - moku
  - api
  - dpd
  - hot-path
  - index
accessed: 2025-11-29 17:41:48
---

# DPD Moku API Hot-Path Index

> [!abstract] Purpose
> This document indexes the **specific Moku API calls** used by the DPD (Demo Probe Driver) project. It serves as a quick-reference for agents and humans working on DPD, cross-linking to full documentation where needed.


> [!WARN]  This note __assumes__ you have a functioning `moku_md` markdown submodule representation installed. 

## Architecture Overview

DPD uses **Multi-Instrument Mode (MIM)** with two instruments:

```
┌─────────────────────────────────────────────────────────────┐
│                    Moku:Go (platform_id=2)                  │
├─────────────────────────────────────────────────────────────┤
│  Slot 1: Oscilloscope          Slot 2: CloudCompile (DPD)   │
│  ┌─────────────────┐           ┌─────────────────────────┐  │
│  │ Ch1 ← InA       │◄──────────│ OutC (HVS state)        │  │
│  │                 │           │ OutB (intensity)        │──┼──► Output2
│  │                 │           │ OutA (trigger)          │  │
│  │                 │           │ InA ◄────────────────────┼──┼── Input1
│  └─────────────────┘           └─────────────────────────┘  │
│                                        │                    │
│                                        └────────────────────┼──► Output1
└─────────────────────────────────────────────────────────────┘
```

**Key Insight**: Slot-to-slot routing (OutC → InA) is **digital** - no analog frontend applies.

---

## Quick Reference: API Methods Used

| Class | Method | DPD Usage | Full Docs |
|-------|--------|-----------|-----------|
| [MultiInstrument](instruments/mim.md) | [`set_instrument()`](instruments/mim.md#set_instrument) | Deploy Osc/CC to slots | [mim.md](instruments/mim.md) |
| | [`set_connections()`](instruments/mim.md#set_connections) | Route OutputC → OscInA | [mim.md](instruments/mim.md) |
| | [`get_connections()`](instruments/mim.md#get_connections) | Verify routing exists | [mim.md](instruments/mim.md) |
| | `relinquish_ownership()` | Clean disconnect | [mim.md](instruments/mim.md) |
| [CloudCompile](instruments/cloudcompile.md) | `set_control(idx, value)` | Write CR0-CR10 | [cloudcompile.md](instruments/cloudcompile.md) |
| | `set_controls([{idx, value}])` | Batch register write | [cloudcompile.md](instruments/cloudcompile.md) |
| [Oscilloscope](moku_md/instruments/oscilloscope.md) | [`set_timebase(t1, t2)`](moku_md/instruments/oscilloscope.md#set_timebase) | 2ms acquisition window | [_oscilloscope.md](moku_md/instruments/oscilloscope.md) |
| | [`get_data()`](moku_md/instruments/oscilloscope.md#get_data) | Read HVS voltage | [_oscilloscope.md](moku_md/instruments/oscilloscope.md) |

---

## Detailed API Usage

### 1. MultiInstrument (MIM) — [Full Docs](instruments/mim.md)

The MIM controller manages the 2-slot configuration.

#### Connection & Setup

```python
from moku.instruments import MultiInstrument, Oscilloscope, CloudCompile

# Connect to Moku:Go (platform_id=2 = 2 slots)
moku = MultiInstrument(
    ip="192.168.31.41",
    platform_id=2,
    force_connect=True
)
```

> [!info] DPD Source
> See `tests/hw/plumbing.py:92-115` — `MokuSession._connect()`

#### Instrument Deployment — [`set_instrument()`](instruments/mim.md#set_instrument)

```python
# Slot 1: Oscilloscope (for HVS state observation)
osc = moku.set_instrument(1, Oscilloscope)

# Slot 2: CloudCompile with DPD bitstream
mcc = moku.set_instrument(2, CloudCompile, bitstream="dpd-bits.tar")
```

> [!warning] Slot Indexing
> Slots are **1-indexed**. Valid range is `[1, platform_id]`.

> [!info] DPD Source
> See `tests/hw/plumbing.py:119-150` — `MokuSession._deploy_instruments()`

#### Signal Routing — [`set_connections()`](instruments/mim.md#set_connections)

```python
moku.set_connections(connections=[
    {'source': 'Input1', 'destination': 'Slot2InA'},      # External trigger → CC
    {'source': 'Slot2OutB', 'destination': 'Output2'},    # Intensity → physical
    {'source': 'Slot2OutC', 'destination': 'Output1'},    # HVS → physical (debug)
    {'source': 'Slot2OutC', 'destination': 'Slot1InA'},   # HVS → Oscilloscope
])
```

> [!danger] Internal Routing is Digital
> The `Slot2OutC → Slot1InA` connection is **internal digital routing**.
> - `moku.set_frontend()` does **NOT** apply here
> - Only physical inputs (Input1, Input2) have analog frontends
> - See [MIM Frontend Gotcha](instruments/mim.md#set_frontend)

> [!info] DPD Source
> See `tests/hw/plumbing.py:152-179` — `MokuSession._setup_routing()`

#### Disconnect — `relinquish_ownership()`

```python
moku.relinquish_ownership()  # Clean disconnect
```

> [!info] DPD Source
> See `tests/hw/plumbing.py:181-190` — `MokuSession._disconnect()`

---

### 2. CloudCompile — [Full Docs](instruments/cloudcompile.md)

The CloudCompile instrument loads DPD's custom FPGA bitstream and provides register access.

#### Control Register Access — `set_control()` / `set_controls()`

```python
# Single register write
mcc.set_control(4, 12500)  # CR4 = trigger_duration (100μs @ 125MHz)

# Batch register write
mcc.set_controls([
    {"idx": 4, "value": 12500},   # CR4
    {"idx": 5, "value": 25000},   # CR5
    {"idx": 6, "value": 250000000}, # CR6
])
```

> [!warning] No Register Readback
> `CloudCompile.get_control()` returns `None` — the firmware doesn't support readback for custom instruments. DPD uses **shadow registers** to track writes:
> ```python
> mcc.set_control(idx, value)
> self._shadow_regs[idx] = value  # Track locally
> ```

> [!warning] Network Propagation Delay
> After `set_control()`, wait **~10ms minimum** for the value to propagate through the Moku network stack:
> ```python
> mcc.set_control(0, 0xE0000004)  # arm_enable
> await asyncio.sleep(0.01)        # Wait for propagation
> ```

> [!info] DPD Source
> See `tests/adapters/moku.py:42-46` — `MokuAsyncController.set_control_register()`
> See `tests/shared/control_interface.py:283-322` — `MokuControl` class


> [!tip] Clock Conversion
> Use `py_tools/clk_utils.py`:
> ```python
> from clk_utils import us_to_cycles
> trig_duration = us_to_cycles(100)  # 100μs → 12500 cycles
> ```

---

### 3. Oscilloscope — [Full Docs](moku_md/instruments/oscilloscope.md)

Used to observe FSM state via HVS (Hierarchical Voltage Scaling) on OutputC.

#### Timebase Configuration — [`set_timebase()`](moku_md/instruments/oscilloscope.md#set_timebase)

```python
osc.set_timebase(-0.001, 0.001)  # 2ms window centered at trigger
```

> [!note] No Frontend Config in MIM
> Individual `osc.set_frontend()` calls **fail** in MIM mode. Use `moku.set_frontend()` for physical inputs only. Internal routing has no frontend.

> [!info] DPD Source
> See `tests/hw/plumbing.py:135-139`

#### Data Acquisition — [`get_data()`](moku_md/instruments/oscilloscope.md#get_data)

```python
data = osc.get_data()
# Returns: {'ch1': [v0, v1, v2, ...], 'ch2': [...], 'time': [...]}

voltage = data['ch1'][len(data['ch1']) // 2]  # Midpoint sample
```

> [!tip] HVS Polling Strategy
> DPD averages **5 samples @ 20ms intervals** for noise reduction:
> ```python
> voltages = []
> for _ in range(5):
>     data = osc.get_data()
>     voltages.append(data['ch1'][len(data['ch1']) // 2])
>     await asyncio.sleep(0.02)
> avg_voltage = sum(voltages) / len(voltages)
> ```

> [!info] DPD Source
> See `tests/adapters/moku.py:82-99` — `MokuAsyncStateReader._read_voltage_averaged()`

---

### 4. Session Layer — [Full Docs](session.md)

The `RequestSession` class handles HTTP communication. DPD doesn't interact with it directly, but understanding it explains propagation delays.

> [!note] Why 10-100ms Delays?
> All Moku API calls go through HTTP REST:
> 1. Python → HTTP POST → Moku device
> 2. Moku firmware processes request
> 3. Moku → HTTP response → Python
>
> This round-trip typically takes **10-100ms**. Control register writes have additional propagation through the FPGA fabric.

---

## DPD Implementation Details

> [!abstract] Authoritative Sources
> The following sections link to canonical DPD documentation. Avoid duplicating content here.

### Control Register Specification

> [!tip] Authoritative Source: [docs/api-v4.md](../docs/api-v4.md)
> - [CR0 - Lifecycle Control](../docs/api-v4.md#cr0---lifecycle-control-register) — FORGE RUN bits, arm/clear/trigger
> - [CR2-CR10 - Configuration](../docs/api-v4.md#cr2-cr10---configuration-registers) — Voltages, timing, monitor
> - [Usage Patterns](../docs/api-v4.md#usage-patterns) — Single-shot, burst, fault recovery
> - [FSM States](../docs/api-v4.md#fsm-states) — State definitions & HVS voltages

**Pre-built CR0 Constants** (from `py_tools/dpd_constants.py`):

| Constant | Value | Usage |
|----------|-------|-------|
| `CR0.RUN` | `0xE0000000` | Module enabled, FSM idle |
| `CR0.RUN_ARMED` | `0xE0000004` | FSM armed, waiting for trigger |
| `CR0.RUN_ARMED_TRIG` | `0xE0000005` | **Atomic arm + trigger** |
| `CR0.RUN_ARMED_CLEAR` | `0xE0000006` | Clear fault while armed |

---

### FSM Initialization Sequence

> [!tip] Authoritative Source: [docs/hardware-debug-checklist.md](../docs/hardware-debug-checklist.md)
> See [Complete Sequence (Python Script)](../docs/hardware-debug-checklist.md#complete-sequence-python-script---api-v40) for step-by-step initialization with register values.

**Summary**: Clear registers → Enable FORGE → Set timing/voltages → Pulse fault_clear → FSM reaches IDLE

> [!info] DPD Source
> See `tests/adapters/moku.py:119-155` — `MokuAsyncHarness.initialize_fsm()`

---

### HVS State Mapping

> [!tip] Authoritative Source: [docs/hvs.md](../docs/hvs.md)
> - [Visual Representation](../docs/hvs.md#visual-representation) — Oscilloscope ASCII diagram
> - [Level 1: Major States](../docs/hvs.md#level-1-major-state-transitions-500mv-steps) — 500mV steps
> - [Level 2: Status Noise](../docs/hvs.md#level-2-status-noise-15mv-fine-detail) — ±15mV encoding
> - [Fault Detection](../docs/hvs.md#fault-detection-sign-flip) — Negative voltage = fault
> - [Digital Unit Conversion](../docs/hvs.md#digital-unit-conversion) — 3277 units per state

**Quick Reference** (see [docs/hvs.md](../docs/hvs.md) for details):

| State | Voltage | Tolerance (HW / Sim) |
|-------|---------|----------------------|
| IDLE | 0.5V | ±300mV / ±30mV |
| ARMED | 1.0V | ±300mV / ±30mV |
| FIRING | 1.5V | ±300mV / ±30mV |
| COOLDOWN | 2.0V | ±300mV / ±30mV |
| FAULT | Negative | Any negative |

---

### Network Register Synchronization

> [!tip] Authoritative Source: [docs/network-register-sync.md](../docs/network-register-sync.md)
> Explains why CR2-CR10 only update in INITIALIZING state (sync-gating for race condition prevention).

---

## File Quick Reference

### Moku API Documentation (`moku_md/`)

| File | Content |
|------|---------|
| [instruments/mim.md](instruments/mim.md) | MultiInstrument Mode |
| [instruments/cloudcompile.md](instruments/cloudcompile.md) | CloudCompile instrument |
| [instruments/_oscilloscope.md](moku_md/instruments/oscilloscope.md) | Oscilloscope instrument |
| [session.md](session.md) | HTTP session management |

### DPD Authoritative Documentation (`docs/`)

| File | Content |
|------|---------|
| [api-v4.md](../docs/api-v4.md) | **Authoritative** register calling convention |
| [hvs.md](../docs/hvs.md) | HVS encoding scheme |
| [hardware-debug-checklist.md](../docs/hardware-debug-checklist.md) | Step-by-step hardware debugging |
| [network-register-sync.md](../docs/network-register-sync.md) | Register sync protocol |
| [custom-wrapper.md](../docs/custom-wrapper.md) | CustomWrapper interface spec |

### DPD Test Infrastructure (`tests/`)

| File | Purpose |
|------|---------|
| `tests/hw/plumbing.py` | MokuSession context manager |
| `tests/adapters/moku.py` | Async API wrappers |
| `tests/shared/control_interface.py` | Abstract control interface |

### DPD Python Utilities (`py_tools/`)

| File | Purpose |
|------|---------|
| `dpd_config.py` | Configuration dataclass |
| `dpd_constants.py` | CR0, FSMState, HVS constants |
| `clk_utils.py` | Clock cycle conversions |

---

## See Also

**Moku API** (this directory):
- [MultiInstrument (MIM)](instruments/mim.md) — Full MIM documentation
- [CloudCompile](instruments/cloudcompile.md) — CloudCompile instrument details
- [Oscilloscope](moku_md/instruments/oscilloscope.md) — Oscilloscope instrument details
- [Session](session.md) — HTTP session management
- [README.md](README.md) — Full Moku API package index

**DPD Documentation** (`docs/`):
- [API v4.0](../docs/api-v4.md) — **Authoritative** register calling convention
- [HVS Encoding](../docs/hvs.md) — Hierarchical Voltage Scaling details
- [Hardware Debug Checklist](../docs/hardware-debug-checklist.md) — Practical debugging
- [Network Register Sync](../docs/network-register-sync.md) — Sync-gating protocol
- [docs/README.md](../docs/README.md) — Full DPD documentation index

**Project-Level**:
- [CLAUDE.md](../CLAUDE.md) — Project instructions for Claude Code

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/moku_md/DPD-API-HOTPATH)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/moku_md/DPD-API-HOTPATH.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/moku_md/DPD-API-HOTPATH.md)
