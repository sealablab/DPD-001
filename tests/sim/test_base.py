"""
CocotB Test Base Class with Verbosity Control

Provides a base class for all CocotB tests that implements:
- Progressive test levels (P1=basic, P2=intermediate, P3=comprehensive)
- Controlled verbosity to minimize LLM context consumption
- Standardized test output formatting

Author: Volo Engineering
Date: 2025-01-26
"""

import cocotb
import os
from enum import IntEnum
from typing import Optional


class TestLevel(IntEnum):
    """
    Test progression levels:
    - P1_BASIC: Minimal output, essential tests only (LLM-friendly)
    - P2_INTERMEDIATE: Moderate output, core functionality
    - P3_COMPREHENSIVE: Full output, edge cases and stress tests
    - P4_EXHAUSTIVE: Debug-level output, all permutations
    """
    P1_BASIC = 1
    P2_INTERMEDIATE = 2
    P3_COMPREHENSIVE = 3
    P4_EXHAUSTIVE = 4


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


class TestBase:
    """
    Base class for CocotB tests with verbosity control.

    Usage in test modules:
        from test_base import TestBase, TestLevel, VerbosityLevel

        class MyModuleTest(TestBase):
            def __init__(self, dut):
                super().__init__(dut, "MyModule")

            async def run_p1_basic(self):
                await self.test("Reset behavior", self.test_reset)
                await self.test("Basic operation", self.test_basic_op)

            async def run_p2_intermediate(self):
                await self.test("Edge cases", self.test_edges)

            async def test_reset(self):
                # Test implementation
                pass
    """

    def __init__(self, dut, module_name: str):
        """
        Initialize test base.

        Args:
            dut: DUT object from CocotB
            module_name: Name of module being tested
        """
        self.dut = dut
        self.module_name = module_name

        # Get verbosity from environment (default: MINIMAL for LLM-friendliness)
        verbosity_str = os.environ.get("COCOTB_VERBOSITY", "MINIMAL")
        try:
            self.verbosity = VerbosityLevel[verbosity_str.upper()]
        except KeyError:
            self.verbosity = VerbosityLevel.MINIMAL

        # Get test level from environment (default: P1_BASIC)
        level_str = os.environ.get("TEST_LEVEL", "P1_BASIC")
        try:
            self.test_level = TestLevel[level_str.upper()]
        except KeyError:
            self.test_level = TestLevel.P1_BASIC

        # Track test results
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
        self.current_phase = None

    def log(self, message: str, level: VerbosityLevel = VerbosityLevel.NORMAL):
        """
        Conditional logging based on verbosity level.

        Args:
            message: Message to log
            level: Required verbosity level for this message
        """
        if self.verbosity >= level:
            self.dut._log.info(message)

    def log_separator(self, level: VerbosityLevel = VerbosityLevel.NORMAL):
        """Log a separator line"""
        self.log("=" * 60, level)

    def log_test_start(self, test_name: str):
        """Log test start based on verbosity"""
        self.test_count += 1

        if self.verbosity == VerbosityLevel.SILENT:
            pass  # No output
        elif self.verbosity == VerbosityLevel.MINIMAL:
            # Just test number and name, no decoration
            self.dut._log.info(f"T{self.test_count}: {test_name}")
        elif self.verbosity == VerbosityLevel.NORMAL:
            self.log_separator()
            self.dut._log.info(f"Test {self.test_count}: {test_name}")
        else:  # VERBOSE or DEBUG
            self.log_separator()
            self.dut._log.info(f"Test {self.test_count}: {test_name}")
            self.log_separator()

    def log_test_pass(self, test_name: str):
        """Log test pass"""
        self.passed_count += 1

        if self.verbosity == VerbosityLevel.SILENT:
            pass  # No output
        elif self.verbosity == VerbosityLevel.MINIMAL:
            self.dut._log.info(f"  ✓ PASS")
        elif self.verbosity >= VerbosityLevel.NORMAL:
            self.dut._log.info(f"✓ {test_name} PASSED")

    def log_test_fail(self, test_name: str, error: str):
        """Log test failure"""
        self.failed_count += 1

        # Always log failures regardless of verbosity
        self.dut._log.error(f"✗ {test_name} FAILED: {error}")

    def log_phase_start(self, phase_name: str):
        """Log phase start (P1, P2, etc.)"""
        self.current_phase = phase_name

        if self.verbosity == VerbosityLevel.SILENT:
            pass
        elif self.verbosity == VerbosityLevel.MINIMAL:
            self.dut._log.info(f"\n{phase_name}")
        else:
            self.log_separator(VerbosityLevel.NORMAL)
            self.dut._log.info(f"PHASE: {phase_name}")
            self.log_separator(VerbosityLevel.NORMAL)

    def log_summary(self):
        """Log test summary"""
        if self.verbosity == VerbosityLevel.SILENT and self.failed_count == 0:
            # Silent mode with all tests passing - no output
            pass
        elif self.verbosity == VerbosityLevel.MINIMAL:
            # Minimal one-line summary
            if self.failed_count == 0:
                self.dut._log.info(f"ALL {self.test_count} TESTS PASSED")
            else:
                self.dut._log.info(f"FAILED: {self.failed_count}/{self.test_count}")
        else:
            # Normal or verbose summary
            self.log_separator()
            self.dut._log.info(f"MODULE: {self.module_name}")
            self.dut._log.info(f"TESTS RUN: {self.test_count}")
            self.dut._log.info(f"PASSED: {self.passed_count}")
            self.dut._log.info(f"FAILED: {self.failed_count}")

            if self.failed_count == 0:
                self.dut._log.info("RESULT: ALL TESTS PASSED ✓")
            else:
                self.dut._log.error(f"RESULT: {self.failed_count} TESTS FAILED ✗")
            self.log_separator()

    async def test(self, test_name: str, test_func):
        """
        Run a single test with proper logging.

        Args:
            test_name: Name of the test
            test_func: Async function to run
        """
        self.log_test_start(test_name)

        try:
            await test_func()
            self.log_test_pass(test_name)
        except Exception as e:
            self.log_test_fail(test_name, str(e))
            raise  # Re-raise to fail the test

    def should_run_level(self, level: TestLevel) -> bool:
        """
        Check if tests at this level should run.

        Progressive: P1 always runs, P2 runs if level >= P2, etc.
        """
        return self.test_level >= level

    async def run_all_tests(self):
        """
        Run all test phases up to the configured level.

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
    """
    Factory function to create test runner with proper configuration.

    Args:
        dut: CocotB DUT object
        module_name: Name of module being tested

    Returns:
        Configured TestBase instance
    """
    return TestBase(dut, module_name)