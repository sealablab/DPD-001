#!/usr/bin/env python3
"""Waveform Screensaver - Floating BpB waveform widgets using prompt_toolkit.

A full-screen application demonstrating:
- P1: Two floating waveform widgets on screen
- P2: 20 FPS display clock with scrolling waveform animation
- P3: DVD-logo style bouncing widget movement

Usage:
    python screensaver.py

Controls:
    q / Ctrl+C - Quit
    Space      - Pause/resume animation
    r          - Reset widget positions
    1-4        - Change renderer (1=Binary, 2=ASCII, 3=CP437, 4=Unicode)

Target: 80x25 terminal (fixed size, no resize handling)
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Tuple, Callable

import numpy as np

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    Float,
    FloatContainer,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style


# =============================================================================
# Constants
# =============================================================================

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 25
FPS = 20
FRAME_INTERVAL = 1.0 / FPS

# Character maps for different renderers
CHAR_MAPS = {
    "binary": {
        "map": " 1",
        "fill": "1",
        "name": "Binary",
    },
    "ascii": {
        "map": " .-=",
        "fill": "#",
        "name": "ASCII",
    },
    "cp437": {
        "map": " \u2591\u2592\u2593",  # ░▒▓
        "fill": "\u2588",              # █
        "name": "CP437",
    },
    "unicode": {
        "map": " \u2581\u2582\u2583\u2584\u2585\u2586\u2587",  # ▁▂▃▄▅▆▇
        "fill": "\u2588",  # █
        "name": "Unicode",
    },
}


# =============================================================================
# Waveform Generation
# =============================================================================

def generate_sine(length: int = 64, phase: float = 0.0) -> np.ndarray:
    """Generate sine wave with optional phase offset."""
    t = np.linspace(phase, phase + 2 * np.pi, length, endpoint=False)
    wave = 63.5 + 63.5 * np.sin(t)
    return np.round(wave).astype(np.uint8)


def generate_cosine(length: int = 64, phase: float = 0.0) -> np.ndarray:
    """Generate cosine wave with optional phase offset."""
    t = np.linspace(phase, phase + 2 * np.pi, length, endpoint=False)
    wave = 63.5 + 63.5 * np.cos(t)
    return np.round(wave).astype(np.uint8)


def generate_triangle(length: int = 64, phase: float = 0.0) -> np.ndarray:
    """Generate triangle wave with phase offset via roll."""
    half = length // 2
    up = np.linspace(0, 127, half, dtype=np.uint8)
    down = np.linspace(127, 0, length - half, dtype=np.uint8)
    wave = np.concatenate([up, down])
    # Apply phase as roll
    offset = int((phase / (2 * np.pi)) * length) % length
    return np.roll(wave, -offset)


# =============================================================================
# BpB Renderer
# =============================================================================

def sample_to_column(
    value: int,
    height: int,
    char_map: str,
    fill_char: str
) -> List[str]:
    """Convert a sample to a column of characters (bottom-to-top)."""
    levels_per_block = len(char_map)
    effective_levels = height * levels_per_block

    if effective_levels > 1:
        scaled = (value * (effective_levels - 1)) // 127
    else:
        scaled = 0

    full_count = scaled // levels_per_block
    partial = scaled % levels_per_block

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

    columns = [
        sample_to_column(int(s), height, char_map, fill_char)
        for s in samples
    ]

    # Transpose and reverse (top row first)
    rows = ["".join(chars) for chars in zip(*columns)]
    return rows[::-1]


# =============================================================================
# Floating Waveform Widget
# =============================================================================

@dataclass
class FloatingWaveformWidget:
    """A floating waveform widget that can move around the screen.

    Attributes:
        width: Width in characters
        height: Height in rows
        x: Current X position (left edge)
        y: Current Y position (top edge)
        dx: X velocity (chars per frame)
        dy: Y velocity (rows per frame)
        renderer: Renderer key (binary/ascii/cp437/unicode)
        wave_gen: Waveform generator function
        phase: Current phase offset for animation
        label: Widget label
        style_class: CSS-like style class name
    """
    width: int = 30
    height: int = 4
    x: float = 0.0
    y: float = 0.0
    dx: float = 0.5
    dy: float = 0.25
    renderer: str = "unicode"
    wave_gen: Callable = field(default_factory=lambda: generate_sine)
    phase: float = 0.0
    label: str = "Wave"
    style_class: str = "widget1"

    # Scroll offset for left-to-right scrolling
    scroll_offset: int = 0

    def get_samples(self) -> np.ndarray:
        """Generate current waveform samples with scroll effect."""
        # Generate more samples than width to allow scrolling
        samples = self.wave_gen(self.width * 2, self.phase)
        # Roll to create scroll effect
        rolled = np.roll(samples, -self.scroll_offset)
        return rolled[:self.width]

    def render(self) -> List[str]:
        """Render the widget content as list of strings."""
        samples = self.get_samples()
        waveform_rows = render_waveform(samples, self.height, self.renderer)

        # Add border
        border_top = "\u250c" + "\u2500" * self.width + "\u2510"  # ┌─┐
        border_bot = "\u2514" + "\u2500" * self.width + "\u2518"  # └─┘

        lines = [border_top]
        for row in waveform_rows:
            lines.append("\u2502" + row + "\u2502")  # │ │
        lines.append(border_bot)

        # Add label
        label_line = f" {self.label} [{CHAR_MAPS[self.renderer]['name']}] "
        lines.append(label_line.center(self.width + 2))

        return lines

    def update(self, screen_width: int, screen_height: int, paused: bool = False):
        """Update widget position and animation state."""
        if paused:
            return

        # Update scroll offset (scrolls left-to-right, so increment)
        self.scroll_offset = (self.scroll_offset + 1) % (self.width * 2)

        # Update position
        self.x += self.dx
        self.y += self.dy

        # Get widget render dimensions (including border and label)
        render_width = self.width + 2  # border adds 2
        render_height = self.height + 3  # border top/bot + label

        # Bounce off edges
        if self.x <= 0:
            self.x = 0
            self.dx = abs(self.dx)
        elif self.x + render_width >= screen_width:
            self.x = screen_width - render_width
            self.dx = -abs(self.dx)

        if self.y <= 0:
            self.y = 0
            self.dy = abs(self.dy)
        elif self.y + render_height >= screen_height:
            self.y = screen_height - render_height
            self.dy = -abs(self.dy)

    def get_formatted_text(self) -> FormattedText:
        """Get formatted text for prompt_toolkit rendering."""
        lines = self.render()
        result = []
        for i, line in enumerate(lines):
            if i > 0:
                result.append(("", "\n"))
            result.append((f"class:{self.style_class}", line))
        return FormattedText(result)

    @property
    def int_x(self) -> int:
        return int(self.x)

    @property
    def int_y(self) -> int:
        return int(self.y)


# =============================================================================
# Screensaver Application
# =============================================================================

class WaveformScreensaver:
    """Full-screen waveform screensaver application."""

    def __init__(self):
        self.paused = False
        self.frame_count = 0

        # Create two floating widgets with different waveforms
        self.widget1 = FloatingWaveformWidget(
            width=28,
            height=4,
            x=5,
            y=2,
            dx=0.6,
            dy=0.3,
            renderer="unicode",
            wave_gen=generate_sine,
            label="Sine",
            style_class="widget1",
        )

        self.widget2 = FloatingWaveformWidget(
            width=24,
            height=3,
            x=40,
            y=12,
            dx=-0.4,
            dy=0.35,
            renderer="cp437",
            wave_gen=generate_triangle,
            label="Triangle",
            style_class="widget2",
        )

        # Build the application
        self.app = self._create_application()

    def _create_status_text(self) -> FormattedText:
        """Create status bar text."""
        status = f" Frame: {self.frame_count:06d} | FPS: {FPS} | "
        status += f"{'PAUSED' if self.paused else 'RUNNING'} | "
        status += f"[q]uit [space]pause [r]eset [1-4]renderer"
        return FormattedText([("class:status", status)])

    def _create_background_text(self) -> str:
        """Create background fill text (dots pattern)."""
        # Create a subtle dot pattern background
        lines = []
        for y in range(SCREEN_HEIGHT):
            line = ""
            for x in range(SCREEN_WIDTH):
                if (x + y) % 4 == 0:
                    line += "\u00b7"  # middle dot ·
                else:
                    line += " "
            lines.append(line)
        return "\n".join(lines)

    def _get_float_for_widget(self, widget: FloatingWaveformWidget) -> Float:
        """Create a Float container for a widget."""
        # Note: left/top must be int, not Callable (prompt_toolkit 3.x)
        # We update these values in the animation loop
        return Float(
            content=Window(
                content=FormattedTextControl(
                    lambda w=widget: w.get_formatted_text()
                ),
                dont_extend_width=True,
                dont_extend_height=True,
            ),
            left=widget.int_x,
            top=widget.int_y,
            transparent=True,
        )

    def _create_application(self) -> Application:
        """Create the prompt_toolkit application."""

        # Key bindings
        kb = KeyBindings()

        @kb.add("q")
        @kb.add("c-c")
        def quit_(event):
            event.app.exit()

        @kb.add("space")
        def toggle_pause(event):
            self.paused = not self.paused

        @kb.add("r")
        def reset_positions(event):
            self.widget1.x = 5
            self.widget1.y = 2
            self.widget2.x = 40
            self.widget2.y = 12

        @kb.add("1")
        def set_binary(event):
            self.widget1.renderer = "binary"
            self.widget2.renderer = "binary"

        @kb.add("2")
        def set_ascii(event):
            self.widget1.renderer = "ascii"
            self.widget2.renderer = "ascii"

        @kb.add("3")
        def set_cp437(event):
            self.widget1.renderer = "cp437"
            self.widget2.renderer = "cp437"

        @kb.add("4")
        def set_unicode(event):
            self.widget1.renderer = "unicode"
            self.widget2.renderer = "unicode"

        # Status bar at bottom
        status_window = Window(
            content=FormattedTextControl(lambda: self._create_status_text()),
            height=1,
            style="class:status",
        )

        # Background with dot pattern
        background = Window(
            content=FormattedTextControl(self._create_background_text),
            style="class:background",
        )

        # Main layout with floating widgets
        from prompt_toolkit.layout.containers import HSplit

        # Store Float references so we can update positions in animation loop
        self.float1 = self._get_float_for_widget(self.widget1)
        self.float2 = self._get_float_for_widget(self.widget2)

        body = FloatContainer(
            content=HSplit([
                background,
                status_window,
            ]),
            floats=[
                self.float1,
                self.float2,
            ],
        )

        # Styles
        style = Style.from_dict({
            "background": "bg:#1a1a2e #4a4a5e",
            "status": "bg:#2d2d44 #aaaacc bold",
            "widget1": "bg:#2a3a4a #88ccff",
            "widget2": "bg:#3a2a4a #ff88cc",
        })

        return Application(
            layout=Layout(body),
            key_bindings=kb,
            style=style,
            full_screen=True,
            mouse_support=False,
        )

    async def animation_loop(self):
        """Main animation loop running at 20 FPS."""
        while True:
            if not self.paused:
                # Update widget positions and animation
                self.widget1.update(SCREEN_WIDTH, SCREEN_HEIGHT - 1, self.paused)
                self.widget2.update(SCREEN_WIDTH, SCREEN_HEIGHT - 1, self.paused)
                self.frame_count += 1

                # Sync Float positions with widget positions
                # (prompt_toolkit 3.x requires static int values for left/top)
                self.float1.left = self.widget1.int_x
                self.float1.top = self.widget1.int_y
                self.float2.left = self.widget2.int_x
                self.float2.top = self.widget2.int_y

            # Invalidate display to trigger redraw
            self.app.invalidate()

            # Wait for next frame
            await asyncio.sleep(FRAME_INTERVAL)

    async def run_async(self):
        """Run the application with animation."""
        # Start animation loop as background task
        animation_task = asyncio.create_task(self.animation_loop())

        try:
            await self.app.run_async()
        finally:
            animation_task.cancel()
            try:
                await animation_task
            except asyncio.CancelledError:
                pass

    def run(self):
        """Run the application (blocking)."""
        asyncio.run(self.run_async())


# =============================================================================
# Main
# =============================================================================

def main():
    """Entry point."""
    print("\033[2J\033[H", end="")  # Clear screen
    print("Starting Waveform Screensaver...")
    print("Press 'q' to quit, Space to pause")
    print()

    screensaver = WaveformScreensaver()
    screensaver.run()


if __name__ == "__main__":
    main()
