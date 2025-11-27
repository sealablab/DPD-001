"""
Demo Probe Driver (DPD) Simulation Test Constants
==================================================

Simulation-specific constants that extend the test infrastructure.
Imports from tests/lib (API v4.0).

Author: Moku Instrument Forge Team
Date: 2025-11-26 (refactored for API v4.0)
"""

import sys
from pathlib import Path

# Add paths for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # DPD-001/
TESTS_PATH = Path(__file__).parent.parent.parent  # tests/
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))
sys.path.insert(0, str(TESTS_PATH))

# =============================================================================
# Re-export from tests.lib (API v4.0 single source of truth)
# =============================================================================
from lib import (
    # Hardware constants
    CR0,
    CR8,
    FSMState,
    HVS,
    Platform,
    DefaultTiming,
    cr0_build,
    cr0_extract,
    cr8_build,
    # FORGE control
    MCC_CR0_ALL_ENABLED,
    MCC_CR0_FORGE_READY,
    MCC_CR0_USER_ENABLE,
    MCC_CR0_CLK_ENABLE,
    # Voltage conversion
    mv_to_digital,
    digital_to_mv,
    us_to_cycles,
    cycles_to_us,
    # Test timing
    P1Timing,
    P2Timing,
    # HVS state values
    HVS_DIGITAL_INITIALIZING,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    # Tolerances
    SIM_HVS_TOLERANCE,
    # Timeouts
    Timeouts,
    # Trigger values
    TRIGGER_THRESHOLD_MV,
    TRIGGER_TEST_VOLTAGE_MV,
    TRIGGER_THRESHOLD_DIGITAL,
    TRIGGER_TEST_VOLTAGE_DIGITAL,
)

# =============================================================================
# Simulation-Specific Constants
# =============================================================================

# Module identification for CocoTB
MODULE_NAME = "dpd_wrapper"
HDL_TOPLEVEL = "customwrapper"  # GHDL lowercases entity names

# HDL source files (relative to project root)
RTL_DIR = PROJECT_ROOT / "rtl"
HDL_SOURCES = [
    RTL_DIR / "CustomWrapper_test_stub.vhd",
    RTL_DIR / "forge_common_pkg.vhd",
    RTL_DIR / "forge_hierarchical_encoder.vhd",
    RTL_DIR / "moku_voltage_threshold_trigger_core.vhd",
    RTL_DIR / "DPD_main.vhd",
    RTL_DIR / "DPD_shim.vhd",
    RTL_DIR / "DPD.vhd",
]

# Clock configuration (convenience aliases)
CLK_PERIOD_NS = Platform.CLK_PERIOD_NS
CLK_FREQ_HZ = Platform.CLK_FREQ_HZ

# =============================================================================
# Backward-Compatible Aliases
# =============================================================================

# FSM States
STATE_INITIALIZING = FSMState.INITIALIZING
STATE_IDLE = FSMState.IDLE
STATE_ARMED = FSMState.ARMED
STATE_FIRING = FSMState.FIRING
STATE_COOLDOWN = FSMState.COOLDOWN
STATE_FAULT = FSMState.FAULT

# HVS values
HVS_DIGITAL_UNITS_PER_STATE = HVS.DIGITAL_UNITS_PER_STATE
HVS_DIGITAL_TOLERANCE = SIM_HVS_TOLERANCE

# Default timing
DEFAULT_TRIG_OUT_DURATION = DefaultTiming.TRIG_OUT_DURATION
DEFAULT_INTENSITY_DURATION = DefaultTiming.INTENSITY_DURATION
DEFAULT_COOLDOWN_INTERVAL = DefaultTiming.COOLDOWN_INTERVAL
DEFAULT_TRIGGER_WAIT_TIMEOUT = DefaultTiming.TRIGGER_WAIT_TIMEOUT

# P1/P2 test values
P1TestValues = P1Timing
P2TestValues = P2Timing

# FORGE control bits
FORGE_READY_BIT = CR0.FORGE_READY
USER_ENABLE_BIT = CR0.USER_ENABLE
CLK_ENABLE_BIT = CR0.CLK_ENABLE
