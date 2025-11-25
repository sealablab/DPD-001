"""
Demo Probe Driver (DPD) Test Constants

Defines test configuration, HDL sources, and test values for CocoTB progressive tests.

Author: Moku Instrument Forge Team
Date: 2025-11-18
"""

from pathlib import Path

# Module identification
MODULE_NAME = "dpd_wrapper"
HDL_TOPLEVEL = "customwrapper"  # GHDL lowercases entity names - use lowercase!

# HDL source files (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # DPD-001/
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
CLK_PERIOD_NS = 8
CLK_FREQ_HZ = 125_000_000

# FSM State Constants (6-bit encoding from DPD_main.vhd)
STATE_IDLE = 0b000000  # 0
STATE_ARMED = 0b000001  # 1
STATE_FIRING = 0b000010  # 2
STATE_COOLDOWN = 0b000011  # 3
STATE_FAULT = 0b111111  # 63

# HVS (Hierarchical Voltage Encoding) Digital Constants
# OutputC shows: digital_value = state × 3277 + status_offset
# These are DIGITAL units (not voltages), sent to 16-bit DAC
# Updated 2025-01-18: Increased from 200 to 3277 units/state for human-visible scope debugging
# 3277 digital units = 0.5V per state @ ±5V full scale (Moku:Go)
# State voltages: IDLE=0V, ARMED=0.5V, FIRING=1.0V, COOLDOWN=1.5V
HVS_DIGITAL_UNITS_PER_STATE = 3277  # Digital units per state (0.5V per state @ ±5V FS)
HVS_DIGITAL_IDLE = 0 * HVS_DIGITAL_UNITS_PER_STATE  # 0 (0.0V)
HVS_DIGITAL_ARMED = 1 * HVS_DIGITAL_UNITS_PER_STATE  # 3277 (0.5V)
HVS_DIGITAL_FIRING = 2 * HVS_DIGITAL_UNITS_PER_STATE  # 6554 (1.0V)
HVS_DIGITAL_COOLDOWN = 3 * HVS_DIGITAL_UNITS_PER_STATE  # 9831 (1.5V)
# FAULT: Negative value (sign flip when status[7]=1)

# HVS tolerance for digital comparisons (allows status offset variation)
# Increased tolerance to ±200 digital units (~30mV @ ±5V FS) for new scaling
HVS_DIGITAL_TOLERANCE = 200  # ±200 digital units (allows ±100 status offset range)

# FORGE Control Scheme Constants (CR0[31:29])
FORGE_READY_BIT = 31  # Set by MCC after deployment
USER_ENABLE_BIT = 30  # User control enable/disable
CLK_ENABLE_BIT = 29  # Clock gating enable

# Combined FORGE control value (all 3 bits set)
MCC_CR0_FORGE_READY = 1 << FORGE_READY_BIT  # 0x80000000
MCC_CR0_USER_ENABLE = 1 << USER_ENABLE_BIT  # 0x40000000
MCC_CR0_CLK_ENABLE = 1 << CLK_ENABLE_BIT  # 0x20000000
MCC_CR0_ALL_ENABLED = MCC_CR0_FORGE_READY | MCC_CR0_USER_ENABLE | MCC_CR0_CLK_ENABLE  # 0xE0000000

# Default timing values (in clock cycles @ 125MHz)
# These match the defaults from DPD-RTL.yaml
DEFAULT_TRIG_OUT_DURATION = 12500  # 100μs
DEFAULT_INTENSITY_DURATION = 25000  # 200μs
DEFAULT_COOLDOWN_INTERVAL = 1250  # 10μs
DEFAULT_TRIGGER_WAIT_TIMEOUT = 250000000  # 2 seconds

# Voltage conversion (Moku ADC/DAC: ±5V = ±32768 digital, 16-bit signed)
# Formula: digital = (voltage_mV / 5000.0) * 32768
V_MAX_MV = 5000  # ±5V range
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


# P1 Test Values (small, fast)
class P1TestValues:
    """Test values optimized for P1 (BASIC) level - fast execution."""

    # Trigger voltages (in mV)
    TRIGGER_THRESHOLD_MV = 950  # Default threshold
    TRIGGER_TEST_VOLTAGE_MV = 1500  # Above threshold

    # Trigger voltages as digital values
    TRIGGER_THRESHOLD_DIGITAL = mv_to_digital(TRIGGER_THRESHOLD_MV)  # ~6225
    TRIGGER_TEST_VOLTAGE_DIGITAL = mv_to_digital(TRIGGER_TEST_VOLTAGE_MV)  # ~9830

    # Timing (reduced for fast P1 tests)
    TRIG_OUT_DURATION = 1000  # 8μs @ 125MHz (reduced from 100μs default)
    INTENSITY_DURATION = 2000  # 16μs @ 125MHz (reduced from 200μs default)
    COOLDOWN_INTERVAL = 500  # 4μs @ 125MHz (reduced from 10μs default)

    # Total FSM cycle time (sum of above)
    TOTAL_FSM_CYCLES = TRIG_OUT_DURATION + INTENSITY_DURATION + COOLDOWN_INTERVAL  # ~3500 cycles

    # Timeout values (conservative, allow for simulation delays)
    STATE_TRANSITION_TIMEOUT_US = 100  # Max time to wait for state change
    FSM_CYCLE_TIMEOUT_US = 500  # Max time for complete FSM cycle


# P2 Test Values (realistic, closer to production)
class P2TestValues:
    """Test values for P2 (INTERMEDIATE) level - realistic timing."""

    TRIGGER_THRESHOLD_MV = 950
    TRIGGER_TEST_VOLTAGE_MV = 1500
    TRIGGER_THRESHOLD_DIGITAL = mv_to_digital(TRIGGER_THRESHOLD_MV)
    TRIGGER_TEST_VOLTAGE_DIGITAL = mv_to_digital(TRIGGER_TEST_VOLTAGE_MV)

    # Production-like timing
    TRIG_OUT_DURATION = DEFAULT_TRIG_OUT_DURATION  # 100μs
    INTENSITY_DURATION = DEFAULT_INTENSITY_DURATION  # 200μs
    COOLDOWN_INTERVAL = DEFAULT_COOLDOWN_INTERVAL  # 10μs

    TOTAL_FSM_CYCLES = TRIG_OUT_DURATION + INTENSITY_DURATION + COOLDOWN_INTERVAL  # ~38750 cycles

    STATE_TRANSITION_TIMEOUT_US = 200
    FSM_CYCLE_TIMEOUT_US = 1000


# Export commonly used values at module level
TRIG_THRESHOLD_MV = P1TestValues.TRIGGER_THRESHOLD_MV
TRIG_TEST_VOLTAGE_MV = P1TestValues.TRIGGER_TEST_VOLTAGE_MV
TRIG_THRESHOLD_DIGITAL = P1TestValues.TRIGGER_THRESHOLD_DIGITAL
TRIG_TEST_VOLTAGE_DIGITAL = P1TestValues.TRIGGER_TEST_VOLTAGE_DIGITAL
