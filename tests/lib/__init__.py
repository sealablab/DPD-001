"""
DPD Test Library
================

Single import point for all test constants, utilities, and configuration.

Usage:
    from tests.lib import CR1, P1Timing, SIM_HVS_TOLERANCE, DPDConfig
    from tests.lib import us_to_cycles, cr1_build

This replaces the fragmented imports from:
- tests/shared/constants.py
- tests/sim/dpd/constants.py
- tests/hw/dpd/constants.py
"""

# Hardware constants (from py_tools/dpd_constants.py)
from .hw import (
    CR0,
    CR1,
    FSMState,
    HVS,
    Platform,
    DefaultTiming,
    cr1_build,
    cr1_extract,
    # Convenience aliases
    MCC_CR0_ALL_ENABLED,
    MCC_CR0_FORGE_READY,
    MCC_CR0_USER_ENABLE,
    MCC_CR0_CLK_ENABLE,
    HVS_DIGITAL_INITIALIZING,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    mv_to_digital,
    digital_to_mv,
)

# Clock utilities (from py_tools/clk_utils.py)
from .clk import (
    s_to_cycles,
    us_to_cycles,
    ns_to_cycles,
    cycles_to_s,
    cycles_to_us,
    cycles_to_ns,
    DEFAULT_CLK_FREQ_HZ,
)

# Test timing configurations
from .timing import (
    P1Timing,
    P2Timing,
    DEFAULT_TRIGGER_WAIT_TIMEOUT,
)

# Tolerances
from .tolerances import (
    SIM_HVS_TOLERANCE,
    HW_HVS_TOLERANCE_V,
    HW_HVS_TOLERANCE_DIGITAL,
)

# Timeouts
from .timeouts import Timeouts

# Configuration dataclass
from .config import DPDConfig

# [COMPAT] Backward compatibility aliases - delete once imports updated
P1TestValues = P1Timing
P2TestValues = P2Timing
HVS_DIGITAL_TOLERANCE = SIM_HVS_TOLERANCE
CLK_PERIOD_NS = Platform.CLK_PERIOD_NS
CLK_FREQ_HZ = Platform.CLK_FREQ_HZ

# Trigger values (from timing base)
TRIGGER_THRESHOLD_MV = P1Timing.TRIGGER_THRESHOLD_MV
TRIGGER_TEST_VOLTAGE_MV = P1Timing.TRIGGER_TEST_VOLTAGE_MV
TRIGGER_THRESHOLD_DIGITAL = P1Timing.TRIGGER_THRESHOLD_DIGITAL
TRIGGER_TEST_VOLTAGE_DIGITAL = P1Timing.TRIGGER_TEST_VOLTAGE_DIGITAL

# State voltage map (for hardware tests)
STATE_VOLTAGE_MAP = HVS.STATE_VOLTAGE_MAP
VOLTAGE_STATE_MAP = {v: k for k, v in STATE_VOLTAGE_MAP.items()}
