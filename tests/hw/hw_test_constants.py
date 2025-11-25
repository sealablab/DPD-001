"""
Hardware Test Constants for Demo Probe Driver (DPD)

Defines timing configurations, state mappings, and test values for hardware testing.
Adapted from cocotb_tests/dpd_wrapper_tests/dpd_wrapper_constants.py

Author: Moku Instrument Forge Team
Date: 2025-01-18
"""

from pathlib import Path

# Module identification
MODULE_NAME = "dpd_hardware"

# Clock configuration (Moku:Go = 125MHz = 8ns period)
CLK_PERIOD_NS = 8
CLK_FREQ_HZ = 125_000_000

# FSM State Constants (voltage-based encoding observed on oscilloscope)
# Based on HVS (Hierarchical Voltage Encoding) on OutputC
# Updated 2025-01-18: 3277 digital units/state = 0.5V/state @ ±5V full scale
# Note: HVS encoding includes status bits which add ±0.015V offset
STATE_VOLTAGE_MAP = {
    "IDLE": 0.0,        # State 0: 0V
    "ARMED": 0.5,       # State 1: 0.5V
    "FIRING": 1.0,      # State 2: 1.0V
    "COOLDOWN": 1.5,    # State 3: 1.5V (note: was "COOLING" in debug_fsm_states.py)
    "STATE_4": 2.0,     # State 4: 2.0V (debugging - may indicate uninitialized or unexpected state)
    "FAULT": -0.5,      # Negative voltage = fault condition
}

# Reverse lookup for state names
VOLTAGE_STATE_MAP = {v: k for k, v in STATE_VOLTAGE_MAP.items()}

# Voltage tolerance for state detection (±300mV, accounting for noise + HVS status bits)
# More forgiving than CocoTB's ±30mV due to real-world ADC noise
# HVS status bits can add up to ±100 digital units (±15mV)
# Increased to ±300mV to account for potential bitstream/encoding mismatches
STATE_VOLTAGE_TOLERANCE = 0.30  # ±300mV (was 0.15)

# FORGE Control Scheme Constants (CR0[31:29])
FORGE_READY_BIT = 31  # Set by MCC after deployment
USER_ENABLE_BIT = 30  # User control enable/disable
CLK_ENABLE_BIT = 29   # Clock gating enable

# Combined FORGE control value (all 3 bits set)
MCC_CR0_FORGE_READY = 1 << FORGE_READY_BIT  # 0x80000000
MCC_CR0_USER_ENABLE = 1 << USER_ENABLE_BIT  # 0x40000000
MCC_CR0_CLK_ENABLE = 1 << CLK_ENABLE_BIT    # 0x20000000
MCC_CR0_ALL_ENABLED = MCC_CR0_FORGE_READY | MCC_CR0_USER_ENABLE | MCC_CR0_CLK_ENABLE  # 0xE0000000

# Voltage conversion (Moku ADC/DAC: ±5V = ±32768 digital, 16-bit signed)
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


def us_to_cycles(microseconds: float) -> int:
    """Convert microseconds to clock cycles @ 125MHz.

    Args:
        microseconds: Time in microseconds

    Returns:
        Number of clock cycles
    """
    return int(microseconds * CLK_FREQ_HZ / 1e6)


def cycles_to_us(cycles: int) -> float:
    """Convert clock cycles to microseconds @ 125MHz.

    Args:
        cycles: Number of clock cycles

    Returns:
        Time in microseconds
    """
    return cycles * 1e6 / CLK_FREQ_HZ


