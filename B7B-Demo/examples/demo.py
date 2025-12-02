#!/usr/bin/env python3
"""Quick start demo for B7B-Demo terminal waveform renderer.

This is the entry point for the quick start guide in B7B-README.md.

Usage:
    python examples/demo.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from wavetables import generate_sine, generate_cosine, generate_linear, generate_triangle
from render.blocks import UnicodeRenderer, CP437Renderer, ASCIIRenderer


def main():
    print("=" * 72)
    print(" B7B-Demo: Terminal Waveform Renderer")
    print(" Unicode Block Character Encoding Demonstration")
    print("=" * 72)
    print()

    # Initialize renderer
    renderer = UnicodeRenderer()

    # Character map demonstration
    print("Character Map (Unicode):")
    print(f"  Map: {renderer.char_map}")
    print(f"  Fill: {renderer.fill_char}")
    print(f"  Fault: {renderer.fault_char}")
    print()

    # Generate waveforms
    sine = generate_sine(64)
    cosine = generate_cosine(64)
    linear = generate_linear(64)
    triangle = generate_triangle(64)

    # Render at 3-bit (1 row) - compact view
    print("-" * 72)
    print(" All waveforms @ 3-bit resolution (1 row):")
    print("-" * 72)
    print()

    waveforms = [
        ("Linear", linear),
        ("Sine", sine),
        ("Cosine", cosine),
        ("Triangle", triangle),
    ]

    for name, wave in waveforms:
        rows = renderer.render_waveform(wave, height=1)
        print(f" {name:10s}: {rows[0]}")

    print()

    # Render sine at multiple resolutions
    print("-" * 72)
    print(" Sine wave at different resolutions:")
    print("-" * 72)
    print()

    for bits in [3, 4, 5]:
        height = 2 ** (bits - 3)  # 1, 2, 4
        rows = renderer.render_waveform(sine, height)
        print(f" {bits}-bit ({height} row{'s' if height > 1 else ''}):")
        for row in rows:
            print(f"   {row}")
        print()

    # Show all three renderers
    print("-" * 72)
    print(" Renderer comparison (sine @ 5-bit):")
    print("-" * 72)
    print()

    renderers = [
        ("Unicode", UnicodeRenderer()),
        ("CP437", CP437Renderer()),
        ("ASCII", ASCIIRenderer()),
    ]

    for name, r in renderers:
        print(f" {name}:")
        rows = r.render_waveform(sine, height=4)
        for row in rows:
            print(f"   {row}")
        print()

    print("=" * 72)
    print(" For more demos:")
    print("   python examples/static_demo.py --help")
    print("   python examples/animation_viewer.py --list")
    print("=" * 72)


if __name__ == "__main__":
    main()
