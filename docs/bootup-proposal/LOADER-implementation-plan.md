---
created: 2025-11-28
modified: 2025-11-28 17:55:57
status: PLAN
accessed: 2025-11-28 17:56:11
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

### File Structure

```
rtl/boot/
├── L2_BUFF_LOADER.vhd        # Main LOADER FSM (exists as stub)
├── L2_BUFF_LOADER.vhd.md     # Documentation (exists as stub)
├── loader_crc16.vhd          # CRC-16-CCITT calculator (NEW)
├── loader_bram_ctrl.vhd      # BRAM write controller (NEW, optional)
└── loader_pkg.vhd            # Constants and types (NEW)
```

### Implementation Order

#### Phase 1: Package and CRC
1. **loader_pkg.vhd** - Define constants, types, FSM states
   - `LOAD_P0`, `LOAD_P1`, `LOAD_P2`, `LOAD_P3`, `FAULT` state constants
   - `WORDS_PER_BUFFER = 1024`
   - `CRC_INIT = 0xFFFF`

2. **loader_crc16.vhd** - CRC-16-CCITT calculator
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
tests/sim/
├── loader/                    # NEW test package
│   ├── __init__.py
│   ├── constants.py           # Test constants, timing
│   ├── helpers.py             # Strobe functions, CRC calc
│   ├── P1_basic.py            # Basic functionality tests
│   └── P2_crc_validation.py   # CRC mismatch tests
└── conftest.py                # Add loader fixtures
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

### File Structure

```
py_tools/
├── boot_cli.py               # Main CLI entry point (NEW)
├── boot_loader.py            # LOADER protocol implementation (NEW)
├── boot_constants.py         # CR0 bit definitions (NEW)
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

### Existing Code to Reuse
- `forge_hierarchical_encoder.vhd` - HVS encoding (use with 1311 units/state)
- `forge_common_pkg.vhd` - Common types
- `tests/sim/conftest.py` - CocoTB fixtures
- `py_tools/moku_cli_common.py` - Moku connection helpers

### External Dependencies
- Python: `crcmod` for CRC-16-CCITT
- CocoTB: Standard test framework
- GHDL: VHDL simulation

---

## Open Questions

1. **ENV_BBUF BRAM instantiation**: Should BOOT module own the BRAMs, or should they be instantiated at TOP level and passed down?

2. **State persistence**: Should LOADER preserve its state if user does RUNR (soft reset) while in LOAD_P1? Or always reset?

3. **Multiple load cycles**: Can user do RUNL → load → RET → RUNL → load again? (Spec implies yes)

4. **Timeout**: Should LOADER have a watchdog timeout if Python client disappears mid-transfer?

---

## See Also

- [LOAD-FSM-spec](LOAD-FSM-spec.md) - Authoritative FSM specification
- [BOOT-FSM-spec](../BOOT-FSM-spec.md) - BOOT module specification
- [boot-process-terms](../boot-process-terms.md) - Naming conventions
