#!/usr/bin/env python3
"""
Moku State Capture Utility

Captures the complete configuration state of a Moku device in multi-instrument mode.

Usage:
    python moku_grab.py <device-ip> [--platform PLATFORM] [--output DIR] [--force]

Examples:
    python moku_grab.py 192.168.1.100
    python moku_grab.py 192.168.1.100 --output ./my_backup
    python moku_grab.py 192.168.1.100 --platform 4 --debug
    python moku_grab.py 192.168.1.100 --debug debug_log.txt
"""

import sys
import json
import inspect
from pathlib import Path
from datetime import datetime

# Add moku-models to path
PROJECT_ROOT = Path(__file__).parent.parent
MOKU_MODELS = PROJECT_ROOT / "libs" / "moku-models-v4"
sys.path.insert(0, str(MOKU_MODELS))

try:
    from loguru import logger
except ImportError:
    print("Error: loguru not installed. Run: uv sync")
    sys.exit(1)

try:
    from moku.instruments import MultiInstrument
    from moku import instruments
except ImportError:
    logger.error("moku library not installed. Run: uv sync")
    sys.exit(1)

# Import shared CLI utilities
from moku_cli_common import time_operation, setup_moku_debug_logging

# Configure loguru with nice formatting
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)


def get_instrument_class(instrument_name):
    """Get instrument class from name string"""
    for name, obj in inspect.getmembers(instruments, inspect.isclass):
        if name == instrument_name:
            return obj
    raise ValueError(f"Unknown instrument: {instrument_name}")


def capture_moku_state(mim: MultiInstrument, output_dir: Path, bitstream_path=None):
    """
    Capture complete state of Moku device in multi-instrument mode.

    Args:
        mim: Connected MultiInstrument instance
        output_dir: Directory to save configuration files
        bitstream_path: Optional path to bitstream file for CloudCompile

    Returns:
        Dictionary with capture results
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_path}")

    # Get current instrument configuration
    with time_operation("Getting instrument list"):
        instrument_list = mim.get_instruments()
    logger.info(f"Current configuration: {instrument_list}")

    results = {
        "mim_config": None,
        "instrument_configs": [],
        "metadata": None
    }

    # Save MIM-level configuration
    logger.info("\nSaving MIM-level configuration...")
    mim_config_path = output_path / "mim_config.mokuconf"
    with time_operation("Saving MIM configuration"):
        mim.save_configuration(str(mim_config_path))
    results["mim_config"] = str(mim_config_path)
    logger.success(f"Saved MIM config to {mim_config_path}")

    # Save each instrument's configuration
    logger.info("\nSaving individual instrument configurations...")
    for slot_num, instrument_name in enumerate(instrument_list, start=1):
        if instrument_name == "":
            logger.info(f"  Slot {slot_num}: Empty")
            continue

        logger.info(f"  Slot {slot_num}: {instrument_name}")

        try:
            # Get instrument class and create reference
            with time_operation(f"  Getting {instrument_name} instance"):
                InstrumentClass = get_instrument_class(instrument_name)
                # CloudCompile requires bitstream path during instantiation
                if instrument_name == "CloudCompile":
                    if not bitstream_path:
                        raise ValueError("CloudCompile requires --bitstream argument")
                    instrument = InstrumentClass.for_slot(slot=slot_num, multi_instrument=mim, bitstream=bitstream_path)
                else:
                    instrument = InstrumentClass.for_slot(slot=slot_num, multi_instrument=mim)

            # Save settings
            config_path = output_path / f"slot{slot_num}_{instrument_name}.mokuconf"
            with time_operation(f"  Saving {instrument_name} settings"):
                instrument.save_settings(str(config_path))

            results["instrument_configs"].append({
                "slot": slot_num,
                "instrument": instrument_name,
                "config_file": str(config_path)
            })

            logger.success(f"    Saved to {config_path}")

        except Exception as e:
            logger.error(f"    Error saving {instrument_name}: {e}")
            results["instrument_configs"].append({
                "slot": slot_num,
                "instrument": instrument_name,
                "error": str(e)
            })

    # Save metadata
    logger.info("\nSaving metadata...")
    with time_operation("Collecting device metadata"):
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "device_ip": getattr(mim, '_ip', getattr(mim, 'ip', 'unknown')),
            "serial_number": mim.serial_number(),
            "mokuos_version": mim.mokuos_version(),
            "platform_id": getattr(mim, '_platform_id', getattr(mim, 'platform_id', None)),
            "slots": [
                {"slot": i+1, "instrument": name}
                for i, name in enumerate(instrument_list)
            ]
        }

    metadata_path = output_path / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    results["metadata"] = str(metadata_path)
    logger.success(f"Saved metadata to {metadata_path}")

    return results


def main():
    import time
    import argparse

    # Custom argument parser for this script
    parser = argparse.ArgumentParser(
        description='Capture complete Moku device state in multi-instrument mode',
        epilog="""
