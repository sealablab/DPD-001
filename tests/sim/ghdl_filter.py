"""
GHDL Output Filter - Intelligent Output Suppression for LLM Context Preservation

Filters GHDL simulation output to remove repetitive warnings and metavalue messages
while preserving important errors and test results.

This dramatically reduces context consumption for LLM-based development workflows.

Author: Volo Engineering
Date: 2025-01-26
"""

import re
import sys
from typing import List, Set, Optional
from enum import Enum
from dataclasses import dataclass


class FilterLevel(Enum):
    """
    Output filtering levels:
    - AGGRESSIVE: Maximum suppression (LLM-friendly)
    - NORMAL: Balanced suppression
    - MINIMAL: Light touch, preserve most warnings
    - NONE: No filtering (pass-through)
    """
    AGGRESSIVE = "aggressive"
    NORMAL = "normal"
    MINIMAL = "minimal"
    NONE = "none"


@dataclass
class FilterStats:
    """Track filtering statistics"""
    total_lines: int = 0
    filtered_lines: int = 0
    metavalue_warnings: int = 0
    truncated_warnings: int = 0
    null_warnings: int = 0
    initialization_warnings: int = 0
    duplicate_warnings: int = 0


class GHDLOutputFilter:
    """
    Filter GHDL output to reduce verbosity while preserving important information.

    Key Features:
    - Suppresses repetitive metavalue warnings
    - Removes initialization noise
    - Deduplicates repeated warnings
    - Preserves errors and important assertions
    - Maintains test PASS/FAIL results
    """

    # Patterns for metavalue-related warnings (highest priority to filter)
    # NOTE: Patterns match both raw GHDL output AND CocoTB-wrapped output
    METAVALUE_PATTERNS = [
        r".*NUMERIC_STD\.[A-Z_]+: metavalue detected.*",
        r".*metavalue detected, returning.*",
        r".*\(assertion warning\): NUMERIC_STD.*metavalue.*",
        r".*STD_LOGIC_.*: metavalue detected.*",
        r".*INFO cocotb:.*NUMERIC_STD\.[A-Z_]+: metavalue detected.*",
        r".*INFO cocotb:.*metavalue detected.*",
    ]

    # Patterns for vector truncation warnings (MASSIVE volume)
    TRUNCATED_PATTERNS = [
        r".*NUMERIC_STD\.TO_SIGNED: vector truncated.*",
        r".*NUMERIC_STD\.TO_UNSIGNED: vector truncated.*",
        r".*INFO cocotb:.*vector truncated.*",
    ]

    # Patterns for null/uninitialized warnings
    NULL_PATTERNS = [
        r".*NUMERIC_STD\.[A-Z_]+: null argument detected.*",
        r".*null argument detected, returning.*",
        r".*\(assertion warning\): NUMERIC_STD.*null.*",
        r".*INFO cocotb:.*null argument detected.*",
    ]

    # Patterns for initialization warnings (typically at time 0)
    INIT_PATTERNS = [
        r".*@0ms.*assertion.*",
        r".*@0fs.*assertion.*",
        r".*at 0 ns.*warning.*",
        r"^\s*0\.00ns.*metavalue.*",
    ]

    # Patterns for GHDL internal messages to filter
    GHDL_INTERNAL_PATTERNS = [
        r".*ghdl:info: simulation.*",
        r".*ghdl:info: elaboration.*",
        r".*ghdl:info: back annotation.*",
        r".*bound check.*",
    ]

    # Patterns to ALWAYS preserve (regardless of filter level)
    PRESERVE_PATTERNS = [
        r".*\bERROR\b.*",
        r".*\bFAIL.*",
        r".*\bPASS.*",
        r".*assertion error.*",
        r".*assertion failure.*",
        r".*TEST.*COMPLETE.*",
        r".*ALL TESTS.*",
        r"^\s*Test \d+:.*",  # Test headers
        r"^={3,}.*",  # Separator lines
        r".*✓.*",  # Success marks
        r".*✗.*",  # Failure marks
        r".*INFO cocotb:.*P[0-9]+.*TESTS.*",  # Test level headers
        r".*INFO cocotb:.*T[0-9]+:.*",  # Test case headers (T1:, T2:, etc)
        r".*cocotb\.customwrapper.*",  # Custom wrapper test output
        r".*Clock started.*",  # Setup messages
        r".*Reset complete.*",  # Setup messages
        r".*FORGE control.*",  # Important test steps
    ]

    def __init__(self, level: FilterLevel = FilterLevel.NORMAL):
        """
        Initialize the filter.

        Args:
            level: Filtering aggressiveness level
        """
        self.level = level
        self.stats = FilterStats()
        self.seen_warnings: Set[str] = set()

        # Compile regex patterns for efficiency
        self.metavalue_re = [re.compile(p, re.IGNORECASE) for p in self.METAVALUE_PATTERNS]
        self.truncated_re = [re.compile(p, re.IGNORECASE) for p in self.TRUNCATED_PATTERNS]
        self.null_re = [re.compile(p, re.IGNORECASE) for p in self.NULL_PATTERNS]
        self.init_re = [re.compile(p, re.IGNORECASE) for p in self.INIT_PATTERNS]
        self.internal_re = [re.compile(p, re.IGNORECASE) for p in self.GHDL_INTERNAL_PATTERNS]
        self.preserve_re = [re.compile(p, re.IGNORECASE) for p in self.PRESERVE_PATTERNS]

    def should_preserve(self, line: str) -> bool:
        """Check if line should always be preserved"""
        return any(regex.match(line) for regex in self.preserve_re)

    def should_filter(self, line: str) -> bool:
        """
        Determine if a line should be filtered based on current level.

        Args:
            line: Input line to check

        Returns:
            True if line should be filtered (not shown), False otherwise
        """
        # Always preserve important lines
        if self.should_preserve(line):
            return False

        # No filtering
        if self.level == FilterLevel.NONE:
            return False

        # Check for duplicate warnings
        normalized = self.normalize_warning(line)
        if normalized and normalized in self.seen_warnings:
            self.stats.duplicate_warnings += 1
            return True
        elif normalized:
            self.seen_warnings.add(normalized)

        # Apply level-based filtering
        if self.level == FilterLevel.AGGRESSIVE:
            # Filter everything we can
            if self.is_truncated_warning(line):
                self.stats.truncated_warnings += 1
                return True
            if self.is_metavalue_warning(line):
                self.stats.metavalue_warnings += 1
                return True
            if self.is_null_warning(line):
                self.stats.null_warnings += 1
                return True
            if self.is_initialization_warning(line):
                self.stats.initialization_warnings += 1
                return True
            if self.is_internal_message(line):
                return True

        elif self.level == FilterLevel.NORMAL:
            # Filter most noise but keep some warnings
            if self.is_truncated_warning(line):
                self.stats.truncated_warnings += 1
                return True
            if self.is_metavalue_warning(line):
                self.stats.metavalue_warnings += 1
                return True
            if self.is_null_warning(line):
                self.stats.null_warnings += 1
                return True
            if self.is_initialization_warning(line):
                self.stats.initialization_warnings += 1
                return True

        elif self.level == FilterLevel.MINIMAL:
            # Only filter the worst offenders (truncated warnings are so noisy we always filter)
            if self.is_truncated_warning(line):
                self.stats.truncated_warnings += 1
                return True
            if self.is_metavalue_warning(line):
                # Keep first occurrence, filter repeats
                if self.stats.metavalue_warnings > 0:
                    self.stats.metavalue_warnings += 1
                    return True
                self.stats.metavalue_warnings += 1

        return False

    def is_metavalue_warning(self, line: str) -> bool:
        """Check if line is a metavalue warning"""
        return any(regex.search(line) for regex in self.metavalue_re)

    def is_truncated_warning(self, line: str) -> bool:
        """Check if line is a vector truncated warning"""
        return any(regex.search(line) for regex in self.truncated_re)

    def is_null_warning(self, line: str) -> bool:
        """Check if line is a null/uninitialized warning"""
        return any(regex.search(line) for regex in self.null_re)

    def is_initialization_warning(self, line: str) -> bool:
        """Check if line is an initialization-time warning"""
        return any(regex.search(line) for regex in self.init_re)

    def is_internal_message(self, line: str) -> bool:
        """Check if line is a GHDL internal message"""
        return any(regex.search(line) for regex in self.internal_re)

    def normalize_warning(self, line: str) -> Optional[str]:
        """
        Normalize a warning line for deduplication.
        Removes timestamps and line numbers to detect duplicates.

        Args:
            line: Warning line to normalize

        Returns:
            Normalized string or None if not a warning
        """
        if "warning" not in line.lower() and "assertion" not in line.lower():
            return None

        # Remove timestamps (various formats)
        normalized = re.sub(r'@?\d+(\.\d+)?\s*(ms|us|ns|ps|fs)', '', line)
        normalized = re.sub(r'^\s*\d+\.\d+ns\s+', '', normalized)

        # Remove line numbers
        normalized = re.sub(r':\d+:\d+', '', normalized)
        normalized = re.sub(r'\(\d+:\d+\)', '', normalized)

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        return normalized if normalized else None

    def filter_lines(self, lines: List[str]) -> List[str]:
        """
        Filter a list of lines.

        Args:
            lines: Input lines to filter

        Returns:
            Filtered lines
        """
        filtered = []

        for line in lines:
            self.stats.total_lines += 1

            if not self.should_filter(line):
                filtered.append(line)
            else:
                self.stats.filtered_lines += 1

        return filtered

    def filter_stream(self, input_stream=sys.stdin, output_stream=sys.stdout):
        """
        Filter lines from input stream to output stream in real-time.

        Args:
            input_stream: Input stream (default: stdin)
            output_stream: Output stream (default: stdout)
        """
        try:
            for line in input_stream:
                self.stats.total_lines += 1

                if not self.should_filter(line.rstrip('\n')):
                    output_stream.write(line)
                    output_stream.flush()
                else:
                    self.stats.filtered_lines += 1
        except KeyboardInterrupt:
            pass
        finally:
            if self.stats.filtered_lines > 0:
                self.print_summary(output_stream)

    def print_summary(self, output_stream=sys.stdout):
        """
        Print filtering summary statistics.

        Args:
            output_stream: Where to print summary
        """
        if self.level == FilterLevel.NONE:
            return

        reduction_pct = (self.stats.filtered_lines / self.stats.total_lines * 100) \
            if self.stats.total_lines > 0 else 0

        output_stream.write(f"\n")
        output_stream.write(f"[GHDL Output Filter - Level: {self.level.value}]\n")
        output_stream.write(f"  Total lines: {self.stats.total_lines}\n")
        output_stream.write(f"  Filtered: {self.stats.filtered_lines} ({reduction_pct:.1f}% reduction)\n")

        if self.stats.truncated_warnings > 0:
            output_stream.write(f"  - Vector truncated warnings: {self.stats.truncated_warnings}\n")
        if self.stats.metavalue_warnings > 0:
            output_stream.write(f"  - Metavalue warnings: {self.stats.metavalue_warnings}\n")
        if self.stats.null_warnings > 0:
            output_stream.write(f"  - Null warnings: {self.stats.null_warnings}\n")
        if self.stats.initialization_warnings > 0:
            output_stream.write(f"  - Initialization warnings: {self.stats.initialization_warnings}\n")
        if self.stats.duplicate_warnings > 0:
            output_stream.write(f"  - Duplicate warnings: {self.stats.duplicate_warnings}\n")


def main():
    """
    Command-line interface for the filter.

    Usage:
        ghdl -r entity | python ghdl_output_filter.py [--level aggressive|normal|minimal|none]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Filter GHDL output to reduce verbosity for LLM workflows"
    )
    parser.add_argument(
        "--level",
        type=str,
        choices=["aggressive", "normal", "minimal", "none"],
        default="normal",
        help="Filtering level (default: normal)"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show filtering summary at the end"
    )

    args = parser.parse_args()

    filter_level = FilterLevel(args.level)
    filter = GHDLOutputFilter(level=filter_level)

    # Process stdin to stdout
    filter.filter_stream()


if __name__ == "__main__":
    main()