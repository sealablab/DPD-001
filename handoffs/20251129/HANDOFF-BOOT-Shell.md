---
created: 2025-11-29
session: BOOT validation + shell CLI
next_session: BOOT shell hardware integration + LOADER commands
branch: claude/resume-boot-validation-01Cm9G5dbMZR9Zv1cvyCzWC7
modified: 2025-11-28 20:40:32
accessed: 2025-11-28 20:40:55
---
# Session Handoff: BOOT Shell CLI Implementation

## What We Did This Session

### 1. Fixed BOOT Compilation Issues
- Renamed `CustomWrapper` → `BootWrapper` in `rtl/boot/BootWrapper_test_stub.vhd`
- Fixed VHDL naming conflict: `ret_bit` signal → `ret_active` (case collision with `RET_BIT` constant)
- BOOT subsystem now compiles cleanly with GHDL

### 2. Created Test Infrastructure
- Added `tests/sim/boot_run.py` - dedicated test runner for BOOT
- Restored `tests/sim/run.py` to DPD-only
- Ran BOOT tests: 4/6 pass (P0/P1/BIOS/PROG transitions work)
- Known test issues: LOAD_ACTIVE and RUNR tests fail due to OutputC muxing

### 3. Built Interactive BOOT Shell
Created `py_tools/boot_shell.py` with:

- **Context-aware prompts**: `INIT>`, `RUN>`, `BIOS>`, `LOAD[n]>`, `PROG$`
- **Esc → RET** key binding for BIOS/LOADER return
- **Tab completion** per context
- **Command registry pattern** for extensibility
- **Live HVS monitor thread** (20Hz polling)
- **Real-time bottom toolbar** showing voltage/state/connection

Key architectural decision: **Context is client-authoritative**
- Shell assumes RUN+X commands work
- Interprets HVS readings within assumed context
- Same voltage, different meaning per module

### 4. Created Documentation
- `docs/bootup-proposal/DRAFT-boot-shell-architecture.md`
- `docs/bootup-proposal/DRAFT-hvs-context-interpretation.md`

## Current State

```
Branch: claude/resume-boot-validation-01Cm9G5dbMZR9Zv1cvyCzWC7
Status: Clean, pushed
```

### Files Modified/Added
```
rtl/boot/BootWrapper_test_stub.vhd  # Entity renamed to BootWrapper
rtl/boot/B0_BOOT_TOP.vhd            # Architecture binding + ret_active fix
tests/sim/boot_run.py               # NEW: BOOT test runner
tests/sim/run.py                    # Restored to DPD-only
py_tools/boot_shell.py              # NEW: Interactive CLI (~500 lines)
docs/bootup-proposal/DRAFT-*.md     # NEW: Architecture docs
```

## Shell Usage

```bash
# Simulation mode
python py_tools/boot_shell.py

# With hardware (not yet implemented)
python py_tools/boot_shell.py -d 192.168.1.100
```

Example session:
```
INIT> run
RUN> l
LOAD[0]> [Esc]
RUN> p
PROG$ _
```

## Next Session Tasks

### Priority 1: Hardware Integration
- Implement `HardwareInterface.connect()` with Moku SDK
- Implement `get_output_c()` for real HVS readings
- Test with actual device

### Priority 2: LOADER Commands
- `load <filename>` - Load buffer from file
- Progress tracking with CRC
- Strobe generation

### Priority 3: BIOS Commands
- `diag` - Run diagnostics
- `mem` - Memory test
- Other self-test functions

### Optional: UI Enhancements
- Full-screen mode with `prompt_toolkit` Application
- Session recording/playback
- Scriptable non-interactive mode

## Key Design Decisions

1. **Separate test runners**: `run.py` (DPD) and `boot_run.py` (BOOT)
2. **Client-authoritative context**: Shell assumes commands work
3. **`prompt_toolkit`**: Chosen for key bindings, live updates, styling
4. **Thread-safe state**: Lock-protected HVS data for monitor thread

## Dependencies Added

```
pip install prompt_toolkit
```

## Quick Reference

### Shell Key Bindings
| Key | Action |
|-----|--------|
| Esc | RET (return from BIOS/LOADER) |
| Tab | Command completion |
| Ctrl+C | Interrupt |
| Ctrl+D | Quit |

### Commands (RUN> context)
| Command | CR0 Value | Action |
|---------|-----------|--------|
| p/prog | 0xF0000000 | → PROG (one-way) |
| b/bios | 0xE8000000 | → BIOS |
| l/loader | 0xE4000000 | → LOADER |
| r/reset | 0xE2000000 | → P0 |

## Context for Next Session

Read these files:
```
py_tools/boot_shell.py              # Main implementation
py_tools/boot_constants.py          # Constants
docs/bootup-proposal/DRAFT-*.md     # Architecture docs
docs/BOOT-FSM-spec.md               # FSM specification
```
