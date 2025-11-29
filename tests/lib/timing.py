"""
Test Timing Configurations

Defines timing configurations for different test levels:
- P1Timing: Fast timing for simulation (8-16us pulses)
- P2Timing: Observable timing for hardware (100-200us pulses)

These are TEST configurations, not production defaults.
Production defaults are in py_tools/dpd_constants.py (DefaultTiming).
"""

from .clk import cycles_to_us
from .hw import HVS


class _TestTimingBase:
    """Base class with shared trigger/voltage values for all test timing levels."""

    # Trigger threshold (shared across all test levels)
    TRIGGER_THRESHOLD_MV = 950
    TRIGGER_TEST_VOLTAGE_MV = 1500

    # Trigger threshold as digital values
    TRIGGER_THRESHOLD_DIGITAL = HVS.mv_to_digital(950)
    TRIGGER_TEST_VOLTAGE_DIGITAL = HVS.mv_to_digital(1500)

    # Output voltages (mV)
    TRIG_OUT_VOLTAGE_MV = 2000
    INTENSITY_VOLTAGE_MV = 1500


class P1Timing(_TestTimingBase):
    """Fast timing for P1 (BASIC) simulation tests.

    Optimized for fast test execution in CocoTB simulations.
    May be too fast for hardware oscilloscope observation.

    Total cycle: ~28us
    """

    # Timing in clock cycles
    TRIG_OUT_DURATION = 1000     # 8us @ 125MHz
    INTENSITY_DURATION = 2000   # 16us @ 125MHz
    COOLDOWN_INTERVAL = 500     # 4us @ 125MHz

    # Derived values
    TOTAL_CYCLES = TRIG_OUT_DURATION + INTENSITY_DURATION + COOLDOWN_INTERVAL

    # Timing in microseconds (for reference)
    TRIG_OUT_DURATION_US = cycles_to_us(TRIG_OUT_DURATION)
    INTENSITY_DURATION_US = cycles_to_us(INTENSITY_DURATION)
    COOLDOWN_INTERVAL_US = cycles_to_us(COOLDOWN_INTERVAL)
    TOTAL_US = cycles_to_us(TOTAL_CYCLES)


class P2Timing(_TestTimingBase):
    """Observable timing for P2 (INTERMEDIATE) hardware tests.

    Slower timing that's easier to observe on oscilloscopes.
    Recommended for hardware tests.

    Total cycle: ~310us
    """

    # Timing in clock cycles
    TRIG_OUT_DURATION = 12500   # 100us @ 125MHz
    INTENSITY_DURATION = 25000  # 200us @ 125MHz
    COOLDOWN_INTERVAL = 1250    # 10us @ 125MHz

    # Derived values
    TOTAL_CYCLES = TRIG_OUT_DURATION + INTENSITY_DURATION + COOLDOWN_INTERVAL

    # Timing in microseconds (for reference)
    TRIG_OUT_DURATION_US = cycles_to_us(TRIG_OUT_DURATION)
    INTENSITY_DURATION_US = cycles_to_us(INTENSITY_DURATION)
    COOLDOWN_INTERVAL_US = cycles_to_us(COOLDOWN_INTERVAL)
    TOTAL_US = cycles_to_us(TOTAL_CYCLES)


# Default trigger wait timeout (shared)
DEFAULT_TRIGGER_WAIT_TIMEOUT = 250_000_000  # 2s @ 125MHz
