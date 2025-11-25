"""
Common CLI argument parsing utilities for Moku device scripts.

Provides shared argument parsing functionality to reduce code duplication
across scripts.
"""

import argparse
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

try:
    from loguru import logger
except ImportError:
    print("Error: loguru not installed. Run: uv sync")
    sys.exit(1)

try:
    from moku import logging as moku_logging
except ImportError:
    # moku_logging is optional - scripts can handle this
    moku_logging = None

try:
    from moku.instruments import MultiInstrument, CloudCompile
except ImportError:
    # These will be imported by scripts that use them
    MultiInstrument = None
    CloudCompile = None


# Platform name to ID mapping
PLATFORM_MAP = {
    'moku_go': 2,
    'moku_lab': 1,
    'moku_pro': 3,
    'moku_delta': 4,
}


def add_common_args(parser: argparse.ArgumentParser, 
                     require_bitstream: bool = False,
                     default_slot: Optional[int] = None,
                     add_verbose: bool = False) -> None:
    """
    Add common Moku device arguments to an ArgumentParser.
    
    Args:
        parser: ArgumentParser instance to add arguments to
        require_bitstream: If True, --bitstream is required; otherwise optional
        default_slot: Default value for --slot (None means no default)
        add_verbose: If True, add --verbose/-v flag for loguru verbosity
    """
    parser.add_argument('device_ip', help='Moku device IP address')
    
    slot_kwargs = {'type': int, 'help': 'Slot number containing CloudCompile (auto-detected if not specified)'}
    if default_slot is not None:
        slot_kwargs['default'] = default_slot
        slot_kwargs['help'] = f'Slot number containing CloudCompile (default: {default_slot})'
    parser.add_argument('--slot', **slot_kwargs)
    
    parser.add_argument(
        '--platform',
        choices=['moku_go', 'moku_lab', 'moku_pro', 'moku_delta'],
        help='Platform type (auto-detected if not specified)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force connect (disconnect existing connections)'
    )
    
    bitstream_kwargs = {
        'type': Path,
        'help': 'Path to bitstream file (.tar) to upload to CloudCompile'
    }
    if require_bitstream:
        bitstream_kwargs['required'] = True
        bitstream_kwargs['help'] = 'Path to bitstream file (.tar) - REQUIRED: CloudCompile always needs a bitstream, even for existing instances'
    parser.add_argument('--bitstream', **bitstream_kwargs)
    
    parser.add_argument(
        '--debug',
        nargs='?',
        const=True,
        type=str,
        metavar='FILE',
        help='Enable debug logging for Moku library. Optionally specify output file (default: stderr)'
    )
    
    if add_verbose:
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose/debug logging output'
        )


def parse_platform_id(args) -> Optional[int]:
    """Map platform name from args to platform ID."""
    if args.platform:
        return PLATFORM_MAP.get(args.platform)
    return None


def setup_moku_debug_logging(args) -> None:
    """
    Enable Moku debug logging if --debug flag is set.
    
    Uses the same stream as loguru (stderr by default) or writes to a file
    if a filename is provided via --debug FILE.
    """
    if not args.debug or not moku_logging:
        return
    
    # Determine output stream
    if args.debug is True:
        # --debug flag without filename: use stderr (same as loguru)
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
    
    # Enable Moku debug logging with the determined stream
    moku_logging.enable_debug_logging(stream=output_stream)


def handle_arg_parsing(
    description: str,
    epilog: Optional[str] = None,
    require_bitstream: bool = False,
    default_slot: Optional[int] = None,
    add_verbose: bool = False,
    additional_positional: Optional[list] = None,
    additional_optional: Optional[list] = None
):
    """
    Parse command line arguments with common Moku device options.
    
    Args:
        description: Description for ArgumentParser
        epilog: Optional epilog text (examples, etc.)
        require_bitstream: If True, --bitstream is required
        default_slot: Default value for --slot
        add_verbose: If True, add --verbose/-v flag
        additional_positional: List of (name, kwargs) tuples for additional positional args
        additional_optional: List of (name, kwargs) tuples for additional optional args
    
    Returns:
        Tuple of (args, platform_id) where platform_id is None or int
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog
    )
    
    # Add common arguments
    add_common_args(parser, require_bitstream, default_slot, add_verbose)
    
    # Add additional positional arguments
    if additional_positional:
        for name, kwargs in additional_positional:
            parser.add_argument(name, **kwargs)
    
    # Add additional optional arguments
    if additional_optional:
        for name, kwargs in additional_optional:
            parser.add_argument(name, **kwargs)
    
    args = parser.parse_args()
    
    # Setup Moku debug logging
    setup_moku_debug_logging(args)
    
    # Map platform name to ID
    platform_id = parse_platform_id(args)
    
    return args, platform_id


@contextmanager
def time_operation(operation_name: str):
    """Context manager to time an operation and log the result."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"  {operation_name}: {elapsed*1000:.2f} ms")


