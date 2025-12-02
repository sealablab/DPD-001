#!/usr/bin/env python3
"""Animation viewer for terminal waveforms.

Designed for easy human iteration through animation effects.
Terminal assumed to be 80x25 with clean initial state.

Usage:
    # Interactive mode (press Enter for next frame, q to quit)
    python examples/animation_viewer.py --effect scroll --interactive

    # Auto-play mode (with delay)
    python examples/animation_viewer.py --effect phase --delay 0.1

    # Generate frames to files for external viewing
    python examples/animation_viewer.py --effect morph --output frames/

    # List all available effects
    python examples/animation_viewer.py --list
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from wavetables import generate_sine, generate_cosine, generate_linear, generate_triangle
from render.blocks import UnicodeRenderer, CP437Renderer, ASCIIRenderer
from animations import (
    scroll_animation,
    phase_animation,
    amplitude_animation,
    morph_animation,
    resolution_animation,
    composite_animation,
)


# ANSI escape codes for terminal control
CLEAR_SCREEN = "\033[2J"
HOME = "\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def get_renderer(name: str):
    """Get renderer by name."""
    renderers = {
        "unicode": UnicodeRenderer(),
        "cp437": CP437Renderer(),
        "ascii": ASCIIRenderer(),
    }
    return renderers.get(name.lower(), UnicodeRenderer())


def get_effect_generator(effect: str, renderer, frames: int = 64):
    """Get animation generator for the specified effect."""
    width = 78  # Leave margin for 80-char terminal

    if effect == "scroll":
        samples = generate_sine(width * 2)  # Double length for scrolling
        return scroll_animation(samples, height=4, frames=frames, step=2)

    elif effect == "phase":
        return phase_animation(width, height=4, frames=frames, wave_type="sine")

    elif effect == "amplitude":
        return amplitude_animation(width, height=4, frames=frames)

    elif effect == "morph-sin-tri":
        return morph_animation(width, height=4, frames=frames,
                               from_wave="sine", to_wave="triangle")

    elif effect == "morph-sin-cos":
        return morph_animation(width, height=4, frames=frames,
                               from_wave="sine", to_wave="cosine")

    elif effect == "resolution-up":
        return resolution_animation(generate_sine(width), frames_per_level=8,
                                    direction="up")

    elif effect == "resolution-down":
        return resolution_animation(generate_sine(width), frames_per_level=8,
                                    direction="down")

    elif effect == "resolution-bounce":
        return resolution_animation(generate_sine(width), frames_per_level=6,
                                    direction="bounce")

    elif effect == "composite":
        return composite_animation(width, height=4, frames=frames)

    else:
        raise ValueError(f"Unknown effect: {effect}")


def render_frame(
    samples: np.ndarray,
    height: int,
    renderer,
    frame_num: int,
    total_frames: int,
    effect_name: str
) -> str:
    """Render a single animation frame as a string."""
    # Ensure samples fit in 78 chars
    if len(samples) > 78:
        indices = np.linspace(0, len(samples) - 1, 78, dtype=int)
        samples = samples[indices]

    rows = renderer.render_waveform(samples, height)

    # Build frame with header and footer
    lines = []
    lines.append("=" * 80)
    lines.append(f" B7B-Demo Animation: {effect_name}")
    lines.append(f" Frame {frame_num + 1}/{total_frames} | Height: {height} blocks | Renderer: {renderer.__class__.__name__}")
    lines.append("=" * 80)
    lines.append("")

    # Add waveform rows with leading space
    for row in rows:
        lines.append(" " + row)

    # Pad to fill remaining space (for consistent frame size)
    current_height = len(lines)
    target_height = 23  # Leave room for prompt in 25-line terminal
    while len(lines) < target_height:
        lines.append("")

    lines.append("-" * 80)
    lines.append(" [Enter]=next  [q]=quit  [r]=restart")

    return "\n".join(lines)


def interactive_mode(effect: str, renderer, frames: int = 64):
    """Run animation in interactive mode (press Enter for each frame)."""
    generator = get_effect_generator(effect, renderer, frames)
    frame_list = list(generator)
    total = len(frame_list)

    idx = 0
    while True:
        samples, height = frame_list[idx]
        frame_str = render_frame(samples, height, renderer, idx, total, effect)

        # Clear and display
        print(HOME + CLEAR_SCREEN + frame_str)

        # Wait for input
        try:
            user_input = input().strip().lower()
        except EOFError:
            break

        if user_input == 'q':
            break
        elif user_input == 'r':
            idx = 0
        elif user_input.isdigit():
            idx = int(user_input) % total
        else:
            idx = (idx + 1) % total


def autoplay_mode(effect: str, renderer, frames: int = 64, delay: float = 0.1, loops: int = 1):
    """Run animation in auto-play mode."""
    print(HIDE_CURSOR, end="", flush=True)

    try:
        for loop in range(loops):
            generator = get_effect_generator(effect, renderer, frames)
            frame_list = list(generator)
            total = len(frame_list)

            for idx, (samples, height) in enumerate(frame_list):
                frame_str = render_frame(samples, height, renderer, idx, total, effect)
                print(HOME + CLEAR_SCREEN + frame_str, flush=True)
                time.sleep(delay)
    finally:
        print(SHOW_CURSOR, end="", flush=True)


def output_frames(effect: str, renderer, output_dir: str, frames: int = 64):
    """Output animation frames to individual files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generator = get_effect_generator(effect, renderer, frames)
    frame_list = list(generator)
    total = len(frame_list)

    for idx, (samples, height) in enumerate(frame_list):
        frame_str = render_frame(samples, height, renderer, idx, total, effect)

        filename = output_path / f"frame_{idx:04d}.txt"
        with open(filename, "w") as f:
            f.write(frame_str)

    print(f"Generated {total} frames in {output_path}/")
    print(f"View with: cat {output_path}/frame_0000.txt")
    print(f"Or iterate: for f in {output_path}/frame_*.txt; do clear; cat $f; read; done")


