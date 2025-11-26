"""
CocoTB Test Base Class with Verbosity Control
==============================================

Extends the shared TestRunnerMixin for CocoTB-specific test execution.
Provides a base class for all CocoTB tests that implements:
- Progressive test levels (P1=basic, P2=intermediate, P3=comprehensive)
- Controlled verbosity to minimize LLM context consumption
- Standardized test output formatting

Author: Moku Instrument Forge Team
Date: 2025-11-26 (refactored to use shared infrastructure)
"""

import cocotb
import os
import sys
from pathlib import Path

# Add shared module to path
TESTS_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(TESTS_PATH))

# Import from shared infrastructure
from shared.test_base_common import (
    TestLevel,
    VerbosityLevel,
    TestResult,
    TestRunnerMixin,
)

# Re-export for backward compatibility
__all__ = ['TestLevel', 'VerbosityLevel', 'TestResult', 'TestBase', 'get_test_runner']


class TestBase(TestRunnerMixin):
    """Base class for CocoTB tests with verbosity control.

    Extends TestRunnerMixin with CocoTB-specific logging and async test execution.

    Usage in test modules:
        from test_base import TestBase, TestLevel, VerbosityLevel

        class MyModuleTest(TestBase):
            def __init__(self, dut):
                super().__init__(dut, "MyModule")

            async def run_p1_basic(self):
                await self.test("Reset behavior", self.test_reset)
                await self.test("Basic operation", self.test_basic_op)

            async def test_reset(self):
                # Test implementation
                pass
    """

    def __init__(self, dut, module_name: str):
        """Initialize test base.

        Args:
            dut: DUT object from CocoTB
            module_name: Name of module being tested
        """
        self.dut = dut
        self.module_name = module_name

        # Get verbosity from environment (default: MINIMAL for LLM-friendliness)
        verbosity_str = os.environ.get("COCOTB_VERBOSITY", "MINIMAL")
        try:
            verbosity = VerbosityLevel[verbosity_str.upper()]
        except KeyError:
            verbosity = VerbosityLevel.MINIMAL

        # Initialize the mixin
        self._init_test_runner(verbosity)

        # Get test level from environment (default: P1_BASIC)
        level_str = os.environ.get("TEST_LEVEL", "P1_BASIC")
        try:
            self.test_level = TestLevel[level_str.upper()]
        except KeyError:
            self.test_level = TestLevel.P1_BASIC

    def _log_message(self, message: str):
        """Log a message via CocoTB's logging."""
        self.dut._log.info(message)

    def _log_error(self, message: str):
        """Log an error message via CocoTB's logging."""
        self.dut._log.error(message)

    async def test(self, test_name: str, test_func):
        """Run a single test with proper logging.

        Args:
            test_name: Name of the test
            test_func: Async function to run
        """
        self.log_test_start(test_name)

        try:
            await test_func()
            self.add_result(test_name, True)
            self.log_test_pass(test_name)
        except Exception as e:
            self.add_result(test_name, False, str(e))
            self.log_test_fail(test_name, str(e))
            raise  # Re-raise to fail the test

    def should_run_level(self, level: TestLevel) -> bool:
        """Check if tests at this level should run.

        Progressive: P1 always runs, P2 runs if level >= P2, etc.
        """
        return self.test_level >= level

    async def run_all_tests(self):
        """Run all test phases up to the configured level.

        Override run_p1_basic, run_p2_intermediate, etc. in subclasses.
        """
        # Always run P1 (basic tests)
        if hasattr(self, 'run_p1_basic'):
            self.log_phase_start("P1 - BASIC TESTS")
            await self.run_p1_basic()

        # Run P2 if level >= P2
        if self.should_run_level(TestLevel.P2_INTERMEDIATE) and hasattr(self, 'run_p2_intermediate'):
            self.log_phase_start("P2 - INTERMEDIATE TESTS")
            await self.run_p2_intermediate()

        # Run P3 if level >= P3
        if self.should_run_level(TestLevel.P3_COMPREHENSIVE) and hasattr(self, 'run_p3_comprehensive'):
            self.log_phase_start("P3 - COMPREHENSIVE TESTS")
            await self.run_p3_comprehensive()

        # Run P4 if level >= P4
        if self.should_run_level(TestLevel.P4_EXHAUSTIVE) and hasattr(self, 'run_p4_exhaustive'):
            self.log_phase_start("P4 - EXHAUSTIVE TESTS")
            await self.run_p4_exhaustive()

        # Print summary
        self.log_summary()

        # Fail if any tests failed
        if self.failed_count > 0:
            raise AssertionError(f"{self.failed_count} tests failed")


def get_test_runner(dut, module_name: str) -> TestBase:
    """Factory function to create test runner with proper configuration.

    Args:
        dut: CocoTB DUT object
        module_name: Name of module being tested

    Returns:
        Configured TestBase instance
    """
    return TestBase(dut, module_name)
