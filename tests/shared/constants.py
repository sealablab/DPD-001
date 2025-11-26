"""
Shared Test Constants - Single Source of Truth
===============================================

This file imports hardware constants from py_tools/dpd_constants.py
(the authoritative source) and adds test-specific values.

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
    CR1,
    FSMState,
    HVS,
    Platform,
    DefaultTiming,
    cr1_build,
    cr1_extract,
)

# =============================================================================
# FORGE Control Scheme Constants (CR0[31:29])
# =============================================================================
FORGE_READY_BIT = 31  # Set by MCC after deployment
USER_ENABLE_BIT = 30  # User control enable/disable
CLK_ENABLE_BIT = 29   # Clock gating enable

MCC_CR0_FORGE_READY = 1 << FORGE_READY_BIT  # 0x80000000
MCC_CR0_USER_ENABLE = 1 << USER_ENABLE_BIT  # 0x40000000
MCC_CR0_CLK_ENABLE = 1 << CLK_ENABLE_BIT    # 0x20000000
MCC_CR0_ALL_ENABLED = MCC_CR0_FORGE_READY | MCC_CR0_USER_ENABLE | MCC_CR0_CLK_ENABLE  # 0xE0000000

# =============================================================================
# Voltage Conversion Utilities
# =============================================================================
V_MAX_MV = 5000      # +/-5V range in millivolts
DIGITAL_MAX = 32768  # 16-bit signed max


def mv_to_digital(millivolts: float) -> int:
    """Convert millivolts to 16-bit signed digital value.

    Args:
        millivolts: Voltage in mV (+/-5000mV range)

    Returns:
        Digital value (+/-32768 range)

    Example:
        >>> mv_to_digital(0)
        0
        >>> mv_to_digital(950)  # Default threshold
        6225
        >>> mv_to_digital(1500)  # Test trigger voltage
        9830
    """
    return int((millivolts / V_MAX_MV) * DIGITAL_MAX)


def digital_to_mv(digital: int) -> float:
    """Convert 16-bit signed digital value to millivolts.

    Args:
        digital: Digital value (+/-32768 range)

    Returns:
        Voltage in mV (+/-5000mV range)
    """
    return (digital / DIGITAL_MAX) * V_MAX_MV


def us_to_cycles(microseconds: float) -> int:
    """Convert microseconds to clock cycles @ 125MHz.

    Args:
        microseconds: Time in microseconds

    Returns:
        Number of clock cycles
    """
    return int(microseconds * Platform.CLK_FREQ_HZ / 1e6)


def cycles_to_us(cycles: int) -> float:
    """Convert clock cycles to microseconds @ 125MHz.

    Args:
        cycles: Number of clock cycles

    Returns:
        Time in microseconds
    """
    return cycles * 1e6 / Platform.CLK_FREQ_HZ


# =============================================================================
# Test Timing Configurations
# =============================================================================
class P1Timing:
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


class P2Timing:
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
# =============================================================================
STATE_VOLTAGE_MAP = {
    "INITIALIZING": 0.0,   # State 0: 0V (transient)
    "IDLE": 0.5,           # State 1: 0.5V
    "ARMED": 1.0,          # State 2: 1.0V
    "FIRING": 1.5,         # State 3: 1.5V
    "COOLDOWN": 2.0,       # State 4: 2.0V
    "FAULT": -0.5,         # Negative voltage indicates fault
}

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
