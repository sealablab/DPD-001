#!/usr/bin/env python3
"""Terminal rasterization pipeline: Canvas → RenderWindow.

This module implements a terminal-native graphics abstraction:

  Canvas          High-resolution internal buffer (samples × bits)
       ↓
  Rasterize       Resample horizontally, quantize vertically
       ↓
  RenderWindow    Character grid with specific BpB depth

The key insight: "Bits per Block" (BpB) is the terminal equivalent of
"bits per pixel" in conventional graphics. It determines the vertical
quantization resolution:

  BpB    Levels   Character Set              Encoding
  ───────────────────────────────────────────────────────
  1.0    2        (spc)1                     Binary (1-bit uber-fallback)
  2.0    4        (spc).-=  or  (spc)░▒▓     ASCII / CP437
  3.0    8        (spc)▁▂▃▄▅▆▇  + █(fill)    Unicode (clean 3-bit)

Clean power-of-2 math at every level:
  - Binary:  1 bit  → 2 levels per block
  - ASCII:   2 bits → 4 levels per block
  - CP437:   2 bits → 4 levels per block
  - Unicode: 3 bits → 8 levels per block

Usage:
    canvas = Canvas(width=128, height=128)  # Internal resolution
    canvas.plot_sine()

    window = RenderWindow(cols=64, rows=4, bpb=3.0)  # Unicode, 4 rows
    window.rasterize(canvas)

    for row in window.get_rows():
        print(row)
"""

from dataclasses import dataclass, field
from enum import Enum
from math import log2
from typing import List, Tuple, Callable, Optional
import numpy as np


# =============================================================================
# Bits-per-Block Definitions
# =============================================================================

class CharacterSet(Enum):
    """Available character sets with their BpB depth."""
    BINARY = "binary"    # 1 BpB (2 levels)
    ASCII = "ascii"      # 2 BpB (4 levels)
    CP437 = "cp437"      # 2 BpB (4 levels)
    UNICODE = "unicode"  # 3 BpB (8 levels)


@dataclass(frozen=True)
class BpBProfile:
    """Bits-per-block profile defining character mapping."""
    name: str
    bpb: float                    # Effective bits per block
    char_map: str                 # Characters for partial blocks (index 0 = empty)
    fill_char: str                # Character for fully filled blocks
    fault_char: str               # Character for fault indication

    @property
    def levels(self) -> int:
        """Number of discrete levels (including zero)."""
        return len(self.char_map)

    def quantize(self, value: float) -> int:
        """Quantize a 0.0-1.0 value to character index."""
        # Map [0, 1] to [0, levels-1]
        idx = int(value * (self.levels - 1) + 0.5)
        return max(0, min(idx, self.levels - 1))

    def get_char(self, index: int) -> str:
        """Get character for quantized index."""
        clamped = max(0, min(index, len(self.char_map) - 1))
        return self.char_map[clamped]


# Pre-defined BpB profiles (all clean powers of 2)
BPB_PROFILES = {
    CharacterSet.BINARY: BpBProfile(
        name="Binary",
        bpb=1.0,
        char_map=" 1",              # 2 levels (1 bit): space + '1'
        fill_char="1",              # '1' for stacked rows
        fault_char="x",
    ),
    CharacterSet.ASCII: BpBProfile(
        name="ASCII",
        bpb=2.0,
        char_map=" .-=",            # 4 levels (2 bits): space, light, medium, heavy
        fill_char="#",              # Hash for stacked rows
        fault_char="x",
    ),
    CharacterSet.CP437: BpBProfile(
        name="CP437",
        bpb=2.0,
        char_map=" ░▒▓",            # 4 levels (2 bits): space, light, medium, dark shade
        fill_char="█",              # Full block for stacked rows
        fault_char="×",
    ),
    CharacterSet.UNICODE: BpBProfile(
        name="Unicode",
        bpb=3.0,
        char_map=" ▁▂▃▄▅▆▇",        # 8 levels (3 bits): space + 7 eighth-blocks
        fill_char="█",              # Full block for stacked rows
        fault_char="×",
    ),
}


# =============================================================================
# Canvas: High-Resolution Internal Buffer
# =============================================================================

