"""
Clock cycle conversion utilities for Moku FPGA timing calculations.

Converts time values (seconds, microseconds, nanoseconds) to clock cycles
for use in FPGA register configurations.

Debug Mode:
  Set SLOW_MODE_SCALE_FACTOR to scale all timing values for human observation.
  Typical use: 1000x slower (100μs becomes 100ms, 10μs becomes 10ms).
  WARNING: Only for debugging FSM transitions - NOT for real probe operation!
"""

import math
import os
from typing import Literal

# Default clock frequency for Moku Go (125 MHz)
DEFAULT_CLK_FREQ_HZ = 125_000_000

# Maximum value for 32-bit unsigned integer
MAX_32BIT = 2**32 - 1

# Debug mode: Scale all timing values for human observation
# Set via environment variable: export CLK_UTILS_SLOW_MODE=1000
# Or programmatically: clk_utils.SLOW_MODE_SCALE_FACTOR = 1000
SLOW_MODE_SCALE_FACTOR = int(os.environ.get('CLK_UTILS_SLOW_MODE', '1'))


class CycleCountOverflowError(ValueError):
    """Raised when a cycle count exceeds 32-bit unsigned integer range."""
    pass


def s_to_cycles(
    seconds: float,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ,
    round_direction: Literal["up", "down"] = "down"
) -> int:
    """
    Convert seconds to clock cycles.

    Args:
        seconds: Time in seconds
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)
        round_direction: "up" for ceiling, "down" for floor

    Returns:
        Number of clock cycles as integer (scaled by SLOW_MODE_SCALE_FACTOR if set)

    Raises:
        CycleCountOverflowError: If result exceeds 32-bit unsigned integer range
    """
    cycles_float = seconds * clk_freq_hz

    if round_direction == "up":
        cycles = math.ceil(cycles_float)
    else:
        cycles = math.floor(cycles_float)

    # Apply slow mode scaling for debugging (makes timing human-observable)
    cycles = cycles * SLOW_MODE_SCALE_FACTOR

    if cycles > MAX_32BIT:
        raise CycleCountOverflowError(
            f"Cycle count {cycles} exceeds 32-bit range (max: {MAX_32BIT})"
        )

    if cycles < 0:
        raise ValueError(f"Negative cycle count {cycles} is invalid")

    return cycles


def us_to_cycles(
    microseconds: float,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ,
    round_direction: Literal["up", "down"] = "down"
) -> int:
    """
    Convert microseconds to clock cycles.

    Args:
        microseconds: Time in microseconds
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)
        round_direction: "up" for ceiling, "down" for floor

    Returns:
        Number of clock cycles as integer

    Raises:
        CycleCountOverflowError: If result exceeds 32-bit unsigned integer range
    """
    seconds = microseconds / 1_000_000
    return s_to_cycles(seconds, clk_freq_hz, round_direction)


def ns_to_cycles(
    nanoseconds: float,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ,
    round_direction: Literal["up", "down"] = "down"
) -> int:
    """
    Convert nanoseconds to clock cycles.

    Args:
        nanoseconds: Time in nanoseconds
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)
        round_direction: "up" for ceiling, "down" for floor

    Returns:
        Number of clock cycles as integer

    Raises:
        CycleCountOverflowError: If result exceeds 32-bit unsigned integer range
    """
    seconds = nanoseconds / 1_000_000_000
    return s_to_cycles(seconds, clk_freq_hz, round_direction)


# Reverse conversions: clock cycles to time units

def cycles_to_s(
    cycles: int,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ
) -> float:
    """
    Convert clock cycles to seconds.

    Args:
        cycles: Number of clock cycles
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)

    Returns:
        Time in seconds as float
    """
    return cycles / clk_freq_hz


def cycles_to_us(
    cycles: int,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ
) -> float:
    """
    Convert clock cycles to microseconds.

    Args:
        cycles: Number of clock cycles
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)

    Returns:
        Time in microseconds as float
    """
    return (cycles / clk_freq_hz) * 1_000_000


def cycles_to_ns(
    cycles: int,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ
) -> float:
    """
    Convert clock cycles to nanoseconds.

    Args:
        cycles: Number of clock cycles
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)

    Returns:
        Time in nanoseconds as float
    """
    return (cycles / clk_freq_hz) * 1_000_000_000


def set_slow_mode(scale_factor: int) -> None:
    """
    Enable slow mode for human-observable timing debugging.

    Args:
        scale_factor: Multiplier for all timing values (e.g., 1000 = 1000x slower)
                      Set to 1 to disable slow mode.

    Example:
        # Make all timing 1000x slower for debugging
        set_slow_mode(1000)

        # 100μs becomes 100ms (visible on scope)
        cycles = us_to_cycles(100)  # Returns 1000x more cycles

        # Disable slow mode
        set_slow_mode(1)

    WARNING: Only for debugging FSM transitions - NOT for real probe operation!
    """
    global SLOW_MODE_SCALE_FACTOR
    SLOW_MODE_SCALE_FACTOR = scale_factor
    if scale_factor > 1:
        print(f"⚠️  SLOW MODE ENABLED: All timing values scaled by {scale_factor}x")
        print(f"   This is for debugging only - NOT for real probe operation!")
    else:
        print("✓ Slow mode disabled (normal timing)")


def get_slow_mode() -> int:
    """Get current slow mode scale factor."""
    return SLOW_MODE_SCALE_FACTOR


if __name__ == "__main__":
    # Example usage
    print(f"Default clock frequency: {DEFAULT_CLK_FREQ_HZ / 1e6} MHz")
    print(f"Current slow mode scale: {SLOW_MODE_SCALE_FACTOR}x")

    print(f"\nForward conversions (time -> cycles):")
    print(f"  1 second = {s_to_cycles(1)} cycles")
    print(f"  100 microseconds = {us_to_cycles(100)} cycles")
    print(f"  1000 nanoseconds = {ns_to_cycles(1000)} cycles")
    print(f"  1.5 nanoseconds (round down) = {ns_to_cycles(1.5, round_direction='down')} cycles")
    print(f"  1.5 nanoseconds (round up) = {ns_to_cycles(1.5, round_direction='up')} cycles")

    print(f"\nReverse conversions (cycles -> time):")
    print(f"  125000000 cycles = {cycles_to_s(125000000)} seconds")
    print(f"  12500 cycles = {cycles_to_us(12500)} microseconds")
    print(f"  125 cycles = {cycles_to_ns(125)} nanoseconds")

    print(f"\n--- Slow Mode Demo ---")
    print(f"Normal mode (100μs):")
    print(f"  {us_to_cycles(100)} cycles")

    set_slow_mode(1000)
    print(f"\nSlow mode 1000x (100μs becomes 100ms):")
    print(f"  {us_to_cycles(100)} cycles")

    set_slow_mode(1)
    print(f"\nBack to normal:")
    print(f"  {us_to_cycles(100)} cycles")
