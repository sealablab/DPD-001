#!/usr/bin/env python3
"""Static waveform rendering demo.

Demonstrates waveforms rendered at different bits-per-block (3-7).
Each bit depth uses a corresponding vertical height:
  - 3 bits: 1 block high
  - 4 bits: 2 blocks high
  - 5 bits: 4 blocks high
  - 6 bits: 8 blocks high
  - 7 bits: 16 blocks high

Usage:
    python examples/static_demo.py [--renderer unicode|cp437|ascii]
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import numpy as np
from wavetables import generate_sine, generate_cosine, generate_linear, generate_triangle
from render.blocks import UnicodeRenderer, CP437Renderer, ASCIIRenderer


# Mapping: bits_per_block -> height in vertical blocks
BITS_TO_HEIGHT = {
    3: 1,
    4: 2,
    5: 4,
    6: 8,
    7: 16,
}


def get_renderer(name: str):
    """Get renderer by name."""
    renderers = {
        "unicode": UnicodeRenderer(),
        "cp437": CP437Renderer(),
        "ascii": ASCIIRenderer(),
    }
    return renderers.get(name.lower(), UnicodeRenderer())


def render_compact(
    samples: np.ndarray,
    height: int,
    renderer,
    width: int = 64
) -> list[str]:
    """Render waveform, resampling to fit width."""
    if len(samples) != width:
        # Resample to fit width
        indices = np.linspace(0, len(samples) - 1, width, dtype=int)
        samples = samples[indices]
    return renderer.render_waveform(samples, height)


def print_waveform_block(
    title: str,
    samples: np.ndarray,
    bits: int,
    renderer,
    width: int = 64
):
    """Print a titled waveform block."""
    height = BITS_TO_HEIGHT[bits]
    rows = render_compact(samples, height, renderer, width)

    # Header
    print(f"{'─' * width}")
    print(f" {title} ({bits}-bit, {height} row{'s' if height > 1 else ''})")
    print(f"{'─' * width}")

    for row in rows:
        print(row)


def demo_single_waveform(wave_name: str, samples: np.ndarray, renderer, width: int = 64):
    """Show a single waveform at all bit depths."""
    print(f"\n{'═' * width}")
    print(f" {wave_name.upper()} WAVEFORM - All Resolutions")
    print(f"{'═' * width}\n")

    for bits in [3, 4, 5, 6, 7]:
        print_waveform_block(wave_name, samples, bits, renderer, width)
        print()


def demo_all_waveforms_at_bits(bits: int, renderer, width: int = 64):
    """Show all waveforms at a single bit depth."""
    height = BITS_TO_HEIGHT[bits]
    print(f"\n{'═' * width}")
    print(f" ALL WAVEFORMS @ {bits}-bit ({height} row{'s' if height > 1 else ''})")
    print(f"{'═' * width}\n")

    waveforms = [
        ("Linear", generate_linear(128)),
        ("Sine", generate_sine(128)),
        ("Cosine", generate_cosine(128)),
        ("Triangle", generate_triangle(128)),
    ]

    for name, samples in waveforms:
        rows = render_compact(samples, height, renderer, width)
        print(f"{name}:")
        for row in rows:
            print(row)
        print()


def demo_comparison_80x25(renderer, show_all: bool = False):
    """Demo that fits in 80x25 terminal."""
    width = 78  # Leave margin

    print("\n" + "=" * 80)
    print(" B7B-Demo: Terminal Waveform Renderer")
    print(" Renderer:", renderer.__class__.__name__)
    print("=" * 80)

    # For 80x25, show the 3 most useful bit depths
    if show_all:
        # Show all bit depths for sine only (compact view)
        print("\n SINE WAVE at all resolutions:\n")
        sine = generate_sine(128)
        for bits in [3, 4, 5, 6, 7]:
            height = BITS_TO_HEIGHT[bits]
            rows = render_compact(sine, height, renderer, width)
            print(f" {bits}b ({height:2d}r): ", end="")
            if height == 1:
                print(rows[0])
            else:
                print()
                for row in rows:
                    print(f"        {row}")
    else:
        # Default: show 3-bit (compact) for all waveforms
        print("\n All waveforms @ 3-bit (1 row):\n")
        waveforms = [
            ("LIN", generate_linear(128)),
            ("SIN", generate_sine(128)),
            ("COS", generate_cosine(128)),
            ("TRI", generate_triangle(128)),
        ]
        for name, samples in waveforms:
            rows = render_compact(samples, 1, renderer, width)
            print(f" {name}: {rows[0]}")

        # Then show sine at 5-bit (nice detail)
        print("\n Sine @ 5-bit (4 rows):\n")
        rows = render_compact(generate_sine(128), 4, renderer, width)
        for row in rows:
            print(f" {row}")


def main():
    parser = argparse.ArgumentParser(description="Static waveform rendering demo")
    parser.add_argument(
        "--renderer", "-r",
        choices=["unicode", "cp437", "ascii"],
        default="unicode",
        help="Renderer backend (default: unicode)"
    )
    parser.add_argument(
        "--wave", "-w",
        choices=["sine", "cosine", "linear", "triangle", "all"],
        default="sine",
        help="Waveform to display (default: sine)"
    )
    parser.add_argument(
        "--bits", "-b",
        type=int,
        choices=[3, 4, 5, 6, 7],
        default=None,
        help="Bits per block (default: show all)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=64,
        help="Width in characters (default: 64)"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact 80x25 demo"
    )
    parser.add_argument(
        "--all-bits",
        action="store_true",
        help="In compact mode, show all bit depths"
    )

    args = parser.parse_args()
    renderer = get_renderer(args.renderer)

    if args.compact:
        demo_comparison_80x25(renderer, show_all=args.all_bits)
        return

    # Get waveform(s)
    waveforms = {
        "sine": generate_sine(128),
        "cosine": generate_cosine(128),
        "linear": generate_linear(128),
        "triangle": generate_triangle(128),
    }

    if args.wave == "all":
        if args.bits:
            # All waveforms at specific bit depth
            demo_all_waveforms_at_bits(args.bits, renderer, args.width)
        else:
            # All waveforms at all bit depths (lots of output)
            for bits in [3, 4, 5, 6, 7]:
                demo_all_waveforms_at_bits(bits, renderer, args.width)
    else:
        samples = waveforms[args.wave]
        if args.bits:
            # Single waveform at specific bit depth
            print_waveform_block(args.wave.capitalize(), samples, args.bits, renderer, args.width)
        else:
            # Single waveform at all bit depths
            demo_single_waveform(args.wave, samples, renderer, args.width)


if __name__ == "__main__":
    main()