Examples:
  # Basic capture (auto-detect platform)
  python moku_grab.py 192.168.1.100

  # Specify platform and output directory
  python moku_grab.py 192.168.1.100 --platform 4 --output ./my_backup

  # Enable debug logging to stderr
  python moku_grab.py 192.168.1.100 --debug

  # Enable debug logging to file
  python moku_grab.py 192.168.1.100 --debug debug_log.txt
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('device_ip', help='IP address of Moku device')
    parser.add_argument('--platform', type=int, choices=[2, 4], default=4,
                        help='Platform ID (2 or 4 for number of slots, default: 4)')
    parser.add_argument('--output', type=str,
                        help='Output directory (default: ./moku_backup_TIMESTAMP)')
    parser.add_argument(
        '--debug',
        nargs='?',
        const=True,
        type=str,
        metavar='FILE',
        help='Enable debug logging for Moku library. Optionally specify output file (default: stderr)'
    )
    parser.add_argument(
        '--bitstream',
        type=str,
        metavar='PATH',
        help='Path to bitstream file (required for CloudCompile instrument)'
    )

    args = parser.parse_args()

    # Default output directory with timestamp
    if args.output is None:
        args.output = f"./moku_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    output_path = Path(args.output)

    # Enable Moku debug logging if requested
    setup_moku_debug_logging(args)

    # Overall timing
    total_start = time.perf_counter()

    # Initialize moku to None for cleanup
    mim = None

    try:
        # Connect to device (special case - uses direct MultiInstrument)
        logger.info(f"Connecting to Moku at {args.device_ip}...")
        with time_operation("Device connection"):
            mim = MultiInstrument(ip=args.device_ip, platform_id=args.platform, force_connect=True, persist_state=True, ignore_busy=True)
        logger.success("Connected")

        # Capture state
        logger.info("\n" + "="*60)
        logger.info("CAPTURING MOKU STATE")
        logger.info("="*60)

        results = capture_moku_state(mim, output_path, bitstream_path=args.bitstream)

        # Summary
        total_elapsed = time.perf_counter() - total_start
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total execution time: {total_elapsed:.3f} s ({total_elapsed*1000:.2f} ms)")
        logger.info(f"Output directory: {output_path.absolute()}")
        logger.info(f"Configurations saved: {len(results['instrument_configs'])} instruments")
        logger.success(f"Complete state captured successfully")

    except Exception as e:
        logger.exception(f"Failed to capture state: {e}")
        sys.exit(1)

    finally:
        # Disconnect
        if mim is not None:
            logger.info("\nDisconnecting...")
            with time_operation("Disconnect (relinquish_ownership)"):
                try:
                    mim.relinquish_ownership()
                    logger.success("Disconnected")
                except Exception as e:
                    logger.warning(f"Disconnect warning: {e}")


if __name__ == "__main__":
    main()
