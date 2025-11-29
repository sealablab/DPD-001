--------------------------------------------------------------------------------
-- File: DPD.vhd
-- Author: Moku Instrument Forge Team
-- Date: 2025-11-29
-- Version: 5.0 (Unified BOOT+DPD integration)
--
-- Description:
--   CustomWrapper architecture for unified BOOT+DPD bitstream.
--   This is a thin wrapper that instantiates B0_BOOT_TOP (BOOT dispatcher),
--   which provides runtime-configurable switching between:
--     - BOOT subsystem (platform initialization)
--     - BIOS subsystem (diagnostic signals)
--     - LOADER subsystem (ENV_BBUF population)
--     - PROG subsystem (DPD application)
--
-- CR0 Bit Layout (from BOOT-FSM-spec.md):
--   CR0[31]    = R (Ready)       ─┐
--   CR0[30]    = U (User)         ├─ RUN gate (must all be '1' for operation)
--   CR0[29]    = N (clkEnable)   ─┘
--   CR0[28]    = P (Program)     ─┐
--   CR0[27]    = B (BIOS)         ├─ Module select (mutually exclusive)
--   CR0[26]    = L (Loader)       │
--   CR0[25]    = R (Reset)       ─┘
--   CR0[24]    = RET             ─── Return to BOOT_P1 (from BIOS/LOAD only)
--   CR0[23:3]  = Reserved
--   CR0[2]     = arm_enable      (DPD lifecycle, active in PROG mode)
--   CR0[1]     = fault_clear     (DPD lifecycle, active in PROG mode)
--   CR0[0]     = sw_trigger      (DPD lifecycle, active in PROG mode)
--
-- Command Reference:
--   0xE0000000 = RUN  (BOOT_P0 → BOOT_P1)
--   0xF0000000 = RUNP (BOOT_P1 → PROG_ACTIVE, one-way)
--   0xE8000000 = RUNB (BOOT_P1 → BIOS_ACTIVE)
--   0xE4000000 = RUNL (BOOT_P1 → LOAD_ACTIVE)
--   0xE2000000 = RUNR (soft reset to BOOT_P0)
--   0xE1000000 = RET  (return to BOOT_P1 from BIOS/LOAD)
--
-- Architecture Hierarchy:
--   Layer 0: DPD.vhd (THIS FILE - thin wrapper, binds CustomWrapper entity)
--   Layer 1: B0_BOOT_TOP.vhd (BOOT dispatcher FSM, 6-state)
--   Layer 2: DPD_shim.vhd (PROG mode only, CR2-CR10 mapping + HVS)
--   Layer 3: DPD_main.vhd (DPD FSM application logic)
--
-- HVS Encoding:
--   Pre-PROG (BOOT/BIOS/LOADER): 197 units/state (~30mV steps)
--     BOOT_P0:     0.000V
--     BOOT_P1:     0.030V
--     BIOS states: 0.24V - 0.33V
--     LOAD states: 0.48V - 0.60V
--
--   PROG (DPD): 3277 units/state (~500mV steps)
--     DPD_IDLE:     0.5V
--     DPD_ARMED:    1.0V
--     DPD_FIRING:   1.5V
--     DPD_COOLDOWN: 2.0V
--
-- Platform: Moku:Go (xc7z020clg400-1)
-- Clock Frequency: 125 MHz
--
-- See Also:
--   docs/BOOT-FSM-spec.md (authoritative BOOT specification)
--   docs/api-v4.md (DPD register map for PROG mode)
--   handoffs/20251129/INTEGRATION-Architecture-Design.md (design rationale)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

architecture bpd_forge of CustomWrapper is

    ----------------------------------------------------------------------------
    -- Component Declaration
    --
    -- The BOOT dispatcher is defined in B0_BOOT_TOP.vhd as:
    --   architecture boot_dispatcher of BootWrapper
    --
    -- We use explicit component declaration for VHDL-93 compatibility.
    ----------------------------------------------------------------------------
    component BootWrapper is
        port (
            -- Clock and Reset
            Clk     : in  std_logic;
            Reset   : in  std_logic;

            -- Input signals (ADC data, signed 16-bit)
            InputA  : in  signed(15 downto 0);
            InputB  : in  signed(15 downto 0);
            InputC  : in  signed(15 downto 0);

            -- Output signals (DAC data, signed 16-bit)
            OutputA : out signed(15 downto 0);
            OutputB : out signed(15 downto 0);
            OutputC : out signed(15 downto 0);

            -- Control registers (32-bit each)
            Control0  : in  std_logic_vector(31 downto 0);
            Control1  : in  std_logic_vector(31 downto 0);
            Control2  : in  std_logic_vector(31 downto 0);
            Control3  : in  std_logic_vector(31 downto 0);
            Control4  : in  std_logic_vector(31 downto 0);
            Control5  : in  std_logic_vector(31 downto 0);
            Control6  : in  std_logic_vector(31 downto 0);
            Control7  : in  std_logic_vector(31 downto 0);
            Control8  : in  std_logic_vector(31 downto 0);
            Control9  : in  std_logic_vector(31 downto 0);
            Control10 : in  std_logic_vector(31 downto 0);
            Control11 : in  std_logic_vector(31 downto 0);
            Control12 : in  std_logic_vector(31 downto 0);
            Control13 : in  std_logic_vector(31 downto 0);
            Control14 : in  std_logic_vector(31 downto 0);
            Control15 : in  std_logic_vector(31 downto 0)
        );
    end component BootWrapper;

