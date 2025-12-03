#!/usr/bin/env python3
"""Waveform Screensaver with REPL - Interactive command interface.

A simple REPL that provides access to various modes:
- B: Bitstream mode (stub)
- R: Register mode (stub)
- L: Log mode (stub)
- P: Preview mode (runs the waveform screensaver)

Usage:
    python screensaver_repl.py

REPL Commands:
    B - Bitstream mode (stub)
    R - Register mode (stub)
    L - Log mode (stub)
    P - Preview mode (screensaver)
    Q - Quit REPL

Screensaver Controls (in P mode):
    q / x / Escape - Exit back to REPL
    Space          - Pause/resume animation
    r              - Reset widget positions
    1-4            - Change renderer
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Callable

import numpy as np

from prompt_toolkit import prompt
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    Float,
    FloatContainer,
    HSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.keys import Keys


# =============================================================================
# Constants
# =============================================================================

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 25
FPS = 20
FRAME_INTERVAL = 1.0 / FPS

CHAR_MAPS = {
    "binary": {"map": " 1", "fill": "1", "name": "Binary"},
    "ascii": {"map": " .-=", "fill": "#", "name": "ASCII"},
    "cp437": {"map": " \u2591\u2592\u2593", "fill": "\u2588", "name": "CP437"},
    "unicode": {
        "map": " \u2581\u2582\u2583\u2584\u2585\u2586\u2587",
        "fill": "\u2588",
        "name": "Unicode",
    },
}


# =============================================================================
# Waveform Generation
# =============================================================================

def generate_sine(length: int = 64, phase: float = 0.0) -> np.ndarray:
    t = np.linspace(phase, phase + 2 * np.pi, length, endpoint=False)
    wave = 63.5 + 63.5 * np.sin(t)
    return np.round(wave).astype(np.uint8)


def generate_triangle(length: int = 64, phase: float = 0.0) -> np.ndarray:
    half = length // 2
    up = np.linspace(0, 127, half, dtype=np.uint8)
    down = np.linspace(127, 0, length - half, dtype=np.uint8)
    wave = np.concatenate([up, down])
    offset = int((phase / (2 * np.pi)) * length) % length
    return np.roll(wave, -offset)


# =============================================================================
# BpB Renderer
# =============================================================================

def sample_to_column(value: int, height: int, char_map: str, fill_char: str) -> List[str]:
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


def render_waveform(samples: np.ndarray, height: int, renderer_key: str) -> List[str]:
    config = CHAR_MAPS[renderer_key]
    columns = [
        sample_to_column(int(s), height, config["map"], config["fill"])
        for s in samples
    ]
    rows = ["".join(chars) for chars in zip(*columns)]
    return rows[::-1]


# =============================================================================
# Floating Waveform Widget
# =============================================================================

@dataclass
class FloatingWaveformWidget:
    width: int = 30
    height: int = 4
    x: float = 0.0
    y: float = 0.0
    dx: float = 0.5
    dy: float = 0.25
    renderer: str = "unicode"
    wave_gen: Callable = field(default_factory=lambda: generate_sine)
    label: str = "Wave"
    style_class: str = "widget1"
    scroll_offset: int = 0

    def get_samples(self) -> np.ndarray:
        samples = self.wave_gen(self.width * 2, 0.0)
        rolled = np.roll(samples, -self.scroll_offset)
        return rolled[:self.width]

    def render(self) -> List[str]:
        samples = self.get_samples()
        waveform_rows = render_waveform(samples, self.height, self.renderer)
        border_top = "\u250c" + "\u2500" * self.width + "\u2510"
        border_bot = "\u2514" + "\u2500" * self.width + "\u2518"
        lines = [border_top]
        for row in waveform_rows:
            lines.append("\u2502" + row + "\u2502")
        lines.append(border_bot)
        label_line = f" {self.label} [{CHAR_MAPS[self.renderer]['name']}] "
        lines.append(label_line.center(self.width + 2))
        return lines

    def update(self, screen_width: int, screen_height: int, paused: bool = False):
        if paused:
            return
        self.scroll_offset = (self.scroll_offset + 1) % (self.width * 2)
        self.x += self.dx
        self.y += self.dy
        render_width = self.width + 2
        render_height = self.height + 3
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
# Screensaver Application (Preview Mode)
# =============================================================================

class WaveformScreensaver:
    """Full-screen waveform screensaver for Preview mode."""

    def __init__(self):
        self.paused = False
        self.frame_count = 0
        self.widget1 = FloatingWaveformWidget(
            width=28, height=4, x=5, y=2, dx=0.6, dy=0.3,
            renderer="unicode", wave_gen=generate_sine,
            label="Sine", style_class="widget1",
        )
        self.widget2 = FloatingWaveformWidget(
            width=24, height=3, x=40, y=12, dx=-0.4, dy=0.35,
            renderer="cp437", wave_gen=generate_triangle,
            label="Triangle", style_class="widget2",
        )
        self.app = self._create_application()

    def _create_status_text(self) -> FormattedText:
        status = f" Frame: {self.frame_count:06d} | FPS: {FPS} | "
        status += f"{'PAUSED' if self.paused else 'RUNNING'} | "
        status += "[q/x/Esc]exit [space]pause [r]eset [1-4]renderer"
        return FormattedText([("class:status", status)])

    def _create_background_text(self) -> str:
        lines = []
        for y in range(SCREEN_HEIGHT):
            line = ""
            for x in range(SCREEN_WIDTH):
                if (x + y) % 4 == 0:
                    line += "\u00b7"
                else:
                    line += " "
            lines.append(line)
        return "\n".join(lines)

    def _get_float_for_widget(self, widget: FloatingWaveformWidget) -> Float:
        return Float(
            content=Window(
                content=FormattedTextControl(lambda w=widget: w.get_formatted_text()),
                dont_extend_width=True,
                dont_extend_height=True,
            ),
            left=lambda w=widget: w.int_x,
            top=lambda w=widget: w.int_y,
            transparent=True,
        )

    def _create_application(self) -> Application:
        kb = KeyBindings()

        # Exit keys: q, x, Escape
        @kb.add("q")
        @kb.add("x")
        @kb.add(Keys.Escape)
        @kb.add("c-c")
        def exit_preview(event):
            event.app.exit()

        @kb.add("space")
        def toggle_pause(event):
            self.paused = not self.paused

        @kb.add("r")
        def reset_positions(event):
            self.widget1.x, self.widget1.y = 5, 2
            self.widget2.x, self.widget2.y = 40, 12

        @kb.add("1")
        def set_binary(event):
            self.widget1.renderer = self.widget2.renderer = "binary"

        @kb.add("2")
        def set_ascii(event):
            self.widget1.renderer = self.widget2.renderer = "ascii"

        @kb.add("3")
        def set_cp437(event):
            self.widget1.renderer = self.widget2.renderer = "cp437"

        @kb.add("4")
        def set_unicode(event):
            self.widget1.renderer = self.widget2.renderer = "unicode"

        status_window = Window(
            content=FormattedTextControl(lambda: self._create_status_text()),
            height=1,
            style="class:status",
        )
        background = Window(
            content=FormattedTextControl(self._create_background_text),
            style="class:background",
        )
        body = FloatContainer(
            content=HSplit([background, status_window]),
            floats=[
                self._get_float_for_widget(self.widget1),
                self._get_float_for_widget(self.widget2),
            ],
        )
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
        while True:
            if not self.paused:
                self.widget1.update(SCREEN_WIDTH, SCREEN_HEIGHT - 1, self.paused)
                self.widget2.update(SCREEN_WIDTH, SCREEN_HEIGHT - 1, self.paused)
                self.frame_count += 1
            self.app.invalidate()
            await asyncio.sleep(FRAME_INTERVAL)

    async def run_async(self):
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
        asyncio.run(self.run_async())


# =============================================================================
# REPL Commands (Stubs)
# =============================================================================

def cmd_bitstream():
    """Bitstream mode - stub."""
    print()
    print("=" * 60)
    print("  BITSTREAM MODE (stub)")
    print("=" * 60)
    print("  This mode would allow loading and managing FPGA bitstreams.")
    print("  Not yet implemented.")
    print("=" * 60)
    print()


def cmd_register():
    """Register mode - stub."""
    print()
    print("=" * 60)
    print("  REGISTER MODE (stub)")
    print("=" * 60)
    print("  This mode would allow reading/writing control registers.")
    print("  Not yet implemented.")
    print("=" * 60)
    print()


def cmd_log():
    """Log mode - stub."""
    print()
    print("=" * 60)
    print("  LOG MODE (stub)")
    print("=" * 60)
    print("  This mode would display system logs and diagnostics.")
    print("  Not yet implemented.")
    print("=" * 60)
    print()


def cmd_preview():
    """Preview mode - runs the screensaver."""
    print()
    print("Entering Preview mode...")
    print("Press 'q', 'x', or Escape to return to REPL")
    print()

    screensaver = WaveformScreensaver()
    screensaver.run()

    print()
    print("Exited Preview mode.")
    print()


# =============================================================================
# REPL
# =============================================================================

BANNER = """
================================================================================
  DPD Waveform Console
================================================================================
  Commands:
    B - Bitstream mode (stub)
    R - Register mode (stub)
    L - Log mode (stub)
    P - Preview mode (waveform screensaver)
    Q - Quit
================================================================================
"""


def run_repl():
    """Run the main REPL loop."""
    print(BANNER)

    while True:
        try:
            # Get user input
            user_input = prompt("RUN> ").strip().upper()

            if not user_input:
                continue

            # Get first character as command
            cmd = user_input[0]

            if cmd == "B":
                cmd_bitstream()
            elif cmd == "R":
                cmd_register()
            elif cmd == "L":
                cmd_log()
            elif cmd == "P":
                cmd_preview()
            elif cmd == "Q":
                print()
                print("Goodbye!")
                break
            else:
                print(f"Unknown command: '{cmd}'. Valid commands: B, R, L, P, Q")

        except KeyboardInterrupt:
            print()
            print("^C - Use 'Q' to quit")
        except EOFError:
            print()
            print("Goodbye!")
            break


# =============================================================================
# Main
# =============================================================================

def main():
    """Entry point."""
    run_repl()


if __name__ == "__main__":
    main()
