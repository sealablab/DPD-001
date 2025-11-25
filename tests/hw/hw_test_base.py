"""
Hardware Test Base Class with Progressive Testing Framework

Provides base class for hardware tests with verbosity control and result tracking.
Adapted from cocotb_tests/test_base.py

Author: Moku Instrument Forge Team
Date: 2025-01-18
"""

import time
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Callable, List

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru not installed. Run: uv sync")
    import sys
    sys.exit(1)

try:
    from moku.instruments import MultiInstrument, Oscilloscope, CloudCompile
except ImportError:
    print("ERROR: moku package not found. Run: uv sync")
    import sys
    sys.exit(1)

from hw_test_helpers import (
    read_fsm_state,
    wait_for_state,
    init_forge_ready,
    validate_routing,
    setup_routing,
)


class TestLevel(IntEnum):
    """
    Test progression levels:
    - P1_BASIC: Minimal tests, essential functionality only
    - P2_INTERMEDIATE: Moderate tests, core functionality
    - P3_COMPREHENSIVE: Full tests, edge cases and stress tests
    """
    P1_BASIC = 1
    P2_INTERMEDIATE = 2
    P3_COMPREHENSIVE = 3


class VerbosityLevel(IntEnum):
    """
    Output verbosity control:
    - SILENT: No output except failures
    - MINIMAL: Test name + PASS/FAIL only
    - NORMAL: Progress indicators + results
    - VERBOSE: Detailed step-by-step output
    - DEBUG: Full debug information
    """
    SILENT = 0
    MINIMAL = 1
    NORMAL = 2
    VERBOSE = 3
    DEBUG = 4


@dataclass
class TestResult:
    """Single test result record."""
    name: str
    passed: bool
    error: Optional[str] = None
    duration_ms: float = 0


