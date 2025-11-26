"""
Unified Async Adapters
======================

Provides platform-agnostic async interface for FSM testing.

Usage:
    # Simulation
    from tests.adapters import CocoTBAsyncHarness
    harness = CocoTBAsyncHarness(dut, jitter_enabled=True)

    # Hardware
    from tests.adapters import MokuAsyncHarness
    harness = MokuAsyncHarness(mcc, osc)

    # Factory function
    from tests.adapters import get_harness
    harness = get_harness("cocotb", dut=dut)
    harness = get_harness("moku", mcc=mcc, osc=osc)

    # Same test code for both!
    await harness.controller.set_cr1(arm_enable=True)
    await harness.wait_for_state("ARMED", timeout_us=1000)
"""

# Base classes (for type hints and subclassing)
from .base import (
    AsyncFSMController,
    AsyncFSMStateReader,
    AsyncFSMTestHarness,
    state_to_digital,
    state_to_voltage,
    decode_state_from_digital,
)

# CocoTB implementation
from .cocotb import (
    CocoTBAsyncController,
    CocoTBAsyncStateReader,
    CocoTBAsyncHarness,
)

# Moku implementation
from .moku import (
    MokuAsyncController,
    MokuAsyncStateReader,
    MokuAsyncHarness,
)


def get_harness(platform: str, **kwargs) -> AsyncFSMTestHarness:
    """Factory function to create platform-appropriate harness.

    Args:
        platform: "cocotb" or "moku"
        **kwargs: Platform-specific arguments

    For CocoTB:
        dut: CocoTB DUT object (required)
        jitter_enabled: bool (optional, default False)
        jitter_range: Tuple[int, int] (optional, default (10, 200))

    For Moku:
        mcc: CloudCompile instance (required)
        osc: Oscilloscope instance (required)
        propagation_delay_ms: float (optional, default 10.0)

    Returns:
        AsyncFSMTestHarness instance

    Example:
        # CocoTB
        harness = get_harness("cocotb", dut=dut, jitter_enabled=True)

        # Moku
        harness = get_harness("moku", mcc=mcc, osc=osc)
    """
    if platform.lower() == "cocotb":
        dut = kwargs.pop("dut")
        jitter_enabled = kwargs.pop("jitter_enabled", False)
        jitter_range = kwargs.pop("jitter_range", (10, 200))
        return CocoTBAsyncHarness(dut, jitter_enabled, jitter_range)

    elif platform.lower() == "moku":
        mcc = kwargs.pop("mcc")
        osc = kwargs.pop("osc")
        propagation_delay_ms = kwargs.pop("propagation_delay_ms", 10.0)
        return MokuAsyncHarness(mcc, osc, propagation_delay_ms)

    else:
        raise ValueError(f"Unknown platform: {platform}. Use 'cocotb' or 'moku'.")
