"""
Demo Probe Driver (DPD) Test Constants

Defines test configuration, HDL sources, and test values for CocoTB progressive tests.

NOTE: Hardware constants (FSM states, HVS values, CR1 bits) now imported from
      py_tools/dpd_constants.py (single source of truth).

Author: Moku Instrument Forge Team
Date: 2025-11-25 (refactored to use shared constants)
"""

import sys
from pathlib import Path

# Add py_tools to path so we can import shared constants
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # DPD-001/
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

from dpd_constants import CR1, FSMState, HVS, Platform, DefaultTiming

# Module identification
MODULE_NAME = "dpd_wrapper"
HDL_TOPLEVEL = "customwrapper"  # GHDL lowercases entity names - use lowercase!

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

# Clock configuration (Moku:Go = 125MHz = 8ns period)
CLK_PERIOD_NS = Platform.CLK_PERIOD_NS  # 8ns
CLK_FREQ_HZ = Platform.CLK_FREQ_HZ      # 125 MHz

# =============================================================================
# FSM State Constants (imported from dpd_constants.py)
# =============================================================================
# Backward-compatible aliases for existing tests
STATE_INITIALIZING = FSMState.INITIALIZING  # 0: Register latch/validation (sync-safe)
STATE_IDLE         = FSMState.IDLE          # 1: Waiting for arm signal
STATE_ARMED        = FSMState.ARMED         # 2: Waiting for trigger
STATE_FIRING       = FSMState.FIRING        # 3: Driving outputs
STATE_COOLDOWN     = FSMState.COOLDOWN      # 4: Thermal safety delay
STATE_FAULT        = FSMState.FAULT         # 63: Sticky fault

# =============================================================================
# HVS (Hierarchical Voltage Encoding) Constants (imported from dpd_constants.py)
# =============================================================================
# Backward-compatible aliases for existing tests
HVS_DIGITAL_UNITS_PER_STATE = HVS.DIGITAL_UNITS_PER_STATE  # 3277 digital units per state

HVS_DIGITAL_INITIALIZING = HVS.VOLTAGE_INITIALIZING  # 0 (0.0V)
HVS_DIGITAL_IDLE         = HVS.VOLTAGE_IDLE          # 3277 (0.5V)
HVS_DIGITAL_ARMED        = HVS.VOLTAGE_ARMED         # 6554 (1.0V)
HVS_DIGITAL_FIRING       = HVS.VOLTAGE_FIRING        # 9831 (1.5V)
HVS_DIGITAL_COOLDOWN     = HVS.VOLTAGE_COOLDOWN      # 13108 (2.0V)

# HVS tolerance for digital comparisons (allows status offset variation)
HVS_DIGITAL_TOLERANCE = 200  # ±200 digital units (allows ±100 status offset range)

# =============================================================================
# FORGE Control Scheme Constants (CR0[31:29])
# =============================================================================
FORGE_READY_BIT = 31  # Set by MCC after deployment
USER_ENABLE_BIT = 30  # User control enable/disable
CLK_ENABLE_BIT = 29   # Clock gating enable

# Combined FORGE control value (all 3 bits set)
MCC_CR0_FORGE_READY = 1 << FORGE_READY_BIT  # 0x80000000
MCC_CR0_USER_ENABLE = 1 << USER_ENABLE_BIT  # 0x40000000
MCC_CR0_CLK_ENABLE = 1 << CLK_ENABLE_BIT    # 0x20000000
MCC_CR0_ALL_ENABLED = MCC_CR0_FORGE_READY | MCC_CR0_USER_ENABLE | MCC_CR0_CLK_ENABLE  # 0xE0000000

# Default timing values (imported from dpd_constants.py)
DEFAULT_TRIG_OUT_DURATION = DefaultTiming.TRIG_OUT_DURATION       # 12500 (100μs)
DEFAULT_INTENSITY_DURATION = DefaultTiming.INTENSITY_DURATION     # 25000 (200μs)
DEFAULT_COOLDOWN_INTERVAL = DefaultTiming.COOLDOWN_INTERVAL       # 1250 (10μs)
DEFAULT_TRIGGER_WAIT_TIMEOUT = DefaultTiming.TRIGGER_WAIT_TIMEOUT # 250000000 (2s)

