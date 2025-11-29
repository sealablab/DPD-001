"""
BOOT Subsystem Constants - Python Mirror of forge_common_pkg.vhd
=================================================================

This file provides Python constants that mirror the VHDL package
rtl/forge_common_pkg.vhd for the BOOT subsystem.

IMPORTANT: This is the authoritative Python source for BOOT constants.
Keep in sync with forge_common_pkg.vhd.

Based on: rtl/forge_common_pkg.vhd (authoritative VHDL specification)
Reference: docs/BOOT-FSM-spec.md, docs/LOAD-FSM-spec.md
"""

from enum import IntEnum
from typing import Dict


# ==============================================================================
# RUN Gate (CR0[31:29])
# ==============================================================================

class RUN:
    """RUN gate bits - must all be '1' for system operation.

    These are the FORGE control bits that enable the BOOT subsystem.
    All three must be set for any module to operate.
    """

    READY_BIT = 31   # R: Ready (platform settled)
    USER_BIT = 30    # U: User enable
    CLK_BIT = 29     # N: Clock enable

    # Masks
    READY_MASK = 1 << READY_BIT   # 0x80000000
    USER_MASK = 1 << USER_BIT     # 0x40000000
    CLK_MASK = 1 << CLK_BIT       # 0x20000000

    # Combined RUN gate (all three bits)
    GATE_MASK = READY_MASK | USER_MASK | CLK_MASK  # 0xE0000000


# ==============================================================================
# Module Select (CR0[28:25])
# ==============================================================================

class SEL:
    """Module select bits - exactly one should be set.

    Priority (if hardware encoder used): P > B > L > R
    Multiple bits set = FAULT condition.
    """

    PROG_BIT = 28    # P: Program (one-way handoff)
    BIOS_BIT = 27    # B: BIOS diagnostics
    LOADER_BIT = 26  # L: Buffer loader
    RESET_BIT = 25   # R: Soft reset

    # Masks
    PROG_MASK = 1 << PROG_BIT     # 0x10000000
    BIOS_MASK = 1 << BIOS_BIT     # 0x08000000
    LOADER_MASK = 1 << LOADER_BIT # 0x04000000
    RESET_MASK = 1 << RESET_BIT   # 0x02000000


# ==============================================================================
# Return Control (CR0[24])
# ==============================================================================

class RET:
    """Return control bit - returns from BIOS/LOADER to BOOT_P1."""

    BIT = 24
    MASK = 1 << BIT  # 0x01000000


# ==============================================================================
# LOADER Control (CR0[23:21])
# ==============================================================================

class LOADER_CTRL:
    """LOADER-specific control bits in CR0.

    CR0[23:22] = Buffer count (00=1, 01=2, 10=3, 11=4)
    CR0[21]    = Data strobe (falling edge triggers action)
    """

    BUFCNT_HI_BIT = 23
    BUFCNT_LO_BIT = 22
    STROBE_BIT = 21

    # Masks
    BUFCNT_MASK = 0x3 << BUFCNT_LO_BIT  # 0x00C00000
    STROBE_MASK = 1 << STROBE_BIT        # 0x00200000

    @staticmethod
    def encode_bufcnt(num_buffers: int) -> int:
        """Encode buffer count (1-4) into CR0 bits.

        Args:
            num_buffers: Number of buffers (1-4)

        Returns:
            Value to OR into CR0 (already shifted)
        """
        assert 1 <= num_buffers <= 4, f"Buffer count must be 1-4, got {num_buffers}"
        return (num_buffers - 1) << LOADER_CTRL.BUFCNT_LO_BIT

    @staticmethod
    def decode_bufcnt(cr0: int) -> int:
        """Decode buffer count from CR0.

        Args:
            cr0: CR0 register value

        Returns:
            Number of buffers (1-4)
        """
        return ((cr0 & LOADER_CTRL.BUFCNT_MASK) >> LOADER_CTRL.BUFCNT_LO_BIT) + 1


# ==============================================================================
# Command Constants (CR0 values)
# ==============================================================================

class CMD:
    """Pre-computed CR0 command values.

    These match the CMD_* constants in forge_common_pkg.vhd.
    """

    RUN  = 0xE0000000  # Just RUN gate (BOOT_P0 -> BOOT_P1)
    RUNP = 0xF0000000  # RUN + P (transfer to PROG, one-way)
    RUNB = 0xE8000000  # RUN + B (transfer to BIOS)
    RUNL = 0xE4000000  # RUN + L (transfer to LOADER)
    RUNR = 0xE2000000  # RUN + R (soft reset to BOOT_P0)
    RET  = 0xE1000000  # RUN + RET (return to BOOT_P1)


