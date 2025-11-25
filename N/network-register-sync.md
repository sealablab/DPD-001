# Network Register Synchronization Protocol

**Date**: 2025-11-25
**Status**: Implemented
**Files**: `forge_common_pkg.vhd`, `DPD_shim.vhd`, `DPD_main.vhd`

## Problem

Network-accessible control registers (CR1-CR10) can be updated asynchronously at any time by the host. This creates race conditions when the FSM is actively operating:

- Parameter changes mid-pulse could cause glitches
- Partial updates (e.g., voltage without duration) create inconsistent states
- No guarantee of atomicity across multiple registers

## Solution

**INIT-only updates**: Configuration parameters are only propagated to the application when the FSM is in the `INITIALIZING` state (`STATE_SYNC_SAFE = 000000`).

### Two-Layer Protection

```
Network Regs → [Shim Gate] → app_reg_* → [Main Latch] → latched_*
                   ↑                          ↑
            sync_safe='1'              INITIALIZING state
```

1. **Shim layer (L2)**: Gates CR2-CR10 updates based on `sync_safe` signal
2. **Main layer (L3)**: Latches all parameters atomically in INITIALIZING

### Signal Classification

| Type | Registers | Gating | Rationale |
|------|-----------|--------|-----------|
| **Lifecycle controls** | CR1 (arm_enable, fault_clear, etc.) | None | Real-time control signals must work in any state |
| **Configuration params** | CR2-CR10 (voltages, durations, thresholds) | sync_safe | Define operation parameters, must be stable |

## Contract

1. `STATE_SYNC_SAFE` is always `000000` (power-on default)
2. FSM starts in INITIALIZING after reset or fault_clear
3. Parameters are latched atomically before transitioning to IDLE
4. To update parameters mid-operation: pulse `fault_clear` to force re-init

## Why Not Other Approaches?

| Alternative | Rejected Because |
|-------------|------------------|
| Pause clock during updates | Overkill; adds complexity for no benefit |
| Double-buffer all registers | Memory overhead; harder to reason about |
| Update in IDLE too | Less explicit; parameters could change unexpectedly |
| Dedicated `ready_for_updates` signal | Redundant; state encoding already provides this |

## Usage Pattern

```python
# Python client workflow
dpd.set_config(voltage=2000, duration_us=100)  # Writes to network regs
dpd.clear_fault()  # Forces INIT → latches params → IDLE
dpd.arm()          # Now safe to operate with new params
```

## Related

- [[fsm-state-encoding]] - Why INITIALIZING is 000000
- [[forge-control-scheme]] - FORGE_READY bits in CR0
