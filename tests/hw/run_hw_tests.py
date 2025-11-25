#!/usr/bin/env python3
"""
Hardware Progressive Test Runner for Demo Probe Driver (DPD)

Runs P1/P2/P3 hardware tests on real Moku device with oscilloscope observation.

Usage:
    python run_hw_tests.py <device_ip>                    # Run P1 tests
    python run_hw_tests.py <device_ip> --level P2         # Run P1+P2 tests
    python run_hw_tests.py <device_ip> --verbose          # Verbose output
    python run_hw_tests.py 192.168.8.98 --osc-slot 1 --cc-slot 2

Environment Variables:
    HW_TEST_LEVEL: Test suite level (P1, P2, P3) - default: P1
    HW_TEST_VERBOSITY: Output level (MINIMAL, NORMAL, VERBOSE, DEBUG) - default: MINIMAL

Prerequisites:
    - Bitstream already deployed to CloudCompile in slot 2
    - Oscilloscope deployed in slot 1
    - Routing configured (auto-configured if missing)

Author: Moku Instrument Forge Team
Date: 2025-01-18
"""

import sys
import os
import argparse
from pathlib import Path

# Add paths for imports
HW_TEST_DIR = Path(__file__).parent      # tests/hw/
PROJECT_ROOT = HW_TEST_DIR.parent.parent  # DPD-001/
PY_TOOLS_DIR = PROJECT_ROOT / "py_tools"

sys.path.insert(0, str(HW_TEST_DIR))    # For hw_test_* modules
sys.path.insert(0, str(PY_TOOLS_DIR))   # For moku_cli_common

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru not installed. Run: uv sync")
    sys.exit(1)

try:
    from moku.instruments import MultiInstrument
except ImportError:
    print("ERROR: moku package not found. Run: uv sync")
    sys.exit(1)

from hw_test_base import TestLevel, VerbosityLevel
from P1_hw_basic import P1_HardwareBasicTests
from P2_hw_intermediate import P2_HardwareIntermediateTests
from P3_hw_comprehensive import P3_HardwareComprehensiveTests

# Import shared utilities from project root
from moku_cli_common import connect_to_device, parse_platform_id, setup_moku_debug_logging


# Configure loguru with nice formatting
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True
)


def parse_test_level(level_str: str) -> TestLevel:
    """Parse test level from string."""
    level_map = {
        'P1': TestLevel.P1_BASIC,
        'P1_BASIC': TestLevel.P1_BASIC,
        'P2': TestLevel.P2_INTERMEDIATE,
        'P2_INTERMEDIATE': TestLevel.P2_INTERMEDIATE,
        'P3': TestLevel.P3_COMPREHENSIVE,
        'P3_COMPREHENSIVE': TestLevel.P3_COMPREHENSIVE,
    }
    return level_map.get(level_str.upper(), TestLevel.P1_BASIC)