# ==============================================================================
# BOOT FSM States
# ==============================================================================

class BOOTState(IntEnum):
    """BOOT module FSM states (6-bit encoding).

    HVS voltage = state * 0.2V (using 1311 units per state)
    """

    P0 = 0           # 0.0V - Initial/Reset
    P1 = 1           # 0.2V - Settled/Dispatcher
    BIOS_ACTIVE = 2  # 0.4V - Control to BIOS
    LOAD_ACTIVE = 3  # 0.6V - Control to LOADER
    PROG_ACTIVE = 4  # 0.8V - Control to PROG
    FAULT = 63       # Negative - Boot fault

    @classmethod
    def from_voltage(cls, voltage: float, tolerance: float = 0.15) -> "BOOTState":
        """Decode state from HVS voltage reading."""
        if voltage < -tolerance:
            return cls.FAULT
        for state in cls:
            if state == cls.FAULT:
                continue
            expected = state * 0.2
            if abs(voltage - expected) < tolerance:
                return state
        raise ValueError(f"Unknown BOOT state for voltage {voltage:.2f}V")


# ==============================================================================
# LOADER FSM States
# ==============================================================================

class LOADState(IntEnum):
    """LOADER module FSM states (6-bit encoding).

    HVS voltage = state * 0.2V (using 1311 units per state)
    """

    P0 = 0       # 0.0V - Setup phase
    P1 = 1       # 0.2V - Transfer phase
    P2 = 2       # 0.4V - Validate phase
    P3 = 3       # 0.6V - Complete
    FAULT = 63   # Negative - CRC mismatch

    @classmethod
    def from_voltage(cls, voltage: float, tolerance: float = 0.15) -> "LOADState":
        """Decode state from HVS voltage reading."""
        if voltage < -tolerance:
            return cls.FAULT
        for state in cls:
            if state == cls.FAULT:
                continue
            expected = state * 0.2
            if abs(voltage - expected) < tolerance:
                return state
        raise ValueError(f"Unknown LOAD state for voltage {voltage:.2f}V")


# ==============================================================================
# HVS Parameters (Pre-PROG encoding: 197 units/state, 11 units/status)
# ==============================================================================

# Pre-PROG HVS encoding constants (from docs/HVS-encoding-scheme.md)
HVS_PRE_STATE_UNITS = 197   # Digital units per state (~30mV @ ±5V FS)
HVS_PRE_STATUS_UNITS = 11  # Digital units per status LSB (~1.7mV)

# Platform constants
V_MAX = 5.0
DIGITAL_MAX = 32768

# Global S value ranges (power-of-2 boundaries)
BOOT_S_RANGE = (0, 7)      # S=0-7: BOOT states
BIOS_S_RANGE = (8, 15)     # S=8-15: BIOS states
LOADER_S_RANGE = (16, 23)  # S=16-23: LOADER states

# BOOT state to global S mapping
BOOT_HVS_S_P0 = 0
BOOT_HVS_S_P1 = 1
BOOT_HVS_S_FAULT = 2

# LOADER state to global S mapping
LOADER_HVS_S_P0 = 16
LOADER_HVS_S_P1 = 17
LOADER_HVS_S_P2 = 18
LOADER_HVS_S_P3 = 19
LOADER_HVS_S_FAULT = 20

# BIOS state to global S mapping
BIOS_HVS_S_IDLE = 8
BIOS_HVS_S_RUN = 9
BIOS_HVS_S_DONE = 10
BIOS_HVS_S_FAULT = 11

# Legacy alias (deprecated - use BIOS_HVS_S_IDLE instead)
BIOS_HVS_S_ACTIVE = BIOS_HVS_S_IDLE


