# Network Register Synchronization Protocol

**Date:** 2025-11-25  
**Status:** Implemented  
**Files:** `forge_common_pkg.vhd`, `DPD_shim.vhd`, `DPD_main.vhd`

---

## Problem

Network-accessible control registers (CR1-CR10) can be updated asynchronously at any time by the host. This creates race conditions when the FSM is actively operating:

- Parameter changes mid-pulse could cause glitches
- Partial updates (e.g., voltage without duration) create inconsistent states
- No guarantee of atomicity across multiple registers

---

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

---

## Contract

1. `STATE_SYNC_SAFE` is always `000000` (power-on default)
2. FSM starts in INITIALIZING after reset or fault_clear
3. Parameters are latched atomically before transitioning to IDLE
4. To update parameters mid-operation: pulse `fault_clear` to force re-init

---

## Why Not Other Approaches?

| Alternative | Rejected Because |
|-------------|------------------|
| Pause clock during updates | Overkill; adds complexity for no benefit |
| Double-buffer all registers | Memory overhead; harder to reason about |
| Update in IDLE too | Less explicit; parameters could change unexpectedly |
| Dedicated `ready_for_updates` signal | Redundant; state encoding already provides this |

---

## Usage Pattern

```python
# Python client workflow
dpd.set_config(voltage=2000, duration_us=100)  # Writes to network regs
dpd.clear_fault()  # Forces INIT → latches params → IDLE
dpd.arm()          # Now safe to operate with new params
```

**See:** [Hardware Debug Checklist](hardware-debug-checklist.md) for step-by-step examples.

---

## Implementation Details

### Shim Layer (DPD_shim.vhd)

```vhdl
-- sync_safe signal: '1' when state = INITIALIZING
sync_safe <= '1' when (app_state_vector = STATE_SYNC_SAFE) else '0';

-- Gate configuration registers
app_reg_2 <= Control2 when sync_safe = '1' else app_reg_2;  -- Voltage params
app_reg_3 <= Control3 when sync_safe = '1' else app_reg_3;
-- ... CR4-CR10 similarly gated

-- Lifecycle controls always pass through
app_reg_1 <= Control1;  -- No gating
```

### Main Layer (DPD_main.vhd)

```vhdl
-- Atomic parameter latching in INITIALIZING state
process(Clk, Reset)
begin
    if Reset = '1' then
        latched_trig_out_voltage <= (others => '0');
        -- ... other latched params
    elsif rising_edge(Clk) then
        if state = STATE_INITIALIZING then
            -- Atomically latch all parameters
            latched_trig_out_voltage <= app_reg_2(15 downto 0);
            latched_intensity_voltage <= app_reg_3(15 downto 0);
            -- ... latch all config params
        end if;
    end if;
end process;
```

---

## Related Documents

- [Hardware Debug Checklist](hardware-debug-checklist.md) - Step-by-step debugging guide
- [HVS Encoding](hvs.md) - Why INITIALIZING is state 0
- [Custom Wrapper](custom-wrapper.md) - Control register details
- [FORGE Control Scheme](../CLAUDE.md#forge-control-scheme) - FORGE_READY bits in CR0

---

**Last Updated:** 2025-01-28  
**Status:** Migrated from review_me, integrated into docs/

