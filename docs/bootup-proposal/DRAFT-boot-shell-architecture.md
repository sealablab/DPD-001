---
status: DRAFT
created: 2025-11-29
author: Claude Code session
modified: 2025-11-30 16:21:17
accessed: 2025-11-30 16:21:17
---
# BOOT Shell Architecture (DRAFT)

This document describes the architecture of the interactive BOOT shell CLI.

## Overview

The BOOT shell provides an interactive command-line interface that mirrors the BOOT FSM's command structure, with real-time HVS monitoring.

## System Architecture

```
                    ┌─────────────────┐
  User Commands ──▶ │  CommandHandler │ ──▶ BOOT_CR0 writes
                    └────────┬────────┘
                             │
            context switch   │  (client-authoritative)
                             ▼
                    ┌─────────────────┐
                    │   ShellState    │ ◀── shared state (thread-safe)
                    └────────▲────────┘
                             │
                    HVS readings (interpreted per context)
                             │
                    ┌────────┴────────┐
                    │   HVSMonitor    │ ◀── 20Hz background thread (daemon)
                    └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Moku OutputC   │ (or simulation)
                    └─────────────────┘
```

## Live Status Bar

The bottom toolbar updates at 10Hz showing real-time HVS data:

```
┌──────────────────────────────────────────────────────────────┐
│ ◉ LOADER │ P1:XFER │ +0.20V │ SIM │                          │
└──────────────────────────────────────────────────────────────┘
  │    │        │         │      │
  │    │        │         │      └── Connection mode (HW/SIM)
  │    │        │         └── Voltage reading (signed)
  │    │        └── State name (context-aware interpretation)
  │    └── Current context (BOOT_P0/P1, BIOS, LOADER, PROG)
  └── Indicator (◉ = OK, ! = FAULT)
```

## Context-Aware HVS Interpretation

**Key principle:** Context is CLIENT-AUTHORITATIVE. The shell assumes RUN+X commands work and interprets HVS accordingly.

Same voltage, different meaning:

| Voltage | BOOT Context | LOADER Context | PROG Context |
|---------|--------------|----------------|--------------|
| 0.0V    | P0           | P0:SETUP       | INIT         |
| 0.2V    | P1           | P1:XFER        | -            |
| 0.4V    | BIOS         | P2:VALIDATE    | -            |
| 0.5V    | -            | -              | IDLE         |
| 0.6V    | LOAD         | P3:DONE        | -            |
| 1.0V    | -            | -              | ARMED        |

## Command Flow

```
INIT> run              # CMD.RUN  → P0 → P1
RUN gate enabled
RUN> l                 # CMD.RUNL → enter LOADER context
Entering LOADER...
LOAD[0]> _             # Client now interprets HVS as LOADER states
  │
  └── [Esc]            # CMD.RET  → return to P1
Returning to dispatcher...
RUN> p                 # CMD.RUNP → one-way handoff to PROG
Transferring to PROG (one-way, no return)...
PROG$ _                # Different prompt indicates no return
```

## UX Design Philosophy

The shell mimics a Unix shell with context-aware prompts:

| Context | Prompt | Notes |
|---------|--------|-------|
| BOOT_P0 | `INIT> ` | Initial state, waiting for RUN |
| BOOT_P1 | `RUN> ` | Dispatcher ready, like a shell prompt |
| BIOS | `BIOS> ` | Diagnostic mode |
| LOADER | `LOAD[n]> ` | Shows transfer progress |
| PROG | `PROG$ ` | Different sigil = no return (like `exec`) |
| FAULT | `FAULT! ` | Error state |

Key bindings:
- `Esc` → RET (return from BIOS/LOADER to dispatcher)
- `Tab` → Command completion (context-aware)
- `Ctrl+C` → Interrupt
- `Ctrl+D` → Quit (if buffer empty)

## Future Enhancements

1. **Full-screen mode** - Split view with command history and live state
2. **LOADER progress bar** - Visual transfer progress
3. **BIOS diagnostic commands** - Memory test, self-test, etc.
4. **Session recording** - Log all commands and state changes
5. **Scriptable mode** - Non-interactive batch execution

## Dependencies

- `prompt_toolkit` - Interactive CLI framework
- `threading` - Background HVS monitor
- `boot_constants` - BOOT subsystem constants

## Files

- `py_tools/boot_shell.py` - Main shell implementation
- `py_tools/boot_constants.py` - Constants and types