def decode_pre_prog(digital_value: int) -> tuple:
    """Decode pre-PROG HVS reading to (context, S, T).
    
    Returns: (context, S, T) where:
        context: "BOOT", "BIOS", "LOADER", "RESERVED", or "UNKNOWN"
        S: global state (0-31)
        T: status value (0-127)
    """
    # Extract S and T using number theory
    # Since gcd(197, 11) = 1, we can solve: D = 197*S + 11*T
    for S in range(32):
        remainder = digital_value - (S * HVS_PRE_STATE_UNITS)
        if remainder >= 0 and remainder % HVS_PRE_STATUS_UNITS == 0:
            T = remainder // HVS_PRE_STATUS_UNITS
            if T <= 127:  # Valid status range
                # Determine context from S (power-of-2 boundaries)
                if S <= BOOT_S_RANGE[1]:
                    context = "BOOT"
                elif S <= BIOS_S_RANGE[1]:
                    context = "BIOS"
                elif S <= LOADER_S_RANGE[1]:
                    context = "LOADER"
                else:
                    context = "RESERVED"
                return (context, S, T)
    
    return ("UNKNOWN", None, None)


def encode_pre_prog(S: int, T: int = 0) -> int:
    """Encode pre-PROG HVS value from global S and status T."""
    return (S * HVS_PRE_STATE_UNITS) + (T * HVS_PRE_STATUS_UNITS)


def digital_to_volts(digital: int) -> float:
    """Convert digital units to voltage (V)."""
    return (digital / DIGITAL_MAX) * V_MAX


# Legacy BOOT_HVS class for backward compatibility (deprecated)
class BOOT_HVS:
    """Legacy HVS encoding - use decode_pre_prog() instead."""
    
    # New encoding values
    DIGITAL_P0 = encode_pre_prog(BOOT_HVS_S_P0, 0)  # 0
    DIGITAL_P1 = encode_pre_prog(BOOT_HVS_S_P1, 0)  # 197
    
    # Legacy compatibility (will be removed)
    UNITS_PER_STATE = HVS_PRE_STATE_UNITS
    VOLTS_PER_STATE = digital_to_volts(HVS_PRE_STATE_UNITS)
    
    @staticmethod
    def decode_state_from_digital(digital: int, tolerance: int = 150) -> str:
        """Decode state name from digital value (uses new decoder)."""
        context, S, T = decode_pre_prog(digital)
        if context == "UNKNOWN":
            return f"UNKNOWN({digital})"
        if digital < -tolerance:
            return "FAULT"
        # Map S values to state names
        if context == "BOOT":
            if S == BOOT_HVS_S_P0:
                return "BOOT_P0"
            elif S == BOOT_HVS_S_P1:
                return "BOOT_P1"
            elif S == BOOT_HVS_S_FAULT:
                return "BOOT_FAULT"
        elif context == "LOADER":
            if S == LOADER_HVS_S_P0:
                return "LOAD_P0"
            elif S == LOADER_HVS_S_P1:
                return "LOAD_P1"
            elif S == LOADER_HVS_S_P2:
                return "LOAD_P2"
            elif S == LOADER_HVS_S_P3:
                return "LOAD_P3"
            elif S == LOADER_HVS_S_FAULT:
                return "LOAD_FAULT"
        return f"{context}_S{S}"


# ==============================================================================
# ENV_BBUF Parameters
# ==============================================================================

class ENV_BBUF:
    """Environment BRAM Buffer parameters.

    Four 4KB buffers for configuration data.
    """

    COUNT = 4
    SIZE_BYTES = 4096
    WORDS = 1024       # 4096 / 4
    ADDR_WIDTH = 10    # log2(1024)
    DATA_WIDTH = 32


# ==============================================================================
# CRC-16-CCITT Parameters
# ==============================================================================

class CRC16:
    """CRC-16-CCITT parameters for LOADER validation."""

    POLYNOMIAL = 0x1021
    INIT = 0xFFFF

    @staticmethod
    def compute(data: bytes) -> int:
        """Compute CRC-16-CCITT for a byte sequence.

        Args:
            data: Bytes to compute CRC over

        Returns:
            16-bit CRC value
        """
        crc = CRC16.INIT
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ CRC16.POLYNOMIAL
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc

    @staticmethod
    def compute_buffer(buffer: bytes) -> int:
        """Compute CRC-16 for a 4KB buffer.

        Args:
            buffer: 4096-byte buffer

        Returns:
            16-bit CRC value
        """
        assert len(buffer) == ENV_BBUF.SIZE_BYTES, \
            f"Buffer must be {ENV_BBUF.SIZE_BYTES} bytes, got {len(buffer)}"
        return CRC16.compute(buffer)


# ==============================================================================
# LOADER Protocol Timing
# ==============================================================================

