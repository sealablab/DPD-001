# DPD Hardware Debug Checklist

**Last Updated:** 2025-11-26 (updated for API v4.0)
**Maintainer:** Moku Instrument Forge Team

> **Purpose:** Minimal bit-flipping sequence to generate observable outputs on real hardware

Starting from all registers = 0, this checklist provides a step-by-step sequence to verify hardware functionality.

---

## FSM State Reference

| State | Binary | Value | Voltage (OutputC) |
|-------|--------|-------|-------------------|
| INITIALIZING | 000000 | 0 | 0.0V |
| IDLE | 000001 | 1 | 0.5V |
| ARMED | 000010 | 2 | 1.0V |
| FIRING | 000011 | 3 | 1.5V |
| COOLDOWN | 000100 | 4 | 2.0V |
| FAULT | 111111 | 63 | Negative voltage |

**Note**: INITIALIZING is a transient state - the FSM quickly transitions to IDLE after reset.

---

## Prerequisites

- Moku:Go connected and accessible
- DPD bitstream loaded in slot 2
- Oscilloscope or external scope connected to Output1 (FSM debug signal)
- **Scope settings:** Set to 500mV/div or 1V/div range, DC coupling
- **Expected voltages:** INITIALIZING(0V), IDLE(0.5V), ARMED(1.0V), FIRING(1.5V), COOLDOWN(2.0V)

---

## Step 0: Baseline (All zeros)

**Expected behavior:** Nothing. FSM stuck, no outputs.

```python
# All control registers = 0x00000000
cc.set_control(0, 0x00000000)  # CR0
cc.set_control(1, 0x00000000)  # CR1
cc.set_control(2, 0x00000000)  # CR2
cc.set_control(3, 0x00000000)  # CR3
cc.set_control(4, 0x00000000)  # CR4
cc.set_control(5, 0x00000000)  # CR5
cc.set_control(6, 0x00000000)  # CR6
cc.set_control(7, 0x00000000)  # CR7
cc.set_control(8, 0x00000000)  # CR8
cc.set_control(9, 0x00000000)  # CR9
cc.set_control(10, 0x00000000) # CR10
```

**Observable outputs:**
- OutputA: 0V (no trigger pulse)
- OutputB: 0V (no intensity output)
- OutputC: Unknown/undefined (FSM not initialized)

---

## Step 1: Enable FORGE_READY (CR0[31:29] = 0b111)

**Purpose:** Initialize FPGA clocking and user enable bits

```python
cc.set_control(0, 0xE0000000)  # CR0[31:29] = 0b111
```

**Expected behavior:**
- FSM initializes and transitions: INITIALIZING (0.0V) → IDLE (0.5V)
- This happens quickly - you may only see IDLE

**Observable outputs:**
- OutputA: Still 0V
- OutputB: Still 0V
- OutputC: ~0.5V (IDLE state)

**SUCCESS CRITERIA:** OutputC reads 0.5V ± 0.30V

---

## Step 2: Arm the FSM (CR0[2] = 1)

**Purpose:** Transition IDLE → ARMED

```python
cc.set_control(0, 0xE0000004)  # CR0 = FORGE + arm_enable
```

**Expected behavior:**
- FSM transitions from IDLE → ARMED
- OutputC should show ~1.0V (ARMED state encoding)

**Observable outputs:**
- OutputA: Still 0V
- OutputB: Still 0V
- OutputC: ~1.0V (ARMED state)

**SUCCESS CRITERIA:** OutputC reads 1.0V ± 0.30V

---

## Step 3: Set voltage for OutputA (CR2[15:0])

**Purpose:** Define non-zero trigger output voltage

```python
# Set trig_out_voltage = 2000mV (2.0V)
cc.set_control(2, 0x000007D0)  # CR2[15:0] = 0x07D0 = 2000 decimal
```

**Expected behavior:**
- No immediate change (FSM still in ARMED, waiting for trigger)
- **Note**: Config params only propagate in INITIALIZING state!

**Observable outputs:**
- OutputA: Still 0V (not firing yet)
- OutputB: Still 0V
- OutputC: ~1.0V (still ARMED)

**SUCCESS CRITERIA:** No change yet (this is correct!)

---

## Step 4: Set duration for OutputA (CR4)

**Purpose:** Define how long the trigger pulse lasts

