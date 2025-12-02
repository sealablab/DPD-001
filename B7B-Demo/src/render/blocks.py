"""Block character rendering for terminal waveforms.

Implements three renderer backends:
- Unicode: 8 levels (3 bits) using space + seventh-block characters
- CP437: 2 levels (1 bit) using space + half-block (DOS compatibility)
- ASCII: 2 levels (1 bit) using space + dash (universal fallback)

The Unicode map uses exactly 8 levels for clean power-of-2 math:
  - 1 row  = 8 levels   = 3 bits
  - 2 rows = 16 levels  = 4 bits
  - 4 rows = 32 levels  = 5 bits
  - 8 rows = 64 levels  = 6 bits
  - 16 rows = 128 levels = 7 bits
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import log2
from typing import List

import numpy as np


# =============================================================================
# Character Maps (AUTHORITATIVE - Clean Power-of-2)
# =============================================================================

# Unicode: 8 levels (3 bits exactly)
# Index 0 = space (empty), indices 1-7 = eighth-blocks
UNICODE_MAP = " ▁▂▃▄▅▆▇"
UNICODE_FILL = "█"
UNICODE_FAULT = "×"

# CP437: 2 levels (1 bit)
CP437_MAP = " ▄"
CP437_FILL = "█"
CP437_FAULT = "×"

# ASCII: 2 levels (1 bit)
ASCII_MAP = " -"
ASCII_FILL = "#"
ASCII_FAULT = "x"


# =============================================================================
# Renderer Base Class
# =============================================================================

@dataclass
class Renderer(ABC):
    """Abstract base class for waveform renderers."""

    @property
    @abstractmethod
    def char_map(self) -> str:
        """Character map for partial blocks (index 0 = empty/space)."""
        pass

    @property
    @abstractmethod
    def fill_char(self) -> str:
        """Character for fully filled blocks."""
        pass

    @property
    @abstractmethod
    def fault_char(self) -> str:
        """Character for fault indication."""
        pass

    @property
    def levels(self) -> int:
        """Number of discrete levels in this renderer."""
        return len(self.char_map)

    @property
    def bits_per_block(self) -> float:
        """Bits of resolution per vertical block."""
        return log2(self.levels) if self.levels > 1 else 0

    def sample_to_char(self, value: int) -> str:
        """Map a value (0 to levels-1) to a character.

        Args:
            value: Value in range [0, levels-1]

        Returns:
            Character from char_map
        """
        clamped = max(0, min(value, len(self.char_map) - 1))
        return self.char_map[clamped]

    def sample_to_column(
        self,
        value: int,
        height: int,
        is_fault: bool = False
    ) -> List[str]:
        """Convert a sample value to a column of characters.

        Args:
            value: 7-bit sample value (0-127)
            height: Number of vertical blocks (1, 2, 4, 8, or 16)
            is_fault: If True, render fault indicator

        Returns:
            List of characters from bottom to top
        """
        if is_fault:
            return [self.fault_char] * height

        # Calculate effective levels for this height
        levels_per_block = self.levels
        effective_levels = height * levels_per_block

        # Scale 0-127 to 0-(effective_levels-1)
        if effective_levels > 1:
            scaled = (value * (effective_levels - 1)) // 127
        else:
            scaled = 0

        # Split into full blocks and partial
        full_count = scaled // levels_per_block
        partial = scaled % levels_per_block

        # Build column bottom-to-top
        column = []
        for row in range(height):
            if row < full_count:
                column.append(self.fill_char)
            elif row == full_count:
                column.append(self.char_map[partial])
            else:
                column.append(" ")

        return column

    def render_waveform(
        self,
        samples: np.ndarray,
        height: int,
        faults: np.ndarray | None = None
    ) -> List[str]:
        """Render a waveform as a list of strings.

        Args:
            samples: Array of 7-bit sample values (0-127)
            height: Number of vertical blocks (1, 2, 4, 8, or 16)
            faults: Optional boolean array indicating fault samples

        Returns:
            List of strings, one per row (top to bottom)
        """
        if faults is None:
            faults = np.zeros(len(samples), dtype=bool)

        # Generate columns
        columns = [
            self.sample_to_column(int(s), height, bool(f))
            for s, f in zip(samples, faults)
        ]

        # Transpose columns to rows and reverse (top row first)
        rows = ["".join(chars) for chars in zip(*columns)]
        return rows[::-1]


# =============================================================================
# Concrete Renderer Implementations
# =============================================================================

class UnicodeRenderer(Renderer):
    """Unicode renderer using eighth-block characters (8 levels = 3 bits)."""

    @property
    def char_map(self) -> str:
        return UNICODE_MAP

    @property
    def fill_char(self) -> str:
        return UNICODE_FILL

    @property
    def fault_char(self) -> str:
        return UNICODE_FAULT


class CP437Renderer(Renderer):
    """CP437 renderer using half-block characters (2 levels = 1 bit)."""

    @property
    def char_map(self) -> str:
        return CP437_MAP

    @property
    def fill_char(self) -> str:
        return CP437_FILL

    @property
    def fault_char(self) -> str:
        return CP437_FAULT


class ASCIIRenderer(Renderer):
    """ASCII renderer using space and dash (2 levels = 1 bit)."""

    @property
    def char_map(self) -> str:
        return ASCII_MAP

    @property
    def fill_char(self) -> str:
        return ASCII_FILL

    @property
    def fault_char(self) -> str:
        return ASCII_FAULT


# =============================================================================
# Convenience Functions (default to Unicode)
# =============================================================================

_default_renderer = UnicodeRenderer()


def sample_to_column(
    value: int,
    height: int,
    is_fault: bool = False
) -> List[str]:
    """Convert a sample value to a column (using Unicode renderer)."""
    return _default_renderer.sample_to_column(value, height, is_fault)


def render_waveform(
    samples: np.ndarray,
    height: int,
    faults: np.ndarray | None = None
) -> List[str]:
    """Render a waveform as a list of strings (using Unicode renderer)."""
    return _default_renderer.render_waveform(samples, height, faults)
