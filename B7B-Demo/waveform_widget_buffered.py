#!/usr/bin/env python3
"""Waveform widget with double-buffered rendering.

Implements a double-buffer pattern for efficient frame updates:
- Front buffer: current display state
- Back buffer: next frame being prepared
- Swap: atomic exchange of buffers

This forms the basis for animation primitives without concerning
ourselves with terminal-level rendering/repainting.

Usage:
    python waveform_widget_buffered.py
    python waveform_widget_buffered.py --demo-swap  # Show buffer swapping
"""

import sys
import tty
import termios
from dataclasses import dataclass, field
from math import log2
from typing import List, Optional, Callable
from copy import deepcopy

import numpy as np


# =============================================================================
# Character Maps (same as original widget)
# =============================================================================

CHAR_MAPS = {
    "unicode": {
        "map": "_▁▂▃▄▅▆▇█",
        "fill": "█",
        "fault": "×",
        "name": "Unicode",
    },
    "cp437": {
        "map": "_▄█",
        "fill": "█",
        "fault": "×",
        "name": "CP437",
    },
    "ascii": {
        "map": "_-`",
        "fill": "#",
        "fault": "x",
        "name": "ASCII",
    },
}

HEIGHT_PRESETS = {
    1: {"height": 1, "bits": 3, "label": "1 row (3-bit)"},
    2: {"height": 2, "bits": 4, "label": "2 rows (4-bit)"},
    3: {"height": 4, "bits": 5, "label": "4 rows (5-bit)"},
    4: {"height": 8, "bits": 6, "label": "8 rows (6-bit)"},
    5: {"height": 16, "bits": 7, "label": "16 rows (7-bit)"},
}


# =============================================================================
# Waveform Generation
# =============================================================================

def generate_sine(length: int = 64, phase: float = 0.0) -> np.ndarray:
    """Generate sine wave with optional phase offset."""
    t = np.linspace(phase, phase + 2 * np.pi, length, endpoint=False)
    wave = 63.5 + 63.5 * np.sin(t)
    return np.round(wave).astype(np.uint8)


def generate_triangle(length: int = 64) -> np.ndarray:
    """Generate triangle wave."""
    half = length // 2
    up = np.linspace(0, 127, half, dtype=np.uint8)
    down = np.linspace(127, 0, length - half, dtype=np.uint8)
    return np.concatenate([up, down])


# =============================================================================
# Buffer Classes
# =============================================================================

