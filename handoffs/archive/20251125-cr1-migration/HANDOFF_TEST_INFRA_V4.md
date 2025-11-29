# Handoff: Test Infrastructure Update for API v4.0

**Date:** 2025-11-26
**Context:** Updating test infrastructure to match v4.0 API (CR0-based lifecycle control)

---

## What Was Done (Phases 1-4)

### Phase 1: Deleted Legacy Code ✅
```
DELETED:
- tests/sim/dpd/P1_dpd_trigger_debug.py
- tests/sim/dpd/dpd_debug_constants.py
- tests/sim/dpd/dpd_debug_helpers.py
- tests/shared/async_adapter.py
- tests/shared/constants.py
```

### Phase 2: Updated DPDConfig ✅
**File:** `tests/lib/dpd_config.py`
- Removed: arm_enable, fault_clear, sw_trigger, sw_trigger_enable, hw_trigger_enable
- Kept: auto_rearm_enable (now builds to CR8[2])
- Now only builds CR2-CR10 (config registers)
- CR0/CR1 handled by adapter methods

### Phase 3: Updated Adapter Interface ✅
**File:** `tests/adapters/base.py`
- Added `_forge_state` and `_lifecycle_state` tracking
- Added FORGE methods: `enable_forge()`, `disable_forge()`
- Added lifecycle methods: `arm()`, `disarm()`, `trigger()`, `clear_fault()`
- Removed: `set_cr1()`, `set_forge_ready()`, `clear_forge_ready()`
- Updated `arm_fsm()`, `software_trigger()`, `reset_to_idle()`

### Phase 4: Updated lib Exports ✅
**Files:** `tests/lib/hw.py`, `tests/lib/__init__.py`
- Added: CR8, cr0_build, cr0_extract, cr8_build
- Removed: cr1_build, cr1_extract

---

## What Remains (Phases 5-7)

### Phase 5: Create Greenfield P1 Tests
**File:** `tests/sim/dpd/P1_basic.py`

Rewrite with tests following CR0 hierarchy:
```python
T1_forge_run_gate()      # CR0[31:29] - FORGE safety
T2_arm_control()         # CR0[2] - arm/disarm
T3_software_trigger()    # CR0[0] - atomic trigger
T4_fault_clear()         # CR0[1] - fault recovery
T5_full_cycle()          # Complete FSM cycle
```

Test pattern:
```python
harness = get_harness("cocotb", dut=dut)
await harness.controller.enable_forge()
await harness.wait_for_state("IDLE")
await harness.controller.arm()
await harness.controller.trigger()  # Single atomic write!
```

### Phase 6: Update Adapter Implementations
**Files:**
- `tests/adapters/cocotb.py` - CocoTB implementation
- `tests/adapters/moku.py` - Hardware implementation

Both need:
- Call `super().__init__()` to initialize state tracking
- Inherit new methods from base class (they're not abstract)

### Phase 7: Verify
```bash
cd tests/sim && python run.py
```

---

## Key Design Decisions

1. **CR0 is sacred** - Only `enable_forge()`/`disable_forge()` touch [31:29]
2. **Lifecycle via methods** - Only `arm()`/`trigger()`/`clear_fault()` touch [2:0]
3. **DPDConfig = CR2-CR10 only** - No lifecycle in config
4. **Single atomic trigger** - `trigger()` writes 0xE0000005 in one operation

---

## Reference Files

- **Plan:** `/Users/johnycsh/.claude/plans/lovely-tumbling-curry.md`
- **API Spec:** `docs/api-v4.md`
- **Constants:** `py_tools/dpd_constants.py`
- **Adapter Base:** `tests/adapters/base.py`

---

## Quick Start for Next Session

```
Continue implementing the v4.0 test infrastructure update.

Phases 1-4 are complete (legacy deletion, DPDConfig, adapter base, lib exports).

Remaining:
1. Phase 5: Rewrite tests/sim/dpd/P1_basic.py with new test pattern
2. Phase 6: Update tests/adapters/cocotb.py and moku.py
3. Phase 7: Run tests and verify

See HANDOFF_TEST_INFRA_V4.md and the plan at
~/.claude/plans/lovely-tumbling-curry.md for full details.
```
