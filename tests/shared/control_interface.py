"""
Control Interface Abstraction
=============================

Abstract interface for control register operations that matches the
CloudCompile API semantics. This allows test code to be portable between
CocoTB simulation and real Moku hardware.

Architecture:
    The interface intentionally separates FORGE control (CR0) from
    application configuration (CR1-CR10), matching the hardware architecture
    where CR0 bits are extracted at the TOP layer.

    FORGE Layer (CR0):     enable_forge() / disable_forge()
    Application Layer:     set_controls() with DPDConfig.to_app_regs_list()

Propagation Model:
    Control register writes are NOT cycle-synchronous. In CocoTB simulation,
    set_control() is async and includes random jitter (10-50 cycles) to model
    the fundamental reality that network writes have variable latency.

    This prevents tests from depending on cycle-exact timing - such tests
    would pass in simulation but fail on real hardware.

    Hardware uses shadow registers since CloudCompile.get_control() returns
    None (firmware doesn't support register readback).

Usage:
    # Simulation (async, includes mandatory propagation jitter)
    ctrl = CocoTBControl(dut)
    await ctrl.set_control(1, value)  # MUST await

    # Hardware (sync, blocks on network I/O, uses shadow registers)
    ctrl = MokuControl(mcc)
    ctrl.set_control(1, value)  # Blocks ~100ms

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TYPE_CHECKING
import sys
import time
import random
from pathlib import Path

# Add py_tools to path for DPDConfig
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

from dpd_constants import CR0

if TYPE_CHECKING:
    from dpd_config import DPDConfig


class ControlInterface(ABC):
    """Abstract interface matching CloudCompile control API semantics.

    This allows test code to use identical patterns for simulation and hardware:

        config = DPDConfig(arm_enable=True, ...)
        ctrl.enable_forge()
        ctrl.set_controls(config.to_app_regs_list())
    """

    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================

    @abstractmethod
    def set_control(self, idx: int, value: int):
        """Set a single control register value.

        Matches CloudCompile.set_control(idx, value) API.

        Args:
            idx: Register index (0-15)
            value: 32-bit register value
        """
        pass

    @abstractmethod
    def get_control(self, idx: int) -> int:
        """Read a single control register value.

        Matches CloudCompile.get_control(idx) API.

        Args:
            idx: Register index (0-15)

        Returns:
            32-bit register value
        """
        pass

    # =========================================================================
    # Concrete Methods - Built on abstract primitives
    # =========================================================================

    def set_controls(self, controls: List[Dict[str, int]]):
        """Set multiple control registers at once.

        Matches CloudCompile.set_controls(controls) API.

        Args:
            controls: List of {"idx": N, "value": V} dicts
        """
        for ctrl in controls:
            self.set_control(ctrl["idx"], ctrl["value"])

    def get_controls(self, indices: Optional[List[int]] = None) -> List[Dict[str, int]]:
        """Read multiple control registers.

        Args:
            indices: List of register indices to read (default: 0-10)

        Returns:
            List of {"idx": N, "value": V} dicts
        """
        if indices is None:
            indices = list(range(11))  # CR0-CR10
        return [{"idx": idx, "value": self.get_control(idx)} for idx in indices]

    # =========================================================================
    # FORGE Control (CR0) - System Layer
    # =========================================================================

    def enable_forge(self):
        """Enable FORGE control (CR0[31:29] = 0b111).

        Sets forge_ready, user_enable, and clk_enable bits.
        This is REQUIRED for the FSM to operate.
        """
        self.set_control(0, CR0.ALL_ENABLED)

    def disable_forge(self):
        """Disable FORGE control (CR0 = 0).

        Clears all FORGE control bits. FSM will freeze.
        """
        self.set_control(0, 0x00000000)

    def set_forge_partial(self, forge_ready: bool = False,
                          user_enable: bool = False,
                          clk_enable: bool = False):
        """Set FORGE control bits individually (for testing).

        Args:
            forge_ready: CR0[31] - Set by loader after deployment
            user_enable: CR0[30] - User control enable
            clk_enable: CR0[29] - Clock gating enable
        """
        value = 0
        if forge_ready:
            value |= CR0.FORGE_READY_MASK
        if user_enable:
            value |= CR0.USER_ENABLE_MASK
        if clk_enable:
            value |= CR0.CLK_ENABLE_MASK
        self.set_control(0, value)

    # =========================================================================
    # Application Configuration (CR1-CR10)
    # =========================================================================

    def apply_config(self, config: "DPDConfig"):
        """Apply DPDConfig to application registers (CR1-CR10).

        This is a convenience method combining set_controls() with
        DPDConfig.to_app_regs_list().

        Args:
            config: DPDConfig instance with application configuration

        Example:
            ctrl.enable_forge()
            ctrl.apply_config(DPDConfig(arm_enable=True, ...))
        """
        self.set_controls(config.to_app_regs_list())

    def clear_app_regs(self):
        """Clear all application registers (CR1-CR10) to zero.

        Useful for resetting state between tests.
        """
        for idx in range(1, 11):
            self.set_control(idx, 0)


class CocoTBControl(ControlInterface):
    """Control interface for CocoTB simulation.

    Wraps a CocoTB DUT object and provides CloudCompile-compatible API.

    IMPORTANT: set_control() is async and includes random jitter (10-50 cycles)
    to model network propagation delay. This prevents tests from depending on
    cycle-exact timing that doesn't exist in hardware.
    """

    # Propagation jitter range (cycles at 125MHz)
    JITTER_MIN_CYCLES = 10   # 80ns minimum
    JITTER_MAX_CYCLES = 50   # 400ns maximum

    def __init__(self, dut):
        """Initialize with CocoTB DUT.

        Args:
            dut: CocoTB Device Under Test object
        """
        self.dut = dut
        self._shadow_regs = {}  # Track writes for get_control()

    async def set_control(self, idx: int, value: int):
        """Set control register on DUT with propagation jitter.

        This is async and MUST be awaited. Includes random jitter to prevent
        tests from depending on cycle-exact timing.

        Args:
            idx: Register index (0-15)
            value: 32-bit register value
        """
        from cocotb.triggers import ClockCycles

        # Write the value immediately
        getattr(self.dut, f"Control{idx}").value = value
        self._shadow_regs[idx] = value

        # Add random jitter to model network propagation
        jitter = random.randint(self.JITTER_MIN_CYCLES, self.JITTER_MAX_CYCLES)
        await ClockCycles(self.dut.Clk, jitter)

    def get_control(self, idx: int) -> int:
        """Read control register from shadow (matches hardware behavior).

        Returns the last value written via set_control(). This matches
        hardware behavior where get_control() returns None from the API
        but we track writes in shadow registers.

        Args:
            idx: Register index (0-15)

        Returns:
            Last written value, or 0 if never written
        """
        return self._shadow_regs.get(idx, 0)

    def get_control_direct(self, idx: int) -> int:
        """Read control register directly from DUT (simulation only).

        Bypasses shadow registers to read actual DUT signal value.
        Useful for debugging but not available on hardware.

        Args:
            idx: Register index (0-15)

        Returns:
            Current DUT signal value
        """
        return int(getattr(self.dut, f"Control{idx}").value)


class MokuControl(ControlInterface):
    """Control interface wrapping CloudCompile instrument.

    Uses shadow registers because CloudCompile.get_control() returns None -
    the firmware doesn't support register readback for custom instruments.

    set_control() is synchronous and blocks on network I/O (~100ms typical).
    """

    def __init__(self, mcc):
        """Initialize with CloudCompile instrument.

        Args:
            mcc: CloudCompile instrument instance
        """
        self.mcc = mcc
        self._shadow_regs = {}  # Track writes (hardware can't read back)

    def set_control(self, idx: int, value: int):
        """Set control register via CloudCompile API.

        Blocks on network I/O. Value is tracked in shadow registers
        since hardware readback is not supported.

        Args:
            idx: Register index (0-15)
            value: 32-bit register value
        """
        self.mcc.set_control(idx, value)
        self._shadow_regs[idx] = value

    def get_control(self, idx: int) -> int:
        """Read control register from shadow registers.

        CloudCompile.get_control() returns None (firmware limitation),
        so we return the last value written via set_control().

        Args:
            idx: Register index (0-15)

        Returns:
            Last written value, or 0 if never written
        """
        return self._shadow_regs.get(idx, 0)

    def set_controls(self, controls: List[Dict[str, int]]):
        """Set multiple registers via CloudCompile batch API.

        Overrides base implementation to use native batch API for efficiency.
        Also updates shadow registers.

        Args:
            controls: List of {"idx": N, "value": V} dicts
        """
        self.mcc.set_controls(controls)
        # Update shadow registers
        for ctrl in controls:
            self._shadow_regs[ctrl["idx"]] = ctrl["value"]