# Voltage conversion (Moku ADC/DAC: ±5V = ±32768 digital, 16-bit signed)
# Formula: digital = (voltage_mV / 5000.0) * 32768
V_MAX_MV = 5000   # ±5V range
DIGITAL_MAX = 32768  # 16-bit signed max


def mv_to_digital(millivolts: float) -> int:
    """Convert millivolts to 16-bit signed digital value.

    Args:
        millivolts: Voltage in mV (±5000mV range)

    Returns:
        Digital value (±32768 range)

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
        digital: Digital value (±32768 range)

    Returns:
        Voltage in mV (±5000mV range)
    """
    return (digital / DIGITAL_MAX) * V_MAX_MV


# =============================================================================
# P1 Test Values (small, fast)
# =============================================================================
class P1TestValues:
    """Test values optimized for P1 (BASIC) level - fast execution."""

    # Trigger voltages (in mV)
    TRIGGER_THRESHOLD_MV = 950   # Default threshold
    TRIGGER_TEST_VOLTAGE_MV = 1500  # Above threshold

    # Trigger voltages as digital values
    TRIGGER_THRESHOLD_DIGITAL = mv_to_digital(TRIGGER_THRESHOLD_MV)      # ~6225
    TRIGGER_TEST_VOLTAGE_DIGITAL = mv_to_digital(TRIGGER_TEST_VOLTAGE_MV)  # ~9830

    # Timing (reduced for fast P1 tests)
    TRIG_OUT_DURATION = 1000   # 8μs @ 125MHz (reduced from 100μs default)
    INTENSITY_DURATION = 2000  # 16μs @ 125MHz (reduced from 200μs default)
    COOLDOWN_INTERVAL = 500    # 4μs @ 125MHz (reduced from 10μs default)

    # Total FSM cycle time (sum of above)
    TOTAL_FSM_CYCLES = TRIG_OUT_DURATION + INTENSITY_DURATION + COOLDOWN_INTERVAL  # ~3500 cycles

    # Timeout values (conservative, allow for simulation delays)
    STATE_TRANSITION_TIMEOUT_US = 100  # Max time to wait for state change
    FSM_CYCLE_TIMEOUT_US = 500         # Max time for complete FSM cycle


# =============================================================================
# P2 Test Values (realistic, closer to production)
# =============================================================================
class P2TestValues:
    """Test values for P2 (INTERMEDIATE) level - realistic timing."""

    TRIGGER_THRESHOLD_MV = 950
    TRIGGER_TEST_VOLTAGE_MV = 1500
    TRIGGER_THRESHOLD_DIGITAL = mv_to_digital(TRIGGER_THRESHOLD_MV)
    TRIGGER_TEST_VOLTAGE_DIGITAL = mv_to_digital(TRIGGER_TEST_VOLTAGE_MV)

    # Production-like timing
    TRIG_OUT_DURATION = DEFAULT_TRIG_OUT_DURATION    # 100μs
    INTENSITY_DURATION = DEFAULT_INTENSITY_DURATION  # 200μs
    COOLDOWN_INTERVAL = DEFAULT_COOLDOWN_INTERVAL    # 10μs

    TOTAL_FSM_CYCLES = TRIG_OUT_DURATION + INTENSITY_DURATION + COOLDOWN_INTERVAL  # ~38750 cycles

    STATE_TRANSITION_TIMEOUT_US = 200
    FSM_CYCLE_TIMEOUT_US = 1000


# =============================================================================
# Export commonly used values at module level
# =============================================================================
TRIG_THRESHOLD_MV = P1TestValues.TRIGGER_THRESHOLD_MV
TRIG_TEST_VOLTAGE_MV = P1TestValues.TRIGGER_TEST_VOLTAGE_MV
TRIG_THRESHOLD_DIGITAL = P1TestValues.TRIGGER_THRESHOLD_DIGITAL
TRIG_TEST_VOLTAGE_DIGITAL = P1TestValues.TRIGGER_TEST_VOLTAGE_DIGITAL
