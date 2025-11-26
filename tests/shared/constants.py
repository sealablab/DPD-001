"""
Shared Test Constants
=====================

This file imports hardware constants from py_tools/dpd_constants.py
(the authoritative source) and adds TEST-SPECIFIC values only.

Dependency Direction:
    py_tools/dpd_constants.py  ← AUTHORITATIVE (hardware truth)
             ↑
    tests/shared/constants.py  ← TEST LAYER (this file)

Both simulation (CocoTB) and hardware (Moku) tests should import from
this module to ensure consistency.

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

import sys
from pathlib import Path

# Add py_tools to path so we can import shared constants
PROJECT_ROOT = Path(__file__).parent.parent.parent  # DPD-001/
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

# =============================================================================
# Re-export from py_tools/dpd_constants.py (authoritative source)
# =============================================================================
from dpd_constants import (
    CR0,
    CR1,
    FSMState,
    HVS,
    Platform,
    DefaultTiming,
    cr1_build,
    cr1_extract,
)

# Re-export from py_tools/clk_utils.py (authoritative source)
from clk_utils import (
    us_to_cycles,
    cycles_to_us,
    ns_to_cycles,
    cycles_to_ns,
    s_to_cycles,
    cycles_to_s,
)

# =============================================================================
# FORGE Control Scheme Constants (CR0[31:29])
# Backward-compatible aliases - use CR0 class for new code
# =============================================================================
FORGE_READY_BIT = CR0.FORGE_READY  # 31
USER_ENABLE_BIT = CR0.USER_ENABLE  # 30
CLK_ENABLE_BIT = CR0.CLK_ENABLE    # 29

MCC_CR0_FORGE_READY = CR0.FORGE_READY_MASK  # 0x80000000
MCC_CR0_USER_ENABLE = CR0.USER_ENABLE_MASK  # 0x40000000
MCC_CR0_CLK_ENABLE = CR0.CLK_ENABLE_MASK    # 0x20000000
MCC_CR0_ALL_ENABLED = CR0.ALL_ENABLED       # 0xE0000000

# =============================================================================
# Voltage Conversion Utilities
# Backward-compatible aliases - use HVS class methods for new code
# =============================================================================
V_MAX_MV = HVS.V_MAX_MV      # 5000 (+/-5V range in millivolts)
DIGITAL_MAX = HVS.DIGITAL_MAX  # 32768 (16-bit signed max)

# Alias functions to HVS class methods
mv_to_digital = HVS.mv_to_digital
digital_to_mv = HVS.digital_to_mv


# =============================================================================
# Test Timing Configurations
# =============================================================================
class _TestTimingBase:
    """Base class with shared trigger/voltage values for all test timing levels."""
    # Trigger threshold (shared across all test levels)
    TRIGGER_THRESHOLD_MV = 950       # Default trigger threshold
    TRIGGER_TEST_VOLTAGE_MV = 1500   # Voltage above threshold for testing

    # Trigger threshold as digital values (computed at class definition time)
    TRIGGER_THRESHOLD_DIGITAL = mv_to_digital(950)
    TRIGGER_TEST_VOLTAGE_DIGITAL = mv_to_digital(1500)

    # Output voltages (mV) - same for all test levels
    TRIG_OUT_VOLTAGE_MV = 2000    # 2V trigger output
    INTENSITY_VOLTAGE_MV = 1500  # 1.5V intensity output


class P1Timing(_TestTimingBase):
    """Fast timing for P1 (BASIC) simulation tests.

    Optimized for fast test execution in CocoTB simulations.
    May be too fast for hardware oscilloscope observation.
    """
    # Timing in clock cycles
    TRIG_OUT_DURATION = 1000    # 8us @ 125MHz
    INTENSITY_DURATION = 2000   # 16us @ 125MHz
    COOLDOWN_INTERVAL = 500     # 4us @ 125MHz

    # Derived values
    TOTAL_CYCLES = TRIG_OUT_DURATION + INTENSITY_DURATION + COOLDOWN_INTERVAL

    # Timing in microseconds (for reference)
    TRIG_OUT_DURATION_US = cycles_to_us(TRIG_OUT_DURATION)      # 8us
    INTENSITY_DURATION_US = cycles_to_us(INTENSITY_DURATION)    # 16us
    COOLDOWN_INTERVAL_US = cycles_to_us(COOLDOWN_INTERVAL)      # 4us
    TOTAL_US = cycles_to_us(TOTAL_CYCLES)                       # 28us


class P2Timing(_TestTimingBase):
    """Observable timing for P2 (INTERMEDIATE) hardware tests.

    Slower timing that's easier to observe on oscilloscopes.
    Recommended for hardware tests.
    """
    # Timing in clock cycles
    TRIG_OUT_DURATION = 12500   # 100us @ 125MHz
    INTENSITY_DURATION = 25000  # 200us @ 125MHz
    COOLDOWN_INTERVAL = 1250    # 10us @ 125MHz

    # Derived values
    TOTAL_CYCLES = TRIG_OUT_DURATION + INTENSITY_DURATION + COOLDOWN_INTERVAL

    # Timing in microseconds (for reference)
    TRIG_OUT_DURATION_US = cycles_to_us(TRIG_OUT_DURATION)      # 100us
    INTENSITY_DURATION_US = cycles_to_us(INTENSITY_DURATION)    # 200us
    COOLDOWN_INTERVAL_US = cycles_to_us(COOLDOWN_INTERVAL)      # 10us
    TOTAL_US = cycles_to_us(TOTAL_CYCLES)                       # 310us


# =============================================================================
# Trigger Voltage Constants
# =============================================================================
TRIGGER_THRESHOLD_MV = 950       # Default trigger threshold
TRIGGER_TEST_VOLTAGE_MV = 1500   # Voltage above threshold for testing

TRIGGER_THRESHOLD_DIGITAL = mv_to_digital(TRIGGER_THRESHOLD_MV)
TRIGGER_TEST_VOLTAGE_DIGITAL = mv_to_digital(TRIGGER_TEST_VOLTAGE_MV)

# =============================================================================
# HVS State Values (digital units for OutputC observation)
# =============================================================================
# Re-export from HVS class for convenience
HVS_DIGITAL_INITIALIZING = HVS.VOLTAGE_INITIALIZING  # 0
HVS_DIGITAL_IDLE = HVS.VOLTAGE_IDLE                  # 3277
HVS_DIGITAL_ARMED = HVS.VOLTAGE_ARMED                # 6554
HVS_DIGITAL_FIRING = HVS.VOLTAGE_FIRING              # 9831
HVS_DIGITAL_COOLDOWN = HVS.VOLTAGE_COOLDOWN          # 13108

# =============================================================================
# Tolerance Values
# =============================================================================
# Simulation tolerance (tighter - direct digital access)
SIM_HVS_TOLERANCE = 200  # +/-200 digital units (~30mV)

# Hardware tolerance (looser - ADC noise, polling latency)
HW_HVS_TOLERANCE_V = 0.30  # +/-300mV
HW_HVS_TOLERANCE_DIGITAL = mv_to_digital(HW_HVS_TOLERANCE_V * 1000)

# =============================================================================
# State Voltage Map (for hardware tests observing via oscilloscope)
# Backward-compatible alias - use HVS.STATE_VOLTAGE_MAP for new code
# =============================================================================
STATE_VOLTAGE_MAP = HVS.STATE_VOLTAGE_MAP

# Reverse lookup for state names
VOLTAGE_STATE_MAP = {v: k for k, v in STATE_VOLTAGE_MAP.items()}

# =============================================================================
# Test Timeouts
# =============================================================================
class Timeouts:
    """Timeout values for test operations."""
    # Simulation timeouts (in microseconds)
    SIM_STATE_TRANSITION_US = 100
    SIM_FSM_CYCLE_US = 500

    # Hardware timeouts (in milliseconds)
    HW_RESET_MS = 500
    HW_ARM_MS = 1000
    HW_TRIGGER_MS = 1000
    HW_FSM_CYCLE_MS = 3000
    HW_STATE_DEFAULT_MS = 2000

    # Oscilloscope polling
    OSC_POLL_COUNT = 5
    OSC_POLL_INTERVAL_MS = 20
