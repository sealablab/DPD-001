"""
Hardware Constants - Thin re-export from py_tools/dpd_constants.py (API v4.0)

This module provides hardware constants for DPD tests.
The authoritative source is py_tools/dpd_constants.py.

API v4.0 Changes:
  - CR0 contains all lifecycle controls (arm, trigger, fault_clear)
  - CR1 is reserved for future campaign mode
  - CR8 contains auto_rearm_enable at bit 2
  - cr1_build/cr1_extract removed - use cr0_build/cr0_extract instead
"""

import sys
from pathlib import Path

# Add py_tools to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

# Re-export everything from dpd_constants
from dpd_constants import (
    # Control Register 0 (FORGE + lifecycle)
    CR0,
    # Control Register 1 (reserved for campaign mode)
    CR1,
    # Control Register 8 (monitor + auto_rearm)
    CR8,
    # FSM state values
    FSMState,
    # HVS encoding
    HVS,
    # Platform constants
    Platform,
    # Default timing
    DefaultTiming,
    # Helper functions (v4.0)
    cr0_build,
    cr0_extract,
    cr8_build,
)

# Convenience aliases for common values
MCC_CR0_ALL_ENABLED = CR0.RUN  # 0xE0000000
MCC_CR0_FORGE_READY = CR0.FORGE_READY_MASK
MCC_CR0_USER_ENABLE = CR0.USER_ENABLE_MASK
MCC_CR0_CLK_ENABLE = CR0.CLK_ENABLE_MASK

# HVS digital values for each state
HVS_DIGITAL_INITIALIZING = HVS.VOLTAGE_INITIALIZING
HVS_DIGITAL_IDLE = HVS.VOLTAGE_IDLE
HVS_DIGITAL_ARMED = HVS.VOLTAGE_ARMED
HVS_DIGITAL_FIRING = HVS.VOLTAGE_FIRING
HVS_DIGITAL_COOLDOWN = HVS.VOLTAGE_COOLDOWN

# Voltage conversion utilities
mv_to_digital = HVS.mv_to_digital
digital_to_mv = HVS.digital_to_mv
