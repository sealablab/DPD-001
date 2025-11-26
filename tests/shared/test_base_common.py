"""
Common Test Base Classes
========================

Shared test infrastructure used by both simulation (CocoTB) and hardware (Moku) tests.
Contains TestLevel, VerbosityLevel, TestResult, and common logging utilities.

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, List, Callable, Any


class TestLevel(IntEnum):
    """Test progression levels.

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
    """Output verbosity control.

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


class TestRunnerMixin:
    """Common test runner logic - mixed into sim/hw base classes.

    This mixin provides common test tracking and logging functionality
    that is shared between CocoTB and hardware test runners.

    Subclasses must implement:
    - _log_message(message: str) - Platform-specific logging
    """

    def _init_test_runner(self, verbosity: VerbosityLevel = VerbosityLevel.MINIMAL):
        """Initialize test runner state. Call from subclass __init__."""
        self.results: List[TestResult] = []
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
        self.verbosity = verbosity
        self.current_phase: Optional[str] = None

    def _log_message(self, message: str):
        """Log a message. Override in subclass for platform-specific logging."""
        print(message)

    def _log_error(self, message: str):
        """Log an error message. Override in subclass for platform-specific logging."""
        print(f"ERROR: {message}")

    def log(self, message: str, level: VerbosityLevel = VerbosityLevel.NORMAL):
        """Conditional logging based on verbosity level.

        Args:
            message: Message to log
            level: Required verbosity level for this message
        """
        if self.verbosity >= level:
            self._log_message(message)

    def log_separator(self, level: VerbosityLevel = VerbosityLevel.NORMAL):
        """Log a separator line."""
        self.log("=" * 60, level)

    def log_test_start(self, test_name: str):
        """Log test start based on verbosity."""
        self.test_count += 1

        if self.verbosity == VerbosityLevel.SILENT:
            pass  # No output
        elif self.verbosity == VerbosityLevel.MINIMAL:
            self._log_message(f"T{self.test_count}: {test_name}")
        elif self.verbosity == VerbosityLevel.NORMAL:
            self.log_separator()
            self._log_message(f"Test {self.test_count}: {test_name}")
        else:  # VERBOSE or DEBUG
            self.log_separator()
            self._log_message(f"Test {self.test_count}: {test_name}")
            self.log_separator()

    def log_test_pass(self, test_name: str, duration_ms: float = 0):
        """Log test pass."""
        self.passed_count += 1

        if self.verbosity == VerbosityLevel.SILENT:
            pass
        elif self.verbosity == VerbosityLevel.MINIMAL:
            self._log_message("  \u2713 PASS")
        elif self.verbosity == VerbosityLevel.NORMAL:
            if duration_ms > 0:
                self._log_message(f"\u2713 {test_name} PASSED ({duration_ms:.0f}ms)")
            else:
                self._log_message(f"\u2713 {test_name} PASSED")
        else:
            if duration_ms > 0:
                self._log_message(f"\u2713 {test_name} PASSED ({duration_ms:.1f}ms)")
            else:
                self._log_message(f"\u2713 {test_name} PASSED")

    def log_test_fail(self, test_name: str, error: str, duration_ms: float = 0):
        """Log test failure."""
        self.failed_count += 1

        # Always log failures regardless of verbosity
        if self.verbosity == VerbosityLevel.MINIMAL:
            self._log_error(f"  \u2717 FAIL: {error}")
        else:
            if duration_ms > 0:
                self._log_error(f"\u2717 {test_name} FAILED ({duration_ms:.0f}ms): {error}")
            else:
                self._log_error(f"\u2717 {test_name} FAILED: {error}")

    def log_phase_start(self, phase_name: str):
        """Log phase start (P1, P2, etc.)."""
        self.current_phase = phase_name

        if self.verbosity == VerbosityLevel.SILENT:
            pass
        elif self.verbosity == VerbosityLevel.MINIMAL:
            self._log_message(f"\n{phase_name}")
        else:
            self.log_separator(VerbosityLevel.NORMAL)
            self._log_message(f"PHASE: {phase_name}")
            self.log_separator(VerbosityLevel.NORMAL)

    def log_summary(self):
        """Log test summary."""
        if self.verbosity == VerbosityLevel.SILENT and self.failed_count == 0:
            pass
        elif self.verbosity == VerbosityLevel.MINIMAL:
            if self.failed_count == 0:
                self._log_message(f"ALL {self.test_count} TESTS PASSED")
            else:
                self._log_error(f"FAILED: {self.failed_count}/{self.test_count}")
        else:
            self.log_separator()
            self._log_message(f"TESTS RUN: {self.test_count}")
            self._log_message(f"PASSED: {self.passed_count}")
            self._log_message(f"FAILED: {self.failed_count}")

            if self.failed_count == 0:
                self._log_message("RESULT: ALL TESTS PASSED \u2713")
            else:
                self._log_error(f"RESULT: {self.failed_count} TESTS FAILED \u2717")

            # Show failed tests
            if self.failed_count > 0 and self.verbosity >= VerbosityLevel.NORMAL:
                self._log_message("\nFailed tests:")
                for result in self.results:
                    if not result.passed:
                        self._log_error(f"  - {result.name}: {result.error}")

            self.log_separator()

    def should_run_level(self, level: TestLevel, current_level: TestLevel) -> bool:
        """Check if tests at this level should run.

        Args:
            level: Test level to check
            current_level: Current configured test level

        Returns:
            True if this level should run
        """
        return current_level >= level

    def add_result(self, name: str, passed: bool, error: Optional[str] = None,
                   duration_ms: float = 0):
        """Add a test result to the results list."""
        self.results.append(TestResult(name, passed, error, duration_ms))