begin

    ----------------------------------------------------------------------------
    -- BOOT Dispatcher Instantiation
    --
    -- The BOOT dispatcher (B0_BOOT_TOP.vhd, architecture boot_dispatcher) is
    -- the actual top-level logic. It handles:
    --
    -- 1. BOOT FSM (6 states: BOOT_P0, BOOT_P1, BIOS_ACTIVE, LOAD_ACTIVE,
    --              PROG_ACTIVE, FAULT)
    -- 2. Module selection via CR0[28:25] (P/B/L/R bits)
    -- 3. Output muxing (combinatorial, no clock delay)
    -- 4. HVS encoding:
    --    - Pre-PROG encoding (197 units/state) for BOOT/BIOS/LOADER
    --    - PROG encoding (3277 units/state) for DPD application
    -- 5. Instantiation of sub-modules:
    --    - B1_BOOT_BIOS (diagnostic signals)
    --    - L2_BUFF_LOADER (ENV_BBUF population + CRC validation)
    --    - DPD_shim → DPD_main (probe driver application)
    --
    -- All MCC signals are passed through directly with no modification.
    ----------------------------------------------------------------------------
    BOOT_DISPATCHER: BootWrapper
        port map (
            -- Clock and Reset
            Clk   => Clk,
            Reset => Reset,

            -- MCC I/O (straight passthrough)
            InputA  => InputA,
            InputB  => InputB,
            InputC  => InputC,
            OutputA => OutputA,
            OutputB => OutputB,
            OutputC => OutputC,

            -- Control Registers (all 16 passed through)
            Control0  => Control0,
            Control1  => Control1,
            Control2  => Control2,
            Control3  => Control3,
            Control4  => Control4,
            Control5  => Control5,
            Control6  => Control6,
            Control7  => Control7,
            Control8  => Control8,
            Control9  => Control9,
            Control10 => Control10,
            Control11 => Control11,
            Control12 => Control12,
            Control13 => Control13,
            Control14 => Control14,
            Control15 => Control15
        );

end architecture bpd_forge;

