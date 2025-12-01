---
created: 2025-11-28
modified: 2025-11-30 16:21:47
status: PLAN
accessed: 2025-11-30 16:20:12
---
# LOADER Implementation Plan

This document outlines the implementation strategy for the LOADER module based on the [LOAD-FSM-spec](LOAD-FSM-spec.md).

## Overview

The implementation has three main tracks:
1. **VHDL RTL** - The hardware implementation
2. **CocoTB Simulation** - Verification in simulation
3. **Python CLI** - The `RUN>` shell interface for hardware interaction

---

## Track 1: VHDL Implementation

### Shared Package: forge_common_pkg.vhd

**CRITICAL:** All BOOT subsystem modules MUST use `rtl/forge_common_pkg.vhd` as the single source of truth for CR0 bit definitions. This package is shared across BOOT, BIOS, LOADER, and PROG modules.

```vhdl
-- Every module that touches CR0 must include:
library WORK;
use WORK.forge_common_pkg.all;

-- Then use named constants, NOT hardcoded values:
if cr0(SEL_LOADER_BIT) = '1' then ...    -- Good
if cr0(26) = '1' then ...                 -- Bad (hardcoded)

-- Use command constants for Python/VHDL alignment:
-- CMD_RUN, CMD_RUNP, CMD_RUNB, CMD_RUNL, CMD_RUNR, CMD_RET
```

The package provides:
- **RUN gate bits**: `RUN_READY_BIT`, `RUN_USER_BIT`, `RUN_CLK_BIT`
- **Module select bits**: `SEL_PROG_BIT`, `SEL_BIOS_BIT`, `SEL_LOADER_BIT`, `SEL_RESET_BIT`
- **LOADER control**: `LOADER_BUFCNT_HI/LO`, `LOADER_STROBE_BIT`
- **FSM states**: `BOOT_STATE_*`, `LOAD_STATE_*`
- **Parameters**: `ENV_BBUF_*`, `HVS_*`, `CRC16_*`
- **Helper functions**: `is_run_active()`, `is_valid_select()`, `get_loader_bufcnt()`

### File Structure

```
rtl/
├── forge_common_pkg.vhd      # AUTHORITATIVE: CR0 bit definitions (SHARED)
└── boot/
    ├── L2_BUFF_LOADER.vhd    # Main LOADER FSM (exists as stub)
    ├── L2_BUFF_LOADER.vhd.md # Documentation (exists as stub)
    └── loader_crc16.vhd      # CRC-16-CCITT calculator (NEW)
```

### Implementation Order

#### Phase 1: CRC Module
1. **loader_crc16.vhd** - CRC-16-CCITT calculator
   - Uses `CRC16_POLYNOMIAL` and `CRC16_INIT` from `forge_common_pkg`
   - Input: 32-bit word, current CRC
   - Output: updated CRC
   - Pure combinatorial (no clock)
   - Test standalone first

#### Phase 2: Core FSM
3. **L2_BUFF_LOADER.vhd** - Main LOADER module
   - Inputs: CR0-CR4, Clk, Reset
   - Outputs: state_vector, status_vector, bram_* signals
   - Internal: offset counter, 4x running CRCs, 4x expected CRCs

#### Phase 3: Integration
4. **B0_BOOT_TOP.vhd** - Update to instantiate LOADER
   - Add LOAD_ACTIVE state handling
   - Wire combinatorial output mux
   - Route ENV_BBUF signals to LOADER

### Key VHDL Design Decisions

```vhdl
-- Strobe edge detection (falling edge)
strobe_prev <= CR0(21) when rising_edge(Clk);
strobe_falling <= strobe_prev and not CR0(21);

-- Parallel BRAM writes (all buffers same offset)
gen_bram: for i in 0 to 3 generate
    env_bbuf_we(i) <= '1' when (state = LOAD_P1 and
                                strobe_falling = '1' and
                                i < buffer_count) else '0';
    env_bbuf_addr(i) <= std_logic_vector(offset);
    env_bbuf_data(i) <= CR(i+1);  -- CR1-CR4
end generate;
```

---

## Track 2: CocoTB Simulation Tests

### File Structure

