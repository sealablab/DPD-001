---
created: 2025-11-28
modified: 2025-11-28
status: DRAFT
---
# LOAD-FSM Specification

This document specifies the LOADER module's Finite State Machine, which handles populating ENV_BBUFs with configuration data from the Python client.

## Overview

The LOADER module receives data from the Python client via Control Registers and writes it to 1-4 BRAM buffers (ENV_BBUFs). It uses a "blind handshake" protocol where both sides agree on fixed timing - no feedback path exists except HVS observation via oscilloscope.

```mermaid
stateDiagram-v2
    [*] --> LOAD_P0: RUNL from BOOT

    state "LOAD_P0 (000000)" as LOAD_P0
    state "LOAD_P1 (000001)" as LOAD_P1
    state "LOAD_P2 (000010)" as LOAD_P2
    state "LOAD_P3 (000011)" as LOAD_P3
    state "FAULT (111111)" as FAULT

    LOAD_P0 --> LOAD_P1: Setup strobe falling edge
    LOAD_P1 --> LOAD_P1: Data strobe (offset < 1024)
    LOAD_P1 --> LOAD_P2: Data strobe (offset = 1024)
    LOAD_P2 --> LOAD_P3: CRC match
    LOAD_P2 --> FAULT: CRC mismatch
    LOAD_P3 --> BOOT_P1: RET

    FAULT --> BOOT_P0: fault_clear
```

## State Definitions

| State | 6-bit Encoding | HVS Voltage | Description |
|-------|----------------|-------------|-------------|
| LOAD_P0 | `000000` | 0.0V | Setup phase - waiting for config |
| LOAD_P1 | `000001` | 0.2V | Transfer phase - receiving data |
| LOAD_P2 | `000010` | 0.4V | Validate phase - checking CRCs |
| LOAD_P3 | `000011` | 0.6V | Complete - ready for RET |
| FAULT | `111111` | Negative | CRC mismatch or protocol error |

> **Note:** LOADER uses the same compressed HVS range as BOOT (0.2V steps) for consistency during boot-time debugging.

## CR Allocation for LOADER

When LOADER is active, it uses CR0 control bits and CR1-CR4 for data:

```
CR0[31:29] = RUN gate (must remain set)
CR0[26]    = L (must remain set - LOADER selected)
CR0[24]    = RET (return to BOOT_P1 when asserted)
CR0[23:22] = Buffer count (00=1, 01=2, 10=3, 11=4)
CR0[21]    = Data strobe (falling edge triggers action)
CR0[20:0]  = Reserved

CR1 = ENV_BBUF_0: CRC-16 during setup, data word during transfer
CR2 = ENV_BBUF_1: CRC-16 during setup, data word during transfer
CR3 = ENV_BBUF_2: CRC-16 during setup, data word during transfer
CR4 = ENV_BBUF_3: CRC-16 during setup, data word during transfer
```

### Buffer Count Encoding

| CR0[23:22] | Buffers Used | CRs Active |
|------------|--------------|------------|
| `00` | 1 buffer | CR1 only |
| `01` | 2 buffers | CR1-CR2 |
| `10` | 3 buffers | CR1-CR3 |
| `11` | 4 buffers | CR1-CR4 |

## Protocol: Blind Handshake

Since the Python client cannot receive feedback from the bitstream (except via oscilloscope streaming), both sides agree on a **fixed phase count** and **generous timing** per phase.

### Timing Constants

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| T_SETUP | 10ms | Time after setup strobe before first data |
| T_WORD | 1ms | Time between data strobes |
| T_VALIDATE | 10ms | Time for CRC validation after final data |

> **Note:** These timings are intentionally slow. Loading 4KB per buffer takes ~1 second. This happens once at startup and reliability is more important than speed.