@dataclass
class CharBuffer:
    """A 2D character buffer representing the waveform display area.

    The buffer is a grid of characters that can be rendered to a terminal.
    Coordinates: (row, col) where row 0 is the top.
    """
    width: int
    height: int
    cells: List[List[str]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize cells if not provided."""
        if not self.cells:
            self.clear()

    def clear(self, fill_char: str = " "):
        """Clear buffer to a fill character."""
        self.cells = [[fill_char] * self.width for _ in range(self.height)]

    def set_cell(self, row: int, col: int, char: str):
        """Set a single cell. Bounds-checked."""
        if 0 <= row < self.height and 0 <= col < self.width:
            self.cells[row][col] = char

    def get_cell(self, row: int, col: int) -> str:
        """Get a single cell. Returns space if out of bounds."""
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.cells[row][col]
        return " "

    def set_column(self, col: int, chars: List[str]):
        """Set an entire column (bottom to top order in input)."""
        # chars[0] is bottom, chars[-1] is top
        # cells[0] is top row, cells[-1] is bottom row
        for i, char in enumerate(chars):
            row = self.height - 1 - i  # Convert bottom-up to top-down
            self.set_cell(row, col, char)

    def get_row(self, row: int) -> str:
        """Get a row as a string."""
        if 0 <= row < self.height:
            return "".join(self.cells[row])
        return " " * self.width

    def get_rows(self) -> List[str]:
        """Get all rows as strings (top to bottom)."""
        return [self.get_row(r) for r in range(self.height)]

    def copy_from(self, other: "CharBuffer"):
        """Copy contents from another buffer (must be same size)."""
        if other.width != self.width or other.height != self.height:
            raise ValueError("Buffer size mismatch")
        for r in range(self.height):
            for c in range(self.width):
                self.cells[r][c] = other.cells[r][c]

    def diff(self, other: "CharBuffer") -> List[tuple]:
        """Return list of (row, col, old_char, new_char) differences."""
        if other.width != self.width or other.height != self.height:
            raise ValueError("Buffer size mismatch")
        diffs = []
        for r in range(self.height):
            for c in range(self.width):
                if self.cells[r][c] != other.cells[r][c]:
                    diffs.append((r, c, self.cells[r][c], other.cells[r][c]))
        return diffs

    def __eq__(self, other: "CharBuffer") -> bool:
        """Check if two buffers have identical contents."""
        if not isinstance(other, CharBuffer):
            return False
        if self.width != other.width or self.height != other.height:
            return False
        return self.cells == other.cells


@dataclass
class DoubleBuffer:
    """Double-buffered character display.

    Manages two CharBuffers:
    - front: The "current" state (what would be displayed)
    - back: The "next" state (being prepared)

    Workflow:
    1. Render to back buffer
    2. Swap when ready
    3. Front now has new content, back can be reused
    """
    width: int
    height: int
    front: CharBuffer = field(init=False)
    back: CharBuffer = field(init=False)
    swap_count: int = field(default=0, init=False)

    def __post_init__(self):
        """Initialize both buffers."""
        self.front = CharBuffer(self.width, self.height)
        self.back = CharBuffer(self.width, self.height)

    def swap(self) -> List[tuple]:
        """Swap front and back buffers.

        Returns:
            List of (row, col, old_char, new_char) differences
            (useful for incremental terminal updates)
        """
        # Calculate diff before swap (for potential incremental updates)
        diffs = self.front.diff(self.back)

        # Swap references (O(1) operation)
        self.front, self.back = self.back, self.front
        self.swap_count += 1

        return diffs

    def clear_back(self, fill_char: str = " "):
        """Clear the back buffer."""
        self.back.clear(fill_char)

    def render_to_back(self, col: int, column_chars: List[str]):
        """Render a column to the back buffer."""
        self.back.set_column(col, column_chars)

    def get_front_rows(self) -> List[str]:
        """Get the front buffer as renderable rows."""
        return self.front.get_rows()

    def get_back_rows(self) -> List[str]:
        """Get the back buffer as renderable rows (for debugging)."""
        return self.back.get_rows()

    def is_dirty(self) -> bool:
        """Check if back buffer differs from front."""
        return self.front != self.back


# =============================================================================
# Rendering Functions
# =============================================================================

def sample_to_column_unicode(value: int, height: int, char_map: str, fill_char: str) -> List[str]:
    """Convert sample to column for Unicode renderer."""
    row_bits = int(log2(height)) if height > 1 else 0
    bits_used = 3 + row_bits

    if bits_used >= 7:
        scaled = value
    else:
        scaled = value >> (7 - bits_used)

    partial = scaled & 0b111
    full_count = scaled >> 3

    column = []
    for row in range(height):
        if row < full_count:
            column.append(fill_char)
        elif row == full_count:
            column.append(char_map[partial])
        else:
            column.append(" ")

    return column


def sample_to_column_reduced(value: int, height: int, char_map: str, fill_char: str) -> List[str]:
    """Convert sample to column for reduced-level renderers."""
    levels_per_block = len(char_map) - 1
    max_scaled = height * levels_per_block

    mapped = (value * max_scaled) // 127
    partial = mapped % (levels_per_block + 1)
    full_count = mapped // (levels_per_block + 1)
    partial = min(partial, len(char_map) - 1)

    column = []
    for row in range(height):
        if row < full_count:
            column.append(fill_char)
        elif row == full_count:
            column.append(char_map[partial])
        else:
            column.append(" ")

    return column


def get_render_fn(renderer_key: str):
    """Get the appropriate rendering function for a renderer."""
    config = CHAR_MAPS[renderer_key]
    if len(config["map"]) == 9:
        return sample_to_column_unicode
    return sample_to_column_reduced


# =============================================================================
# Buffered Widget
# =============================================================================

@dataclass
class BufferedWaveformWidget:
    """Waveform widget with double-buffered rendering.

    The widget maintains:
    - Double buffer for the waveform display area
    - Current renderer configuration
    - Current waveform data
    """
    width: int = 64
    height: int = 4
    renderer: str = "unicode"

    buffer: DoubleBuffer = field(init=False)
    samples: np.ndarray = field(init=False)

    def __post_init__(self):
        """Initialize buffers and default waveform."""
        self.buffer = DoubleBuffer(self.width, self.height)
        self.samples = generate_sine(self.width)
        # Render initial state to both buffers
        self._render_to_buffer(self.buffer.front)
        self._render_to_buffer(self.buffer.back)

    def _render_to_buffer(self, buf: CharBuffer):
        """Render current samples to a specific buffer."""
        config = CHAR_MAPS[self.renderer]
        char_map = config["map"]
        fill_char = config["fill"]
        render_fn = get_render_fn(self.renderer)

        buf.clear()
        for col, sample in enumerate(self.samples):
            if col >= self.width:
                break
            column_chars = render_fn(int(sample), self.height, char_map, fill_char)
            buf.set_column(col, column_chars)

    def set_samples(self, samples: np.ndarray):
        """Set new sample data and render to back buffer."""
        self.samples = samples
        self._render_to_buffer(self.buffer.back)

    def set_renderer(self, renderer: str):
        """Change renderer and re-render to back buffer."""
        if renderer in CHAR_MAPS:
            self.renderer = renderer
            self._render_to_buffer(self.buffer.back)

    def resize(self, width: int = None, height: int = None):
        """Resize the widget (creates new buffers)."""
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height

        self.buffer = DoubleBuffer(self.width, self.height)
        if len(self.samples) != self.width:
            self.samples = generate_sine(self.width)
        self._render_to_buffer(self.buffer.front)
        self._render_to_buffer(self.buffer.back)

    def swap(self) -> List[tuple]:
        """Swap buffers and return diff."""
        return self.buffer.swap()

    def get_display_rows(self) -> List[str]:
        """Get current display (front buffer) as rows."""
        return self.buffer.get_front_rows()

    def get_pending_rows(self) -> List[str]:
        """Get pending display (back buffer) as rows."""
        return self.buffer.get_back_rows()

    def is_dirty(self) -> bool:
        """Check if there's a pending update."""
        return self.buffer.is_dirty()


# =============================================================================
# Demo / Test Functions
# =============================================================================

CLEAR = "\033[2J"
HOME = "\033[H"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
INVERSE = "\033[7m"


def demo_buffer_swap():
    """Demonstrate buffer swapping with visual feedback."""
    print(f"{CLEAR}{HOME}")
    print(f"{BOLD}Double Buffer Swap Demo{RESET}")
    print("=" * 72)
    print()

    # Create widget
    widget = BufferedWaveformWidget(width=48, height=4, renderer="unicode")

    print(f"Initial state (swap_count={widget.buffer.swap_count}):")
    print(f"{DIM}Front buffer:{RESET}")
    for row in widget.get_display_rows():
        print(f"  {row}")
    print()

    # Prepare new frame in back buffer
    print(f"{BOLD}Preparing new frame in back buffer...{RESET}")
    new_samples = generate_sine(48, phase=np.pi/2)  # Phase-shifted sine
    widget.set_samples(new_samples)

    print(f"\nBack buffer (pending):")
    for row in widget.get_pending_rows():
        print(f"  {row}")

    print(f"\nDirty: {widget.is_dirty()}")
    print(f"\nDiff count: {len(widget.buffer.front.diff(widget.buffer.back))} cells changed")

    # Swap
    print(f"\n{BOLD}Swapping buffers...{RESET}")
    diffs = widget.swap()

    print(f"\nAfter swap (swap_count={widget.buffer.swap_count}):")
    print(f"{DIM}Front buffer (now showing new frame):{RESET}")
    for row in widget.get_display_rows():
        print(f"  {row}")

    print(f"\nDirty after swap: {widget.is_dirty()}")
    print(f"Diffs returned: {len(diffs)} cells")
    print()


def demo_incremental_update():
    """Demonstrate incremental updates using diff."""
    print(f"{CLEAR}{HOME}")
    print(f"{BOLD}Incremental Update Demo{RESET}")
    print("=" * 72)
    print()

    widget = BufferedWaveformWidget(width=32, height=2, renderer="unicode")

    print("Frame 0:")
    for row in widget.get_display_rows():
        print(f"  {row}")
    print()

    # Simulate animation: slight phase shift
    for frame in range(1, 4):
        phase = (frame * np.pi) / 8
        new_samples = generate_sine(32, phase=phase)
        widget.set_samples(new_samples)

        # Get diff before swap
        diffs = widget.buffer.front.diff(widget.buffer.back)

        # Swap
        widget.swap()

        print(f"Frame {frame} ({len(diffs)} cells changed):")
        for row in widget.get_display_rows():
            print(f"  {row}")

        # Show which columns changed
        changed_cols = sorted(set(c for _, c, _, _ in diffs))
        print(f"  Changed columns: {changed_cols[:10]}{'...' if len(changed_cols) > 10 else ''}")
        print()


def demo_renderer_switch():
    """Demonstrate renderer switching with double buffering."""
    print(f"{CLEAR}{HOME}")
    print(f"{BOLD}Renderer Switch Demo{RESET}")
    print("=" * 72)
    print()

    widget = BufferedWaveformWidget(width=48, height=4, renderer="unicode")

    renderers = ["unicode", "cp437", "ascii"]

    for renderer in renderers:
        widget.set_renderer(renderer)
        widget.swap()

        config = CHAR_MAPS[renderer]
        print(f"{BOLD}{config['name']}{RESET} (map: {config['map']})")
        for row in widget.get_display_rows():
            print(f"  {row}")
        print()


def interactive_demo():
    """Interactive demo with keyboard controls."""

    def get_char() -> str:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    widget = BufferedWaveformWidget(width=64, height=4, renderer="unicode")
    phase = 0.0

    print("\033[?25l", end="")  # Hide cursor

    try:
        while True:
            # Render current state
            print(f"{HOME}{CLEAR}")
            print(f"{BOLD}Buffered Waveform Widget{RESET}")
            print("=" * 72)
            print(f"Renderer: {BOLD}{CHAR_MAPS[widget.renderer]['name']}{RESET}  |  "
                  f"Height: {BOLD}{widget.height}{RESET}  |  "
                  f"Swaps: {BOLD}{widget.buffer.swap_count}{RESET}  |  "
                  f"Dirty: {BOLD}{widget.is_dirty()}{RESET}")
            print()

            print(f"{DIM}Front buffer:{RESET}")
            for row in widget.get_display_rows():
                print(f" {row}")
            print()

            if widget.is_dirty():
                print(f"{DIM}Back buffer (pending):{RESET}")
                for row in widget.get_pending_rows():
                    print(f" {row}")
                print()

            print("-" * 72)
            print(f" {BOLD}u/c/a{RESET}=renderer  {BOLD}1-5{RESET}=height  "
                  f"{BOLD}n{RESET}=next phase  {BOLD}s{RESET}=swap  {BOLD}q{RESET}=quit")

            key = get_char()

            if key == 'q' or key == '\x03':
                break
            elif key == 'u':
                widget.set_renderer("unicode")
            elif key == 'c':
                widget.set_renderer("cp437")
            elif key == 'a':
                widget.set_renderer("ascii")
            elif key in '12345':
                heights = {1: 1, 2: 2, 3: 4, 4: 8, 5: 16}
                widget.resize(height=heights[int(key)])
            elif key == 'n':
                # Prepare next frame (phase shift)
                phase += np.pi / 8
                widget.set_samples(generate_sine(widget.width, phase))
            elif key == 's':
                # Swap buffers
                widget.swap()

    finally:
        print("\033[?25h", end="")  # Show cursor
        print(f"{CLEAR}{HOME}")


# =============================================================================
# Main
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Buffered Waveform Widget")
    parser.add_argument("--demo-swap", action="store_true",
                        help="Demo buffer swapping")
    parser.add_argument("--demo-incremental", action="store_true",
                        help="Demo incremental updates")
    parser.add_argument("--demo-renderer", action="store_true",
                        help="Demo renderer switching")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive mode")

    args = parser.parse_args()

    if args.demo_swap:
        demo_buffer_swap()
    elif args.demo_incremental:
        demo_incremental_update()
    elif args.demo_renderer:
        demo_renderer_switch()
    elif args.interactive:
        interactive_demo()
    else:
        # Default: show all demos
        demo_buffer_swap()
        input("\nPress Enter for next demo...")
        demo_incremental_update()
        input("\nPress Enter for next demo...")
        demo_renderer_switch()
        print("\nRun with --interactive for keyboard control")


if __name__ == "__main__":
    main()
