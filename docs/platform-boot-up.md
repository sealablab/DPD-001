# [platform-boot-up](docs/platform-boot-up.md)

> **Status**: Draft
> **Version**: 0.1
> **Date**: 2025-11-27

---
# @CLAUDE


## `RUNP` vs `RUNB` (BIOS vs PROGRAM)
We are going to create a small self-contained BIOS that will be 'inked in' to the 'main' BPD Program 

Conceptually these registers are layed out so that one would 'boot' the machine by entering (figuritavely speaking) 
- `RUNP` (Run Program)
- `RUNB` (Run BIOS)

## `RUNB` (RUN BIOS)
The `BIOS` is out of scope for this conversation, suffice it to so that it will be minimal and likely generate known simple waveforms on Outputs A-C and (hopefully) be able to capture samples on **Inputs** InputA-C

__interacting__ with the BIOS will be absolutely rudimentary - this is because there is no documented ability to read register values out over the network. 

## `RUNP` (RUN PROGRAM)
This is will transfer control to the regularly scheduled application - the DPD demo probe driver.

@CLAUDE: Rework the lines below

## Overview

This document describes the multi-phase initialization process for FORGE applications on the Moku platform. The process ensures reliable handoff from platform boot through application runtime.
#

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INITIALIZATION TIMELINE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PLATFORM          P0                P1                 P2              │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  Moku loads     ┌──────────┐    ┌──────────┐      ┌──────────┐         │
│  bitstream  ───>│  NULL    │───>│ LOADING  │─────>│ RUNTIME  │         │
│                 │  STATE   │    │  PHASE   │      │  PHASE   │         │
│                 └──────────┘    └──────────┘      └──────────┘         │
│                                                                         │
│  CR0[31:29]=000    RUN=111         RUN=111          RUN=111            │
│  All CRs=0x00      BRAM writes     App config       FSM active         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## P0: Platform Startup (NULL State)

### Platform Behavior

When the Moku platform loads a CloudCompile bitstream:

1. **Bitstream deployment**: Platform transfers compiled bitstream to FPGA
2. **Register initialization**: All Control Registers (CR0-CR15) are initialized to `0x00000000`
3. **Clock enabled**: System clock (125 MHz) is running
4. **Handoff**: Platform signals "ready" and awaits user interaction

### FORGE Safety Gate

The CR0[31:29] "RUN" scheme provides a reliable handoff mechanism:

```
CR0[31:29] = "RUN" bits
─────────────────────────────────────────
  Bit 31: forge_ready  (R) - Set by loader
  Bit 30: user_enable  (U) - User control
  Bit 29: clk_enable   (N) - Clock gating
─────────────────────────────────────────

RUN = 0xE0000000 (all three bits set)
```

**Key invariant**: The application FSM remains frozen until `CR0[31:29] = 0b111`.

This ensures:
- No spurious outputs during bitstream loading
- Deterministic startup behavior
- Safe state until software explicitly enables operation

### P0 → P1 Transition

``` python 
@CLAUDE
Some notes:
 we need to clarify about 'the FSM' and 'initializating state'
```

