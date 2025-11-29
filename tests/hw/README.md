# Hardware Test Plumbing

This directory contains the **hardware plumbing** for running tests against a
real Moku device. It is shared infrastructure that the DPD and (future) BOOT
hardware tests can both use.

### Files

- `plumbing.py`  
  - Defines `MokuConfig` – basic connection/slot configuration.  
  - Defines `MokuSession` – async context manager that:
    - Connects to the device (via `moku_cli_common` if available).  
    - Deploys `Oscilloscope` and `CloudCompile` instruments.  
    - Sets up routing so `CloudCompile` `OutputC` feeds the oscilloscope
      (`Slot{cc}OutC → Slot{osc}InA`) for HVS/state observation.  
    - Cleans up and relinquishes ownership on exit.  
  - Provides `create_hardware_harness(...)` convenience helper that returns
    `(session, MokuAsyncHarness)`.

> **DPD usage:** `tests/run.py --backend hw` uses `MokuSession` under the hood
> to create a `MokuAsyncHarness` and then runs the selected DPD test module’s
> `run_hardware_tests()` (when present) or a basic connectivity test.

> **BOOT roadmap:** BOOT/LOADER hardware tests will reuse the same plumbing but
> with BOOT‑specific constants (`tests/lib/boot_hw.py`, `boot_timing.py`) and
> state decoding based on `BOOT_HVS` from `py_tools/boot_constants.py`.

---

## P1 BOOT Hardware Smoke Test – Design Note

Goal: **verify the BOOT dispatcher’s HVS states on real hardware** using the
same pattern as the DPD basic hardware test.

High-level plan (to be implemented in a `boot` test module later):

1. **Harness setup**
   - Use `MokuSession` + `MokuAsyncHarness` from `plumbing.py`.  
   - State reader should interpret `OutputC` using `BOOT_HVS` instead of the
     DPD 0.5 V/state scale.

2. **Initial state check**
   - After bitstream deployment, read current state via `state_reader`.  
   - Expect `BOOT_P0` (≈0.0 V, digital ≈0). If in `FAULT`, log and attempt a
     `fault_clear` (CR0[1]) once before failing.

3. **RUN gate → `BOOT_P1`**
   - Write `CMD.RUN` (`0xE0000000`) to CR0 via the hardware controller.  
   - Wait a modest settling time (e.g. 200 ms using `wait_cycles`).  
   - Expect `BOOT_P1` (≈0.2 V, digital ≈`BOOT_HVS.DIGITAL_P1` within tolerance).

4. **Module select spot checks**
   - Optionally, perform one or two single-step transitions:
     - `CMD.RUNL` → expect LOADER context (`LOAD_ACTIVE` / LOADER_P0 encoding).  
     - `CMD.RUNR` → return to `BOOT_P0`.  
   - Keep this P1 test focused on **presence and stability** of BOOT HVS steps,
     not full LOADER protocol.

5. **Exit criteria**
   - Test passes if:
     - Hardware can be contacted,  
     - HVS reading transitions from 0.0 V → 0.2 V after `CMD.RUN`,  
     - Optional RUNL/RUNR spot checks behave as expected.  
   - Any persistent mismatch between expected and measured voltage/state should
     be reported with both **digital** and **voltage** values for oscilloscope
     correlation.



