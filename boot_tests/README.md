# BOOT Subsystem Tests

CocoTB simulation tests for the BOOT subsystem (BOOT dispatcher and LOADER).

## Quick Start

```bash
# Run BOOT FSM tests
cd boot_tests
python run.py --test-module boot_fsm.P1_basic

# Run LOADER tests
python run.py --test-module loader.P1_basic

# Verbose output with waveforms
python run.py --test-module boot_fsm.P1_basic --verbose --waves
```

## Directory Structure

```
boot_tests/
├── run.py                 # Unified test runner (sim/hw)
├── lib/
│   └── __init__.py        # BOOT-specific constants + tests/lib re-exports
├── sim/
│   ├── conftest.py        # Shared CocoTB fixtures
│   ├── boot_fsm/
│   │   ├── __init__.py
│   │   └── P1_basic.py    # BOOT dispatcher FSM tests
│   └── loader/
│       ├── __init__.py
│       └── P1_basic.py    # LOADER FSM tests
└── adapters/              # (future) async harness adapters
```

## Test Levels

- **P1 (BASIC)**: Fast smoke tests for state transitions
- **P2 (INTERMEDIATE)**: CRC validation, fault injection (planned)
- **P3 (COMPREHENSIVE)**: Stress testing (planned)

## HVS State Voltages

BOOT uses compressed 0.2V steps (vs DPD's 0.5V):

| State | Voltage | Digital |
|-------|---------|---------|
| BOOT_P0 | 0.0V | 0 |
| BOOT_P1 | 0.2V | 1311 |
| BIOS_ACTIVE | 0.4V | 2622 |
| LOAD_ACTIVE | 0.6V | 3933 |
| PROG_ACTIVE | 0.8V | 5244 |
| FAULT | Negative | < -150 |

## See Also

- `rtl/boot/` - VHDL source files
- `py_tools/boot_constants.py` - Python constants
- `docs/BOOT-FSM-spec.md` - BOOT specification
- `docs/LOAD-FSM-spec.md` - LOADER specification
