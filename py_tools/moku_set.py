#!/usr/bin/env python3
"""
Moku State Restore Utility

Restores a complete configuration state to a Moku device in multi-instrument mode.

Usage:
    python moku_set.py <device-ip> <config-dir> [--platform PLATFORM] [--bitstream PATH] [--dry-run]

Examples:
    python moku_set.py 192.168.1.100 ./c
    python moku_set.py 192.168.1.100 ./c --bitstream cr10_bits.tar
    python moku_set.py 192.168.1.100 ./c --platform 2 --dry-run
    python moku_set.py 192.168.1.100 ./c --debug debug_log.txt
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


def discover_configs(config_dir: Path):
    """
    Discover configuration files in a directory.

    Args:
        config_dir: Directory containing .mokuconf files

    Returns:
        Dictionary with 'mim_config', 'slot_configs', 'metadata'
    """
    config_path = Path(config_dir)
    if not config_path.exists():
        raise FileNotFoundError(f"Config directory not found: {config_path}")

    # Find MIM config
    mim_config = config_path / "mim_config.mokuconf"
    if not mim_config.exists():
        raise FileNotFoundError(f"MIM config not found: {mim_config}")

    # Find slot configs
    slot_configs = sorted(config_path.glob("slot*_*.mokuconf"))

    # Find metadata
    metadata_file = config_path / "metadata.json"
    metadata = None
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

    return {
        "mim_config": mim_config,
        "slot_configs": slot_configs,
        "metadata": metadata
    }


def validate_configs(configs, target_platform_id=None):
    """
    Perform minimal validation on configuration files.

    Args:
        configs: Dictionary from discover_configs()
        target_platform_id: Expected platform ID (2 or 4)

    Raises:
        ValueError: If validation fails
    """
    metadata = configs["metadata"]

    if metadata is None:
        logger.warning("No metadata.json found - skipping validation")
        return

    logger.info("Validating configuration compatibility...")

    # Check platform ID if specified
    if target_platform_id is not None:
        saved_platform = metadata.get("platform_id")
        if saved_platform != target_platform_id:
            raise ValueError(
                f"Platform mismatch: config is for platform {saved_platform}, "
                f"but target is platform {target_platform_id}"
            )
        logger.info(f"  Platform ID: {saved_platform} ✓")

    # Display metadata info
    logger.info(f"  Captured from: {metadata.get('device_ip', 'unknown')}")
    logger.info(f"  Serial number: {metadata.get('serial_number', 'unknown')}")
    logger.info(f"  MokuOS version: {metadata.get('mokuos_version', 'unknown')}")
    logger.info(f"  Timestamp: {metadata.get('timestamp', 'unknown')}")

    # Check for CloudCompile
    slots = metadata.get("slots", [])
    has_cloudcompile = any(slot.get("instrument") == "CloudCompile" for slot in slots)

    return has_cloudcompile


def restore_moku_state(mim: MultiInstrument, configs, bitstream_path=None, dry_run=False):
    """
    Restore complete state to Moku device in multi-instrument mode.

    Args:
        mim: Connected MultiInstrument instance
        configs: Dictionary from discover_configs()
        bitstream_path: Optional path to bitstream file for CloudCompile
        dry_run: If True, only show what would be done

    Returns:
        Dictionary with restore results
    """
    results = {
        "mim_config": None,
        "instrument_configs": []
    }

    logger.info("\n" + "="*60)
    logger.info("CONFIGURATION TO RESTORE")
    logger.info("="*60)
    logger.info(f"MIM config: {configs['mim_config']}")
    for slot_config in configs['slot_configs']:
        logger.info(f"Slot config: {slot_config}")

    if dry_run:
        logger.warning("\n[DRY RUN MODE] - No changes will be made")
        logger.info("\nWould perform the following operations:")
        logger.info(f"  1. Load MIM configuration from {configs['mim_config']}")
        for i, slot_config in enumerate(configs['slot_configs'], start=2):
            slot_name = slot_config.stem  # e.g., "slot1_Oscilloscope"
            logger.info(f"  {i}. Load {slot_name} configuration")
        logger.success("\n[DRY RUN COMPLETE] - No changes made")
        return results

    # Load MIM-level configuration
    logger.info("\n" + "="*60)
    logger.info("LOADING MIM CONFIGURATION")
    logger.info("="*60)
    with time_operation("Loading MIM configuration"):
        mim.load_configuration(str(configs['mim_config']))
    results["mim_config"] = str(configs['mim_config'])
    logger.success(f"Loaded MIM config from {configs['mim_config']}")

    # Get instrument list after MIM load
    with time_operation("Getting instrument list"):
        instrument_list = mim.get_instruments()
    logger.info(f"Active instruments: {instrument_list}")

    # Load each instrument's configuration
    logger.info("\n" + "="*60)
    logger.info("LOADING INSTRUMENT CONFIGURATIONS")
    logger.info("="*60)

    for slot_config in configs['slot_configs']:
        # Parse slot number and instrument name from filename
        # Format: slot<N>_<InstrumentName>.mokuconf
        stem = slot_config.stem
        parts = stem.split('_', 1)
        if len(parts) != 2 or not parts[0].startswith('slot'):
            logger.warning(f"Skipping unrecognized config file: {slot_config}")
            continue

        slot_num = int(parts[0].replace('slot', ''))
        instrument_name = parts[1]

        logger.info(f"\nSlot {slot_num}: {instrument_name}")

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

            # Load settings
            with time_operation(f"  Loading {instrument_name} settings"):
                instrument.load_settings(str(slot_config))

            results["instrument_configs"].append({
                "slot": slot_num,
                "instrument": instrument_name,
                "config_file": str(slot_config)
            })

            logger.success(f"    Loaded from {slot_config}")

        except Exception as e:
            logger.error(f"    Error loading {instrument_name}: {e}")
            raise  # Abort on failure per requirements

    return results


def main():
    import time
    import argparse

    # Custom argument parser for this script
    parser = argparse.ArgumentParser(
        description='Restore complete Moku device state in multi-instrument mode',
        epilog="""