```
The transition from NULL to LOADING occurs when:

1. Python client connects to Moku device
2. Client writes `CR0 = 0xE0000000` (RUN enabled)
3. FSM enters INITIALIZING state (transient)
 @CLAUDE - 
4. Client proceeds to LOADING phase

```python
# P0 → P1 transition
dpd.set_control(0, CR0.RUN)  # 0xE0000000
# FSM now responsive, ready for BRAM loading
```

---

## P1: Loading Phase (Environment Setup)

### Concept: Environment Buffers

Borrowing from userland Linux programming, we treat BRAM as **Environment Buffers** - data structures that are:

- **Available at program start**: Loaded before application logic executes
- **Specified externally**: Populated by the Python client, not hardcoded in RTL
- **Immutable during runtime**: Set once during loading, read-only thereafter

This is analogous to environment variables (`$PATH`, `$HOME`) that a process inherits at startup.

### BRAM Buffer Specification

| Parameter | Current | Future |
|-----------|---------|--------|
| Buffer size | 4 KB (1024 × 32-bit words) | 16 KB (4 × 4 KB banks) |
| Address width | 12-bit (byte) / 10-bit (word) | 14-bit (byte) / 12-bit (word) |
| Data width | 32-bit | 32-bit |
| Access pattern | Sequential write, random read | Same |

**Note**: The 4 KB size in `volo_bram_loader.vhd` is arbitrary. Moku:Go has sufficient BRAM for 16 KB or more.

### Loading Protocol

During P1, CR2-CR15 serve as the **BRAM loader interface**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CR USAGE DURING LOADING PHASE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  CR0:  FORGE control (RUN bits) - same as runtime                       │
│  CR1:  Reserved                                                         │
│                                                                         │
│  ─── BRAM LOADER INTERFACE (P1 only) ───                                │
│                                                                         │
│  CR2:  [0]     loader_start      - Begin loading sequence               │
│        [31:16] word_count        - Number of 32-bit words to load       │
│                                                                         │
│  CR3:  [11:0]  bram_addr         - Write address (word-aligned)         │
│                                                                         │
│  CR4:  [31:0]  bram_data         - 32-bit data to write                 │
│                                                                         │
│  CR5:  [0]     write_strobe      - Pulse to commit write                │
│                                                                         │
│  CR6-CR15: Reserved for extended protocol / multi-bank support          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Loading Sequence (Python)

```python
def load_environment(moku, buffer: bytes):
    """
    Load Environment Buffer into BRAM during P1.

    IMPORTANT: This MUST be called even if buffer is unused.
    A consistent loading sequence ensures reproducible behavior.
    """
    # Convert bytes to 32-bit words
    words = [
        int.from_bytes(buffer[i:i+4], 'little')
        for i in range(0, len(buffer), 4)
    ]

    # Start loading
    moku.set_control(2, (len(words) << 16) | 0x0001)  # word_count + start

    # Write each word
    for addr, data in enumerate(words):
        moku.set_control(3, addr)       # Address
        moku.set_control(4, data)       # Data
        moku.set_control(5, 0x0001)     # Strobe high
        moku.set_control(5, 0x0000)     # Strobe low

    # Loading complete - CR2-CR15 now revert to application semantics
```

### Mandatory Loading Policy

**Design decision**: ALL Python clients MUST execute the BRAM loading sequence, even if the Environment Buffer is empty or unused.

Rationale:
1. **Reproducibility**: Same initialization path regardless of application mode
2. **Encourages usage**: Developers see the mechanism and consider using it
3. **Debugging**: Known-good state in BRAM aids troubleshooting
4. **Future-proofing**: Adding Environment data doesn't change client structure

```python
# Even for simple one-off mode, load an empty/default environment
env = DPDEnvironment()  # Default: zeros or sentinel values
env.load(moku)          # Always called

