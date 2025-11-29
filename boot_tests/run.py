#!/usr/bin/env python3
"""
Unified Test Runner for BOOT Subsystem
=======================================

Runs the SAME test code against simulation (CocoTB/GHDL) or real hardware (Moku).
Based on tests/run.py but configured for BOOT subsystem testing.

Usage:
    # Simulation (default)
    python run.py
    python run.py --backend sim

    # Hardware
    python run.py --backend hw --device 192.168.31.41 --bitstream boot-bits.tar

    # Options
    python run.py --test-module boot_fsm.P1_basic   # BOOT FSM tests
    python run.py --test-module loader.P1_basic     # LOADER tests
    python run.py --verbose                          # Verbose output

Environment Variables:
    TEST_MODULE: Test module to run (default: boot_fsm.P1_basic)
    COCOTB_VERBOSITY: Sim verbosity (MINIMAL, NORMAL, VERBOSE, DEBUG)

Author: Moku Instrument Forge Team
Date: 2025-11-29
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure paths are set up
BOOT_TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = BOOT_TESTS_DIR.parent
TESTS_DIR = PROJECT_ROOT / "tests"
SIM_DIR = BOOT_TESTS_DIR / "sim"

sys.path.insert(0, str(BOOT_TESTS_DIR))
sys.path.insert(0, str(SIM_DIR))
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

# Import loguru for consistent logging
try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru not installed. Run: uv sync")
    sys.exit(1)


def setup_logging(verbose: bool = False):
    """Configure loguru for test output."""
    logger.remove()

    if verbose:
        log_level = "DEBUG"
        log_format = (
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    else:
        log_level = "INFO"
        log_format = (
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        )

    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=True,
    )


def run_simulation(args):
    """Run tests using CocoTB/GHDL simulator."""
    os.chdir(SIM_DIR)

    if str(SIM_DIR) not in sys.path:
        sys.path.insert(0, str(SIM_DIR))

    # Set environment for CocoTB
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    os.environ["TEST_MODULE"] = args.test_module

    if args.verbose:
        os.environ["COCOTB_VERBOSITY"] = "VERBOSE"
        os.environ["GHDL_FILTER"] = "minimal"
    else:
        os.environ.setdefault("COCOTB_VERBOSITY", "MINIMAL")

    # BOOT HDL configuration
    RTL_DIR = PROJECT_ROOT / "rtl"
    BOOT_RTL_DIR = RTL_DIR / "boot"
    HDL_TOPLEVEL = "customwrapper"  # GHDL lowercases entity names

    # BOOT-specific source files (order matters for GHDL)
    HDL_SOURCES = [
        # Entity declaration (must come first)
        BOOT_RTL_DIR / "BootWrapper_test_stub.vhd",
        # Shared package
        RTL_DIR / "forge_common_pkg.vhd",
        # BOOT modules
        BOOT_RTL_DIR / "loader_crc16.vhd",
        BOOT_RTL_DIR / "L2_BUFF_LOADER.vhd",
        BOOT_RTL_DIR / "B0_BOOT_TOP.vhd",
    ]

    logger.info("=" * 70)
    logger.info("BOOT Unified Test Runner - SIMULATION")
    logger.info("=" * 70)
    logger.info(f"Backend: CocoTB + GHDL")
    logger.info(f"Test Module: {args.test_module}")
    logger.debug(f"Verbose: {args.verbose}")
    logger.info("=" * 70)

    # Check sources exist
    missing = [str(s) for s in HDL_SOURCES if not s.exists()]
    if missing:
        logger.error(f"Missing source files: {missing}")
        sys.exit(1)

    try:
        from cocotb_test.simulator import run as cocotb_run

        cocotb_run(
            vhdl_sources=[str(src) for src in HDL_SOURCES],
            toplevel=HDL_TOPLEVEL,
            toplevel_lang="vhdl",
            module=args.test_module,
            simulator="ghdl",
            waves=args.waves,
            extra_args=["--std=08"],
        )
        logger.success("Simulation tests completed!")

    except ImportError:
        logger.error("cocotb-test not installed. Run: uv sync")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        sys.exit(1)


def run_hardware(args):
    """Run tests using Moku hardware."""
    if not args.device:
        logger.error("--device required for hardware backend")
        sys.exit(1)
    if not args.bitstream:
        logger.error("--bitstream required for hardware backend")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("BOOT Unified Test Runner - HARDWARE")
    logger.info("=" * 70)
    logger.info(f"Backend: Moku @ {args.device}")
    logger.info(f"Bitstream: {args.bitstream}")
    logger.info(f"Test Module: {args.test_module}")
    logger.debug(f"Verbose: {args.verbose}")
    logger.info("=" * 70)

    # TODO: Implement hardware test runner for BOOT
    # This will use the same MokuSession infrastructure as tests/run.py
    logger.warning("Hardware testing for BOOT not yet implemented")
    logger.info("Use simulation for now: python run.py --backend sim")


def main():
    parser = argparse.ArgumentParser(
        description='Unified BOOT Test Runner (sim or hardware)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulation
  python run.py
  python run.py --backend sim --test-module boot_fsm.P1_basic
  python run.py --backend sim --test-module loader.P1_basic

  # Hardware (future)
  python run.py --backend hw --device 192.168.31.41 --bitstream boot-bits.tar
        """
    )

    parser.add_argument(
        '--backend', '-b',
        choices=['sim', 'hw'],
        default='sim',
        help='Test backend: sim (CocoTB/GHDL) or hw (Moku hardware)'
    )
    parser.add_argument(
        '--device', '-d',
        type=str,
        help='Moku device IP address (required for hw backend)'
    )
    parser.add_argument(
        '--bitstream',
        type=str,
        help='Path to CloudCompile bitstream (required for hw backend)'
    )
    parser.add_argument(
        '--test-module', '-m',
        type=str,
        default=os.environ.get('TEST_MODULE', 'boot_fsm.P1_basic'),
        help='Test module to run (default: boot_fsm.P1_basic)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output (DEBUG level logging)'
    )
    parser.add_argument(
        '--waves',
        action='store_true',
        help='Enable waveform capture (sim only)'
    )

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    if args.backend == 'sim':
        run_simulation(args)
    else:
        run_hardware(args)


if __name__ == "__main__":
    main()
