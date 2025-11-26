# DPD Hardware Debug Checklist

**Last Updated:** 2025-01-28 (migrated from review_me)  
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

## Step 2: Arm the FSM (CR1[0] = 1)

**Purpose:** Transition IDLE → ARMED

```python
cc.set_control(1, 0x00000001)  # CR1[0] = arm_enable = 1
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

## Step 8: **FIRE!** Software trigger (CR1[1] = 1)

**Purpose:** Trigger the FSM to fire outputs

```python
# Set sw_trigger = 1 (while keeping arm_enable = 1)
cc.set_control(1, 0x00000003)  # CR1[1:0] = 0b11 (sw_trigger + arm_enable)
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

## Step 9: Clear to return to IDLE (CR1[3] = 1)

**Purpose:** Reset FSM back to IDLE state via fault_clear

```python
# Pulse fault_clear to force re-initialization
cc.set_control(1, 0x00000008)  # CR1[3] = fault_clear = 1
time.sleep(0.01)
cc.set_control(1, 0x00000000)  # Clear all CR1 bits
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

## Complete Sequence (Python Script)

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

print("Step 1: Enable FORGE_READY")
cc.set_control(0, 0xE0000000)
time.sleep(0.5)

print("Step 2: Arm FSM")
cc.set_control(1, 0x00000001)
time.sleep(0.5)

print("Step 3: Set OutputA voltage = 2000mV")
cc.set_control(2, 0x000007D0)
time.sleep(0.2)

print("Step 4: Set OutputA duration = 100μs")
cc.set_control(4, 0x000030D4)
time.sleep(0.2)

print("Step 5: Set OutputB voltage = 3000mV")
cc.set_control(3, 0x00000BB8)
time.sleep(0.2)

print("Step 6: Set OutputB duration = 200μs")
cc.set_control(5, 0x000061A8)
time.sleep(0.2)

print("Step 7: Set cooldown = 10μs")
cc.set_control(7, 0x000004E2)
time.sleep(0.2)

print("Step 8: FIRE! (software trigger)")
cc.set_control(1, 0x00000003)
time.sleep(0.5)  # Wait for pulse sequence to complete

print("Step 9: Clear fault, return to IDLE")
cc.set_control(1, 0x00000008)
time.sleep(0.01)
cc.set_control(1, 0x00000000)

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
- **Solution:** Check that durations are non-zero, pulse fault_clear (CR1[3])

### If outputs happen but you can't see them:
- **Problem:** Pulses are too fast (100-200μs)
- **Solution:**
  - Use oscilloscope with edge trigger on Output1/Output2
  - Set very long durations (CR4 = 0x01000000 for ~67ms trigger pulse)
  - Monitor OutputC instead (it holds final state)

### If config changes don't take effect:
- **Problem:** Configuration registers only update in INITIALIZING state
- **Solution:** Pulse fault_clear (CR1[3]) to force re-initialization, then re-arm

### If nothing happens at all:
- **Problem:** Network timeout, bitstream not responding
- **Solution:**
  - Verify device IP is correct
  - Try power-cycling the Moku:Go
  - Re-upload bitstream

---

## Key Insights

1. **OutputC is your best friend** - It shows FSM state persistently
2. **Outputs are FAST** - 100-200μs pulses are hard to see without a scope
3. **State sequence is:** INITIALIZING (0.0V) → IDLE (0.5V) → ARMED (1.0V) → FIRING (1.5V) → COOLDOWN (2.0V) → back to IDLE (0.5V)
4. **Minimum working config requires:**
   - CR0[31:29] = 0b111 (FORGE_READY)
   - CR1[0] = 1 (arm)
   - CR2[15:0] = non-zero voltage for OutputA
   - CR3[15:0] = non-zero voltage for OutputB
   - CR4 = non-zero duration for OutputA
   - CR5 = non-zero duration for OutputB
   - CR7 = non-zero cooldown
   - CR1[1] = 1 (trigger!)

5. **Config register gotcha:** CR2-CR10 only propagate in INITIALIZING state. To apply new config mid-operation, pulse fault_clear first!

6. **The magic bit sequence is:** CR0 → CR1[0] → CR2-7 (config) → CR1[1] (fire!)

---

## Related Documents

- [HVS Encoding](hvs.md) - Understanding OutputC voltage encoding
- [Network Register Sync](network-register-sync.md) - Why config only updates in INITIALIZING
- [Custom Wrapper](custom-wrapper.md) - Control register details
- [Hardware Tests](../tests/hw/) - Automated hardware test suite

---

**Last Updated:** 2025-01-28  
**Status:** Migrated from review_me, integrated into docs/

