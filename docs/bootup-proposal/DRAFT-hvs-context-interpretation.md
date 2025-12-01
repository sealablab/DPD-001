---
status: DRAFT
created: 2025-11-29
author: Claude Code session
modified: 2025-11-28 20:31:02
accessed: 2025-11-30 16:21:21
---
# HVS Context-Aware Interpretation (DRAFT)

This document describes how the BOOT shell interprets HVS (Hierarchical Voltage Scaling) readings based on the current client context.

## Core Principle

**The client is authoritative on context.**

When the client sends `CMD.RUNL`, it assumes the BOOT FSM transitions to LOAD_ACTIVE. From that point, HVS readings are interpreted as LOADER states, not BOOT states.

This design avoids the need for globally unique HVS voltages across all modules.

## Interpretation Model

```
┌─────────────────────────────────────────────────────────────┐
│                      Client State Machine                    │
│                                                              │
│   ┌────────┐  RUNL   ┌────────┐  RET    ┌────────┐          │
│   │ BOOT   │ ──────▶ │ LOADER │ ──────▶ │ BOOT   │          │
│   │ P1     │         │ context│         │ P1     │          │
│   └────────┘         └────────┘         └────────┘          │
│       │                  │                                   │
│       │                  │                                   │
│       ▼                  ▼                                   │
│   Interpret as       Interpret as                            │
│   BOOT states        LOADER states                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ OutputC
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Hardware                               │
│                                                              │
│   OutputC = 0.2V  (same voltage, different meaning)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## State Tables

### BOOT Context (0.2V steps = 1311 digital units)

| State | Digital | Voltage | Name |
|-------|---------|---------|------|
| P0 | 0 | 0.0V | Initial/Reset |
| P1 | 1311 | 0.2V | Dispatcher |
| BIOS_ACTIVE | 2622 | 0.4V | BIOS mode |
| LOAD_ACTIVE | 3933 | 0.6V | LOADER mode |
| PROG_ACTIVE | 5244 | 0.8V | PROG mode |
| FAULT | negative | <0V | Error |

### LOADER Context (0.2V steps = 1311 digital units)

| State | Digital | Voltage | Name |
|-------|---------|---------|------|
| P0 | 0 | 0.0V | Setup phase |
| P1 | 1311 | 0.2V | Transfer phase |
| P2 | 2622 | 0.4V | Validate phase |
| P3 | 3933 | 0.6V | Complete |
| FAULT | negative | <0V | CRC error |

### PROG/DPD Context (0.5V steps = 3277 digital units)

| State | Digital | Voltage | Name |
|-------|---------|---------|------|
| INITIALIZING | 0 | 0.0V | Init |
| IDLE | 3277 | 0.5V | Ready |
| ARMED | 6554 | 1.0V | Waiting trigger |
| FIRING | 9831 | 1.5V | Active |
| COOLDOWN | 13108 | 2.0V | Recovery |
| FAULT | -3277 | -0.5V | Error |

## Same Voltage, Different Meaning

Consider a reading of **0.2V (1311 digital units)**:

| If Client Context Is | Interpretation |
|---------------------|----------------|
| BOOT_P1 | BOOT_P1 (dispatcher ready) |
| LOADER | LOAD_P1 (transfer in progress) |
| PROG | Unknown (between states) |

The client's context tracking determines the interpretation.

## Fault Detection

Faults are **universally detectable**: any negative voltage indicates an error state, regardless of context.

```python
is_fault = (digital < -TOLERANCE)  # ~-200 units
```

This allows immediate fault notification even if context tracking is wrong.

## Implementation

```python
class HVSMonitor(threading.Thread):
    def _interpret(self, digital: int, context: ShellContext) -> str:
        # Select table based on context
        if context in (ShellContext.BOOT_P0, ShellContext.BOOT_P1):
            table = self.BOOT_STATES
        elif context == ShellContext.LOADER:
            table = self.LOADER_STATES
        elif context == ShellContext.PROG:
            table = self.DPD_STATES
        else:
            table = self.BOOT_STATES

        # Find closest match within tolerance
        for expected, name in table.items():
            if abs(digital - expected) <= self.TOLERANCE:
                return name

        return f"?{digital}"  # Unknown
```

## Benefits

1. **Simpler hardware** - No need for globally unique HVS values
2. **Efficient encoding** - Each module uses full 0-1V range
3. **Clear semantics** - Client knows what it asked for
4. **Fault safety** - Negative voltage always means error

## Limitations

1. **Assumes commands work** - If RUNL fails silently, client interprets wrong
2. **No cross-module detection** - Can't detect "wrong module" from HVS alone
3. **Requires client discipline** - Must track context correctly

## Mitigation

For critical applications, add sanity checks:
- Verify HVS is in expected range for context
- Timeout if expected transition doesn't occur
- Use BIOS diagnostics to verify module operation