class LOADER_TIMING:
    """Timing constants for LOADER protocol (from LOAD-FSM-spec.md).

    These are intentionally slow for reliability over speed.
    """

    T_STROBE_MS = 1      # Strobe pulse width
    T_SETUP_MS = 10      # Delay after setup strobe
    T_WORD_MS = 1        # Delay between data words
    T_VALIDATE_MS = 10   # Delay for CRC validation

    # Total transfer time for 4KB buffer
    # = T_SETUP + (1024 * (T_STROBE + T_WORD)) + T_VALIDATE
    # = 10 + (1024 * 2) + 10 = ~2058ms per buffer
    T_BUFFER_APPROX_MS = 2100


# ==============================================================================
# Helper Functions
# ==============================================================================

def build_loader_cr0(
    num_buffers: int = 1,
    strobe: bool = False,
    ret: bool = False,
) -> int:
    """Build CR0 value for LOADER operations.

    Args:
        num_buffers: Number of buffers to load (1-4)
        strobe: Set strobe bit high
        ret: Set return bit (exit LOADER)

    Returns:
        CR0 value with RUN + RUNL + specified bits
    """
    value = CMD.RUNL  # Start with RUN + L
    value |= LOADER_CTRL.encode_bufcnt(num_buffers)
    if strobe:
        value |= LOADER_CTRL.STROBE_MASK
    if ret:
        value |= RET.MASK
    return value


def is_run_active(cr0: int) -> bool:
    """Check if all RUN gate bits are set."""
    return (cr0 & RUN.GATE_MASK) == RUN.GATE_MASK


def get_module_select(cr0: int) -> str:
    """Get which module is selected from CR0.

    Returns:
        One of: 'PROG', 'BIOS', 'LOADER', 'RESET', 'NONE', 'MULTIPLE'
    """
    sel_bits = (cr0 >> SEL.RESET_BIT) & 0xF  # Bits 28:25

    count = bin(sel_bits).count('1')
    if count == 0:
        return 'NONE'
    if count > 1:
        return 'MULTIPLE'

    if sel_bits & 0x8:
        return 'PROG'
    if sel_bits & 0x4:
        return 'BIOS'
    if sel_bits & 0x2:
        return 'LOADER'
    if sel_bits & 0x1:
        return 'RESET'

    return 'NONE'


# ==============================================================================
# Quick Reference
# ==============================================================================

if __name__ == "__main__":
    """Print quick reference when run as script."""
    print("BOOT Subsystem Constants - Quick Reference")
    print("=" * 60)

    print("\nCR0 Bit Layout (BOOT):")
    print("  [31]   R (Ready)    ─┐")
    print("  [30]   U (User)      ├── RUN gate (must all be '1')")
    print("  [29]   N (clkEn)    ─┘")
    print("  [28]   P (Program)  ─┐")
    print("  [27]   B (BIOS)      ├── Module select (one only)")
    print("  [26]   L (Loader)    │")
    print("  [25]   R (Reset)    ─┘")
    print("  [24]   RET          ─── Return to BOOT_P1")
    print("  [23:22] Buffer count (LOADER)")
    print("  [21]   Strobe (LOADER)")

    print("\nCommand Values:")
    for name in ['RUN', 'RUNP', 'RUNB', 'RUNL', 'RUNR', 'RET']:
        value = getattr(CMD, name)
        print(f"  CMD.{name:4s} = 0x{value:08X}")

    print("\nBOOT States (HVS @ 0.2V/state):")
    for state in BOOTState:
        if state == BOOTState.FAULT:
            print(f"  {state.name:12s} = {state.value:2d} (Negative voltage)")
        else:
            voltage = state * 0.2
            print(f"  {state.name:12s} = {state.value:2d} ({voltage:.1f}V)")

    print("\nLOADER States:")
    for state in LOADState:
        if state == LOADState.FAULT:
            print(f"  LOAD_{state.name:6s} = {state.value:2d} (Negative voltage)")
        else:
            voltage = state * 0.2
            print(f"  LOAD_{state.name:6s} = {state.value:2d} ({voltage:.1f}V)")

    print("\nENV_BBUF:")
    print(f"  Count: {ENV_BBUF.COUNT} buffers")
    print(f"  Size:  {ENV_BBUF.SIZE_BYTES} bytes ({ENV_BBUF.WORDS} words)")

    print("\nCRC-16-CCITT:")
    print(f"  Polynomial: 0x{CRC16.POLYNOMIAL:04X}")
    print(f"  Init:       0x{CRC16.INIT:04X}")