```python
# Set trig_out_duration = 12500 cycles (100μs @ 125MHz)
cc.set_control(4, 0x000030D4)  # 12500 decimal = 0x30D4
```

**Expected behavior:**
- No immediate change (still waiting for trigger)

**Observable outputs:**
- OutputA: Still 0V
- OutputB: Still 0V
- OutputC: ~1.0V (still ARMED)

**SUCCESS CRITERIA:** No change yet (this is correct!)

---

## Step 5: Set voltage for OutputB (CR3[15:0])

**Purpose:** Define non-zero intensity output voltage

```python
# Set intensity_voltage = 3000mV (3.0V)
cc.set_control(3, 0x00000BB8)  # CR3[15:0] = 0x0BB8 = 3000 decimal
```

**Expected behavior:**
- No immediate change (still waiting for trigger)

**Observable outputs:**
- OutputA: Still 0V
- OutputB: Still 0V
- OutputC: ~1.0V (still ARMED)

**SUCCESS CRITERIA:** No change yet (this is correct!)

---

## Step 6: Set duration for OutputB (CR5)

**Purpose:** Define how long the intensity pulse lasts

```python
# Set intensity_duration = 25000 cycles (200μs @ 125MHz)
cc.set_control(5, 0x000061A8)  # 25000 decimal = 0x61A8
```

**Expected behavior:**
- No immediate change (still waiting for trigger)

**Observable outputs:**
- OutputA: Still 0V
- OutputB: Still 0V
- OutputC: ~1.0V (still ARMED)

**SUCCESS CRITERIA:** No change yet (this is correct!)

---

## Step 7: Set cooldown interval (CR7)

**Purpose:** Define cooldown period after firing

```python
# Set cooldown_interval = 1250 cycles (10μs @ 125MHz)
cc.set_control(7, 0x000004E2)  # 1250 decimal = 0x4E2
```

**Expected behavior:**
- No immediate change (still waiting for trigger)

**Observable outputs:**
- OutputA: Still 0V
- OutputB: Still 0V
- OutputC: ~1.0V (still ARMED)

**SUCCESS CRITERIA:** No change yet (this is correct!)

---

## Step 8: **FIRE!** Software trigger (CR0[0] = 1)

**Purpose:** Trigger the FSM to fire outputs (atomic single-write trigger!)

```python
# API v4.0: Single atomic write triggers immediately
cc.set_control(0, 0xE0000005)  # CR0 = FORGE + arm + sw_trigger
```

**Expected behavior (happens VERY fast, within ~310μs):**
1. FSM: ARMED (1.0V) → FIRING (1.5V)
2. OutputB: Goes to 3.0V for 200μs (intensity pulse on Output2)
3. FSM: FIRING (1.5V) → COOLDOWN (2.0V) for 10μs
4. FSM: COOLDOWN (2.0V) → IDLE (0.5V) (completes cycle)
5. OutputC transitions: 1.0V → 1.5V → 2.0V → 0.5V (returns to IDLE)

**Observable outputs (if you catch them!):**
- OutputB (on Output2): 3.0V pulse for 200μs
- OutputC (on Output1): Voltage transitions through states, settles at 0.5V (IDLE)

**SUCCESS CRITERIA:**
- OutputC settles at ~0.5V (IDLE state after completing fire cycle)
- If you have a scope with edge trigger, catch the pulse on Output2 (OutputB intensity)

---

## Step 9: Clear to return to IDLE (CR0[1] = 1)

**Purpose:** Reset FSM back to IDLE state via fault_clear

```python
# API v4.0: fault_clear is CR0[1], edge-triggered with auto-clear
cc.set_control(0, 0xE0000002)  # CR0 = FORGE + fault_clear
# No need to clear - RTL auto-clears after 4 cycles
```

**Expected behavior:**
- FSM goes through: current_state → INITIALIZING (0.0V) → IDLE (0.5V)
- **Important**: This is also how you apply new configuration parameters!

**Observable outputs:**
- OutputA: 0V
- OutputB: 0V
- OutputC: ~0.5V (IDLE state)

**SUCCESS CRITERIA:** OutputC reads 0.5V ± 0.30V

---

## Complete Sequence (Python Script) - API v4.0