@dataclass
class Canvas:
    """High-resolution internal buffer for waveform data.

    The canvas stores normalized float values [0.0, 1.0] at full resolution.
    This is the "source" in the rasterization pipeline.

    Coordinates:
        - x: horizontal position (0 to width-1), left to right
        - y: vertical position (0 to height-1), bottom to top

    The canvas can hold arbitrary 2D data, but is optimized for waveforms
    where each x column has a single y value (1D function).
    """
    width: int = 128
    height: int = 128

    # Internal storage: 2D array of normalized values [0, 1]
    # data[y][x] where y=0 is bottom
    data: np.ndarray = field(init=False)

    # For 1D waveforms, we also track the "curve"
    waveform: np.ndarray = field(init=False)

    def __post_init__(self):
        """Initialize empty canvas."""
        self.data = np.zeros((self.height, self.width), dtype=np.float32)
        self.waveform = np.zeros(self.width, dtype=np.float32)

    def clear(self, value: float = 0.0):
        """Clear canvas to a uniform value."""
        self.data.fill(value)
        self.waveform.fill(value)

    def set_pixel(self, x: int, y: int, value: float = 1.0):
        """Set a single pixel (bounds-checked)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.data[y, x] = np.clip(value, 0.0, 1.0)

    def get_pixel(self, x: int, y: int) -> float:
        """Get pixel value (0.0 if out of bounds)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return float(self.data[y, x])
        return 0.0

    def plot_waveform(self, samples: np.ndarray):
        """Plot a 1D waveform onto the canvas.

        Args:
            samples: Array of values [0.0, 1.0] with length matching canvas width
        """
        # Resample if needed
        if len(samples) != self.width:
            indices = np.linspace(0, len(samples) - 1, self.width)
            samples = np.interp(indices, np.arange(len(samples)), samples)

        self.waveform = np.clip(samples, 0.0, 1.0).astype(np.float32)

        # Also fill the 2D data for potential future use
        self.data.fill(0.0)
        for x, val in enumerate(self.waveform):
            y = int(val * (self.height - 1))
            self.data[y, x] = 1.0

    def plot_sine(self, periods: float = 1.0, phase: float = 0.0):
        """Plot a sine wave."""
        t = np.linspace(phase, phase + 2 * np.pi * periods, self.width, endpoint=False)
        samples = 0.5 + 0.5 * np.sin(t)
        self.plot_waveform(samples)

    def plot_cosine(self, periods: float = 1.0, phase: float = 0.0):
        """Plot a cosine wave."""
        t = np.linspace(phase, phase + 2 * np.pi * periods, self.width, endpoint=False)
        samples = 0.5 + 0.5 * np.cos(t)
        self.plot_waveform(samples)

    def plot_triangle(self, periods: float = 1.0):
        """Plot a triangle wave."""
        samples = np.abs(2 * (np.linspace(0, periods, self.width) % 1) - 1)
        self.plot_waveform(samples)

    def plot_sawtooth(self, periods: float = 1.0):
        """Plot a sawtooth wave."""
        samples = np.linspace(0, periods, self.width) % 1
        self.plot_waveform(samples)

    def resample_horizontal(self, target_width: int) -> np.ndarray:
        """Resample waveform to target width."""
        if target_width == self.width:
            return self.waveform.copy()

        indices = np.linspace(0, self.width - 1, target_width)
        return np.interp(indices, np.arange(self.width), self.waveform)


# =============================================================================
# RenderWindow: Character Grid with BpB Depth
# =============================================================================