```
tests/
├── lib/
│   ├── boot_hw.py             # BOOT-specific constants (imports boot_constants.py)
│   └── boot_timing.py         # BOOT/LOADER test timing
├── adapters/
│   └── base.py                # Updated: AsyncFSMStateReader with configurable units_per_state
└── sim/
    ├── boot_fsm/              # NEW: BOOT dispatcher tests
    │   ├── __init__.py
    │   └── P1_basic.py        # BOOT state transitions
    └── loader/                # NEW: LOADER tests
        ├── __init__.py
        ├── helpers.py         # Strobe functions, CRC calc
        ├── P1_basic.py        # Basic functionality tests
        └── P2_crc.py          # CRC validation tests
```

### Test Cases

#### P1_basic.py - Smoke Tests
```python
async def test_loader_enters_load_p0_on_runl():
    """BOOT-P1 → LOAD_P0 when RUNL asserted"""

async def test_loader_accepts_setup_strobe():
    """Config latched on setup strobe falling edge"""

async def test_loader_increments_offset():
    """Offset increments on each data strobe"""

async def test_loader_completes_after_1024_words():
    """Transitions to LOAD_P2 after 1024 strobes"""

async def test_loader_returns_on_ret():
    """LOAD_P3 → BOOT_P1 when RET asserted"""
```

#### P2_crc_validation.py - CRC Tests
```python
async def test_crc_match_success():
    """Correct CRC → LOAD_P3"""

async def test_crc_mismatch_fault():
    """Wrong CRC → FAULT state"""

async def test_partial_buffer_crc():
    """CRC only checked for enabled buffers"""
```

### Simulation Timing

For simulation, use accelerated timing:
```python
# Sim constants (much faster than real hardware)
T_STROBE_SIM = 10  # cycles (not 1ms)
T_WORD_SIM = 20    # cycles between words
```

---

## Track 3: Python CLI (`RUN>` Shell)

### Shared Constants: Alignment with VHDL

The Python CLI must use the same CR0 bit definitions as `forge_common_pkg.vhd`. Create a Python mirror of the VHDL constants:

```python
# py_tools/boot_constants.py - MUST match forge_common_pkg.vhd

# RUN Gate (CR0[31:29])
RUN_READY_BIT = 31
RUN_USER_BIT = 30
RUN_CLK_BIT = 29

# Module Select (CR0[28:25])
SEL_PROG_BIT = 28
SEL_BIOS_BIT = 27
SEL_LOADER_BIT = 26
SEL_RESET_BIT = 25

# Command values (must match CMD_* in VHDL)
CMD_RUN  = 0xE0000000
CMD_RUNP = 0xF0000000
CMD_RUNB = 0xE8000000
CMD_RUNL = 0xE4000000
CMD_RUNR = 0xE2000000
CMD_RET  = 0xE1000000
```

### File Structure

```
py_tools/
├── boot_constants.py         # CR0 bit definitions (mirrors forge_common_pkg.vhd)
├── boot_cli.py               # Main CLI entry point (NEW)
├── boot_loader.py            # LOADER protocol implementation (NEW)
└── moku_cli_common.py        # Existing common utilities
```

### CLI Design: `RUN>` Prompt

```
$ python -m py_tools.boot_cli 192.168.1.100 --bitstream DPD.tar

Connecting to Moku @ 192.168.1.100...
Loading bitstream DPD.tar...
Platform settled.

RUN> help
Commands:
  RUN      - Set RUN bits (BOOT-P0 → BOOT-P1)
  RUNP     - Transfer to PROG (one-way)
  RUNB     - Transfer to BIOS
  RUNL     - Transfer to LOADER
  RUNR     - Soft reset to BOOT-P0
  RET      - Return to BOOT-P1 (from BIOS/LOADER)

  LOAD <file> [file2] [file3] [file4]  - Load 1-4 buffer files
  STATUS   - Show current state (from OutputC)
  CR0      - Show CR0 value
  QUIT     - Exit

RUN> RUNL
→ LOAD_P0 (waiting for setup)

LOAD> LOAD env0.bin env1.bin
Loading 2 buffers (8KB total)...
  ENV_BBUF_0: env0.bin (4096 bytes, CRC=0x1234)
  ENV_BBUF_1: env1.bin (4096 bytes, CRC=0x5678)
Transferring... [████████████████████] 100%
Validating CRCs...
→ LOAD_P3 (complete)

LOAD> RET
→ BOOT-P1

RUN> RUNP
→ PROG_ACTIVE (application running)
Goodbye!
```

