#!/usr/bin/env python3
"""Waveform Split-Screen REPL - Integrated waveform display with command interface.

A split-screen application with:
- Top-left: Waveform widget 1 (sine)
- Top-right: Waveform widget 2 (triangle)
- Bottom: REPL command area
- Status bar: FAULT indicator + inline animated waveform

This version does NOT use alternate screen/full screen mode.

Usage:
    python screensaver_split.py

REPL Commands:
    B - Bitstream mode (stub)
    R - Register mode (stub)
    L - Log mode (stub)
    P - Pause/resume animation
    F - Toggle FAULT indicator
    Q - Quit
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Callable
from datetime import datetime

import numpy as np

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.formatted_text import FormattedText, HTML
from prompt_toolkit.styles import Style


# =============================================================================
# Constants
# =============================================================================

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 25
FPS = 20
FRAME_INTERVAL = 1.0 / FPS

# Widget dimensions (half screen each)
WIDGET_WIDTH = 38  # Leave room for borders
WIDGET_HEIGHT = 10  # Top half of 25 rows

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


def render_inline_waveform(samples: np.ndarray, renderer_key: str = "unicode") -> str:
    """Render a single-line (1 row, 3 BpB) waveform."""
    config = CHAR_MAPS[renderer_key]
    chars = []
    for s in samples:
        # Map 0-127 to 0-7 for unicode (8 levels including space)
        level = (int(s) * 7) // 127
        if level == 0:
            chars.append(" ")
        elif level >= 7:
            chars.append(config["fill"])
        else:
            chars.append(config["map"][level])
    return "".join(chars)


# =============================================================================
# Static Waveform Widget (for split layout)
# =============================================================================

@dataclass
class StaticWaveformWidget:
    """A waveform widget for fixed position in split layout."""
    width: int = 36
    height: int = 6
    renderer: str = "unicode"
    wave_gen: Callable = field(default_factory=lambda: generate_sine)
    label: str = "Wave"
    scroll_offset: int = 0

    def get_samples(self) -> np.ndarray:
        samples = self.wave_gen(self.width * 2, 0.0)
        rolled = np.roll(samples, -self.scroll_offset)
        return rolled[:self.width]

    def render(self) -> List[str]:
        samples = self.get_samples()
        waveform_rows = render_waveform(samples, self.height, self.renderer)

        # Box drawing characters
        H_LINE = "\u2500"  # ─
        V_LINE = "\u2502"  # │
        TL = "\u250c"      # ┌
        TR = "\u2510"      # ┐
        BL = "\u2514"      # └
        BR = "\u2518"      # ┘

        # Build framed widget
        title = f" {self.label} [{CHAR_MAPS[self.renderer]['name']}] "
        title_padded = title.center(self.width, H_LINE)

        lines = [TL + title_padded + TR]
        for row in waveform_rows:
            # Pad row to width if needed
            padded_row = row.ljust(self.width)[:self.width]
            lines.append(V_LINE + padded_row + V_LINE)
        lines.append(BL + H_LINE * self.width + BR)

        return lines

    def update(self, paused: bool = False):
        if not paused:
            self.scroll_offset = (self.scroll_offset + 1) % (self.width * 2)

    def get_formatted_text(self) -> FormattedText:
        lines = self.render()
        result = []
        for i, line in enumerate(lines):
            if i > 0:
                result.append(("", "\n"))
            result.append(("class:widget", line))
        return FormattedText(result)


# =============================================================================
# Split Screen REPL Application
# =============================================================================

class SplitScreenREPL:
    """Split-screen REPL with embedded waveform widgets."""

    def __init__(self):
        self.paused = False
        self.fault_active = False
        self.frame_count = 0
        self.output_lines: List[str] = []
        self.max_output_lines = 8

        # Create widgets
        self.widget1 = StaticWaveformWidget(
            width=36, height=6,
            renderer="unicode", wave_gen=generate_sine,
            label="CH1 Sine",
        )
        self.widget2 = StaticWaveformWidget(
            width=36, height=6,
            renderer="cp437", wave_gen=generate_triangle,
            label="CH2 Triangle",
        )

        # Status bar waveform (shorter, for inline display)
        self.status_wave_offset = 0

        # Input buffer
        self.input_buffer = Buffer(
            multiline=False,
            accept_handler=self._handle_input,
        )

        # Build application
        self.app = self._create_application()

        # Add welcome message
        self._add_output("=" * 76)
        self._add_output("  DPD Waveform Console - Split Screen Mode")
        self._add_output("=" * 76)
        self._add_output("  Commands: B=Bitstream  R=Register  L=Log  P=Pause  F=Fault  Q=Quit")
        self._add_output("")

    def _add_output(self, text: str):
        """Add a line to the output area."""
        self.output_lines.append(text)
        # Keep only the last N lines
        if len(self.output_lines) > self.max_output_lines:
            self.output_lines = self.output_lines[-self.max_output_lines:]

    def _handle_input(self, buffer: Buffer):
        """Handle REPL input."""
        text = buffer.text.strip().upper()

        if not text:
            return

        cmd = text[0]

        if cmd == "B":
            self._add_output("RUN> B")
            self._add_output("  [BITSTREAM] Mode not implemented (stub)")
        elif cmd == "R":
            self._add_output("RUN> R")
            self._add_output("  [REGISTER] Mode not implemented (stub)")
        elif cmd == "L":
            self._add_output("RUN> L")
            self._add_output("  [LOG] Mode not implemented (stub)")
        elif cmd == "P":
            self.paused = not self.paused
            state = "PAUSED" if self.paused else "RUNNING"
            self._add_output(f"RUN> P")
            self._add_output(f"  Animation {state}")
        elif cmd == "F":
            self.fault_active = not self.fault_active
            state = "ACTIVE" if self.fault_active else "CLEARED"
            self._add_output(f"RUN> F")
            self._add_output(f"  FAULT {state}")
        elif cmd == "Q":
            self._add_output("RUN> Q")
            self._add_output("  Goodbye!")
            self.app.exit()
        else:
            self._add_output(f"RUN> {text}")
            self._add_output(f"  Unknown command: '{cmd}'")

    def _get_output_text(self) -> FormattedText:
        """Get the output area content."""
        result = []
        for i, line in enumerate(self.output_lines):
            if i > 0:
                result.append(("", "\n"))
            result.append(("class:output", line))
        return FormattedText(result)

    def _get_prompt_text(self) -> FormattedText:
        """Get the prompt prefix."""
        return FormattedText([("class:prompt", "RUN> ")])

    def _get_status_bar_text(self) -> FormattedText:
        """Get status bar content with FAULT indicator and inline waveform."""
        # Time
        now = datetime.now().strftime("%H:%M:%S")

        # Frame counter
        frame_str = f"Frame:{self.frame_count:06d}"

        # Pause indicator
        pause_str = "PAUSED" if self.paused else "RUNNING"

        # Inline waveform (20 chars)
        wave_samples = generate_sine(40, 0.0)
        wave_samples = np.roll(wave_samples, -self.status_wave_offset)[:20]
        wave_str = render_inline_waveform(wave_samples, "unicode")

        # Build status bar
        result = []

        # Left section: FAULT indicator
        if self.fault_active:
            result.append(("class:fault", " FAULT "))
        else:
            result.append(("class:ok", "  OK   "))

        result.append(("class:status", " \u2502 "))  # │ separator

        # Status info
        result.append(("class:status", f"{frame_str} "))
        result.append(("class:status", f"\u2502 "))
        result.append(("class:status", f"{pause_str:7s} "))
        result.append(("class:status", f"\u2502 "))

        # Inline waveform with label
        result.append(("class:status", "Wave: "))
        result.append(("class:wave-inline", wave_str))
        result.append(("class:status", " "))

        # Right section: time
        result.append(("class:status", f"\u2502 "))
        result.append(("class:status", f"{now} "))

        return FormattedText(result)

    def _get_separator_text(self) -> str:
        """Get horizontal separator line."""
        return "\u2500" * 78  # ─

    def _create_application(self) -> Application:
        """Create the prompt_toolkit application."""

        kb = KeyBindings()

        @kb.add("c-c")
        @kb.add("c-q")
        def exit_app(event):
            event.app.exit()

        # Widget windows
        widget1_window = Window(
            content=FormattedTextControl(lambda: self.widget1.get_formatted_text()),
            width=D(preferred=40),
            height=D(preferred=9),
        )

        widget2_window = Window(
            content=FormattedTextControl(lambda: self.widget2.get_formatted_text()),
            width=D(preferred=40),
            height=D(preferred=9),
        )

        # Separator between widgets
        widget_separator = Window(
            content=FormattedTextControl("\u2502"),  # │
            width=1,
            style="class:separator",
        )

        # Top row: two widgets side by side
        top_row = VSplit([
            widget1_window,
            widget_separator,
            widget2_window,
        ])

        # Horizontal separator
        h_separator = Window(
            content=FormattedTextControl(self._get_separator_text),
            height=1,
            style="class:separator",
        )

        # Output area
        output_window = Window(
            content=FormattedTextControl(lambda: self._get_output_text()),
            height=D(preferred=8, max=10),
            style="class:output-area",
        )

        # Input prompt
        input_window = VSplit([
            Window(
                content=FormattedTextControl(lambda: self._get_prompt_text()),
                width=5,
                dont_extend_width=True,
            ),
            Window(
                content=BufferControl(buffer=self.input_buffer),
                style="class:input",
            ),
        ], height=1)

        # Status bar
        status_bar = Window(
            content=FormattedTextControl(lambda: self._get_status_bar_text()),
            height=1,
            style="class:status-bar",
        )

        # Main layout
        layout = HSplit([
            top_row,
            h_separator,
            output_window,
            h_separator,
            input_window,
            status_bar,
        ])

        # Styles
        style = Style.from_dict({
            "widget": "bg:#1a2a3a #88ccff",
            "separator": "#444466",
            "output-area": "bg:#1a1a2e #aaaacc",
            "output": "#ccccee",
            "prompt": "bold #ffcc00",
            "input": "#ffffff",
            "status-bar": "bg:#2a2a4a #aaaacc",
            "status": "#8888aa",
            "fault": "bg:#aa0000 #ffffff bold",
            "ok": "bg:#006600 #ffffff",
            "wave-inline": "#88ff88",
        })

        return Application(
            layout=Layout(layout, focused_element=self.input_buffer),
            key_bindings=kb,
            style=style,
            full_screen=False,  # NOT full screen / alternate screen
            mouse_support=False,
        )

    async def animation_loop(self):
        """Animation loop for updating widgets."""
        while True:
            if not self.paused:
                self.widget1.update(paused=False)
                self.widget2.update(paused=False)
                self.status_wave_offset = (self.status_wave_offset + 1) % 40
                self.frame_count += 1

            self.app.invalidate()
            await asyncio.sleep(FRAME_INTERVAL)

    async def run_async(self):
        """Run the application with animation."""
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
    repl = SplitScreenREPL()
    repl.run()


if __name__ == "__main__":
    main()
