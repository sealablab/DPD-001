"""Block character rendering for terminal waveforms.

Implements three renderer backends:
- Unicode: 9 levels using eighth-block characters
- CP437: 3 levels using half-blocks (DOS compatibility)
- ASCII: 3 levels using _-` (universal fallback)

The core insight: 3 LSBs map directly to Unicode eighth-blocks.
Higher bit depths use additional vertical rows.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import log2
from typing import List

import numpy as np


# =============================================================================
# Character Maps (from REQUIREMENTS.md - AUTHORITATIVE)
# =============================================================================

# Unicode: 9 levels (3 bits + overflow)
# Index 0 = baseline, indices 1-7 = partial blocks, index 8 = full
UNICODE_MAP = "_▁▂▃▄▅▆▇█"
UNICODE_FILL = "█"
UNICODE_FAULT = "×"

# CP437: 3 levels (1.5 bits)
CP437_MAP = "_▄█"
CP437_FILL = "█"
CP437_FAULT = "×"

# ASCII: 3 levels using vertical position metaphor
ASCII_MAP = "_-`"
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
        """Character map for partial blocks (including zero level)."""
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
    def bits_per_block(self) -> int:
        """Bits of resolution per vertical block (before overflow)."""
        # Unicode has 9 levels (0-8), but 8 partial levels = 3 bits
        # CP437/ASCII have 3 levels = ~1.5 bits
        if self.levels == 9:
            return 3
        elif self.levels == 3:
            return 1  # Conservative: 2 transitions = 1 bit
        else:
            return int(log2(self.levels - 1)) if self.levels > 1 else 0

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

        # Determine how many bits we're using based on height
        # height = 2^(bits_used - 3) for Unicode
        # So bits_used = 3 + log2(height)
        row_bits = int(log2(height)) if height > 1 else 0
        bits_used = 3 + row_bits

        # Scale sample to available resolution
        # For Unicode: value >> (7 - bits_used) gives us the scaled value
        if bits_used >= 7:
            scaled = value
        else:
            scaled = value >> (7 - bits_used)

        # For Unicode (9 levels = 3 bits + overflow)
        if self.levels == 9:
            # Split into full blocks (upper bits) and partial (lower 3 bits)
            partial = scaled & 0b111
            full_count = scaled >> 3
        else:
            # For CP437/ASCII (3 levels)
            # We need to map to our reduced levels
            # Scale the value to 0-2 range per block
            levels_per_block = self.levels - 1  # 2 for CP437/ASCII
            max_scaled = height * levels_per_block
            # Map 0-127 to 0-max_scaled
            mapped = (value * max_scaled) // 127
            partial = mapped % levels_per_block
            full_count = mapped // levels_per_block
            # Adjust: if partial is 0 and we have full blocks, show the full char
            if full_count > 0 and partial == 0:
                # Show partial as the max level for that block
                partial = 0  # baseline shows underscore

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
    """Unicode renderer using eighth-block characters."""

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
    """CP437 renderer using half-block characters."""

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
    """ASCII renderer using _-` characters."""

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