--------------------------------------------------------------------------------
-- Usage Instructions
--------------------------------------------------------------------------------
--
-- 1. Platform Boot Sequence:
--
--    a) Power-on: Control0 = 0x00000000 → BOOT_P0 (initial state)
--    b) Set RUN gate: Control0 = 0xE0000000 → BOOT_P1 (dispatcher ready)
--
-- 2. Module Selection (from BOOT_P1):
--
--    a) Activate DPD Application (PROG mode):
--       Control0 = 0xF0000000  # RUNP
--       → BOOT transitions to PROG_ACTIVE
--       → DPD_shim takes control, CR2-CR10 become active
--       → DPD FSM runs (IDLE → ARMED → FIRING → COOLDOWN)
--       → This is a ONE-WAY transition (cannot return to BOOT)
--
--    b) Activate BIOS (diagnostics):
--       Control0 = 0xE8000000  # RUNB
--       → BIOS outputs known reference signals for wiring validation
--       → Can return via RET command
--
--    c) Activate LOADER (buffer population):
--       Control0 = 0xE4000000  # RUNL
--       → LOADER accepts data via CR1-CR4, populates ENV_BBUFs
--       → Can return via RET command
--
--    d) Return from BIOS/LOADER to dispatcher:
--       Control0 = 0xE1000000  # RET
--       → Returns to BOOT_P1 (dispatcher state)
--       → NOT available from PROG mode
--
--    e) Soft reset:
--       Control0 = 0xE2000000  # RUNR
--       → Returns to BOOT_P0 (clears ENV_BBUFs)
--
-- 3. DPD Application Mode (PROG_ACTIVE):
--
--    Once RUNP is issued, the DPD application controls all outputs.
--    This is a **one-way transition** - cannot return to BOOT without reset.
--
--    DPD uses CR0[2:0] for lifecycle control:
--    - CR0[2] = arm_enable  (level-sensitive, enable FSM arming)
--    - CR0[1] = fault_clear (edge-triggered, clear fault state)
--    - CR0[0] = sw_trigger  (edge-triggered, software trigger pulse)
--
--    DPD uses CR2-CR10 for configuration:
--    - CR2: Trigger threshold [31:16] + trigger output voltage [15:0]
--    - CR3: Intensity output voltage [15:0]
--    - CR4-CR7: Timing (trigger duration, intensity duration, timeout, cooldown)
--    - CR8: Monitor threshold [31:16] + auto_rearm[2] + polarity[1] + enable[0]
--    - CR9-CR10: Monitor window timing
--
--    See docs/api-v4.md for complete register specification.
--
-- 4. Expert Workflow Example:
--
--    # 1. Boot platform
--    Control0 = 0xE0000000  # RUN (BOOT_P0 → BOOT_P1)
--
--    # 2. Load ENV_BBUFs with configuration data
--    Control0 = 0xE4000000  # RUNL (enter LOADER mode)
--    # ... (populate buffers via LOADER protocol - see LOAD-FSM-spec.md)
--    Control0 = 0xE1000000  # RET (return to BOOT_P1)
--
--    # 3. Run diagnostics (optional)
--    Control0 = 0xE8000000  # RUNB (enter BIOS mode)
--    # ... (observe BIOS outputs on oscilloscope)
--    Control0 = 0xE1000000  # RET (return to BOOT_P1)
--
--    # 4. Launch DPD application (one-way!)
--    Control0 = 0xF0000000  # RUNP (enter PROG mode)
--    # ... (configure DPD via CR2-CR10, arm/trigger via CR0[2:0])
--    # ... (DPD application runs normally)
--
-- 5. HVS Debugging via OutputC:
--
--    OutputC encodes FSM state as analog voltage for oscilloscope debugging.
--    This allows "train like you fight" development - same bitstream for
--    development and production.
--
--    Pre-PROG encoding (BOOT/BIOS/LOADER): 197 units/state (~30mV steps)
--    - BOOT_P0:      0.000V (initial state)
--    - BOOT_P1:      0.030V (dispatcher ready)
--    - BIOS_IDLE:    0.24V
--    - BIOS_RUN:     0.27V
--    - BIOS_DONE:    0.30V
--    - LOAD_P0:      0.48V
--    - LOAD_P1:      0.51V (data transfer)
--    - LOAD_P2:      0.54V (CRC validation)
--    - LOAD_P3:      0.57V (complete)
--
--    PROG encoding (DPD): 3277 units/state (~500mV steps)
--    - DPD_INITIALIZING: 0.0V  (transient)
--    - DPD_IDLE:         0.5V  (waiting for arm)
--    - DPD_ARMED:        1.0V  (waiting for trigger)
--    - DPD_FIRING:       1.5V  (driving outputs)
--    - DPD_COOLDOWN:     2.0V  (thermal safety delay)
--    - DPD_FAULT:        Negative voltage (sign flip)
--
--    **Key Transition**: BOOT_P1 → DPD_IDLE shows as 0.03V → 0.5V on scope.
--    This validates successful RUNP handoff.
--
-- 6. Backward Compatibility:
--
--    Existing DPD Python code can be updated with minimal changes:
--
--    OLD (DPD-only bitstream):
--      dpd.set_control(0, 0xE0000000)  # Enable RUN
--      dpd.set_control(2, threshold)   # Configure
--
--    NEW (unified bitstream):
--      dpd.set_control(0, 0xE0000000)  # RUN → BOOT_P1
--      dpd.set_control(0, 0xF0000000)  # RUNP → PROG_ACTIVE
--      dpd.set_control(2, threshold)   # Configure (same as before)
--
--    The RUNP step is the only addition. All DPD configuration (CR2-CR10)
--    and lifecycle controls (CR0[2:0]) work identically.
--
-- 7. Resource Budget:
--
--    Target FPGA: xc7z020clg400-1 (Zynq-7020)
--    - 85K logic cells
--    - 140 BRAM blocks (18Kb each)
--    - 220 DSP slices
--
--    Estimated usage:
--    - BOOT+BIOS+LOADER: ~15% logic, 4 BRAM blocks, 0 DSP
--    - DPD application:  ~10% logic, 0 BRAM, 0 DSP
--    - Total:            ~25% logic, 4 BRAM blocks, 0 DSP
--
--    Target: < 50% FPGA capacity (met with significant margin)
--
--------------------------------------------------------------------------------