def connect_to_device(device_ip: str, platform_id: int | None = None, force: bool = False, 
                     read_timeout: Optional[int] = None) -> MultiInstrument:
    """
    Connect to Moku device with platform detection.
    
    Args:
        device_ip: IP address of the Moku device
        platform_id: Optional platform ID (1=Lab, 2=Go, 3=Pro, 4=Delta)
        force: If True, force connect (disconnect existing connections)
        read_timeout: Optional read timeout in seconds (default: None)
    
    Returns:
        MultiInstrument instance
    
    Raises:
        ConnectionError: If connection fails
    """
    if MultiInstrument is None:
        raise ImportError("MultiInstrument not available. Import moku.instruments first.")
    
    platform_id_map = {
        1: "Moku:Lab",
        2: "Moku:Go",
        3: "Moku:Pro",
        4: "Moku:Delta",
    }
    
    logger.info(f"Connecting to device at {device_ip}...")
    logger.debug(f"Platform ID: {platform_id}, Force connect: {force}")
    
    if platform_id is None:
        # Try each platform
        logger.debug("Auto-detecting platform type...")
        for pid in [2, 1, 3, 4]:  # Go, Lab, Pro, Delta
            platform_name = platform_id_map[pid]
            logger.debug(f"Trying {platform_name} (platform_id={pid})...")
            try:
                kwargs = {
                    'platform_id': pid,
                    'force_connect': force,
                    'persist_state': True  # Preserve existing state
                }
                if read_timeout is not None:
                    kwargs['read_timeout'] = read_timeout
                
                moku = MultiInstrument(device_ip, **kwargs)
                logger.success(f"Connected to {platform_name} at {device_ip}")
                return moku
            except Exception as e:
                error_msg = str(e).lower()
                logger.debug(f"Failed to connect as {platform_name}: {e}")
                if "already exists" in error_msg or "busy" in error_msg:
                    logger.debug("Device is busy, trying next platform...")
                    continue
                continue
        logger.error(f"Could not connect to {device_ip} with any platform type")
        raise ConnectionError(f"Could not connect to {device_ip}. Try --force to disconnect existing connections.")
    else:
        # Use specified platform
        platform_name = platform_id_map.get(platform_id, f"Platform {platform_id}")
        logger.debug(f"Using specified platform: {platform_name} (platform_id={platform_id})")
        try:
            kwargs = {
                'platform_id': platform_id,
                'force_connect': force,
                'persist_state': True
            }
            if read_timeout is not None:
                kwargs['read_timeout'] = read_timeout
            
            moku = MultiInstrument(device_ip, **kwargs)
            logger.success(f"Connected to {platform_name} at {device_ip}")
            return moku
        except Exception as e:
            logger.error(f"Failed to connect to {platform_name}: {e}")
            raise


def get_cloudcompile_instance(moku: MultiInstrument, slot_num: int, 
                               bitstream_path: Path | None = None,
                               require_bitstream: bool = False) -> CloudCompile:
    """
    Get CloudCompile instance from specified slot.
    
    Args:
        moku: MultiInstrument instance
        slot_num: Slot number containing CloudCompile
        bitstream_path: Optional path to bitstream file. If provided, will upload it.
        require_bitstream: If True, bitstream_path must be provided and valid
    
    Returns:
        CloudCompile instance
    
    Raises:
        ValueError: If require_bitstream is True but bitstream_path is None
        FileNotFoundError: If bitstream_path is provided but file doesn't exist
        RuntimeError: If CloudCompile instance cannot be accessed
    """
    if CloudCompile is None:
        raise ImportError("CloudCompile not available. Import moku.instruments first.")
    
    logger.debug(f"Getting CloudCompile instance for slot {slot_num}...")
    
    if require_bitstream:
        if not bitstream_path:
            raise ValueError("Bitstream path is required for CloudCompile")
        if not bitstream_path.exists():
            logger.error(f"Bitstream file not found: {bitstream_path}")
            raise FileNotFoundError(f"Bitstream file not found: {bitstream_path}")
        
        file_size = bitstream_path.stat().st_size
        logger.debug(f"Bitstream file size: {file_size / (1024*1024):.2f} MB")
        logger.info(f"Using bitstream: {bitstream_path.name}")
        logger.debug(f"Bitstream path (absolute): {bitstream_path.absolute()}")
    
    try:
        if bitstream_path:
            # Upload bitstream and get instance
            if not bitstream_path.exists():
                raise FileNotFoundError(f"Bitstream file not found: {bitstream_path}")
            logger.debug(f"Calling moku.set_instrument({slot_num}, CloudCompile, bitstream={bitstream_path})")
            cc = moku.set_instrument(slot_num, CloudCompile, bitstream=str(bitstream_path))
            logger.success(f"CloudCompile instance ready for slot {slot_num}")
            return cc
        else:
            # Try to get existing instance (without bitstream parameter)
            logger.debug(f"Calling moku.set_instrument({slot_num}, CloudCompile)")
            cc = moku.set_instrument(slot_num, CloudCompile)
            logger.success(f"CloudCompile instance ready for slot {slot_num}")
            return cc
    except TypeError:
        # If set_instrument requires bitstream, we can't proceed without it
        raise RuntimeError(
            f"CloudCompile in slot {slot_num} requires bitstream parameter. "
            "The instrument may not be deployed yet. Please provide --bitstream or deploy it first."
        )
    except Exception as e:
        logger.error(f"Exception when accessing CloudCompile in slot {slot_num}: {e}")
        logger.debug("Exception details:", exc_info=True)
        raise RuntimeError(f"Could not access CloudCompile in slot {slot_num}: {e}")

