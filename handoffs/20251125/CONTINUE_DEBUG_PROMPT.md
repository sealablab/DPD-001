# Quick Prompt for Continuing FSM Debug

**Copy this prompt to start a new conversation:**

---

I'm debugging an FSM spurious trigger issue in the DPD project. Please read the handoff document and continue the investigation.

**Handoff Document:**
- `DPD-001/HANDOFF_FSM_DEBUG_CONTINUATION.md`

**Quick Summary:**
- Trigger path metavalues are FIXED ✅
- FSM still transitions to FIRING incorrectly ❌
- FSM skips IDLE/ARMED, goes directly INITIALIZING → FIRING
- Happens at cycle 1 even though `combined_trigger = '0'`

**What I need:**
1. Investigate why FSM goes to FIRING when `ext_trigger_in` should be '0'
2. Check FSM state initialization and next-state logic
3. Monitor `ext_trigger_in` signal directly in debug test
4. Identify root cause and implement fix

**Key Files:**
- `rtl/DPD_shim.vhd` - Trigger path (already fixed)
- `rtl/DPD_main.vhd` - FSM logic (needs investigation)
- `tests/sim/dpd_wrapper_tests/P1_dpd_trigger_debug.py` - Debug test

**Test Command:**
```bash
cd /Users/johnycsh/DPD/DPD-001/tests/sim
TEST_MODULE=dpd_wrapper_tests.P1_dpd_trigger_debug uv run python run.py
```

Please continue the investigation using the cocotb test runner agent patterns.

---

