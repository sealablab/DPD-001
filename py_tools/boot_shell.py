#!/usr/bin/env python3
"""
BOOT Shell - Interactive CLI for BOOT/BIOS/LOADER subsystems

A shell-like interface that mirrors the BOOT FSM's command structure:

    RUN> _           # BOOT_P1 - dispatcher ready
    RUN> l           # RUNL → enter LOADER
    LOAD[0]> _       # LOADER context
    LOAD[1024]> _    # Shows transfer progress
    [Esc]            # RET → return to dispatcher
    RUN> b           # RUNB → enter BIOS
    BIOS> _          # BIOS context
    [Esc]            # RET → return to dispatcher
    RUN> p           # RUNP → launch PROG (no return)
    PROG$ _          # One-way, different prompt style

Key Features:
- Context-aware prompts matching FSM state
- Esc key mapped to RET transition (BIOS/LOADER → RUN)
- Tab completion for commands per context
- Real-time HVS voltage display (optional)
- Extensible command handlers for BIOS and LOADER

Usage:
    python boot_shell.py                    # Simulation mode (no hardware)
    python boot_shell.py --device 192.168.1.100  # Connect to Moku

Requirements:
    pip install prompt_toolkit

Author: Moku Instrument Forge Team
Date: 2025-11-29
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from enum import Enum, auto
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
import sys

# Import BOOT constants
try:
    from boot_constants import CMD, BOOTState, LOADState, BOOT_HVS, RET
except ImportError:
    # Running from different directory
    sys.path.insert(0, str(__file__).rsplit('/', 1)[0])
    from boot_constants import CMD, BOOTState, LOADState, BOOT_HVS, RET


# =============================================================================
# Shell State
# =============================================================================

class ShellContext(Enum):
    """Shell context matching BOOT FSM states."""
    BOOT_P0 = auto()      # Initial - not yet running
    BOOT_P1 = auto()      # Dispatcher ready (RUN>)
    BIOS = auto()         # BIOS active (BIOS>)
    LOADER = auto()       # LOADER active (LOAD>)
    PROG = auto()         # PROG active (PROG$) - one-way
    FAULT = auto()        # Fault state


@dataclass
class ShellState:
    """Mutable shell state."""
    context: ShellContext = ShellContext.BOOT_P0
    loader_offset: int = 0          # Current LOADER word offset (0-1023)
    loader_buffers: int = 1         # Number of buffers being loaded
    last_cr0: int = 0               # Last CR0 value sent
    connected: bool = False         # True if connected to hardware
    device_ip: Optional[str] = None
    verbose: bool = False


# =============================================================================
# Command Handlers
# =============================================================================

@dataclass
class CommandResult:
    """Result of a command execution."""
    success: bool
    message: str = ""
    new_context: Optional[ShellContext] = None


class CommandHandler:
    """Base command handler with context-specific commands."""

    def __init__(self, state: ShellState, hw_interface: Optional["HardwareInterface"] = None):
        self.state = state
        self.hw = hw_interface

        # Command registry: context -> {command: (handler, help)}
        self.commands: Dict[ShellContext, Dict[str, tuple]] = {
            ShellContext.BOOT_P0: {
                "run": (self.cmd_run, "Enable RUN gate (→ BOOT_P1)"),
                "status": (self.cmd_status, "Show current state"),
                "help": (self.cmd_help, "Show available commands"),
                "quit": (self.cmd_quit, "Exit shell"),
            },
            ShellContext.BOOT_P1: {
                "p": (self.cmd_prog, "RUNP: Transfer to PROG (one-way)"),
                "prog": (self.cmd_prog, "RUNP: Transfer to PROG (one-way)"),
                "b": (self.cmd_bios, "RUNB: Transfer to BIOS"),
                "bios": (self.cmd_bios, "RUNB: Transfer to BIOS"),
                "l": (self.cmd_loader, "RUNL: Transfer to LOADER"),
                "loader": (self.cmd_loader, "RUNL: Transfer to LOADER"),
                "r": (self.cmd_reset, "RUNR: Soft reset to BOOT_P0"),
                "reset": (self.cmd_reset, "RUNR: Soft reset to BOOT_P0"),
                "status": (self.cmd_status, "Show current state"),
                "help": (self.cmd_help, "Show available commands"),
                "quit": (self.cmd_quit, "Exit shell"),
            },
            ShellContext.BIOS: {
                # BIOS-specific commands go here
                "diag": (self.cmd_bios_diag, "Run diagnostics"),
                "mem": (self.cmd_bios_mem, "Memory test"),
                "status": (self.cmd_status, "Show current state"),
                "help": (self.cmd_help, "Show available commands"),
                # Esc/ret handled by key binding
            },
            ShellContext.LOADER: {
                # LOADER-specific commands go here
                "load": (self.cmd_loader_load, "Load buffer from file"),
                "progress": (self.cmd_loader_progress, "Show transfer progress"),
                "verify": (self.cmd_loader_verify, "Verify CRC"),
                "status": (self.cmd_status, "Show current state"),
                "help": (self.cmd_help, "Show available commands"),
                # Esc/ret handled by key binding
            },
            ShellContext.PROG: {
                # PROG context - limited commands, no return
                "status": (self.cmd_status, "Show current state"),
                "help": (self.cmd_help, "Show available commands"),
                # Note: No quit - must power cycle or use external reset
            },
            ShellContext.FAULT: {
                "clear": (self.cmd_fault_clear, "Clear fault and reset"),
                "status": (self.cmd_status, "Show current state"),
                "help": (self.cmd_help, "Show available commands"),
            },
        }

    def execute(self, command: str) -> CommandResult:
        """Execute a command in current context."""
        parts = command.strip().split()
        if not parts:
            return CommandResult(True)

        cmd_name = parts[0].lower()
        args = parts[1:]

        context_cmds = self.commands.get(self.state.context, {})
        if cmd_name in context_cmds:
            handler, _ = context_cmds[cmd_name]
            return handler(*args)
        else:
            return CommandResult(False, f"Unknown command: {cmd_name}")

    def get_completions(self) -> List[str]:
        """Get command completions for current context."""
        return list(self.commands.get(self.state.context, {}).keys())

    # -------------------------------------------------------------------------
    # Dispatcher commands (BOOT_P1)
    # -------------------------------------------------------------------------

    def cmd_run(self, *args) -> CommandResult:
        """Enable RUN gate."""
        self._send_cr0(CMD.RUN)
        return CommandResult(True, "RUN gate enabled", ShellContext.BOOT_P1)

    def cmd_prog(self, *args) -> CommandResult:
        """Transfer to PROG (one-way)."""
        self._send_cr0(CMD.RUNP)
        return CommandResult(
            True,
            "Transferring to PROG (one-way, no return)...",
            ShellContext.PROG
        )

    def cmd_bios(self, *args) -> CommandResult:
        """Transfer to BIOS."""
        self._send_cr0(CMD.RUNB)
        return CommandResult(True, "Entering BIOS...", ShellContext.BIOS)

    def cmd_loader(self, *args) -> CommandResult:
        """Transfer to LOADER."""
        self._send_cr0(CMD.RUNL)
        self.state.loader_offset = 0
        return CommandResult(True, "Entering LOADER...", ShellContext.LOADER)

    def cmd_reset(self, *args) -> CommandResult:
        """Soft reset to BOOT_P0."""
        self._send_cr0(CMD.RUNR)
        return CommandResult(True, "Resetting to BOOT_P0...", ShellContext.BOOT_P0)

    def cmd_return(self, *args) -> CommandResult:
        """Return to dispatcher (RET)."""
        if self.state.context in (ShellContext.BIOS, ShellContext.LOADER):
            self._send_cr0(CMD.RET)
            return CommandResult(True, "Returning to dispatcher...", ShellContext.BOOT_P1)
        else:
            return CommandResult(False, "RET only available from BIOS/LOADER")

    # -------------------------------------------------------------------------
    # BIOS commands (stubs for now)
    # -------------------------------------------------------------------------

    def cmd_bios_diag(self, *args) -> CommandResult:
        """Run BIOS diagnostics."""
        return CommandResult(True, "[BIOS] Diagnostics: Not yet implemented")

    def cmd_bios_mem(self, *args) -> CommandResult:
        """Run memory test."""
        return CommandResult(True, "[BIOS] Memory test: Not yet implemented")

    # -------------------------------------------------------------------------
    # LOADER commands (stubs for now)
    # -------------------------------------------------------------------------

    def cmd_loader_load(self, *args) -> CommandResult:
        """Load buffer from file."""
        if not args:
            return CommandResult(False, "Usage: load <filename>")
        return CommandResult(True, f"[LOADER] Loading {args[0]}: Not yet implemented")

    def cmd_loader_progress(self, *args) -> CommandResult:
        """Show transfer progress."""
        return CommandResult(
            True,
            f"[LOADER] Progress: {self.state.loader_offset}/1024 words"
        )

    def cmd_loader_verify(self, *args) -> CommandResult:
        """Verify CRC."""
        return CommandResult(True, "[LOADER] CRC verification: Not yet implemented")

    # -------------------------------------------------------------------------
    # Common commands
    # -------------------------------------------------------------------------

    def cmd_status(self, *args) -> CommandResult:
        """Show current state."""
        ctx_name = self.state.context.name
        cr0_hex = f"0x{self.state.last_cr0:08X}"
        connected = "Connected" if self.state.connected else "Simulation"

        lines = [
            f"Context:   {ctx_name}",
            f"Last CR0:  {cr0_hex}",
            f"Mode:      {connected}",
        ]

        if self.state.context == ShellContext.LOADER:
            lines.append(f"Offset:    {self.state.loader_offset}/1024")
            lines.append(f"Buffers:   {self.state.loader_buffers}")

        return CommandResult(True, "\n".join(lines))

    def cmd_help(self, *args) -> CommandResult:
        """Show available commands."""
        context_cmds = self.commands.get(self.state.context, {})
        lines = [f"Available commands in {self.state.context.name}:"]
        for cmd, (_, help_text) in sorted(context_cmds.items()):
            lines.append(f"  {cmd:10s} - {help_text}")

        if self.state.context in (ShellContext.BIOS, ShellContext.LOADER):
            lines.append("")
            lines.append("  [Esc]      - Return to dispatcher (RET)")

        return CommandResult(True, "\n".join(lines))

    def cmd_quit(self, *args) -> CommandResult:
        """Exit shell."""
        raise KeyboardInterrupt("User quit")

    def cmd_fault_clear(self, *args) -> CommandResult:
        """Clear fault and reset."""
        # In real implementation, send fault_clear pulse
        return CommandResult(True, "Clearing fault...", ShellContext.BOOT_P0)

    # -------------------------------------------------------------------------
    # Hardware interface
    # -------------------------------------------------------------------------

    def _send_cr0(self, value: int):
        """Send CR0 value to hardware (or simulate)."""
        self.state.last_cr0 = value
        if self.hw and self.state.connected:
            self.hw.set_cr0(value)


# =============================================================================
# Hardware Interface (stub for now)
# =============================================================================

class HardwareInterface:
    """Interface to Moku hardware (stub implementation)."""

    def __init__(self, device_ip: str):
        self.device_ip = device_ip
        self.connected = False

    def connect(self) -> bool:
        """Connect to device."""
        # TODO: Implement actual Moku connection
        print(f"[HW] Would connect to {self.device_ip}")
        return False

    def set_cr0(self, value: int):
        """Set CR0 register."""
        print(f"[HW] CR0 = 0x{value:08X}")

    def get_output_c(self) -> int:
        """Read OutputC (HVS voltage)."""
        return 0

    def disconnect(self):
        """Disconnect from device."""
        pass


# =============================================================================
# Shell UI
# =============================================================================

class BootShell:
    """Interactive BOOT shell using prompt_toolkit."""

    # Prompt styles per context
    PROMPT_STYLES = {
        ShellContext.BOOT_P0: ("class:p0", "INIT> "),
        ShellContext.BOOT_P1: ("class:run", "RUN> "),
        ShellContext.BIOS: ("class:bios", "BIOS> "),
        ShellContext.LOADER: ("class:load", "LOAD[{offset}]> "),
        ShellContext.PROG: ("class:prog", "PROG$ "),
        ShellContext.FAULT: ("class:fault", "FAULT! "),
    }

    STYLE = Style.from_dict({
        "p0": "#888888",           # Gray - not running
        "run": "#00aa00 bold",     # Green - dispatcher ready
        "bios": "#aa8800 bold",    # Yellow - BIOS
        "load": "#0088aa bold",    # Cyan - LOADER
        "prog": "#aa00aa bold",    # Magenta - PROG (one-way)
        "fault": "#aa0000 bold",   # Red - fault
    })

    def __init__(self, device_ip: Optional[str] = None):
        self.state = ShellState()

        # Hardware interface (optional)
        self.hw: Optional[HardwareInterface] = None
        if device_ip:
            self.hw = HardwareInterface(device_ip)
            self.state.device_ip = device_ip

        # Command handler
        self.handler = CommandHandler(self.state, self.hw)

        # Key bindings
        self.kb = self._create_key_bindings()

        # Prompt session
        self.session = PromptSession(
            history=InMemoryHistory(),
            key_bindings=self.kb,
            style=self.STYLE,
        )

    def _create_key_bindings(self) -> KeyBindings:
        """Create context-aware key bindings."""
        kb = KeyBindings()

        @kb.add('escape')
        def _(event):
            """Esc → RET transition from BIOS/LOADER."""
            if self.state.context in (ShellContext.BIOS, ShellContext.LOADER):
                result = self.handler.cmd_return()
                if result.success:
                    if result.new_context:
                        self.state.context = result.new_context
                    print(f"\n{result.message}")
                    # Clear current input and redraw prompt
                    event.app.current_buffer.reset()

        @kb.add('c-c')
        def _(event):
            """Ctrl+C → interrupt/quit."""
            raise KeyboardInterrupt()

        @kb.add('c-d')
        def _(event):
            """Ctrl+D → quit if buffer empty."""
            if not event.app.current_buffer.text:
                raise EOFError()

        return kb

    def _get_prompt(self) -> str:
        """Get formatted prompt for current context."""
        style_class, template = self.PROMPT_STYLES[self.state.context]

        # Format template with state variables
        prompt_text = template.format(
            offset=self.state.loader_offset,
        )

        return [(style_class, prompt_text)]

    def _get_completer(self) -> WordCompleter:
        """Get completer for current context."""
        return WordCompleter(self.handler.get_completions(), ignore_case=True)

    def run(self):
        """Run the interactive shell."""
        print("BOOT Shell v0.1")
        print("Type 'help' for commands, Ctrl+C to quit")

        if self.state.device_ip:
            print(f"Device: {self.state.device_ip}")
            if self.hw and self.hw.connect():
                self.state.connected = True
                print("Connected to hardware")
            else:
                print("Running in simulation mode")
        else:
            print("Running in simulation mode (no device specified)")

        print()

        # Start in P0, user must 'run' to get to P1
        self.state.context = ShellContext.BOOT_P0

        try:
            while True:
                try:
                    # Get input with context-aware prompt and completion
                    text = self.session.prompt(
                        self._get_prompt(),
                        completer=self._get_completer(),
                    )

                    # Execute command
                    result = self.handler.execute(text)

                    # Handle result
                    if result.message:
                        print(result.message)

                    if result.new_context:
                        self.state.context = result.new_context

                except KeyboardInterrupt:
                    print("\n^C")
                    continue

        except EOFError:
            print("\nGoodbye!")
        except KeyboardInterrupt:
            print("\nGoodbye!")
        finally:
            if self.hw:
                self.hw.disconnect()


# =============================================================================
# Main
# =============================================================================

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="BOOT Shell - Interactive CLI for BOOT/BIOS/LOADER"
    )
    parser.add_argument(
        "--device", "-d",
        help="Moku device IP address (omit for simulation mode)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    shell = BootShell(device_ip=args.device)
    shell.state.verbose = args.verbose
    shell.run()


if __name__ == "__main__":
    main()