### Implementation: boot_loader.py

```python
class BootLoader:
    """Implements LOADER protocol from LOAD-FSM-spec."""

    def __init__(self, moku: CloudCompile, oscilloscope=None):
        self.moku = moku
        self.scope = oscilloscope  # Optional, for state verification

    def load_buffers(self, files: list[Path],
                     progress_callback=None) -> bool:
        """Load 1-4 files into ENV_BBUFs."""
        # 1. Read files, compute CRCs
        # 2. Setup phase (buffer count + CRCs)
        # 3. Transfer phase (1024 strobes)
        # 4. Validate phase (check OutputC)

    def _strobe(self):
        """Pulse CR0[21] high then low."""

    def _read_state(self) -> str:
        """Read OutputC via oscilloscope, decode HVS."""
```

### Implementation: boot_cli.py

```python
import cmd
from pathlib import Path

class BootShell(cmd.Cmd):
    prompt = 'RUN> '

    def __init__(self, moku_ip: str, bitstream: Path):
        super().__init__()
        self.moku = CloudCompile(moku_ip)
        self.loader = BootLoader(self.moku)
        # ... setup oscilloscope for state reading

    def do_RUNL(self, arg):
        """Transfer to LOADER"""
        self.moku.set_control(0, 0xE4000000)
        self.prompt = 'LOAD> '

    def do_LOAD(self, arg):
        """LOAD file1 [file2] [file3] [file4]"""
        files = [Path(f) for f in arg.split()]
        success = self.loader.load_buffers(files,
            progress_callback=self._show_progress)
        if success:
            print("→ LOAD_P3 (complete)")
        else:
            print("→ FAULT (CRC mismatch)")

    def do_RET(self, arg):
        """Return to BOOT-P1"""
        self.moku.set_control(0, 0xE1000000)
        self.prompt = 'RUN> '
```

---

## Implementation Schedule

### Week 1: Foundation
- [ ] Create `loader_pkg.vhd` with constants
- [ ] Implement and test `loader_crc16.vhd` standalone
- [ ] Set up `tests/sim/loader/` test structure
- [ ] Write P1 basic test stubs

### Week 2: Core LOADER
- [ ] Implement `L2_BUFF_LOADER.vhd` FSM
- [ ] Write BRAM interface logic
- [ ] Pass P1 basic tests in simulation
- [ ] Write P2 CRC validation tests

### Week 3: Integration
- [ ] Update `B0_BOOT_TOP.vhd` with LOADER instantiation
- [ ] Implement output muxing
- [ ] Full BOOT → LOADER → BOOT round-trip test

### Week 4: CLI & Hardware
- [ ] Implement `boot_loader.py` protocol
- [ ] Implement `boot_cli.py` shell
- [ ] Hardware test on real Moku
- [ ] Documentation cleanup

---

## Dependencies

### Shared Package (AUTHORITATIVE)
- **`rtl/forge_common_pkg.vhd`** - Single source of truth for CR0 bit definitions
  - All VHDL modules MUST use this package
  - Python code MUST mirror these constants in `py_tools/boot_constants.py`

### Existing Code to Reuse
- `forge_hierarchical_encoder.vhd` - HVS encoding (use with `HVS_BOOT_UNITS_PER_STATE`)
- `tests/sim/conftest.py` - CocoTB fixtures
- `py_tools/moku_cli_common.py` - Moku connection helpers

### External Dependencies
- Python: `crcmod` for CRC-16-CCITT
- CocoTB: Standard test framework
- GHDL: VHDL simulation

---

## Design Decisions (Resolved)

1. **ENV_BBUF BRAM instantiation**: ✅ BOOT module owns the BRAMs (synthesized as TOP on MCC platform)

2. **State persistence**: ✅ RUNR resets LOADER state (full reset to BOOT_P0)

3. **Multiple load cycles**: ✅ Yes - RUNL → load → RET → RUNL → load again works

4. **Timeout**: ✅ No watchdog - Python client is responsible for completing transfer

---

## See Also

- [LOAD-FSM-spec](LOAD-FSM-spec.md) - Authoritative FSM specification
- [BOOT-FSM-spec](../BOOT-FSM-spec.md) - BOOT module specification
- [boot-process-terms](../boot-process-terms.md) - Naming conventions