class HardwareTestBase:
    """
    Base class for hardware progressive tests.

    Usage in test modules:
        from hw_test_base import HardwareTestBase, TestLevel, VerbosityLevel

        class MyHardwareTest(HardwareTestBase):
            def __init__(self, moku, osc_slot=1, cc_slot=2):
                super().__init__(moku, "MyTest", osc_slot, cc_slot)

            def run_p1_basic(self):
                self.test("Reset behavior", self.test_reset)
                self.test("Basic operation", self.test_basic_op)

            def test_reset(self):
                # Test implementation
                state, _ = self.read_state()
                assert state == "IDLE", f"Expected IDLE, got {state}"
    """

    def __init__(self, moku: MultiInstrument, test_name: str,
                 osc_slot: int = 1, cc_slot: int = 2,
                 bitstream: str = None,
                 verbosity: VerbosityLevel = VerbosityLevel.MINIMAL,
                 validate_instruments: bool = True):
        """
        Initialize hardware test base.

        Args:
            moku: Connected MultiInstrument instance
            test_name: Name of test suite
            osc_slot: Oscilloscope slot number (default: 1)
            cc_slot: CloudCompile slot number (default: 2)
            bitstream: Path to CloudCompile bitstream (required for CloudCompile.for_slot)
            verbosity: Output verbosity level
            validate_instruments: If True, validate instruments are deployed
        """
        self.moku = moku
        self.test_name = test_name
        self.osc_slot = osc_slot
        self.cc_slot = cc_slot
        self.bitstream = bitstream
        self.verbosity = verbosity

        # Track test results
        self.results: List[TestResult] = []
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
        self.current_phase = None

        # Get instrument instances
        if validate_instruments:
            self.log(f"Validating instruments in slots {osc_slot} (OSC) and {cc_slot} (CC)...",
                     VerbosityLevel.VERBOSE)

        try:
            # Use for_slot() pattern to access already-deployed instruments
            self.osc = Oscilloscope.for_slot(slot=osc_slot, multi_instrument=moku)

            # CloudCompile requires bitstream parameter even when accessing existing deployment
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
            self.log("✓ Instruments validated", VerbosityLevel.VERBOSE)

    def log(self, message: str, level: VerbosityLevel = VerbosityLevel.NORMAL):
        """
        Conditional logging based on verbosity level.

        Args:
            message: Message to log
            level: Required verbosity level for this message
        """
        if self.verbosity >= level:
            logger.info(message)

    def log_separator(self, level: VerbosityLevel = VerbosityLevel.NORMAL):
        """Log a separator line."""
        self.log("=" * 70, level)

    def log_test_start(self, test_name: str):
        """Log test start based on verbosity."""
        self.test_count += 1

        if self.verbosity == VerbosityLevel.SILENT:
            pass  # No output
        elif self.verbosity == VerbosityLevel.MINIMAL:
            # Just test number and name, no decoration
            logger.info(f"T{self.test_count}: {test_name}")
        elif self.verbosity == VerbosityLevel.NORMAL:
            self.log_separator()
            logger.info(f"Test {self.test_count}: {test_name}")
        else:  # VERBOSE or DEBUG
            self.log_separator()
            logger.info(f"Test {self.test_count}: {test_name}")
            self.log_separator()

    def log_test_pass(self, test_name: str, duration_ms: float):
        """Log test pass."""
        self.passed_count += 1

        if self.verbosity == VerbosityLevel.SILENT:
            pass  # No output
        elif self.verbosity == VerbosityLevel.MINIMAL:
            logger.info(f"  ✓ PASS")
        elif self.verbosity == VerbosityLevel.NORMAL:
            logger.info(f"✓ {test_name} PASSED ({duration_ms:.0f}ms)")
        else:  # VERBOSE or DEBUG
            logger.info(f"✓ {test_name} PASSED ({duration_ms:.1f}ms)")

    def log_test_fail(self, test_name: str, error: str, duration_ms: float):
        """Log test failure."""
        self.failed_count += 1

        # Always log failures regardless of verbosity
        if self.verbosity == VerbosityLevel.MINIMAL:
            logger.error(f"  ✗ FAIL: {error}")
        else:
            logger.error(f"✗ {test_name} FAILED ({duration_ms:.0f}ms): {error}")

    def log_phase_start(self, phase_name: str):
        """Log phase start (P1, P2, etc.)."""
        self.current_phase = phase_name

        if self.verbosity == VerbosityLevel.SILENT:
            pass
        elif self.verbosity == VerbosityLevel.MINIMAL:
            logger.info(f"\n{phase_name}")
        else:
            self.log_separator(VerbosityLevel.NORMAL)
            logger.info(f"PHASE: {phase_name}")
            self.log_separator(VerbosityLevel.NORMAL)

    def log_summary(self):
        """Log test summary."""
        if self.verbosity == VerbosityLevel.SILENT and self.failed_count == 0:
            # Silent mode with all tests passing - no output
            pass
        elif self.verbosity == VerbosityLevel.MINIMAL:
            # Minimal one-line summary
            if self.failed_count == 0:
                logger.info(f"ALL {self.test_count} TESTS PASSED")
            else:
                logger.error(f"FAILED: {self.failed_count}/{self.test_count}")
        else:
            # Normal or verbose summary
            self.log_separator()
            logger.info(f"TEST SUITE: {self.test_name}")
            logger.info(f"TESTS RUN: {self.test_count}")
            logger.info(f"PASSED: {self.passed_count}")
            logger.info(f"FAILED: {self.failed_count}")

            if self.failed_count == 0:
                logger.info("RESULT: ALL TESTS PASSED ✓")
            else:
                logger.error(f"RESULT: {self.failed_count} TESTS FAILED ✗")

            # Show failed tests
            if self.failed_count > 0 and self.verbosity >= VerbosityLevel.NORMAL:
                logger.info("\nFailed tests:")
                for result in self.results:
                    if not result.passed:
                        logger.error(f"  - {result.name}: {result.error}")

            self.log_separator()

    def test(self, test_name: str, test_func: Callable):
        """
        Run a single test with proper logging and error handling.

        Args:
            test_name: Name of the test
            test_func: Function to run (no async, since hardware tests are synchronous)
        """
        self.log_test_start(test_name)
        start_time = time.time()

        try:
            test_func()  # Run test
            duration_ms = (time.time() - start_time) * 1000
            self.results.append(TestResult(test_name, True, duration_ms=duration_ms))
            self.log_test_pass(test_name, duration_ms)
        except AssertionError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            self.results.append(TestResult(test_name, False, error_msg, duration_ms))
            self.log_test_fail(test_name, error_msg, duration_ms)
            # Don't re-raise - continue to next test
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Unexpected error: {e}"
            self.results.append(TestResult(test_name, False, error_msg, duration_ms))
            self.log_test_fail(test_name, error_msg, duration_ms)

    def should_run_level(self, level: TestLevel, current_level: TestLevel) -> bool:
        """
        Check if tests at this level should run.

        Args:
            level: Test level to check
            current_level: Current configured test level

        Returns:
            True if this level should run
        """
        return current_level >= level

    def read_state(self, poll_count: int = 5) -> tuple[str, float]:
        """
        Read current FSM state from oscilloscope.

        Convenience wrapper around hw_test_helpers.read_fsm_state.

        Args:
            poll_count: Number of samples to average

        Returns:
            Tuple of (state_name, voltage)
        """
        return read_fsm_state(self.osc, poll_count=poll_count)

    def wait_state(self, expected_state: str, timeout_ms: float = 2000) -> bool:
        """
        Wait for FSM to reach expected state.

        Convenience wrapper around hw_test_helpers.wait_for_state.

        Args:
            expected_state: Target state name
            timeout_ms: Timeout in milliseconds

        Returns:
            True if state reached, False on timeout
        """
        return wait_for_state(self.osc, expected_state, timeout_ms=timeout_ms)

    def validate_routing(self) -> bool:
        """
        Validate routing is configured correctly.

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

    def run_all_tests(self, test_level: TestLevel = TestLevel.P1_BASIC):
        """
        Run all test phases up to the configured level.

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

        # Return success/failure
        return self.failed_count == 0