@dataclass
class RenderWindow:
    """Terminal viewport with specific dimensions and BpB depth.

    The RenderWindow is the "destination" in the rasterization pipeline.
    It holds a character grid that can be output to the terminal.

    Parameters:
        cols: Number of character columns
        rows: Number of character rows (vertical resolution)
        charset: Character set determining BpB depth

    Effective vertical resolution = rows × BpB levels
    """
    cols: int = 64
    rows: int = 4
    charset: CharacterSet = CharacterSet.UNICODE

    # Double-buffered character grids
    front: List[List[str]] = field(init=False)
    back: List[List[str]] = field(init=False)

    # Swap counter for debugging
    swap_count: int = field(default=0, init=False)

    def __post_init__(self):
        """Initialize buffers."""
        self.front = self._make_buffer()
        self.back = self._make_buffer()

    def _make_buffer(self) -> List[List[str]]:
        """Create an empty character buffer."""
        return [[" "] * self.cols for _ in range(self.rows)]

    @property
    def profile(self) -> BpBProfile:
        """Get the BpB profile for current charset."""
        return BPB_PROFILES[self.charset]

    @property
    def bpb(self) -> float:
        """Bits per block for current charset."""
        return self.profile.bpb

    @property
    def levels_per_block(self) -> int:
        """Discrete levels per character block."""
        return self.profile.levels

    @property
    def effective_levels(self) -> int:
        """Total vertical levels (rows × levels_per_block)."""
        return self.rows * self.profile.levels

    @property
    def effective_bits(self) -> float:
        """Effective vertical bit depth."""
        return log2(self.effective_levels) if self.effective_levels > 1 else 0

    def clear_back(self, fill_char: str = " "):
        """Clear the back buffer."""
        for r in range(self.rows):
            for c in range(self.cols):
                self.back[r][c] = fill_char

    def rasterize(self, canvas: Canvas):
        """Rasterize canvas onto the back buffer.

        This is the core of the pipeline:
        1. Resample canvas horizontally to match cols
        2. Quantize each sample vertically to rows × BpB levels
        3. Convert to character representation
        """
        # Step 1: Horizontal resampling
        samples = canvas.resample_horizontal(self.cols)

        # Step 2-3: Vertical quantization and character mapping
        profile = self.profile
        levels = self.effective_levels

        self.clear_back()

        for col, sample in enumerate(samples):
            # Quantize to [0, effective_levels - 1]
            quantized = int(sample * (levels - 1) + 0.5)
            quantized = max(0, min(quantized, levels - 1))

            # Convert to (full_blocks, partial_level)
            # levels_per_block = number of distinct levels per character cell
            levels_per_block = profile.levels

            full_blocks = quantized // levels_per_block
            partial = quantized % levels_per_block

            # Fill column from bottom
            for row in range(self.rows):
                # row 0 is displayed at bottom (rows-1 in buffer)
                buf_row = self.rows - 1 - row

                if row < full_blocks:
                    self.back[buf_row][col] = profile.fill_char
                elif row == full_blocks:
                    self.back[buf_row][col] = profile.get_char(partial)
                else:
                    self.back[buf_row][col] = " "

    def swap(self) -> int:
        """Swap front and back buffers.

        Returns:
            Number of cells that changed
        """
        # Count differences
        diff_count = sum(
            1 for r in range(self.rows) for c in range(self.cols)
            if self.front[r][c] != self.back[r][c]
        )

        # Swap
        self.front, self.back = self.back, self.front
        self.swap_count += 1

        return diff_count

    def get_rows(self) -> List[str]:
        """Get front buffer as list of strings (top to bottom)."""
        return ["".join(row) for row in self.front]

    def get_pending_rows(self) -> List[str]:
        """Get back buffer as list of strings."""
        return ["".join(row) for row in self.back]

    def resize(self, cols: int = None, rows: int = None):
        """Resize the render window."""
        if cols is not None:
            self.cols = cols
        if rows is not None:
            self.rows = rows
        self.front = self._make_buffer()
        self.back = self._make_buffer()


# =============================================================================
# Pipeline Helper
# =============================================================================

@dataclass
class RasterPipeline:
    """Complete rasterization pipeline: Canvas → RenderWindow.

    Convenience class that manages the full pipeline.
    """
    canvas_width: int = 128
    canvas_height: int = 128
    window_cols: int = 64
    window_rows: int = 4
    charset: CharacterSet = CharacterSet.UNICODE

    canvas: Canvas = field(init=False)
    window: RenderWindow = field(init=False)

    def __post_init__(self):
        self.canvas = Canvas(self.canvas_width, self.canvas_height)
        self.window = RenderWindow(self.window_cols, self.window_rows, self.charset)

    def plot(self, waveform_type: str = "sine", **kwargs):
        """Plot a waveform to the canvas."""
        if waveform_type == "sine":
            self.canvas.plot_sine(**kwargs)
        elif waveform_type == "cosine":
            self.canvas.plot_cosine(**kwargs)
        elif waveform_type == "triangle":
            self.canvas.plot_triangle(**kwargs)
        elif waveform_type == "sawtooth":
            self.canvas.plot_sawtooth(**kwargs)

    def render(self) -> List[str]:
        """Rasterize canvas to window and return rows."""
        self.window.rasterize(self.canvas)
        self.window.swap()
        return self.window.get_rows()

    def set_charset(self, charset: CharacterSet):
        """Change character set."""
        self.window.charset = charset

    def set_window_size(self, cols: int = None, rows: int = None):
        """Resize render window."""
        self.window.resize(cols, rows)


