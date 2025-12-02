#!/usr/bin/env python3
"""Standalone waveform widget for terminal display.

A bare-bones text widget that renders waveforms using block characters.
Self-contained with minimal dependencies (numpy only).

Features:
- Three renderer backends: Unicode, CP437, ASCII
- Five height presets: 1, 2, 4, 8, 16 blocks (3-7 bits resolution)
- Interactive keyboard controls

Usage:
    python waveform_widget.py

Controls:
    u/c/a   - Switch renderer (Unicode/CP437/ASCII)
    1-5     - Switch height (1/2/4/8/16 blocks)
    s/t/l/r - Switch waveform (Sine/Triangle/Linear/Random)
    q       - Quit
"""

import sys
import tty
import termios
from dataclasses import dataclass
from math import log2
from typing import List, Tuple

import numpy as np


# =============================================================================
# Character Maps
# =============================================================================

CHAR_MAPS = {
    "unicode": {
        "map": "_▁▂▃▄▅▆▇█",  # 9 levels (3 bits + overflow)
        "fill": "█",
        "fault": "×",
        "name": "Unicode",
    },
    "cp437": {
        "map": "_▄█",  # 3 levels
        "fill": "█",
        "fault": "×",
        "name": "CP437",
    },
    "ascii": {
        "map": "_-`",  # 3 levels
        "fill": "#",
        "fault": "x",
        "name": "ASCII",
    },
}

# Height presets (power of 2)
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

def generate_sine(length: int = 64) -> np.ndarray:
    """Generate one period of sine wave, scaled 0-127."""
    t = np.linspace(0, 2 * np.pi, length, endpoint=False)
    wave = 63.5 + 63.5 * np.sin(t)
    return np.round(wave).astype(np.uint8)


def generate_triangle(length: int = 64) -> np.ndarray:
    """Generate triangle wave, scaled 0-127."""
    half = length // 2
    up = np.linspace(0, 127, half, dtype=np.uint8)
    down = np.linspace(127, 0, length - half, dtype=np.uint8)
    return np.concatenate([up, down])


def generate_linear(length: int = 64) -> np.ndarray:
    """Generate linear ramp 0-127."""
    return np.linspace(0, 127, length, dtype=np.uint8)


def generate_random(length: int = 64) -> np.ndarray:
    """Generate random samples 0-127."""
    return np.random.randint(0, 128, length, dtype=np.uint8)


WAVEFORMS = {
    "s": ("Sine", generate_sine),
    "t": ("Triangle", generate_triangle),
    "l": ("Linear", generate_linear),
    "r": ("Random", generate_random),
}


# =============================================================================
# Rendering Engine
# =============================================================================

def sample_to_column_unicode(value: int, height: int, char_map: str, fill_char: str) -> List[str]:
    """Convert a sample to a column for Unicode (9-level) renderer."""
    # Determine bits used based on height
    row_bits = int(log2(height)) if height > 1 else 0
    bits_used = 3 + row_bits

    # Scale sample to available resolution
    if bits_used >= 7:
        scaled = value
    else:
        scaled = value >> (7 - bits_used)

    # Split into full blocks and partial
    partial = scaled & 0b111
    full_count = scaled >> 3

    # Build column bottom-to-top
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
    """Convert a sample to a column for reduced (3-level) renderers."""
    levels_per_block = len(char_map) - 1  # 2 for CP437/ASCII
    max_scaled = height * levels_per_block

    # Map 0-127 to 0-max_scaled
    mapped = (value * max_scaled) // 127
    partial = mapped % (levels_per_block + 1)
    full_count = mapped // (levels_per_block + 1)

    # Clamp partial to valid range
    partial = min(partial, len(char_map) - 1)

    # Build column bottom-to-top
    column = []
    for row in range(height):
        if row < full_count:
            column.append(fill_char)
        elif row == full_count:
            column.append(char_map[partial])
        else:
            column.append(" ")

    return column


def render_waveform(
    samples: np.ndarray,
    height: int,
    renderer_key: str
) -> List[str]:
    """Render waveform as list of strings (top to bottom)."""
    config = CHAR_MAPS[renderer_key]
    char_map = config["map"]
    fill_char = config["fill"]

    # Choose rendering function based on character map size
    if len(char_map) == 9:
        render_fn = sample_to_column_unicode
    else:
        render_fn = sample_to_column_reduced

    # Generate columns
    columns = [
        render_fn(int(s), height, char_map, fill_char)
        for s in samples
    ]

    # Transpose and reverse (top row first)
    rows = ["".join(chars) for chars in zip(*columns)]
    return rows[::-1]


# =============================================================================
# Terminal Utilities
# =============================================================================

