# DPD Test Suite

Unified test runner for Demo Probe Driver - runs the same tests against simulation (CocoTB/GHDL) or real hardware (Moku).

## Quick Start

### Simulation (Default)

```bash
cd /Users/johnycsh/DPD/DPD-001/tests

# Run P1 basic tests
uv run python run.py

# Verbose output
uv run python run.py -v
```

### Hardware Testing

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

## Command Line Options

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

```
tests/
├── run.py              # Unified test runner
├── lib/                # Constants, utilities, test base classes (API v4.0)
├── adapters/           # Async adapters for sim/hw convergence
│   ├── base.py         # Abstract interfaces
│   ├── cocotb.py       # CocoTB implementation
│   └── moku.py         # Moku hardware implementation
├── shared/             # Control interface abstractions
├── hw/                 # Hardware-specific plumbing
│   └── plumbing.py     # MokuSession context manager
└── sim/                # Simulation tests
    ├── run.py          # Sim-only runner (alternative)
    └── dpd/
        └── P1_basic.py # P1 test suite (5 tests)
```

## API v4.0

All tests use the v4.0 API where lifecycle controls are in CR0:
- `CR0[31:29]` - FORGE control (forge_ready, user_enable, clk_enable)
- `CR0[2]` - arm_enable (level-sensitive)
- `CR0[1]` - fault_clear (edge-triggered, auto-clear)
- `CR0[0]` - sw_trigger (edge-triggered, auto-clear)

See [docs/api-v4.md](../docs/api-v4.md) for the complete calling convention.
