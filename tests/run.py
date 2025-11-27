#!/usr/bin/env python3
"""
Unified Test Runner for Demo Probe Driver
==========================================

Runs the SAME test code against simulation (CocoTB/GHDL) or real hardware (Moku).
The async adapter pattern enables true "write once, run anywhere" testing.

Usage:
    # Simulation (default)
    python run.py
    python run.py --backend sim

    # Hardware
    python run.py --backend hw --device 192.168.31.41 --bitstream dpd-bits.tar

    # Options
    python run.py --test-module dpd.P1_unified    # Specific test module
    python run.py --verbose                        # Verbose output
    python run.py --backend hw --force             # Force disconnect existing
    python run.py --backend hw --debug             # Enable Moku debug logging

Environment Variables:
    TEST_MODULE: Test module to run (default: dpd.P1_async_adapter_test)
    COCOTB_VERBOSITY: Sim verbosity (MINIMAL, NORMAL, VERBOSE, DEBUG)

Architecture:
    Both backends use the AsyncFSMTestHarness interface:
    - Simulation: CocoTBAsyncHarness (cycle-accurate, instant state reads)
    - Hardware: MokuAsyncHarness (network delays, oscilloscope polling)

    Test code is identical - only the harness creation differs.

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path

# Ensure paths are set up
TESTS_DIR = Path(__file__).parent
SIM_DIR = TESTS_DIR / "sim"
HW_DIR = TESTS_DIR / "hw"
PROJECT_ROOT = TESTS_DIR.parent

sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(SIM_DIR))
sys.path.insert(0, str(HW_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

# Import loguru for consistent logging
try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru not installed. Run: uv sync")
    sys.exit(1)


def setup_logging(verbose: bool = False):
    """Configure loguru for test output."""
    logger.remove()  # Remove default handler

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


def setup_moku_debug_logging(args):
    """Enable Moku debug logging if --debug flag is set."""
    if not getattr(args, 'debug', None):
        return

    try:
        from moku import logging as moku_logging
    except ImportError:
        logger.warning("moku.logging not available, --debug flag ignored")
        return

    # Determine output stream
    if args.debug is True:
        # --debug flag without filename: use stderr
        output_stream = sys.stderr
        logger.info("Moku debug logging enabled (output to stderr)")
    else:
        # --debug FILE: open file for writing
        debug_file = Path(args.debug)
        try:
            output_stream = open(debug_file, 'w', encoding='utf-8')
            logger.info(f"Moku debug logging enabled (output to {debug_file})")
        except Exception as e:
            logger.error(f"Failed to open debug log file {debug_file}: {e}")
            logger.warning("Falling back to stderr for Moku debug logging")
            output_stream = sys.stderr

    moku_logging.enable_debug_logging(stream=output_stream)


def run_simulation(args):
    """Run tests using CocoTB/GHDL simulator."""
    os.chdir(SIM_DIR)

    # Ensure sim path is first for correct imports
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

    # Import sim-specific modules (must be after chdir and path setup)
    from sim.dpd.constants import HDL_SOURCES, HDL_TOPLEVEL

    logger.info("=" * 70)
    logger.info("DPD Unified Test Runner - SIMULATION")
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

    # Setup Moku debug logging if requested
    setup_moku_debug_logging(args)

    logger.info("=" * 70)
    logger.info("DPD Unified Test Runner - HARDWARE")
    logger.info("=" * 70)
    logger.info(f"Backend: Moku @ {args.device}")
    logger.info(f"Bitstream: {args.bitstream}")
    logger.info(f"Test Module: {args.test_module}")
    logger.debug(f"Verbose: {args.verbose}")
    logger.debug(f"Force: {args.force}")
    logger.info("=" * 70)

    # Import the test module and run with hardware harness
    asyncio.run(_run_hardware_async(args))


async def _run_hardware_async(args):
    """Async hardware test execution."""
    from hw.plumbing import MokuSession, MokuConfig

    config = MokuConfig(
        device_ip=args.device,
        bitstream_path=args.bitstream,
        force_connect=args.force,
    )

    logger.info(f"Connecting to {args.device}...")

    try:
        async with MokuSession(config) as session:
            logger.success("Connected")
            harness = session.create_harness()

            logger.info("Running hardware tests...")

            # Try to import the unified test runner
            try:
                import importlib
                module = importlib.import_module(args.test_module.replace("/", "."))

                if hasattr(module, 'run_hardware_tests'):
                    # New unified API
                    results = await module.run_hardware_tests(harness)
                    if results:
                        logger.success("Hardware tests completed!")
                    else:
                        logger.error("Some hardware tests failed")
                        sys.exit(1)
                else:
                    # Fallback: run basic connectivity test
                    logger.warning(f"Module {args.test_module} has no run_hardware_tests(), running basic test")
                    await _basic_hardware_test(harness)
                    logger.success("Basic hardware test passed!")

            except ImportError as e:
                logger.warning(f"Could not import {args.test_module}: {e}")
                logger.info("Running basic connectivity test instead...")
                await _basic_hardware_test(harness)
                logger.success("Basic hardware test passed!")

    except Exception as e:
        logger.error(f"Hardware test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def _basic_hardware_test(harness):
    """Basic connectivity and state read test."""
    # Debug: Check raw oscilloscope data
    try:
        raw_data = harness.osc.get_data()
        if 'ch1' in raw_data:
            ch1 = raw_data['ch1']
            logger.debug(f"Oscilloscope ch1: len={len(ch1)}, min={min(ch1):.3f}, max={max(ch1):.3f}, mid={ch1[len(ch1)//2]:.3f}")
        else:
            logger.debug(f"Oscilloscope keys: {raw_data.keys()}")
    except Exception as e:
        logger.debug(f"Could not read raw oscilloscope data: {e}")

    # Read current state (get_state returns state_name, digital_value)
    state, digital = await harness.state_reader.get_state()
    voltage = await harness.state_reader.read_state_voltage()
    logger.info(f"Current FSM state: {state} (digital={digital}, voltage={voltage:.3f}V)")

    # Enable FORGE
    logger.info("Enabling FORGE control...")
    await harness.controller.set_forge_ready()
    await harness.controller.wait_ms(200)

    # Read state again
    state, digital = await harness.state_reader.get_state()
    voltage = await harness.state_reader.read_state_voltage()
    logger.info(f"After FORGE enable: {state} (digital={digital}, voltage={voltage:.3f}V)")

    # If in FAULT, try to clear it
    if state == "FAULT":
        logger.warning("FSM in FAULT, attempting fault_clear...")
        await harness.controller.set_cr1(fault_clear=True)
        await harness.controller.wait_ms(100)
        await harness.controller.set_cr1(fault_clear=False)
        await harness.controller.wait_ms(200)

        state, digital = await harness.state_reader.get_state()
        voltage = await harness.state_reader.read_state_voltage()
        logger.info(f"After fault_clear: {state} (digital={digital}, voltage={voltage:.3f}V)")

    # Try to reach IDLE
    success = await harness.wait_for_state("IDLE", timeout_us=1000000)
    if success:
        logger.success("FSM reached IDLE")
    else:
        state, digital = await harness.state_reader.get_state()
        voltage = await harness.state_reader.read_state_voltage()
        logger.warning(f"FSM in {state} (digital={digital}, voltage={voltage:.3f}V) - expected IDLE")


def main():
    parser = argparse.ArgumentParser(
        description='Unified DPD Test Runner (sim or hardware)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulation
  python run.py
  python run.py --backend sim --test-module dpd.P1_async_adapter_test

  # Hardware
  python run.py --backend hw --device 192.168.31.41 --bitstream dpd-bits.tar
  python run.py --backend hw --device 192.168.31.41 --bitstream dpd-bits.tar --force
  python run.py --backend hw --device 192.168.31.41 --bitstream dpd-bits.tar --debug
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
        default=os.environ.get('TEST_MODULE', 'sim.dpd.P1_async_adapter_test'),
        help='Test module to run (default: sim.dpd.P1_async_adapter_test)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output (DEBUG level logging)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force disconnect existing connections (hw only)'
    )
    parser.add_argument(
        '--waves',
        action='store_true',
        help='Enable waveform capture (sim only)'
    )
    parser.add_argument(
        '--debug',
        nargs='?',
        const=True,
        type=str,
        metavar='FILE',
        help='Enable Moku debug logging. Optionally specify output file (default: stderr)'
    )

    args = parser.parse_args()

    # Setup logging based on verbosity
    setup_logging(verbose=args.verbose)

    if args.backend == 'sim':
        run_simulation(args)
    else:
        run_hardware(args)


if __name__ == "__main__":
    main()
