"""
Clock Utilities - Thin re-export from py_tools/clk_utils.py

This module provides clock conversion utilities for DPD tests.
The authoritative source is py_tools/clk_utils.py.
"""

import sys
from pathlib import Path

# Add py_tools to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

# Re-export everything from clk_utils
from clk_utils import (
    # Time to cycles
    s_to_cycles,
    us_to_cycles,
    ns_to_cycles,
    # Cycles to time
    cycles_to_s,
    cycles_to_us,
    cycles_to_ns,
    # Slow mode (debug)
    set_slow_mode,
    get_slow_mode,
    SLOW_MODE_SCALE_FACTOR,
    # Constants
    DEFAULT_CLK_FREQ_HZ,
    MAX_32BIT,
    # Exceptions
    CycleCountOverflowError,
)
