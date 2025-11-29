# DPD / BOOT Test Suite

Unified test infrastructure for Demo Probe Driver (DPD) and the BOOT subsystem.
The same high‑level test patterns are used for simulation (CocoTB/GHDL) and
hardware (Moku), with async adapters hiding backend differences.

## Quick Start

### Simulation – DPD (application)

```bash
cd /Users/johnycsh/DPD/DPD-001/tests

# Run P1 basic DPD tests via unified runner
uv run python run.py

# Verbose output
uv run python run.py -v
```

### Simulation – BOOT / LOADER

```bash
cd /Users/johnycsh/DPD/DPD-001/tests/sim

# BOOT dispatcher P1 tests
uv run python boot_run.py

# LOADER P1 tests
TEST_MODULE=loader.P1_basic uv run python boot_run.py
```

### Hardware – DPD (application)

```bash
cd /Users/johnycsh/DPD/DPD-001/tests

# Basic hardware test
uv run python run.py --backend hw --device YOUR_IP --bitstream ../dpd-bits.tar

# With verbose logging
uv run python run.py --backend hw --device YOUR_IP --bitstream ../dpd-bits.tar -v

# Force disconnect existing connections
uv run python run.py --backend hw --device YOUR_IP --bitstream ../dpd-bits.tar --force

# With Moku API debug logging
uv run python run.py --backend hw --device YOUR_IP --bitstream ../dpd-bits.tar --debug
```

> **Note:** BOOT hardware tests will share the same adapters and hardware
> plumbing (`tests/hw/plumbing.py`) but are not wired into `run.py` yet.

## Command Line Options (DPD unified runner)

| Option | Description |
|--------|-------------|
| `--backend sim` | Use CocoTB/GHDL simulation (default) |
| `--backend hw` | Use Moku hardware |
| `--device IP` | Moku device IP address (required for hw) |
| `--bitstream PATH` | Path to CloudCompile bitstream (required for hw) |
| `--test-module NAME` | Test module to run (default: dpd.P1_basic) |
| `-v, --verbose` | Verbose output (DEBUG level) |
| `-f, --force` | Force disconnect existing connections |
| `--debug [FILE]` | Enable Moku debug logging (stderr or file) |
| `--waves` | Enable waveform capture (sim only) |

## Test Structure

```text
tests/
├── run.py              # Unified runner for DPD (sim + hw)
├── lib/                # Constants, utilities, test base classes (API v4.0)
│   ├── __init__.py     # Re-exports from py_tools + test-specific constants
│   ├── hw.py           # DPD hardware constants
│   ├── boot_hw.py      # BOOT hardware constants [PLANNED]
│   ├── timing.py       # DPD test timing (P1Timing, P2Timing)
│   ├── boot_timing.py  # BOOT/LOADER test timing [PLANNED]
│   └── tolerances.py   # HVS tolerances (sim vs hw)
├── adapters/           # Async adapters for sim/hw convergence
│   ├── base.py         # Abstract interfaces (configurable units_per_state)
│   ├── cocotb.py       # CocoTB implementation (simulation harness)
│   └── moku.py         # Moku hardware implementation (hardware harness)
├── shared/             # Control interface abstractions
├── hw/                 # Hardware-specific plumbing
│   ├── __init__.py
│   └── plumbing.py     # MokuSession context manager + routing for HVS
└── sim/                # Simulation tests and runners
    ├── run.py          # Sim-only DPD runner (alternative to tests/run.py --backend sim)
    ├── boot_run.py     # Sim-only BOOT/LOADER runner (CocoTB + GHDL)
    ├── dpd/            # DPD application tests
    │   └── P1_basic.py # P1 test suite (5 tests)
    ├── boot_fsm/       # BOOT dispatcher tests
    │   └── P1_basic.py # BOOT state transitions + HVS checks
    └── loader/         # LOADER module tests
        └── P1_basic.py # LOADER state transitions + CRC happy-path
```

## API v4.0

All tests use the v4.0 API where lifecycle controls are in CR0:

- `CR0[31:29]` – FORGE control (forge_ready, user_enable, clk_enable)
- `CR0[2]` – arm_enable (level-sensitive)
- `CR0[1]` – fault_clear (edge-triggered, auto-clear)
- `CR0[0]` – sw_trigger (edge-triggered, auto-clear)

See `docs/api-v4.md` for the complete calling convention.
