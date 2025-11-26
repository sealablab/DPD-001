---
publish: "true"
type: reference
created: 2025-11-25
modified: 2025-11-25
tags: [python, utilities, example]
---
# py_tools - Style 3: Code Block Reference

The `py_tools` directory contains standalone Python utilities for FPGA configuration and Moku device interaction.

## clk_utils
**Module:** `py_tools/clk_utils.py` ([source](https://github.com/sealablab/DPD-001/blob/main/py_tools/clk_utils.py))

Clock cycle conversion utilities for Moku FPGA timing calculations. Converts time values (μs, ns) to 125MHz clock cycles with optional SLOW_MODE scaling for debugging FSM transitions on oscilloscope.

## dpd_config
**Module:** `py_tools/dpd_config.py` ([source](https://github.com/sealablab/DPD-001/blob/main/py_tools/dpd_config.py))

DPD configuration dataclass providing structured interface for control registers. Maps friendly parameter names to CR1-CR10 register values. All timing stored in clock cycles, voltages in millivolts.

## dpd_constants
**Module:** `py_tools/dpd_constants.py` ([source](https://github.com/sealablab/DPD-001/blob/main/py_tools/dpd_constants.py))

Shared constants for DPD operation: CR1 bit definitions, FSM states, HVS voltage encoding, platform specs, and default timing values.

## moku_cli_common
**Module:** `py_tools/moku_cli_common.py` ([source](https://github.com/sealablab/DPD-001/blob/main/py_tools/moku_cli_common.py))

Common CLI argument parsing and device connection utilities. Reduces duplication across `moku_grab.py` and `moku_set.py` scripts.

## moku_grab
**Module:** `py_tools/moku_grab.py` ([source](https://github.com/sealablab/DPD-001/blob/main/py_tools/moku_grab.py))

Script to fetch DPD configuration and state from live Moku device. Displays control registers, FSM state, and monitor values.

## moku_set
**Module:** `py_tools/moku_set.py` ([source](https://github.com/sealablab/DPD-001/blob/main/py_tools/moku_set.py))

Script to upload DPD configuration to live Moku device. Supports direct register writes or DPDConfig-based updates.

## See Also
- [[CLAUDE]] - Development guidance for Claude Code
- [[tests/sim/README]] - Simulation test framework
