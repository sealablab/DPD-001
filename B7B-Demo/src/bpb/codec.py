"""BpB (Bits per Block) codec.

The BpB encoding uses bit 7 (MSB) as a fault flag:
- Bit 7 = 0: Normal sample (bits 6:0 = magnitude 0-127)
- Bit 7 = 1: Fault indicator (bits 6:0 = fault code)

This maps naturally to signed int8: negative values indicate faults.
"""

import numpy as np
from typing import Tuple


def is_fault(raw: np.int8) -> bool:
    """Check if a raw BpB word indicates a fault.

    Args:
        raw: Raw BpB word as signed int8

    Returns:
        True if fault bit is set (negative value)
    """
    return raw < 0


def decode_word(raw: np.int8) -> Tuple[bool, int, int]:
    """Decode a raw BpB word.

    Args:
        raw: Raw BpB word as signed int8

    Returns:
        Tuple of (is_fault, value, guard_bits)
        - is_fault: True if fault bit set
        - value: 7-bit magnitude (0-127)
        - guard_bits: Reserved for future use
    """
    fault = raw < 0
    # Mask off the fault bit to get magnitude
    value = int(raw) & 0x7F
    guard = 0  # Reserved
    return (fault, value, guard)


def encode_sample(magnitude: int) -> np.int8:
    """Encode a magnitude value as a BpB word.

    Args:
        magnitude: Value 0-127

    Returns:
        BpB word with fault bit clear
    """
    if not 0 <= magnitude <= 127:
        raise ValueError(f"Magnitude must be 0-127, got {magnitude}")
    return np.int8(magnitude)


def encode_fault(fault_code: int = 0) -> np.int8:
    """Encode a fault indicator as a BpB word.

    Args:
        fault_code: Optional fault code 0-127

    Returns:
        BpB word with fault bit set (negative value)
    """
    if not 0 <= fault_code <= 127:
        raise ValueError(f"Fault code must be 0-127, got {fault_code}")
    # Set bit 7 by making value negative
    return np.int8(fault_code - 128)