# Then proceed to application configuration
config = DPDConfig(...)
config.apply(moku)
```

### P1 → P2 Transition

The transition from LOADING to RUNTIME occurs when:

1. BRAM loading is complete (loader FSM in DONE state)
2. Client writes application configuration to CR2-CR10
3. Client arms the FSM via CR0

```python
# P1 complete, transition to P2
config = DPDConfig(
    trig_out_voltage=2000,
    intensity_voltage=1500,
    # ...
)
moku.set_controls(config.to_app_regs_list())  # CR2-CR10 now app config
moku.set_control(0, CR0.RUN_ARMED)            # P2: Runtime begins
```

---

## P2: Runtime Phase (Application Active)

### CR Semantics in Runtime

During P2, Control Registers have their "normal" application semantics:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CR USAGE DURING RUNTIME PHASE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  CR0:  Lifecycle control (FORGE + arm/trigger/fault)                    │
│  CR1:  Campaign control (abort, pause)                                  │
│  CR2:  Trigger threshold + trigger output voltage                       │
│  CR3:  Intensity max voltage + intensity output voltage                 │
│  CR4:  Trigger pulse duration                                           │
│  CR5:  Intensity pulse duration                                         │
│  CR6:  Trigger wait timeout                                             │
│  CR7:  Cooldown interval                                                │
│  CR8:  Monitor control + mode config                                    │
│  CR9:  Monitor window start                                             │
│  CR10: Monitor window duration                                          │
│  CR11-CR15: Reserved / campaign statistics                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Environment Buffer Access

During runtime, the application reads from Environment Buffers but cannot write:

```vhdl
-- In DPD_main.vhd (runtime)
intensity_value <= env_bram_data(15 downto 0);  -- Read from LUT
-- No write path exists - BRAM is read-only during P2
```

---

## Environment Buffer Structures

### IntensityLUT

A lookup table mapping percentage (0-100%) to output voltage (mV).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INTENSITY LUT STRUCTURE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Base Address: 0x000                                                    │
│  Entry Count:  101 (indices 0-100)                                      │
│  Entry Width:  16-bit signed (mV)                                       │
│  Word Packing: One entry per 32-bit word (upper 16 bits unused)         │
│                                                                         │
│  ┌────────┬────────────────────────────────────────────────────────┐    │
│  │ Index  │ Meaning                                                │    │
│  ├────────┼────────────────────────────────────────────────────────┤    │
│  │   0    │ 0% intensity → 0x0000 (0 mV)                           │    │
│  │   1    │ 1% intensity → computed from max_voltage               │    │
│  │  ...   │ ...                                                    │    │
│  │  50    │ 50% intensity                                          │    │
│  │  ...   │ ...                                                    │    │
│  │ 100    │ 100% intensity → max_voltage (≤ 3300 mV)               │    │
│  └────────┴────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Total Size: 101 words × 4 bytes = 404 bytes                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Campaign Parameters

Fixed parameters for campaign mode (set once, used throughout campaign).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CAMPAIGN PARAMETERS STRUCTURE                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Base Address: 0x100 (after IntensityLUT)                               │
│                                                                         │
│  ┌────────┬──────────────────┬─────────────────────────────────────┐    │
│  │ Offset │ Field            │ Description                         │    │
│  ├────────┼──────────────────┼─────────────────────────────────────┤    │
│  │ 0x00   │ trigger_count    │ N = number of triggers in campaign  │    │
│  │ 0x04   │ inter_pulse_us   │ Delay between pulses (microseconds) │    │
│  │ 0x08   │ intensity_profile│ 0=constant, 1=ramp, 2=custom LUT    │    │
│  │ 0x0C   │ fault_threshold  │ Max faults before campaign abort    │    │
│  │ 0x10   │ reserved[4]      │ Future expansion                    │    │
│  └────────┴──────────────────┴─────────────────────────────────────┘    │
│                                                                         │
│  Total Size: 32 bytes (8 words)                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Memory Map Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ENVIRONMENT BUFFER MEMORY MAP                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Address Range    │ Size      │ Structure                               │
│  ─────────────────┼───────────┼─────────────────────────────────────    │
│  0x000 - 0x194    │ 404 bytes │ IntensityLUT[101]                       │
│  0x100 - 0x11F    │ 32 bytes  │ CampaignParams                          │
│  0x120 - 0xFFF    │ ~3.5 KB   │ Reserved / Future expansion             │
│                                                                         │
│  Total: 4 KB (current) / 16 KB (future)                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Summary

| Phase | Name | CR0[31:29] | CR2-CR15 Semantics | BRAM Access |
|-------|------|------------|--------------------| ------------|
| **P0** | NULL | `000` | Undefined (all zeros) | N/A |
| **P1** | LOADING | `111` | BRAM loader protocol | Write |
| **P2** | RUNTIME | `111` | Application config | Read-only |

---

## Design Rationale

### Why Environment Buffers?

1. **Separation of concerns**: Large data structures (LUTs, tables) don't consume CR address space
2. **Immutability**: Once loaded, parameters can't be accidentally modified during operation
3. **Flexibility**: Python computes complex curves; RTL just indexes into pre-computed values
4. **Determinism**: Same loading sequence every time, regardless of operating mode

### Why Mandatory Loading?

1. **Single code path**: Simplifies testing and debugging
2. **Known state**: BRAM contents are always defined (no uninitialized memory)
3. **Future compatibility**: Adding Environment data doesn't require client restructuring

### Why Time-Division Multiplexing on CRs?

1. **Register scarcity**: Only 16 CRs available; can't dedicate 5 to loader
2. **Phase separation**: Loading and runtime are mutually exclusive
3. **Simplicity**: No mode bits needed; phase determines semantics

---

## References

- [API v4.0](api-v4.md) - Runtime register calling convention
- [Network Register Sync](network-register-sync.md) - Sync-safe gating
- [volo_bram_loader.vhd](../volo_bram_loader.vhd) - Reference BRAM loader implementation

---

## Open Questions

1. **Buffer size**: Should we upgrade to 16 KB now, or keep 4 KB for simplicity?
2. **Multi-bank**: Should Environment Buffers span multiple BRAM banks for larger datasets?
3. **Checksum**: Should the loader verify buffer integrity (CRC/checksum)?
4. **Default values**: What should empty/unused Environment Buffers contain? (zeros? sentinels?)
