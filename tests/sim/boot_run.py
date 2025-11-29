#!/usr/bin/env python3
"""
CocoTB Test Runner for BOOT Subsystem

Runs BOOT FSM and LOADER tests with GHDL simulator.

Usage:
    python boot_run.py                              # Run boot_fsm P1 tests
    TEST_MODULE=loader.P1_basic python boot_run.py  # Run LOADER tests
    WAVES=true python boot_run.py                   # Enable waveform capture

Environment Variables:
    TEST_MODULE: Test module to run (default: boot_fsm.P1_basic)
    WAVES: Enable waveform capture (true/false, default: false)
    GHDL_FILTER: Output filter level (aggressive, normal, minimal, none)

Future Vision:
    The BOOT FSM's command structure (RUN/RUNL/RUNB/RUNP/RET) naturally
    maps to a shell-like CLI interface:

        RUN> _        # BOOT_P1 dispatcher prompt
        RUN> L        # RUNL → LOADER mode
        LOAD> ...     # data transfer operations
        LOAD> [Esc]   # RET → back to dispatcher
        RUN> B        # RUNB → BIOS diagnostics
        BIOS> [Esc]   # RET → back to dispatcher
        RUN> P        # RUNP → launch app (like exec, no return)

    See docs/BOOT-FSM-spec.md for the full state machine specification.

Author: Moku Instrument Forge Team
Date: 2025-11-29
"""

import os
import sys
from pathlib import Path

# Ensure we're in the tests/sim directory
os.chdir(Path(__file__).parent)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent  # DPD-001/
RTL_DIR = PROJECT_ROOT / "rtl"

# BOOT HDL configuration
HDL_TOPLEVEL = "bootwrapper"  # GHDL lowercases entity names

HDL_SOURCES = [
    RTL_DIR / "forge_common_pkg.vhd",
    RTL_DIR / "forge_hierarchical_encoder.vhd",
    RTL_DIR / "boot" / "loader_crc16.vhd",
    RTL_DIR / "boot" / "L2_BUFF_LOADER.vhd",
    RTL_DIR / "boot" / "BootWrapper_test_stub.vhd",
    RTL_DIR / "boot" / "B0_BOOT_TOP.vhd",
]


def main():
    """Run BOOT CocoTB tests."""

    # Test module selection
    test_module = os.environ.get("TEST_MODULE", "boot_fsm.P1_basic")

    # Waveform capture
    waves = os.environ.get("WAVES", "false").lower() == "true"

    # Simulator
    sim = os.environ.get("SIM", "ghdl")

    print("=" * 70)
    print("BOOT Subsystem Test Runner")
    print("=" * 70)
    print(f"Simulator: {sim}")
    print(f"Top-level: {HDL_TOPLEVEL}")
    print(f"Test Module: {test_module}")
    print(f"Waveforms: {'Enabled' if waves else 'Disabled'}")
    print(f"Sources: {len(HDL_SOURCES)} VHDL files")
    print("=" * 70)

    # Check source files exist
    missing = [str(src) for src in HDL_SOURCES if not src.exists()]
    if missing:
        print(f"\n❌ ERROR: Missing source files:")
        for src in missing:
            print(f"  - {src}")
        sys.exit(1)

    try:
        from cocotb_test.simulator import run as cocotb_run

        cocotb_run(
            vhdl_sources=[str(src) for src in HDL_SOURCES],
            toplevel=HDL_TOPLEVEL,
            toplevel_lang="vhdl",
            module=test_module,
            simulator=sim,
            waves=waves,
            extra_args=["--std=08"],
        )

        print(f"\n✅ BOOT tests completed successfully!")

    except ImportError:
        print("\n❌ ERROR: cocotb-test not installed")
        print("Install with: pip install cocotb-test")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