# P1 Test Values (fast CocoTB timing - may be too fast for hardware observation)
class P1TestValues:
    """Test values from CocoTB P1 (BASIC) level - very fast execution."""

    # Trigger voltages (in mV)
    TRIGGER_THRESHOLD_MV = 950  # Default threshold
    TRIGGER_TEST_VOLTAGE_MV = 1500  # Above threshold

    # Trigger voltages as digital values
    TRIGGER_THRESHOLD_DIGITAL = mv_to_digital(TRIGGER_THRESHOLD_MV)  # ~6225
    TRIGGER_TEST_VOLTAGE_DIGITAL = mv_to_digital(TRIGGER_TEST_VOLTAGE_MV)  # ~9830

    # Timing (reduced for fast P1 tests - may be too fast for oscilloscope polling)
    TRIG_OUT_DURATION_CYCLES = 1000  # 8μs @ 125MHz
    INTENSITY_DURATION_CYCLES = 2000  # 16μs @ 125MHz
    COOLDOWN_INTERVAL_CYCLES = 500   # 4μs @ 125MHz

    # Convert to microseconds for readability
    TRIG_OUT_DURATION_US = cycles_to_us(TRIG_OUT_DURATION_CYCLES)      # 8μs
    INTENSITY_DURATION_US = cycles_to_us(INTENSITY_DURATION_CYCLES)    # 16μs
    COOLDOWN_INTERVAL_US = cycles_to_us(COOLDOWN_INTERVAL_CYCLES)      # 4μs

    # Total FSM cycle time
    TOTAL_FSM_CYCLES = TRIG_OUT_DURATION_CYCLES + INTENSITY_DURATION_CYCLES + COOLDOWN_INTERVAL_CYCLES
    TOTAL_FSM_US = cycles_to_us(TOTAL_FSM_CYCLES)  # ~28μs

    # Output voltages (for pulse verification)
    TRIG_OUT_VOLTAGE_MV = 2000      # OutputA voltage during trigger pulse
    INTENSITY_VOLTAGE_MV = 1500     # OutputB voltage during intensity pulse


# P2 Test Values (realistic, human-observable timing - RECOMMENDED for hardware)
class P2TestValues:
    """Test values for P2 (INTERMEDIATE) level - realistic timing, easier to observe."""

    TRIGGER_THRESHOLD_MV = 950
    TRIGGER_TEST_VOLTAGE_MV = 1500
    TRIGGER_THRESHOLD_DIGITAL = mv_to_digital(TRIGGER_THRESHOLD_MV)
    TRIGGER_TEST_VOLTAGE_DIGITAL = mv_to_digital(TRIGGER_TEST_VOLTAGE_MV)

    # Production-like timing (easier to observe on oscilloscope)
    TRIG_OUT_DURATION_CYCLES = 12500   # 100μs @ 125MHz
    INTENSITY_DURATION_CYCLES = 25000  # 200μs @ 125MHz
    COOLDOWN_INTERVAL_CYCLES = 1250    # 10μs @ 125MHz

    TRIG_OUT_DURATION_US = cycles_to_us(TRIG_OUT_DURATION_CYCLES)      # 100μs
    INTENSITY_DURATION_US = cycles_to_us(INTENSITY_DURATION_CYCLES)    # 200μs
    COOLDOWN_INTERVAL_US = cycles_to_us(COOLDOWN_INTERVAL_CYCLES)      # 10μs

    TOTAL_FSM_CYCLES = TRIG_OUT_DURATION_CYCLES + INTENSITY_DURATION_CYCLES + COOLDOWN_INTERVAL_CYCLES
    TOTAL_FSM_US = cycles_to_us(TOTAL_FSM_CYCLES)  # ~310μs

    TRIG_OUT_VOLTAGE_MV = 2000
    INTENSITY_VOLTAGE_MV = 1500


# Default timing configuration for hardware tests (use P2 for visibility)
DEFAULT_TRIG_OUT_DURATION_US = P2TestValues.TRIG_OUT_DURATION_US
DEFAULT_INTENSITY_DURATION_US = P2TestValues.INTENSITY_DURATION_US
DEFAULT_COOLDOWN_INTERVAL_US = P2TestValues.COOLDOWN_INTERVAL_US
DEFAULT_TRIGGER_THRESHOLD_MV = P2TestValues.TRIGGER_THRESHOLD_MV
DEFAULT_TRIGGER_TEST_VOLTAGE_MV = P2TestValues.TRIGGER_TEST_VOLTAGE_MV
DEFAULT_TRIG_OUT_VOLTAGE_MV = P2TestValues.TRIG_OUT_VOLTAGE_MV
DEFAULT_INTENSITY_VOLTAGE_MV = P2TestValues.INTENSITY_VOLTAGE_MV

# Oscilloscope polling configuration
OSC_POLL_COUNT_DEFAULT = 5          # Number of samples to average for state reading
OSC_POLL_INTERVAL_MS = 20           # Milliseconds between oscilloscope polls
OSC_STATE_TIMEOUT_MS = 2000         # Default timeout for state transitions (2 seconds)

# Test timeouts (conservative for real hardware)
TEST_RESET_TIMEOUT_MS = 500
TEST_ARM_TIMEOUT_MS = 1000
TEST_TRIGGER_TIMEOUT_MS = 1000
TEST_FSM_CYCLE_TIMEOUT_MS = 3000    # Must be > TOTAL_FSM_US + margin
