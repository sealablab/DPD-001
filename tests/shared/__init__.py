"""
Shared Test Infrastructure for DPD
===================================

This package contains test infrastructure shared between simulation (CocoTB)
and hardware (Moku) tests.

Modules:
- control_interface: Abstract interface for control register operations
- test_base_common: Common TestLevel, VerbosityLevel, TestResult, logging
- state_helpers: Abstract interface for FSM state operations
- test_cases: Data-driven test case definitions

For constants, import from tests.lib (API v4.0):
    from tests.lib import CR0, P1Timing, HVS

Usage:
    from tests.shared.control_interface import CocoTBControl, MokuControl
    from tests.shared.test_base_common import TestLevel, VerbosityLevel
"""

from .control_interface import (
    ControlInterface,
    CocoTBControl,
    MokuControl,
)

from .test_base_common import (
    TestLevel,
    VerbosityLevel,
    TestResult,
)