Examples:
  # Basic restore (auto-detect platform)
  python moku_set.py 192.168.1.100 ./c

  # Specify platform and bitstream for CloudCompile
  python moku_set.py 192.168.1.100 ./c --platform 2 --bitstream cr10_bits.tar

  # Dry run to preview changes
  python moku_set.py 192.168.1.100 ./c --dry-run

  # Enable debug logging to file
  python moku_set.py 192.168.1.100 ./c --debug debug_log.txt
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('device_ip', help='IP address of Moku device')
    parser.add_argument('config_dir', help='Directory containing .mokuconf files')
    parser.add_argument('--platform', type=int, choices=[2, 4], default=2,
                        help='Platform ID (2 or 4 for number of slots, default: 2)')
    parser.add_argument(
        '--bitstream',
        type=str,
        metavar='PATH',
        help='Path to bitstream file (required for CloudCompile instrument)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without actually loading configuration'
    )
    parser.add_argument(
        '--force-connect',
        action='store_true',
        help='Force connection even if device is in use'
    )
    parser.add_argument(
        '--ignore-busy',
        action='store_true',
        help='Ignore busy status when connecting'
    )
    parser.add_argument(
        '--persist-state',
        action='store_true',
        help='Persist state after connection'
    )
    parser.add_argument(
        '--debug',
        nargs='?',
        const=True,
        type=str,
        metavar='FILE',
        help='Enable debug logging for Moku library. Optionally specify output file (default: stderr)'
    )

    args = parser.parse_args()

    config_dir = Path(args.config_dir)

    # Enable Moku debug logging if requested
    setup_moku_debug_logging(args)

    # Overall timing
    total_start = time.perf_counter()

    # Initialize moku to None for cleanup
    mim = None

    try:
        # Discover configuration files
        logger.info("="*60)
        logger.info("DISCOVERING CONFIGURATION FILES")
        logger.info("="*60)
        configs = discover_configs(config_dir)
        logger.info(f"Found MIM config: {configs['mim_config']}")
        logger.info(f"Found {len(configs['slot_configs'])} slot configs")
        for slot_config in configs['slot_configs']:
            logger.info(f"  - {slot_config.name}")

        # Validate configurations
        logger.info("\n" + "="*60)
        logger.info("VALIDATION")
        logger.info("="*60)
        has_cloudcompile = validate_configs(configs, target_platform_id=args.platform)

        # Check CloudCompile requirements
        if has_cloudcompile and not args.bitstream and not args.dry_run:
            raise ValueError(
                "Configuration contains CloudCompile instrument but --bitstream not provided"
            )

        logger.success("Validation passed")

        if not args.dry_run:
            # Connect to device
            logger.info("\n" + "="*60)
            logger.info("CONNECTING TO DEVICE")
            logger.info("="*60)
            logger.info(f"Connecting to Moku at {args.device_ip}...")
            with time_operation("Device connection"):
                mim = MultiInstrument(
                    ip=args.device_ip,
                    platform_id=args.platform,
                    force_connect=args.force_connect,
                    persist_state=args.persist_state,
                    ignore_busy=args.ignore_busy
                )
            logger.success("Connected")

        # Restore state
        results = restore_moku_state(mim, configs, bitstream_path=args.bitstream, dry_run=args.dry_run)

        # Summary
        total_elapsed = time.perf_counter() - total_start
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total execution time: {total_elapsed:.3f} s ({total_elapsed*1000:.2f} ms)")
        if not args.dry_run:
            logger.info(f"MIM config loaded: {results['mim_config']}")
            logger.info(f"Instrument configs loaded: {len(results['instrument_configs'])} instruments")
            logger.success(f"State restored successfully to {args.device_ip}")

    except Exception as e:
        logger.exception(f"Failed to restore state: {e}")
        sys.exit(1)

    finally:
        # Disconnect
        if mim is not None and not args.dry_run:
            logger.info("\nDisconnecting...")
            with time_operation("Disconnect (relinquish_ownership)"):
                try:
                    mim.relinquish_ownership()
                    logger.success("Disconnected")
                except Exception as e:
                    logger.warning(f"Disconnect warning: {e}")


if __name__ == "__main__":
    main()