# ANSI escape codes
CLEAR = "\033[2J"
HOME = "\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def get_char() -> str:
    """Read a single character from stdin (non-blocking style)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


# =============================================================================
# Widget State
# =============================================================================

@dataclass
class WidgetState:
    """Current state of the waveform widget."""
    renderer: str = "unicode"
    height_preset: int = 3  # Default to 4 rows (5-bit)
    waveform: str = "s"     # Sine
    width: int = 64         # Samples to display

    @property
    def height(self) -> int:
        return HEIGHT_PRESETS[self.height_preset]["height"]

    @property
    def bits(self) -> int:
        return HEIGHT_PRESETS[self.height_preset]["bits"]

    @property
    def height_label(self) -> str:
        return HEIGHT_PRESETS[self.height_preset]["label"]

    @property
    def renderer_name(self) -> str:
        return CHAR_MAPS[self.renderer]["name"]

    @property
    def waveform_name(self) -> str:
        return WAVEFORMS[self.waveform][0]

    def get_samples(self) -> np.ndarray:
        _, generator = WAVEFORMS[self.waveform]
        return generator(self.width)


# =============================================================================
# Widget Display
# =============================================================================

def render_widget(state: WidgetState) -> str:
    """Render the complete widget as a string."""
    samples = state.get_samples()
    waveform_rows = render_waveform(samples, state.height, state.renderer)

    lines = []

    # Header
    lines.append("=" * 72)
    lines.append(f"{BOLD} Waveform Widget{RESET}")
    lines.append("=" * 72)
    lines.append("")

    # Status line
    lines.append(f" Renderer: {BOLD}{state.renderer_name}{RESET}  |  "
                 f"Height: {BOLD}{state.height_label}{RESET}  |  "
                 f"Wave: {BOLD}{state.waveform_name}{RESET}")
    lines.append("")

    # Character map display
    config = CHAR_MAPS[state.renderer]
    lines.append(f" Char map: {DIM}{config['map']}{RESET}  Fill: {config['fill']}  Fault: {config['fault']}")
    lines.append("")

    # Waveform display
    lines.append("-" * 72)
    for row in waveform_rows:
        lines.append(" " + row)
    lines.append("-" * 72)
    lines.append("")

    # Controls
    lines.append(f"{DIM} Controls:{RESET}")
    lines.append(f"   {BOLD}u/c/a{RESET} - Renderer (Unicode/CP437/ASCII)")
    lines.append(f"   {BOLD}1-5{RESET}   - Height (1/2/4/8/16 rows)")
    lines.append(f"   {BOLD}s/t/l/r{RESET} - Waveform (Sine/Triangle/Linear/Random)")
    lines.append(f"   {BOLD}q{RESET}     - Quit")
    lines.append("")

    return "\n".join(lines)


def run_widget():
    """Main widget loop."""
    state = WidgetState()

    print(HIDE_CURSOR, end="", flush=True)

    try:
        while True:
            # Render and display
            output = render_widget(state)
            print(HOME + CLEAR + output, end="", flush=True)

            # Wait for input
            key = get_char()

            # Handle input
            if key == "q" or key == "\x03":  # q or Ctrl+C
                break
            elif key == "u":
                state.renderer = "unicode"
            elif key == "c":
                state.renderer = "cp437"
            elif key == "a":
                state.renderer = "ascii"
            elif key in "12345":
                state.height_preset = int(key)
            elif key in "stlr":
                state.waveform = key

    finally:
        print(SHOW_CURSOR, end="", flush=True)
        print(CLEAR + HOME, end="", flush=True)


# =============================================================================
# Non-interactive Mode
# =============================================================================

def print_static(
    renderer: str = "unicode",
    height_preset: int = 3,
    waveform: str = "s"
):
    """Print a static waveform (non-interactive)."""
    state = WidgetState(
        renderer=renderer,
        height_preset=height_preset,
        waveform=waveform
    )
    print(render_widget(state))


def print_all_combinations():
    """Print all renderer/height combinations for comparison."""
    for renderer in ["unicode", "cp437", "ascii"]:
        print(f"\n{'='*72}")
        print(f" Renderer: {CHAR_MAPS[renderer]['name']}")
        print(f"{'='*72}")

        for preset in [1, 2, 3]:  # Show 1, 2, 4 rows for brevity
            state = WidgetState(renderer=renderer, height_preset=preset)
            samples = state.get_samples()
            rows = render_waveform(samples, state.height, renderer)

            print(f"\n {state.height_label}:")
            for row in rows:
                print(f"   {row}")


# =============================================================================
# Main
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Waveform Widget")
    parser.add_argument(
        "--static", action="store_true",
        help="Print static output (non-interactive)"
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Print all renderer/height combinations"
    )
    parser.add_argument(
        "-r", "--renderer",
        choices=["unicode", "cp437", "ascii"],
        default="unicode",
        help="Renderer for static mode"
    )
    parser.add_argument(
        "-p", "--preset",
        type=int, choices=[1, 2, 3, 4, 5],
        default=3,
        help="Height preset (1-5) for static mode",
        dest="height_preset"
    )
    parser.add_argument(
        "-w", "--wave",
        choices=["s", "t", "l", "r"],
        default="s",
        help="Waveform: s=sine, t=triangle, l=linear, r=random"
    )

    # Parse args manually to avoid conflict with -h
    args, _ = parser.parse_known_args()

    if args.compare:
        print_all_combinations()
    elif args.static:
        print_static(args.renderer, args.height_preset, args.wave)
    else:
        run_widget()


if __name__ == "__main__":
    main()
