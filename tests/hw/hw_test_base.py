"""
Hardware Test Base Class with Progressive Testing Framework
============================================================

Extends the shared TestRunnerMixin for Moku hardware test execution.
Provides base class for hardware tests with verbosity control and result tracking.

Author: Moku Instrument Forge Team
Date: 2025-11-26 (refactored to use shared infrastructure)
"""

import time
import sys
from pathlib import Path
from typing import Optional, Callable, List, Tuple

# Add shared module to path
TESTS_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(TESTS_PATH))

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru not installed. Run: uv sync")
    sys.exit(1)

try:
    from moku.instruments import MultiInstrument, Oscilloscope, CloudCompile
except ImportError:
    print("ERROR: moku package not found. Run: uv sync")
    sys.exit(1)

# Import from shared infrastructure
from shared.test_base_common import (
    TestLevel,
    VerbosityLevel,
    TestResult,
    TestRunnerMixin,
)

from dpd.helpers import (
    read_fsm_state,
    wait_for_state,
    init_forge_ready,
    validate_routing,
    setup_routing,
)

# Re-export for backward compatibility
__all__ = ['TestLevel', 'VerbosityLevel', 'TestResult', 'HardwareTestBase']


class HardwareTestBase(TestRunnerMixin):
    """Base class for hardware progressive tests.

    Extends TestRunnerMixin with Moku-specific functionality.

    Usage in test modules:
        from hw_test_base import HardwareTestBase, TestLevel, VerbosityLevel

        class MyHardwareTest(HardwareTestBase):
            def __init__(self, moku, osc_slot=1, cc_slot=2):
                super().__init__(moku, "MyTest", osc_slot, cc_slot)

            def run_p1_basic(self):
                self.test("Reset behavior", self.test_reset)
                self.test("Basic operation", self.test_basic_op)

            def test_reset(self):
                state, _ = self.read_state()
                assert state == "IDLE", f"Expected IDLE, got {state}"
    """

    def __init__(self, moku: MultiInstrument, test_name: str,
                 osc_slot: int = 1, cc_slot: int = 2,
                 bitstream: str = None,
                 verbosity: VerbosityLevel = VerbosityLevel.MINIMAL,
                 validate_instruments: bool = True):
        """Initialize hardware test base.

        Args:
            moku: Connected MultiInstrument instance
            test_name: Name of test suite
            osc_slot: Oscilloscope slot number (default: 1)
            cc_slot: CloudCompile slot number (default: 2)
            bitstream: Path to CloudCompile bitstream
            verbosity: Output verbosity level
            validate_instruments: If True, validate instruments are deployed
        """
        self.moku = moku
        self.test_name = test_name
        self.osc_slot = osc_slot
        self.cc_slot = cc_slot
        self.bitstream = bitstream

        # Initialize the mixin
        self._init_test_runner(verbosity)

        # Get instrument instances
        if validate_instruments:
            self.log(f"Validating instruments in slots {osc_slot} (OSC) and {cc_slot} (CC)...",
                     VerbosityLevel.VERBOSE)

        try:
            self.osc = Oscilloscope.for_slot(slot=osc_slot, multi_instrument=moku)

            if bitstream is None:
                raise ValueError("bitstream parameter is required for CloudCompile.for_slot()")
            self.mcc = CloudCompile.for_slot(slot=cc_slot, multi_instrument=moku, bitstream=bitstream)
        except Exception as e:
            self.log(f"ERROR: Failed to get instruments: {e}", VerbosityLevel.MINIMAL)
            raise RuntimeError(
                f"Failed to get instruments. Ensure Oscilloscope is in slot {osc_slot} "
                f"and CloudCompile is in slot {cc_slot}. Error: {e}"
            )

        if validate_instruments:
            self.log("\u2713 Instruments validated", VerbosityLevel.VERBOSE)

    def _log_message(self, message: str):
        """Log a message via loguru."""
        logger.info(message)

    def _log_error(self, message: str):
        """Log an error message via loguru."""
        logger.error(message)

    def test(self, test_name: str, test_func: Callable):
        """Run a single test with proper logging and error handling.

        Args:
            test_name: Name of the test
            test_func: Function to run (synchronous)
        """
        self.log_test_start(test_name)
        start_time = time.time()

        try:
            test_func()
            duration_ms = (time.time() - start_time) * 1000
            self.add_result(test_name, True, duration_ms=duration_ms)
            self.log_test_pass(test_name, duration_ms)
        except AssertionError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            self.add_result(test_name, False, error_msg, duration_ms)
            self.log_test_fail(test_name, error_msg, duration_ms)
            # Don't re-raise - continue to next test
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Unexpected error: {e}"
            self.add_result(test_name, False, error_msg, duration_ms)
            self.log_test_fail(test_name, error_msg, duration_ms)

    def read_state(self, poll_count: int = 5) -> Tuple[str, float]:
        """Read current FSM state from oscilloscope.

        Args:
            poll_count: Number of samples to average

        Returns:
            Tuple of (state_name, voltage)
        """
        return read_fsm_state(self.osc, poll_count=poll_count)

    def wait_state(self, expected_state: str, timeout_ms: float = 2000) -> bool:
        """Wait for FSM to reach expected state.

        Args:
            expected_state: Target state name
            timeout_ms: Timeout in milliseconds

        Returns:
            True if state reached, False on timeout
        """
        return wait_for_state(self.osc, expected_state, timeout_ms=timeout_ms)

    def validate_routing(self) -> bool:
        """Validate routing is configured correctly.

        Returns:
            True if routing is correct, False otherwise
        """
        return validate_routing(self.moku, self.osc_slot, self.cc_slot)

    def setup_routing(self):
        """Set up routing for tests."""
        setup_routing(self.moku, self.osc_slot, self.cc_slot)

    def init_forge(self):
        """Initialize FORGE_READY bits."""
        init_forge_ready(self.mcc)

    def run_all_tests(self, test_level: TestLevel = TestLevel.P1_BASIC) -> bool:
        """Run all test phases up to the configured level.

        Override run_p1_basic, run_p2_intermediate, etc. in subclasses.

        Args:
            test_level: Maximum test level to run

        Returns:
            True if all tests passed, False otherwise
        """
        # Always run P1 (basic tests)
        if hasattr(self, 'run_p1_basic'):
            self.log_phase_start("P1 - BASIC TESTS")
            self.run_p1_basic()

        # Run P2 if level >= P2
        if self.should_run_level(TestLevel.P2_INTERMEDIATE, test_level) and hasattr(self, 'run_p2_intermediate'):
            self.log_phase_start("P2 - INTERMEDIATE TESTS")
            self.run_p2_intermediate()

        # Run P3 if level >= P3
        if self.should_run_level(TestLevel.P3_COMPREHENSIVE, test_level) and hasattr(self, 'run_p3_comprehensive'):
            self.log_phase_start("P3 - COMPREHENSIVE TESTS")
            self.run_p3_comprehensive()

        # Print summary
        self.log_summary()

        return self.failed_count == 0
