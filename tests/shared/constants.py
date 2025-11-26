"""
Shared Test Constants - BACKWARD COMPATIBILITY SHIM
===================================================

[COMPAT] This entire file is a backward compatibility shim.
         Delete once all imports updated to use tests/lib directly.

This file now re-exports from tests/lib/ for backward compatibility.
New code should import directly from tests/lib.

Migration:
    OLD: from shared.constants import P1Timing, SIM_HVS_TOLERANCE
    NEW: from lib import P1Timing, SIM_HVS_TOLERANCE
"""

import sys
from pathlib import Path

# Add lib to path
TESTS_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(TESTS_PATH))

# Re-export everything from lib
from lib import (
    # Hardware constants
    CR0,
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
    # HVS values
    HVS_DIGITAL_INITIALIZING,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    # Voltage conversion
    mv_to_digital,
    digital_to_mv,
    # Clock utilities
    us_to_cycles,
    cycles_to_us,
    ns_to_cycles,
    cycles_to_ns,
    s_to_cycles,
    cycles_to_s,
    # Timing
    P1Timing,
    P2Timing,
    DEFAULT_TRIGGER_WAIT_TIMEOUT,
    # Tolerances
    SIM_HVS_TOLERANCE,
    HW_HVS_TOLERANCE_V,
    HW_HVS_TOLERANCE_DIGITAL,
    # Timeouts
    Timeouts,
    # State maps
    STATE_VOLTAGE_MAP,
    VOLTAGE_STATE_MAP,
    # Backward compat
    P1TestValues,
    P2TestValues,
    HVS_DIGITAL_TOLERANCE,
    CLK_PERIOD_NS,
    CLK_FREQ_HZ,
    TRIGGER_THRESHOLD_MV,
    TRIGGER_TEST_VOLTAGE_MV,
    TRIGGER_THRESHOLD_DIGITAL,
    TRIGGER_TEST_VOLTAGE_DIGITAL,
)

# Additional backward compat aliases
FORGE_READY_BIT = CR0.FORGE_READY
USER_ENABLE_BIT = CR0.USER_ENABLE
CLK_ENABLE_BIT = CR0.CLK_ENABLE
V_MAX_MV = HVS.V_MAX_MV
DIGITAL_MAX = HVS.DIGITAL_MAX
