"""
Demo Probe Driver (DPD) Simulation Test Constants
==================================================

Simulation-specific constants that extend the shared test infrastructure.
Imports from tests/shared/constants.py for common values.

Author: Moku Instrument Forge Team
Date: 2025-11-26 (refactored to use shared infrastructure)
"""

import sys
from pathlib import Path

# Add paths for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # DPD-001/
TESTS_PATH = Path(__file__).parent.parent.parent  # tests/
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))
sys.path.insert(0, str(TESTS_PATH))

# =============================================================================
# Re-export from shared constants (single source of truth)
# =============================================================================
from shared.constants import (
    # Hardware constants from py_tools
    CR1,
    FSMState,
    HVS,
    Platform,
    DefaultTiming,
    cr1_build,
    cr1_extract,
    # FORGE control
    MCC_CR0_ALL_ENABLED,
    MCC_CR0_FORGE_READY,
    MCC_CR0_USER_ENABLE,
    MCC_CR0_CLK_ENABLE,
    FORGE_READY_BIT,
    USER_ENABLE_BIT,
    CLK_ENABLE_BIT,
    # Voltage conversion
    mv_to_digital,
    digital_to_mv,
    us_to_cycles,
    cycles_to_us,
    V_MAX_MV,
    DIGITAL_MAX,
    # Test timing
    P1Timing,
    P2Timing,
    # Trigger values
    TRIGGER_THRESHOLD_MV,
    TRIGGER_TEST_VOLTAGE_MV,
    TRIGGER_THRESHOLD_DIGITAL,
    TRIGGER_TEST_VOLTAGE_DIGITAL,
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
# These maintain compatibility with existing test code

# FSM States
STATE_INITIALIZING = FSMState.INITIALIZING
STATE_IDLE = FSMState.IDLE
STATE_ARMED = FSMState.ARMED
STATE_FIRING = FSMState.FIRING
STATE_COOLDOWN = FSMState.COOLDOWN
STATE_FAULT = FSMState.FAULT

# HVS values (already exported above, but alias for compatibility)
HVS_DIGITAL_UNITS_PER_STATE = HVS.DIGITAL_UNITS_PER_STATE
HVS_DIGITAL_TOLERANCE = SIM_HVS_TOLERANCE

# Default timing
DEFAULT_TRIG_OUT_DURATION = DefaultTiming.TRIG_OUT_DURATION
DEFAULT_INTENSITY_DURATION = DefaultTiming.INTENSITY_DURATION
DEFAULT_COOLDOWN_INTERVAL = DefaultTiming.COOLDOWN_INTERVAL
DEFAULT_TRIGGER_WAIT_TIMEOUT = DefaultTiming.TRIGGER_WAIT_TIMEOUT

# =============================================================================
# Backward-Compatible Aliases for P1TestValues/P2TestValues
# =============================================================================
# These aliases allow old code using P1TestValues.X to continue working
# New code should import P1Timing/P2Timing directly from shared.constants

# P1TestValues is now an alias for P1Timing (with trigger constants available at module level)
P1TestValues = P1Timing

# P2TestValues is now an alias for P2Timing
P2TestValues = P2Timing

# =============================================================================
# Module-level convenience exports
# =============================================================================
TRIG_THRESHOLD_MV = TRIGGER_THRESHOLD_MV
TRIG_TEST_VOLTAGE_MV = TRIGGER_TEST_VOLTAGE_MV
TRIG_THRESHOLD_DIGITAL = TRIGGER_THRESHOLD_DIGITAL
TRIG_TEST_VOLTAGE_DIGITAL = TRIGGER_TEST_VOLTAGE_DIGITAL
