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
# P1TestValues Class (backward compatibility)
# =============================================================================
class P1TestValues:
    """Test values optimized for P1 (BASIC) level - fast execution.

    This class wraps P1Timing for backward compatibility.
    """
    # Trigger voltages (in mV)
    TRIGGER_THRESHOLD_MV = TRIGGER_THRESHOLD_MV
    TRIGGER_TEST_VOLTAGE_MV = TRIGGER_TEST_VOLTAGE_MV

    # Trigger voltages as digital values
    TRIGGER_THRESHOLD_DIGITAL = TRIGGER_THRESHOLD_DIGITAL
    TRIGGER_TEST_VOLTAGE_DIGITAL = TRIGGER_TEST_VOLTAGE_DIGITAL

    # Timing (from P1Timing)
    TRIG_OUT_DURATION = P1Timing.TRIG_OUT_DURATION
    INTENSITY_DURATION = P1Timing.INTENSITY_DURATION
    COOLDOWN_INTERVAL = P1Timing.COOLDOWN_INTERVAL
    TOTAL_FSM_CYCLES = P1Timing.TOTAL_CYCLES

    # Timeout values
    STATE_TRANSITION_TIMEOUT_US = Timeouts.SIM_STATE_TRANSITION_US
    FSM_CYCLE_TIMEOUT_US = Timeouts.SIM_FSM_CYCLE_US


class P2TestValues:
    """Test values for P2 (INTERMEDIATE) level - realistic timing.

    This class wraps P2Timing for backward compatibility.
    """
    TRIGGER_THRESHOLD_MV = TRIGGER_THRESHOLD_MV
    TRIGGER_TEST_VOLTAGE_MV = TRIGGER_TEST_VOLTAGE_MV
    TRIGGER_THRESHOLD_DIGITAL = TRIGGER_THRESHOLD_DIGITAL
    TRIGGER_TEST_VOLTAGE_DIGITAL = TRIGGER_TEST_VOLTAGE_DIGITAL

    TRIG_OUT_DURATION = P2Timing.TRIG_OUT_DURATION
    INTENSITY_DURATION = P2Timing.INTENSITY_DURATION
    COOLDOWN_INTERVAL = P2Timing.COOLDOWN_INTERVAL
    TOTAL_FSM_CYCLES = P2Timing.TOTAL_CYCLES

    STATE_TRANSITION_TIMEOUT_US = 200
    FSM_CYCLE_TIMEOUT_US = 1000


# =============================================================================
# Module-level convenience exports
# =============================================================================
TRIG_THRESHOLD_MV = TRIGGER_THRESHOLD_MV
TRIG_TEST_VOLTAGE_MV = TRIGGER_TEST_VOLTAGE_MV
TRIG_THRESHOLD_DIGITAL = TRIGGER_THRESHOLD_DIGITAL
TRIG_TEST_VOLTAGE_DIGITAL = TRIGGER_TEST_VOLTAGE_DIGITAL
