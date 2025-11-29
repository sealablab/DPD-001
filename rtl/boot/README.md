created: 2025-11-28
modified: 2025-11-28 02:27:49
accessed: 2025-11-28 02:20:45
---
## `boot/` [README](rtl/boot/README.md)

This directory contains the BOOT subsystem RTL for the CR0 `RUN` boot process.
The BOOT FSM is the **dispatcher** that decides whether the platform is in:

- **BOOT** (P0 / P1)
- **BIOS** diagnostics
- **LOADER** (buffer loading into ENV_BBUF)
- **PROG** (main DPD application)

The authoritative behavioral spec is `docs/BOOT-FSM-spec.md`.

### File Map (RTL)

- **`B0_BOOT_TOP.vhd`**  
  Top‑level BOOT dispatcher FSM. Implements:
  - RUN gate (`CR0[31:29]`) and module select (`CR0[28:25]`) decoding  
  - 6‑state BOOT FSM (P0, P1, BIOS_ACTIVE, LOAD_ACTIVE, PROG_ACTIVE, FAULT)  
  - Combinatorial output muxing for `OutputA/B/C`  
  - Instantiation of `L2_BUFF_LOADER` for ENV_BBUF writes  
  - HVS encoding using compressed 0.2 V/state (1311 digital units)

- **`B1_BOOT_BIOS.vhd`**  
  Placeholder for BIOS diagnostics module. Planned behavior:
  - Runs under BOOT supervision in `BIOS_ACTIVE` state  
  - Drives `OutputC` at 0.4 V when active (same HVS scale as BOOT)  
  - Returns to BOOT via `CR0[24] = RET`  
  See `B1_BOOT_BIOS.vhd.md` for design notes.

- **`L2_BUFF_LOADER.vhd`**  
  LOADER FSM responsible for filling the four ENV_BBUF BRAM regions:
  - Uses `CR0[23:21]` (buffer count + strobe) and `CR1` (data/CRC)  
  - 4‑state LOADER FSM (P0–P3 plus FAULT) with CRC‑16 validation  
  - HVS output encodes LOADER state (0.0 V–0.6 V, 0.2 V steps)

- **`loader_crc16.vhd`**  
  Pure combinatorial CRC‑16‑CCITT implementation used by LOADER.

- **`P3_PROG_START.vhd`**  
  Placeholder for PROG handoff stage. Intended responsibilities:
  - One‑way handoff into the DPD application (`PROG_ACTIVE`)  
  - No return path to BOOT; faults owned by PROG  
  See `P3_PROG_START.vhd.md` for future design.

- **`BootWrapper_test_stub.vhd`**  
  CloudCompile wrapper stub for BOOT subsystem used by CocoTB:
  - Declares `entity BootWrapper` with Moku CloudCompile interface  
  - Avoids entity name collision with `rtl/CustomWrapper_test_stub.vhd`  
  - Bound to `architecture boot_forge of BootWrapper` in `B0_BOOT_TOP.vhd`

### Related Python / Tools

- **`py_tools/boot_constants.py`** – Python mirror of `forge_common_pkg.vhd` for BOOT/LOADER
  (CR0 command values, BOOT/LOAD state enums, HVS scaling, ENV_BBUF sizes, CRC params).
- **`py_tools/boot_shell.py`** – Interactive BOOT shell:
  - Context‑aware prompts (`RUN>`, `LOAD[…] >`, `BIOS>`, `PROG$`)  
  - Maps shell commands to CR0 commands (`run`, `l`, `b`, `p`, `r`, `RET`)  
  - Optional live HVS monitor that interprets `OutputC` based on context.

### Simulation Tests

All BOOT/LOADER simulation tests live under `tests/sim` and use CocoTB + GHDL.

- **Dispatcher FSM (BOOT)**  
  - `tests/sim/boot_fsm/P1_basic.py` – P1 basic BOOT dispatcher tests  
    - Reset → `BOOT_P0`  
    - RUN (`CMD.RUN`) → `BOOT_P1`  
    - RUNL / RUNB / RUNP / RUNR transitions  
    - HVS voltage checks for each state (0.0 V–0.8 V)

- **LOADER FSM**  
  - `tests/sim/loader/P1_basic.py` – P1 basic LOADER tests  
    - `RUNL` entry from BOOT (`LOAD_ACTIVE` context)  
    - P0 → P1 on setup strobe  
    - Data transfer strobes and 1024‑word completion (CRC happy‑path)

- **Runner**  
  - `tests/sim/boot_run.py` – BOOT‑only sim runner  
    - Default: `TEST_MODULE=boot_fsm.P1_basic`  
    - Override: `TEST_MODULE=loader.P1_basic` for LOADER tests  
    - Sources: `forge_common_pkg.vhd`, `boot/loader_crc16.vhd`,
      `boot/L2_BUFF_LOADER.vhd`, `boot/BootWrapper_test_stub.vhd`,
      `boot/B0_BOOT_TOP.vhd`

Quickstart:

```bash
cd tests/sim

# BOOT dispatcher tests
uv run python boot_run.py

# LOADER tests
TEST_MODULE=loader.P1_basic uv run python boot_run.py
```

### Pre‑requisites

- **API v4.0 control model** – Read `docs/api-v4.md` for CR0 layout and lifecycle.  
- **BOOT FSM details** – Read `docs/BOOT-FSM-spec.md` (authoritative).  
- **LOADER FSM details** – Read `docs/LOAD-FSM-spec.md` (when promoted to AUTHORITATIVE).

The `.vhd.md` sidecar docs (`B0_BOOT_TOP.vhd.md`, `B1_BOOT_BIOS.vhd.md`,
`L2_BUFF_LOADER.vhd.md`, `P3_PROG_START.vhd.md`) should be kept in sync with the
RTL behavior and the test expectations above.

---
