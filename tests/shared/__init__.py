"""
Shared Test Infrastructure for DPD
===================================

This package contains test infrastructure shared between simulation (CocoTB)
and hardware (Moku) tests.

Modules:
- constants: Shared constants (re-exports from py_tools + test-specific)
- test_base_common: Common TestLevel, VerbosityLevel, TestResult, logging
- state_helpers: Abstract interface for FSM state operations
- test_cases: Data-driven test case definitions

Usage:
    from tests.shared.constants import MCC_CR0_ALL_ENABLED, P1Timing
    from tests.shared.test_base_common import TestLevel, VerbosityLevel
    from tests.shared.test_cases import P1_TEST_RESET
"""

from .constants import (
    # Re-export hardware constants
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
    # Test timing
    P1Timing,
    P2Timing,
    # Voltage helpers
    mv_to_digital,
    digital_to_mv,
)

from .test_base_common import (
    TestLevel,
    VerbosityLevel,
    TestResult,
)