### Protocol Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 0: Setup                                                  │
├─────────────────────────────────────────────────────────────────┤
│ 1. Client sets CR0[23:22] = buffer_count                        │
│ 2. Client sets CR1-CR4 = expected CRC-16 values (one per buf)   │
│ 3. Client sets CR0[21] = 1 (strobe HIGH)                        │
│ 4. Client waits T_STROBE (1ms)                                  │
│ 5. Client sets CR0[21] = 0 (strobe LOW) ← LOADER latches config │
│ 6. Client waits T_SETUP (10ms)                                  │
│                                                                 │
│ LOADER: Latches buffer_count and CRC values on falling edge     │
│ LOADER: Initializes offset = 0, running CRCs = 0xFFFF           │
│ LOADER: Transitions to LOAD_P1                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Phase 1..1024: Data Transfer                                    │
├─────────────────────────────────────────────────────────────────┤
│ For each word (offset 0 to 1023):                               │
│   1. Client sets CR1-CR4 = data words for all buffers           │
│   2. Client sets CR0[21] = 1 (strobe HIGH)                      │
│   3. Client waits T_STROBE (1ms)                                │
│   4. Client sets CR0[21] = 0 (strobe LOW) ← LOADER writes       │
│   5. Client waits T_WORD (1ms)                                  │
│                                                                 │
│ LOADER: On falling edge:                                        │
│   - Writes CR1 → ENV_BBUF_0[offset] (if enabled)                │
│   - Writes CR2 → ENV_BBUF_1[offset] (if enabled)                │
│   - Writes CR3 → ENV_BBUF_2[offset] (if enabled)                │
│   - Writes CR4 → ENV_BBUF_3[offset] (if enabled)                │
│   - Updates running CRC for each buffer                         │
│   - Increments offset                                           │
│                                                                 │
│ After offset reaches 1024:                                      │
│ LOADER: Transitions to LOAD_P2                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Phase 1025: Validation                                          │
├─────────────────────────────────────────────────────────────────┤
│ Client waits T_VALIDATE (10ms)                                  │
│                                                                 │
│ LOADER: Compares running CRCs vs expected CRCs                  │
│   - All match → Transitions to LOAD_P3 (Complete)               │
│   - Any mismatch → Transitions to FAULT                         │
│                                                                 │
│ Client: Polls OutputC via oscilloscope                          │
│   - Positive voltage (0.6V) = LOAD_P3 = Success                 │
│   - Negative voltage = FAULT = CRC mismatch                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Phase 1026: Return                                              │
├─────────────────────────────────────────────────────────────────┤
│ Client sets CR0[24] = 1 (RET)                                   │
│                                                                 │
│ LOADER: Returns control to BOOT_P1                              │
│ BOOT: OutputC shows BOOT_P1 voltage (0.2V)                      │
└─────────────────────────────────────────────────────────────────┘
```

## CRC-16-CCITT Implementation

The LOADER uses CRC-16-CCITT for simple error detection:

- **Polynomial:** 0x1021 (x^16 + x^12 + x^5 + 1)
- **Initial value:** 0xFFFF
- **Input:** 32-bit words, processed MSB first

### VHDL Implementation (LFSR)

```vhdl
-- CRC-16-CCITT update for 32-bit word
-- Processes one byte at a time (4 iterations per word)
function crc16_update(crc : unsigned(15 downto 0);
                      data : std_logic_vector(31 downto 0))
    return unsigned is
    variable c : unsigned(15 downto 0) := crc;
    variable d : std_logic_vector(7 downto 0);
begin
    for i in 3 downto 0 loop  -- Process 4 bytes, MSB first
        d := data(i*8+7 downto i*8);
        for j in 7 downto 0 loop
            if (c(15) xor d(j)) = '1' then
                c := (c(14 downto 0) & '0') xor x"1021";
            else
                c := c(14 downto 0) & '0';
            end if;
        end loop;
    end loop;
    return c;
end function;
```

### Python Client CRC Calculation

```python
import crcmod

# CRC-16-CCITT
crc16_func = crcmod.predefined.mkCrcFun('crc-ccitt-false')

def compute_buffer_crc(data: bytes) -> int:
    """Compute CRC-16 for a 4KB buffer."""
    assert len(data) == 4096
    return crc16_func(data)
