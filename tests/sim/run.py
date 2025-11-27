#!/usr/bin/env python3
"""
CocoTB Test Runner for Demo Probe Driver

Runs P1 (BASIC) tests with GHDL simulator with intelligent output filtering.

The filter automatically reduces GHDL output by ~99.4% (12,589 → 73 lines)
by suppressing repetitive warnings while preserving test results and errors.

Usage:
    python run.py                           # Run P1 tests with automatic filtering
    COCOTB_VERBOSITY=NORMAL python run.py   # More verbose output
    TEST_LEVEL=P2_INTERMEDIATE python run.py  # Run P2 tests (when implemented)
    GHDL_FILTER=none python run.py          # Disable GHDL output filtering
    
    # Debug tests (for FSM trigger investigation)
    TEST_MODULE=dpd.P1_dpd_trigger_debug python run.py
    WAVES=true TEST_MODULE=dpd.P1_dpd_trigger_debug python run.py

Environment Variables:
    COCOTB_VERBOSITY: Test output level (MINIMAL, NORMAL, VERBOSE, DEBUG)
    TEST_LEVEL: Test suite level (P1_BASIC, P2_INTERMEDIATE, etc.)
    TEST_MODULE: Test module to run (default: dpd.P1_basic)
    WAVES: Enable waveform capture (true/false, default: false)
    GHDL_FILTER: GHDL output filter level (aggressive, normal, minimal, none)
                 Default: auto-selected based on COCOTB_VERBOSITY

Author: Moku Instrument Forge Team
Date: 2025-11-25 (updated for debug test support)
"""

import os
import sys
import io
from pathlib import Path
from contextlib import contextmanager

# Ensure we're in the cocotb_tests directory
os.chdir(Path(__file__).parent)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# HDL configuration (previously in dpd/constants.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent  # DPD-001/
RTL_DIR = PROJECT_ROOT / "rtl"

MODULE_NAME = "dpd_wrapper"
HDL_TOPLEVEL = "customwrapper"  # GHDL lowercases entity names

HDL_SOURCES = [
    RTL_DIR / "CustomWrapper_test_stub.vhd",
    RTL_DIR / "forge_common_pkg.vhd",
    RTL_DIR / "forge_hierarchical_encoder.vhd",
    RTL_DIR / "moku_voltage_threshold_trigger_core.vhd",
    RTL_DIR / "DPD_main.vhd",
    RTL_DIR / "DPD_shim.vhd",
    RTL_DIR / "DPD.vhd",
]

# Import GHDL filter
from ghdl_filter import GHDLOutputFilter, FilterLevel


def get_ghdl_filter_level():
    """
    Determine GHDL filter level based on COCOTB_VERBOSITY or explicit override.
    """
    # Explicit override takes precedence
    if "GHDL_FILTER" in os.environ:
        filter_str = os.environ["GHDL_FILTER"].lower()
        if filter_str == "aggressive":
            return FilterLevel.AGGRESSIVE
        elif filter_str == "normal":
            return FilterLevel.NORMAL
        elif filter_str == "minimal":
            return FilterLevel.MINIMAL
        elif filter_str == "none":
            return FilterLevel.NONE
        else:
            print(f"⚠️  Warning: Unknown GHDL_FILTER='{filter_str}', using 'normal'")
            return FilterLevel.NORMAL

    # Auto-select based on COCOTB_VERBOSITY
    verbosity = os.environ.get("COCOTB_VERBOSITY", "MINIMAL").upper()

    if verbosity == "MINIMAL":
        return FilterLevel.AGGRESSIVE
    elif verbosity == "NORMAL":
        return FilterLevel.NORMAL
    elif verbosity == "VERBOSE":
        return FilterLevel.MINIMAL
    elif verbosity == "DEBUG":
        return FilterLevel.NONE
    else:
        return FilterLevel.NORMAL


class FilteredOutput(io.TextIOBase):
    """
    A stream wrapper that filters output through GHDLOutputFilter before
    writing to the original stream.
    """
    def __init__(self, original_stream, ghdl_filter):
        self.original = original_stream
        self.filter = ghdl_filter

    def write(self, text):
        """Filter text line by line and write to original stream"""
        for line in text.splitlines(keepends=True):
            self.filter.stats.total_lines += 1

            if not self.filter.should_filter(line.rstrip('\n')):
                self.original.write(line)
                self.original.flush()
            else:
                self.filter.stats.filtered_lines += 1

    def flush(self):
        self.original.flush()

    def isatty(self):
        return self.original.isatty()


@contextmanager
def filtered_output(filter_level):
    """
    Context manager that redirects stdout/stderr through the GHDL filter.
    """
    if filter_level == FilterLevel.NONE:
        # No filtering - pass through
        yield
        return

    # Create filter
    ghdl_filter = GHDLOutputFilter(level=filter_level)

    # Save original streams
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr

    # Wrap with filtering
    filtered_stdout = FilteredOutput(orig_stdout, ghdl_filter)
    filtered_stderr = FilteredOutput(orig_stderr, ghdl_filter)

    try:
        sys.stdout = filtered_stdout
        sys.stderr = filtered_stderr
        yield
    finally:
        # Restore original streams
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr

        # Print filter summary
        if ghdl_filter.stats.filtered_lines > 0:
            ghdl_filter.print_summary(orig_stdout)


def main():
    """Run CocoTB tests with real-time output filtering"""

    # Set environment variables for CocoTB
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    os.environ.setdefault("COCOTB_VERBOSITY", os.environ.get("COCOTB_VERBOSITY", "MINIMAL"))
    os.environ.setdefault("TEST_LEVEL", os.environ.get("TEST_LEVEL", "P1_BASIC"))

    # Simulator configuration
    sim = os.environ.get("SIM", "ghdl")

    # GHDL output filter configuration
    filter_level = get_ghdl_filter_level()

    # Waveform capture configuration
    waves = os.environ.get("WAVES", "false").lower() == "true"

    # Test module selection (default to basic tests, can override for debug)
    test_module = os.environ.get("TEST_MODULE", "dpd.P1_basic")

    print(f"=" * 70)
    print(f"Running {MODULE_NAME} tests")
    print(f"=" * 70)
    print(f"Simulator: {sim}")
    print(f"Top-level: {HDL_TOPLEVEL}")
    print(f"Test Module: {test_module}")
    print(f"Test Level: {os.environ['TEST_LEVEL']}")
    print(f"Verbosity: {os.environ['COCOTB_VERBOSITY']}")
    print(f"GHDL Filter: {filter_level.value}")
    print(f"Waveforms: {'Enabled' if waves else 'Disabled'}")
    print(f"Sources: {len(HDL_SOURCES)} VHDL files")
    print(f"=" * 70)

    # Check that all source files exist
    missing_sources = [str(src) for src in HDL_SOURCES if not src.exists()]
    if missing_sources:
        print(f"\n❌ ERROR: Missing source files:")
        for src in missing_sources:
            print(f"  - {src}")
        sys.exit(1)

    try:
        from cocotb_test.simulator import run as cocotb_run

        # Run tests with filtered output
        with filtered_output(filter_level):
            cocotb_run(
                vhdl_sources=[str(src) for src in HDL_SOURCES],
                toplevel=HDL_TOPLEVEL,
                toplevel_lang="vhdl",
                module=test_module,
                simulator=sim,
                waves=waves,
                extra_args=["--std=08"],
            )

        print(f"\n✅ Tests completed successfully!")

    except ImportError:
        print("\n❌ ERROR: cocotb-test not installed")
        print("Install with: pip install cocotb-test")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
