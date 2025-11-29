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
# HVS Parameters (BOOT uses compressed 0.2V steps)
# ==============================================================================

class BOOT_HVS:
    """HVS encoding for BOOT subsystem.

    BOOT uses compressed 0.2V steps (1311 units) to keep all states
    in the 0-1V range. This differs from PROG which uses 0.5V steps.
    """

    # Digital units per state (0.2V steps @ +/-5V full scale)
    UNITS_PER_STATE = 1311

    # Voltage per state
    VOLTS_PER_STATE = 0.2

    # Platform constants (same as PROG)
    V_MAX = 5.0
    DIGITAL_MAX = 32768

    # Expected digital values for BOOT states
    DIGITAL_P0 = 0              # 0.0V
    DIGITAL_P1 = 1311           # 0.2V
    DIGITAL_BIOS_ACTIVE = 2622  # 0.4V
    DIGITAL_LOAD_ACTIVE = 3933  # 0.6V
    DIGITAL_PROG_ACTIVE = 5244  # 0.8V

    # State-to-digital map
    STATE_DIGITAL_MAP: Dict[str, int] = {
        "BOOT_P0": DIGITAL_P0,
        "BOOT_P1": DIGITAL_P1,
        "BIOS_ACTIVE": DIGITAL_BIOS_ACTIVE,
        "LOAD_ACTIVE": DIGITAL_LOAD_ACTIVE,
        "PROG_ACTIVE": DIGITAL_PROG_ACTIVE,
    }

    # State-to-voltage map
    STATE_VOLTAGE_MAP: Dict[str, float] = {
        "BOOT_P0": 0.0,
        "BOOT_P1": 0.2,
        "BIOS_ACTIVE": 0.4,
        "LOAD_ACTIVE": 0.6,
        "PROG_ACTIVE": 0.8,
        "FAULT": -0.2,  # Negative indicates fault
    }

    @staticmethod
    def state_to_digital(state: int, status_offset: int = 0) -> int:
        """Convert FSM state + status offset to digital units."""
        return (state * BOOT_HVS.UNITS_PER_STATE) + status_offset

    @staticmethod
    def digital_to_volts(digital: int) -> float:
        """Convert digital units to voltage (V)."""
        return (digital / BOOT_HVS.DIGITAL_MAX) * BOOT_HVS.V_MAX

    @staticmethod
    def volts_to_digital(voltage: float) -> int:
        """Convert voltage (V) to digital units."""
        return int((voltage / BOOT_HVS.V_MAX) * BOOT_HVS.DIGITAL_MAX)

    @staticmethod
    def decode_state_from_digital(digital: int, tolerance: int = 150) -> str:
        """Decode BOOT state name from digital value."""
        if digital < -tolerance:
            return "FAULT"
        for state_name, expected in BOOT_HVS.STATE_DIGITAL_MAP.items():
            if abs(digital - expected) <= tolerance:
                return state_name
        return f"UNKNOWN({digital})"


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