# =============================================================================
# Demo
# =============================================================================

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def demo_pipeline():
    """Demonstrate the Canvas → RenderWindow pipeline."""
    print(f"\n{BOLD}Canvas → RenderWindow Pipeline Demo{RESET}")
    print("=" * 72)

    # Create high-res canvas
    canvas = Canvas(width=128, height=128)
    canvas.plot_sine()

    print(f"\n{DIM}Canvas: {canvas.width}×{canvas.height} (internal resolution){RESET}")

    # Render to different window configurations
    configs = [
        (64, 1, CharacterSet.UNICODE, "64×1 Unicode (3 BpB)"),
        (64, 2, CharacterSet.UNICODE, "64×2 Unicode (3 BpB)"),
        (64, 4, CharacterSet.UNICODE, "64×4 Unicode (3 BpB)"),
        (64, 4, CharacterSet.CP437, "64×4 CP437 (2 BpB)"),
        (64, 4, CharacterSet.ASCII, "64×4 ASCII (2 BpB)"),
        (64, 4, CharacterSet.BINARY, "64×4 Binary (1 BpB)"),
        (32, 2, CharacterSet.UNICODE, "32×2 Unicode (downscaled)"),
    ]

    for cols, rows, charset, label in configs:
        window = RenderWindow(cols, rows, charset)
        window.rasterize(canvas)
        window.swap()

        profile = window.profile
        print(f"\n{BOLD}{label}{RESET}")
        print(f"  Effective: {window.effective_levels} levels ({window.effective_bits:.1f} bits)")
        print(f"  Char map: {profile.char_map}")
        for row in window.get_rows():
            print(f"  {row}")


def demo_resolution_ladder():
    """Show the same waveform at increasing effective resolution."""
    print(f"\n{BOLD}Resolution Ladder (same canvas, different windows){RESET}")
    print("=" * 72)

    canvas = Canvas(width=64, height=128)
    canvas.plot_sine()

    # Show Unicode at increasing row counts
    print(f"\n{DIM}Unicode (3 BpB) at increasing row counts:{RESET}")

    for rows in [1, 2, 4, 8]:
        window = RenderWindow(cols=64, rows=rows, charset=CharacterSet.UNICODE)
        window.rasterize(canvas)
        window.swap()

        print(f"\n  {rows} row(s) → {window.effective_levels} levels ({window.effective_bits:.1f} effective bits):")
        for row in window.get_rows():
            print(f"    {row}")


def demo_charset_comparison():
    """Compare character sets at same window size."""
    print(f"\n{BOLD}Character Set Comparison (same window size){RESET}")
    print("=" * 72)

    canvas = Canvas(width=64, height=128)
    canvas.plot_sine()

    for charset in [CharacterSet.UNICODE, CharacterSet.CP437, CharacterSet.ASCII, CharacterSet.BINARY]:
        window = RenderWindow(cols=64, rows=4, charset=charset)
        window.rasterize(canvas)
        window.swap()

        profile = window.profile
        print(f"\n{BOLD}{profile.name}{RESET} ({profile.bpb} BpB)")
        print(f"  Map: {profile.char_map}  Fill: {profile.fill_char}")
        print(f"  Effective: {window.effective_levels} levels")
        for row in window.get_rows():
            print(f"  {row}")


def demo_downscaling():
    """Demonstrate downscaling from canvas to window."""
    print(f"\n{BOLD}Downscaling Demo{RESET}")
    print("=" * 72)

    # Large canvas
    canvas = Canvas(width=256, height=256)
    canvas.plot_sine(periods=2)  # Two periods

    print(f"\n{DIM}Canvas: {canvas.width}×{canvas.height} (2 sine periods){RESET}")

    # Various window sizes
    sizes = [(64, 4), (32, 2), (16, 1)]

    for cols, rows in sizes:
        window = RenderWindow(cols, rows, CharacterSet.UNICODE)
        window.rasterize(canvas)
        window.swap()

        print(f"\n  Window {cols}×{rows}:")
        for row in window.get_rows():
            print(f"    {row}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Terminal Rasterization Pipeline")
    parser.add_argument("--pipeline", action="store_true", help="Pipeline demo")
    parser.add_argument("--resolution", action="store_true", help="Resolution ladder demo")
    parser.add_argument("--charset", action="store_true", help="Charset comparison demo")
    parser.add_argument("--downscale", action="store_true", help="Downscaling demo")
    parser.add_argument("--all", action="store_true", help="Run all demos")

    args = parser.parse_args()

    if args.all or not any([args.pipeline, args.resolution, args.charset, args.downscale]):
        demo_pipeline()
        demo_resolution_ladder()
        demo_charset_comparison()
        demo_downscaling()
    else:
        if args.pipeline:
            demo_pipeline()
        if args.resolution:
            demo_resolution_ladder()
        if args.charset:
            demo_charset_comparison()
        if args.downscale:
            demo_downscaling()

    print()


if __name__ == "__main__":
    main()
