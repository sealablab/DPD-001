"""
Hardware Test Constants for Demo Probe Driver (DPD)
====================================================

Hardware-specific constants that extend the shared test infrastructure.
Imports from tests/shared/constants.py for common values.

Author: Moku Instrument Forge Team
Date: 2025-11-26 (refactored to use shared infrastructure)
"""

import sys
from pathlib import Path

# Add shared module to path
TESTS_PATH = Path(__file__).parent.parent
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
    HW_HVS_TOLERANCE_V,
    HW_HVS_TOLERANCE_DIGITAL,
    # State voltage map
    STATE_VOLTAGE_MAP,
    VOLTAGE_STATE_MAP,
    # Timeouts
    Timeouts,
)

# =============================================================================
# Hardware-Specific Constants
# =============================================================================

# Module identification
MODULE_NAME = "dpd_hardware"

# Clock configuration (convenience aliases)
CLK_PERIOD_NS = Platform.CLK_PERIOD_NS
CLK_FREQ_HZ = Platform.CLK_FREQ_HZ

# Hardware voltage tolerance (wider than simulation)
STATE_VOLTAGE_TOLERANCE = HW_HVS_TOLERANCE_V  # +/-300mV

# =============================================================================
# Backward-Compatible Aliases
# =============================================================================

# Oscilloscope polling configuration
OSC_POLL_COUNT_DEFAULT = Timeouts.OSC_POLL_COUNT
OSC_POLL_INTERVAL_MS = Timeouts.OSC_POLL_INTERVAL_MS
OSC_STATE_TIMEOUT_MS = Timeouts.HW_STATE_DEFAULT_MS

# Test timeouts (conservative for real hardware)
TEST_RESET_TIMEOUT_MS = Timeouts.HW_RESET_MS
TEST_ARM_TIMEOUT_MS = Timeouts.HW_ARM_MS
TEST_TRIGGER_TIMEOUT_MS = Timeouts.HW_TRIGGER_MS
TEST_FSM_CYCLE_TIMEOUT_MS = Timeouts.HW_FSM_CYCLE_MS


# =============================================================================
# Backward-Compatible Aliases for P1TestValues/P2TestValues
# =============================================================================
# These aliases allow old code using P1TestValues.X to continue working
# New code should import P1Timing/P2Timing directly from shared.constants

# P1TestValues is now an alias for P1Timing
P1TestValues = P1Timing

# P2TestValues is now an alias for P2Timing (recommended for hardware tests)
P2TestValues = P2Timing

# =============================================================================
# Default timing configuration (use P2 for visibility)
# =============================================================================
DEFAULT_TRIG_OUT_DURATION_US = P2Timing.TRIG_OUT_DURATION_US
DEFAULT_INTENSITY_DURATION_US = P2Timing.INTENSITY_DURATION_US
DEFAULT_COOLDOWN_INTERVAL_US = P2Timing.COOLDOWN_INTERVAL_US
DEFAULT_TRIGGER_THRESHOLD_MV = P2Timing.TRIGGER_THRESHOLD_MV
DEFAULT_TRIGGER_TEST_VOLTAGE_MV = P2Timing.TRIGGER_TEST_VOLTAGE_MV
DEFAULT_TRIG_OUT_VOLTAGE_MV = P2Timing.TRIG_OUT_VOLTAGE_MV
DEFAULT_INTENSITY_VOLTAGE_MV = P2Timing.INTENSITY_VOLTAGE_MV