def list_effects():
    """List all available animation effects."""
    effects = [
        ("scroll", "Scroll waveform left (streaming data effect)"),
        ("phase", "Phase shift animation (waveform moves horizontally)"),
        ("amplitude", "Amplitude modulation (breathing effect)"),
        ("morph-sin-tri", "Morph from sine to triangle wave"),
        ("morph-sin-cos", "Morph from sine to cosine wave"),
        ("resolution-up", "Resolution sweep 3-bit to 7-bit"),
        ("resolution-down", "Resolution sweep 7-bit to 3-bit"),
        ("resolution-bounce", "Resolution bounce (up and down)"),
        ("composite", "Combined phase + amplitude effects"),
    ]

    print("\nAvailable animation effects:\n")
    for name, desc in effects:
        print(f"  {name:20s} - {desc}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Animation viewer for terminal waveforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                          # List all effects
  %(prog)s --effect scroll --interactive   # Step through frames
  %(prog)s --effect phase --delay 0.1      # Auto-play
  %(prog)s --effect morph-sin-tri --output frames/  # Save to files
        """
    )

    parser.add_argument(
        "--effect", "-e",
        default="scroll",
        help="Animation effect name (use --list to see options)"
    )
    parser.add_argument(
        "--renderer", "-r",
        choices=["unicode", "cp437", "ascii"],
        default="unicode",
        help="Renderer backend"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode (press Enter for each frame)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=None,
        help="Auto-play delay between frames in seconds"
    )
    parser.add_argument(
        "--frames", "-f",
        type=int,
        default=64,
        help="Number of animation frames"
    )
    parser.add_argument(
        "--loops", "-l",
        type=int,
        default=1,
        help="Number of loops for auto-play (0=infinite, Ctrl+C to stop)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output directory for frame files"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available animation effects"
    )

    args = parser.parse_args()

    if args.list:
        list_effects()
        return

    renderer = get_renderer(args.renderer)

    if args.output:
        output_frames(args.effect, renderer, args.output, args.frames)
    elif args.interactive:
        interactive_mode(args.effect, renderer, args.frames)
    elif args.delay is not None:
        loops = args.loops if args.loops > 0 else 999999
        try:
            autoplay_mode(args.effect, renderer, args.frames, args.delay, loops)
        except KeyboardInterrupt:
            print(SHOW_CURSOR + "\nStopped.")
    else:
        # Default: output first few frames as preview
        generator = get_effect_generator(args.effect, renderer, args.frames)
        frame_list = list(generator)
        total = len(frame_list)

        print(f"\nAnimation: {args.effect} ({total} frames)")
        print(f"Renderer: {renderer.__class__.__name__}")
        print("\nFirst 3 frames preview:\n")

        for idx in [0, total // 2, total - 1]:
            samples, height = frame_list[idx]
            print(f"--- Frame {idx + 1}/{total} (height={height}) ---")
            rows = renderer.render_waveform(samples, height)
            for row in rows:
                print(" " + row)
            print()

        print("Run with --interactive or --delay for full animation")


if __name__ == "__main__":
    main()