```python
import time
from moku.instruments import MultiInstrument, CloudCompile

# Connect
m = MultiInstrument('192.168.8.98', platform_id=2, force_connect=True)
cc = m.set_instrument(2, CloudCompile)

print("Step 0: All zeros baseline")
for i in range(11):
    cc.set_control(i, 0x00000000)
time.sleep(0.5)

print("Step 1: Enable FORGE + configure timing (params latch in INITIALIZING)")
cc.set_control(0, 0xE0000000)  # FORGE enabled
time.sleep(0.1)

# Configure during INITIALIZING state
print("Step 2-7: Configure all parameters")
cc.set_control(2, 0x000007D0)  # OutputA voltage = 2000mV
cc.set_control(3, 0x00000BB8)  # OutputB voltage = 3000mV
cc.set_control(4, 0x000030D4)  # OutputA duration = 100μs
cc.set_control(5, 0x000061A8)  # OutputB duration = 200μs
cc.set_control(7, 0x000004E2)  # Cooldown = 10μs
time.sleep(0.2)

print("Step 8: Arm FSM")
cc.set_control(0, 0xE0000004)  # FORGE + arm_enable
time.sleep(0.5)

print("Step 9: FIRE! (atomic trigger)")
cc.set_control(0, 0xE0000005)  # FORGE + arm + sw_trigger
time.sleep(0.5)  # Wait for pulse sequence to complete

print("Step 10: Clear fault, return to IDLE")
cc.set_control(0, 0xE0000002)  # FORGE + fault_clear (auto-clears)
time.sleep(0.1)
cc.set_control(0, 0xE0000000)  # Return to FORGE only

print("\nSequence complete!")
m.relinquish_ownership()
```

---

## Troubleshooting

### If OutputC never changes from initial value:
- **Problem:** FORGE_READY not working, or bitstream not loaded
- **Solution:** Verify bitstream upload, check CR0 = 0xE0000000

### If OutputC gets stuck at 1.0V after arming:
- **Problem:** FSM armed but waiting for trigger (this is correct!)
- **Solution:** Send software trigger (Step 8)

### If OutputC goes to negative voltage:
- **Problem:** FSM entered FAULT state
- **Solution:** Check that durations are non-zero, pulse fault_clear via `cc.set_control(0, 0xE0000002)`

### If outputs happen but you can't see them:
- **Problem:** Pulses are too fast (100-200μs)
- **Solution:**
  - Use oscilloscope with edge trigger on Output1/Output2
  - Set very long durations (CR4 = 0x01000000 for ~67ms trigger pulse)
  - Monitor OutputC instead (it holds final state)

### If config changes don't take effect:
- **Problem:** Configuration registers only update in INITIALIZING state
- **Solution:** Pulse fault_clear via `cc.set_control(0, 0xE0000002)` to force re-initialization, then re-arm

### If nothing happens at all:
- **Problem:** Network timeout, bitstream not responding
- **Solution:**
  - Verify device IP is correct
  - Try power-cycling the Moku:Go
  - Re-upload bitstream

---

## Key Insights (API v4.0)

1. **OutputC is your best friend** - It shows FSM state persistently
2. **Outputs are FAST** - 100-200μs pulses are hard to see without a scope
3. **State sequence is:** INITIALIZING (0.0V) → IDLE (0.5V) → ARMED (1.0V) → FIRING (1.5V) → COOLDOWN (2.0V) → back to IDLE (0.5V)
4. **Minimum working config requires:**
   - CR0 = 0xE0000000 (FORGE enabled)
   - CR2[15:0] = non-zero voltage for OutputA
   - CR3[15:0] = non-zero voltage for OutputB
   - CR4 = non-zero duration for OutputA
   - CR5 = non-zero duration for OutputB
   - CR7 = non-zero cooldown
   - CR0 = 0xE0000005 (atomic arm + trigger!)

5. **Config register gotcha:** CR2-CR10 only propagate in INITIALIZING state. To apply new config mid-operation, pulse fault_clear (CR0[1]) first!

6. **The API v4.0 magic:** Single atomic write `0xE0000005` arms AND triggers in one operation!

---

## Related Documents

- [API v4.0 Reference](api-v4.md) - Authoritative SW/HW calling convention
- [HVS Encoding](hvs.md) - Understanding OutputC voltage encoding
- [Network Register Sync](network-register-sync.md) - Why config only updates in INITIALIZING
- [Custom Wrapper](docs/N/CustomWrapper.md) - Control register details

---

**Last Updated:** 2025-11-26
**Status:** Updated for API v4.0

