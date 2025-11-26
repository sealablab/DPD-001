"""
Hardware Constants - Thin re-export from py_tools/dpd_constants.py

This module provides hardware constants for DPD tests.
The authoritative source is py_tools/dpd_constants.py.
"""

import sys
from pathlib import Path

# Add py_tools to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

# Re-export everything from dpd_constants
from dpd_constants import (
    # Control Register 0 (FORGE control)
    CR0,
    # Control Register 1 (lifecycle/trigger)
    CR1,
    # FSM state values
    FSMState,
    # HVS encoding
    HVS,
    # Platform constants
    Platform,
    # Default timing
    DefaultTiming,
    # Helper functions
    cr1_build,
    cr1_extract,
)

# Convenience aliases for common values
MCC_CR0_ALL_ENABLED = CR0.ALL_ENABLED
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
