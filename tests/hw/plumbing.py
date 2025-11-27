"""
Hardware Plumbing - Moku Device Setup and Teardown
===================================================

Extracted from run_hw_tests.py to enable unified sim/hw testing.
This module handles all hardware-specific concerns:
- Device connection
- Instrument deployment (Oscilloscope + CloudCompile)
- Routing configuration
- Cleanup/disconnect

Usage:
    from hw.plumbing import MokuSession

    async with MokuSession(ip="192.168.31.41", bitstream="dpd.tar") as session:
        harness = session.create_harness()
        # Use harness like CocoTBAsyncHarness...
"""

import sys
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Add paths
HW_PATH = Path(__file__).parent
TESTS_PATH = HW_PATH.parent
PROJECT_ROOT = TESTS_PATH.parent
sys.path.insert(0, str(TESTS_PATH))
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

# Import loguru for consistent logging
try:
    from loguru import logger
except ImportError:
    # Fallback if loguru not available
    import logging
    logger = logging.getLogger(__name__)

from adapters import MokuAsyncHarness


@dataclass
class MokuConfig:
    """Configuration for Moku hardware session."""
    device_ip: str
    bitstream_path: str
    osc_slot: int = 1
    cc_slot: int = 2
    platform_id: int = 2  # Moku:Go
    force_connect: bool = False
    propagation_delay_ms: float = 10.0


class MokuSession:
    """
    Context manager for Moku hardware test sessions.

    Handles:
    - MultiInstrument connection
    - Oscilloscope and CloudCompile deployment
    - Signal routing (OutputC → OscInA for HVS state observation)
    - Graceful cleanup on exit

    Example:
        config = MokuConfig(device_ip="192.168.31.41", bitstream_path="dpd.tar")
        async with MokuSession(config) as session:
            harness = session.create_harness()
            await harness.wait_for_state("IDLE")
    """

    def __init__(self, config: MokuConfig):
        self.config = config
        self.moku = None
        self.osc = None
        self.mcc = None
        self._connected = False

    async def __aenter__(self):
        """Connect and set up instruments."""
        await self._connect()
        await self._deploy_instruments()
        await self._setup_routing()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up and disconnect."""
        await self._disconnect()
        return False

    async def _connect(self):
        """Connect to Moku device."""
        # Import here to avoid dependency issues when running sim-only
        try:
            from moku.instruments import MultiInstrument
        except ImportError:
            raise RuntimeError("moku package not installed. Run: uv sync")

        try:
            from moku_cli_common import connect_to_device
            self.moku = connect_to_device(
                self.config.device_ip,
                self.config.platform_id,
                force=self.config.force_connect,
                read_timeout=5
            )
        except ImportError:
            # Fallback if moku_cli_common not available
            logger.debug("moku_cli_common not available, using direct MultiInstrument")
            self.moku = MultiInstrument(
                self.config.device_ip,
                platform_id=self.config.platform_id,
                force_connect=self.config.force_connect
            )

        self._connected = True

    async def _deploy_instruments(self):
        """Deploy Oscilloscope and CloudCompile to slots."""
        from moku.instruments import Oscilloscope, CloudCompile

        logger.debug(f"Deploying Oscilloscope to slot {self.config.osc_slot}")
        self.osc = self.moku.set_instrument(
            self.config.osc_slot,
            Oscilloscope
        )

        # Configure oscilloscope timebase for HVS reading
        # NOTE: Frontend (impedance, coupling, range) cannot be set in MIM for internal routing.
        # MIM set_frontend() only applies to physical Moku inputs (Input1, Input2), not
        # internal slot-to-slot routing which is digital. Our routing is:
        #   Slot{cc}OutC → Slot{osc}InA (internal, no analog frontend)
        # The oscilloscope receives the full ±5V digital range from CloudCompile OutputC.
        try:
            self.osc.set_timebase(-0.001, 0.001)  # 2ms window centered at trigger
            logger.debug("Oscilloscope configured: 2ms timebase window")
        except Exception as e:
            logger.warning(f"Could not configure oscilloscope timebase: {e}")

        logger.debug(f"Deploying CloudCompile to slot {self.config.cc_slot} with bitstream {self.config.bitstream_path}")
        self.mcc = self.moku.set_instrument(
            self.config.cc_slot,
            CloudCompile,
            bitstream=self.config.bitstream_path
        )

        # Brief delay for instruments to initialize
        await asyncio.sleep(0.5)
        logger.debug("Instruments deployed successfully")

    async def _setup_routing(self):
        """Configure signal routing for HVS observation."""
        osc_slot = self.config.osc_slot
        cc_slot = self.config.cc_slot

        # Check if routing already configured
        connections = self.moku.get_connections()
        required = f"Slot{cc_slot}OutC"
        target = f"Slot{osc_slot}InA"

        needs_routing = True
        for conn in connections:
            if conn.get('source') == required and conn.get('destination') == target:
                needs_routing = False
                break

        if needs_routing:
            logger.debug(f"Setting up routing: {required} → {target}")
            self.moku.set_connections(connections=[
                {'source': 'Input1', 'destination': f'Slot{cc_slot}InA'},
                {'source': f'Slot{cc_slot}OutB', 'destination': 'Output2'},
                {'source': f'Slot{cc_slot}OutC', 'destination': 'Output1'},
                {'source': f'Slot{cc_slot}OutC', 'destination': f'Slot{osc_slot}InA'},
            ])
            await asyncio.sleep(0.3)
            logger.debug("Routing configured")
        else:
            logger.debug("Routing already configured")

    async def _disconnect(self):
        """Disconnect from device."""
        if self.moku and self._connected:
            try:
                logger.debug("Disconnecting from device...")
                self.moku.relinquish_ownership()
                logger.debug("Disconnected")
            except Exception as e:
                logger.debug(f"Disconnect warning: {e}")
            self._connected = False

    def create_harness(self) -> MokuAsyncHarness:
        """Create a MokuAsyncHarness for this session."""
        if not self.mcc or not self.osc:
            raise RuntimeError("Session not initialized. Use 'async with MokuSession(...)'")

        return MokuAsyncHarness(
            self.mcc,
            self.osc,
            propagation_delay_ms=self.config.propagation_delay_ms
        )


# Convenience function for simple usage
async def create_hardware_harness(
    device_ip: str,
    bitstream_path: str,
    **kwargs
) -> tuple[MokuSession, MokuAsyncHarness]:
    """
    Quick setup for hardware testing.

    Returns:
        Tuple of (session, harness) - caller must close session when done.

    Example:
        session, harness = await create_hardware_harness("192.168.31.41", "dpd.tar")
        try:
            await harness.wait_for_state("IDLE")
        finally:
            await session._disconnect()
    """
    config = MokuConfig(device_ip=device_ip, bitstream_path=bitstream_path, **kwargs)
    session = MokuSession(config)
    await session._connect()
    await session._deploy_instruments()
    await session._setup_routing()
    return session, session.create_harness()