def parse_verbosity(verbosity_str: str) -> VerbosityLevel:
    """Parse verbosity level from string."""
    verbosity_map = {
        'SILENT': VerbosityLevel.SILENT,
        'MINIMAL': VerbosityLevel.MINIMAL,
        'NORMAL': VerbosityLevel.NORMAL,
        'VERBOSE': VerbosityLevel.VERBOSE,
        'DEBUG': VerbosityLevel.DEBUG,
    }
    return verbosity_map.get(verbosity_str.upper(), VerbosityLevel.MINIMAL)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='DPD Hardware Progressive Test Runner',
        epilog="""
Examples:
  # Run P1 tests on Moku:Go
  python run_hw_tests.py 192.168.8.98

  # Run P1+P2 tests with verbose output
  python run_hw_tests.py 192.168.8.98 --level P2 --verbose

  # Specify slots explicitly
  python run_hw_tests.py 192.168.8.98 --osc-slot 1 --cc-slot 2

  # Enable Moku debug logging
  python run_hw_tests.py 192.168.8.98 --debug

  # Force connect (disconnect existing connections)
  python run_hw_tests.py 192.168.8.98 --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('device_ip', help='IP address of the Moku device')
    parser.add_argument('--osc-slot', type=int, default=1, help='Oscilloscope slot (default: 1)')
    parser.add_argument('--cc-slot', type=int, default=2, help='CloudCompile slot (default: 2)')
    parser.add_argument(
        '--bitstream',
        type=str,
        required=True,
        help='Path to DPD bitstream file (required for CloudCompile access)'
    )
    parser.add_argument(
        '--level',
        choices=['P1', 'P2', 'P3'],
        default=os.environ.get('HW_TEST_LEVEL', 'P1'),
        help='Test level to run (default: P1 or HW_TEST_LEVEL env var)'
    )
    parser.add_argument(
        '--verbosity',
        choices=['SILENT', 'MINIMAL', 'NORMAL', 'VERBOSE', 'DEBUG'],
        default=os.environ.get('HW_TEST_VERBOSITY', 'MINIMAL'),
        help='Output verbosity (default: MINIMAL or HW_TEST_VERBOSITY env var)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Shorthand for --verbosity VERBOSE'
    )
    parser.add_argument(
        '--platform',
        choices=['moku_go', 'moku_lab', 'moku_pro', 'moku_delta'],
        help='Platform type (default: auto-detect)'
    )
    parser.add_argument('--force', action='store_true', help='Force connection')
    parser.add_argument(
        '--debug',
        nargs='?',
        const=True,
        type=str,
        metavar='FILE',
        help='Enable debug logging for Moku library. Optionally specify output file (default: stderr)'
    )

    args = parser.parse_args()

    # Override verbosity if --verbose flag used
    if args.verbose:
        args.verbosity = 'VERBOSE'

    # Parse levels
    test_level = parse_test_level(args.level)
    verbosity = parse_verbosity(args.verbosity)

    # Enable Moku debug logging if requested
    setup_moku_debug_logging(args)

    # Parse platform ID
    platform_id = parse_platform_id(args)
    if platform_id is None:
        platform_id = 2  # Default to Moku:Go

    logger.info("=" * 70)
    logger.info("DPD Hardware Progressive Tests")
    logger.info("=" * 70)
    logger.info(f"Device: {args.device_ip}")
    logger.info(f"Test Level: {test_level.name}")
    logger.info(f"Verbosity: {verbosity.name}")
    logger.info(f"Oscilloscope Slot: {args.osc_slot}")
    logger.info(f"CloudCompile Slot: {args.cc_slot}")
    logger.info("=" * 70)

    moku = None

    try:
        # Connect to device
        logger.info(f"\nConnecting to {args.device_ip}...")
        moku = connect_to_device(args.device_ip, platform_id, force=args.force, read_timeout=5)
        logger.success("✓ Connected")

        # Validate instruments are deployed
        logger.info(f"\nValidating instruments...")
        logger.info(f"  Checking slot {args.osc_slot} (Oscilloscope)...")
        logger.info(f"  Checking slot {args.cc_slot} (CloudCompile)...")

        # Run tests based on level
        all_passed = True

        if test_level >= TestLevel.P1_BASIC:
            logger.info("\n" + "=" * 70)
            logger.info("Running P1 (BASIC) Tests")
            logger.info("=" * 70)
            p1_tests = P1_HardwareBasicTests(moku, args.osc_slot, args.cc_slot, args.bitstream, verbosity)
            p1_passed = p1_tests.run_all_tests(TestLevel.P1_BASIC)
            all_passed = all_passed and p1_passed

        if test_level >= TestLevel.P2_INTERMEDIATE:
            logger.info("\n" + "=" * 70)
            logger.info("Running P2 (INTERMEDIATE) Tests")
            logger.info("=" * 70)
            p2_tests = P2_HardwareIntermediateTests(moku, args.osc_slot, args.cc_slot, args.bitstream, verbosity)
            p2_passed = p2_tests.run_all_tests(TestLevel.P2_INTERMEDIATE)
            all_passed = all_passed and p2_passed

        if test_level >= TestLevel.P3_COMPREHENSIVE:
            logger.info("\n" + "=" * 70)
            logger.info("Running P3 (COMPREHENSIVE) Tests")
            logger.info("=" * 70)
            p3_tests = P3_HardwareComprehensiveTests(moku, args.osc_slot, args.cc_slot, args.bitstream, verbosity)
            p3_passed = p3_tests.run_all_tests(TestLevel.P3_COMPREHENSIVE)
            all_passed = all_passed and p3_passed

        # Final summary
        logger.info("\n" + "=" * 70)
        if all_passed:
            logger.success("✅ ALL TESTS PASSED")
        else:
            logger.error("❌ SOME TESTS FAILED")
        logger.info("=" * 70)

        sys.exit(0 if all_passed else 1)

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if moku is not None:
            logger.info("\n👋 Disconnecting...")
            try:
                moku.relinquish_ownership()
                logger.success("Disconnected")
            except Exception as e:
                logger.warning(f"Disconnect warning: {e}")


if __name__ == "__main__":
    main()