```

## Design Rationale

### Why Blind Handshake?

The Moku platform provides no read-back path for Control Registers or internal state. The only feedback mechanism is streaming OutputC via oscilloscope. Rather than implement complex retry logic based on oscilloscope readings, we use generous fixed timing that ensures success under all reasonable conditions.

### Why Falling Edge?

Rising edge detection can suffer from glitches if the client's write isn't atomic. Falling edge is more robust:
1. Client sets strobe HIGH
2. Client waits (strobe is stable HIGH)
3. Client sets strobe LOW
4. LOADER acts on the clean falling edge

### Why Parallel Writes?

Writing all 4 buffers in parallel with a shared offset pointer:
1. Simplifies address generation (single counter)
2. Reduces protocol complexity (one strobe per offset, not per buffer)
3. Makes timing predictable (fixed 1024 strobes regardless of buffer count)

### Why CRC-16 Not CRC-32?

CRC-16-CCITT is:
1. Simple LFSR implementation (~20 lines VHDL)
2. Sufficient for detecting bit flips over 4KB
3. Fits in 16 bits (easy to pack into CR registers)
4. Well-supported in Python (`crcmod`)

We're not protecting against adversarial corruption - just network/timing glitches.

### Why 1ms Per Word?

At 1ms per word:
- 1024 words × 1ms = ~1 second per buffer load
- Network RTT is typically 10-50ms for Moku
- 1ms provides 10-100x margin over network latency

This is deliberately conservative. Speed is not a concern for one-time startup loading.

## HVS Integration

LOADER uses the same compressed HVS range as BOOT:

```vhdl
loader_hvs_encoder : forge_hierarchical_encoder
    generic map (
        DIGITAL_UNITS_PER_STATE => 1311  -- ~0.2V steps
    )
    port map (...);
```

| OutputC Voltage | LOADER State |
|-----------------|--------------|
| 0.0V | LOAD_P0 (setup) |
| 0.2V | LOAD_P1 (transfer) |
| 0.4V | LOAD_P2 (validate) |
| 0.6V | LOAD_P3 (complete) |
| Negative | FAULT |

## Python Client Example

```python
import time
from moku.instruments import CloudCompile

class BootLoader:
    T_STROBE = 0.001   # 1ms strobe width
    T_SETUP = 0.010    # 10ms setup delay
    T_WORD = 0.001     # 1ms between words
    T_VALIDATE = 0.010 # 10ms validation delay

    def __init__(self, moku: CloudCompile):
        self.moku = moku

    def load_buffers(self, buffers: list[bytes]) -> bool:
        """Load 1-4 buffers (each 4KB) into ENV_BBUFs."""
        assert 1 <= len(buffers) <= 4
        assert all(len(b) == 4096 for b in buffers)

        # Compute CRCs
        crcs = [compute_buffer_crc(b) for b in buffers]
        crcs += [0] * (4 - len(crcs))  # Pad to 4

        # Phase 0: Setup
        buffer_count = len(buffers) - 1  # 0=1buf, 1=2buf, etc.
        self.moku.set_control(0, 0xE4000000 | (buffer_count << 22))
        self.moku.set_control(1, crcs[0])
        self.moku.set_control(2, crcs[1])
        self.moku.set_control(3, crcs[2])
        self.moku.set_control(4, crcs[3])

        # Strobe setup
        self._strobe()
        time.sleep(self.T_SETUP)

        # Phase 1..1024: Data transfer
        for offset in range(1024):
            for i, buf in enumerate(buffers):
                word = int.from_bytes(buf[offset*4:(offset+1)*4], 'big')
                self.moku.set_control(i + 1, word)
            self._strobe()
            time.sleep(self.T_WORD)

        # Phase 1025: Wait for validation
        time.sleep(self.T_VALIDATE)

        # Check result via oscilloscope (implementation varies)
        return self._check_success()

    def _strobe(self):
        """Pulse CR0[21] high then low."""
        cr0 = self.moku.get_control(0)
        self.moku.set_control(0, cr0 | (1 << 21))
        time.sleep(self.T_STROBE)
        self.moku.set_control(0, cr0 & ~(1 << 21))

    def _check_success(self) -> bool:
        """Check OutputC via oscilloscope for success/fault."""
        # Implementation depends on oscilloscope streaming setup
        # Returns True if OutputC shows LOAD_P3 voltage (0.6V)
        # Returns False if OutputC shows negative voltage (FAULT)
        pass
```

## See Also

- [BOOT-FSM-spec](../BOOT-FSM-spec.md) - BOOT module specification
- [boot-process-terms](../boot-process-terms.md) - Naming conventions
- [volo_bram_loader.vhd](../../rtl/volo_bram_loader.vhd) - Reference implementation (simpler protocol)
