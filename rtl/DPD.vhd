--------------------------------------------------------------------------------
-- File: DPD.vhd
-- Author: Moku Instrument Forge Team
-- Date: 2025-11-26
-- Version: 4.0 (API-breaking refactor - CR0 lifecycle consolidation)
--
-- Description:
--   CustomWrapper architecture for Demo Probe Driver using Forge 3-layer pattern.
--   Implements FORGE_READY control scheme (CR0[31:29]) for safe MCC integration.
--
-- API Version 4.0 Changes:
--   - All lifecycle controls now in CR0 (arm_enable, fault_clear, sw_trigger)
--   - CR1 reserved for future campaign mode
--   - auto_rearm_enable moved to CR8[2]
--   - Removed sw_trigger_enable and hw_trigger_enable (not needed)
--
-- CR0 Bit Layout:
--   CR0[31]   = forge_ready       (R) ─┐
--   CR0[30]   = user_enable       (U)  ├── "RUN" - FORGE safety gate
--   CR0[29]   = clk_enable        (N) ─┘
--   CR0[28]   = campaign_enable   (P) [reserved]
--   CR0[27:3] = reserved
--   CR0[2]    = arm_enable        (A)
--   CR0[1]    = fault_clear       (C) [edge-triggered, auto-clear in shim]
--   CR0[0]    = sw_trigger        (T) [edge-triggered, auto-clear in shim]
--
-- Register Mapping:
--   CR0        → Lifecycle control (FORGE + arm/trigger/fault)
--   CR1        → Campaign control (reserved for future)
--   CR2-CR10   → Configuration registers (sync-safe gated)
--   CR11-CR15  → Campaign statistics (reserved for future)
--
-- Architecture:
--   Layer 1: DPD.vhd (THIS FILE - TOP, extracts CR0 bits)
--   Layer 2: DPD_shim.vhd (register mapping, edge detection, HVS encoding)
--   Layer 3: DPD_main.vhd (FSM logic)
--
-- Platform: Moku:Go
-- Clock Frequency: 125 MHz
--
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

architecture bpd_forge of CustomWrapper is

    ----------------------------------------------------------------------------
    -- FORGE Control Signals (extracted from CR0[31:29])
    -- These are combinational (no registration) for immediate response
    ----------------------------------------------------------------------------
    signal forge_ready  : std_logic;
    signal user_enable  : std_logic;
    signal clk_enable   : std_logic;
    signal loader_done  : std_logic;

    ----------------------------------------------------------------------------
    -- Lifecycle Control Signals (extracted from CR0[2:0])
    -- Combinational extraction at TOP for direct path to shim
    ----------------------------------------------------------------------------
    signal arm_enable   : std_logic;
    signal fault_clear  : std_logic;
    signal sw_trigger   : std_logic;

begin

    ----------------------------------------------------------------------------
    -- Extract FORGE Control Bits from Control0 (Combinational)
    --
    -- CR0[31] = forge_ready  (R) - set by loader after deployment
    -- CR0[30] = user_enable  (U) - user control
    -- CR0[29] = clk_enable   (N) - clock gating
    --
    -- These three bits form "RUN" - all must be set for FSM operation
    ----------------------------------------------------------------------------
    forge_ready <= Control0(31);
    user_enable <= Control0(30);
    clk_enable  <= Control0(29);

    ----------------------------------------------------------------------------
    -- Extract Lifecycle Control Bits from Control0 (Combinational)
    --
    -- CR0[2] = arm_enable   (A) - arm FSM (IDLE → ARMED)
    -- CR0[1] = fault_clear  (C) - clear fault state (edge-triggered)
    -- CR0[0] = sw_trigger   (T) - software trigger (edge-triggered)
    --
    -- These are extracted at TOP level for direct path, then edge detection
    -- and auto-clear are handled in the shim layer.
    ----------------------------------------------------------------------------
    arm_enable  <= Control0(2);
    fault_clear <= Control0(1);
    sw_trigger  <= Control0(0);

    ----------------------------------------------------------------------------
    -- BRAM Loader Done Signal
    --
    -- TODO: Connect to actual BRAM loader when implemented
    -- For now, tie to '1' (no BRAM loading required)
    ----------------------------------------------------------------------------
    loader_done <= '1';

    ----------------------------------------------------------------------------
    -- Instantiate DPD Forge Shim (Layer 2)
    --
    -- The shim layer:
    --   1. Receives FORGE control and lifecycle signals
    --   2. Implements edge detection for fault_clear and sw_trigger
    --   3. Implements auto-clear (pulse stretcher) for edge-triggered signals
    --   4. Maps CR2-CR10 to friendly names (sync-safe gated)
    --   5. Computes global_enable via combine_forge_ready()
    --   6. Instantiates DPD_main (Layer 3)
    --   7. Generates HVS encoding on OutputC
    ----------------------------------------------------------------------------
    DPD_SHIM_INST: entity WORK.DPD_shim
        port map (
            -- Clock and Reset
            Clk   => Clk,
            Reset => Reset,

            -- FORGE Control (3-bit "RUN" scheme)
            forge_ready  => forge_ready,
            user_enable  => user_enable,
            clk_enable   => clk_enable,
            loader_done  => loader_done,

            -- Lifecycle Control (from CR0, direct path)
            arm_enable   => arm_enable,
            fault_clear  => fault_clear,
            sw_trigger   => sw_trigger,

            -- Configuration Registers (CR2-CR10, sync-safe gated)
            app_reg_2  => Control2,
            app_reg_3  => Control3,
            app_reg_4  => Control4,
            app_reg_5  => Control5,
            app_reg_6  => Control6,
            app_reg_7  => Control7,
            app_reg_8  => Control8,
            app_reg_9  => Control9,
            app_reg_10 => Control10,

            -- BRAM Interface (reserved for future use)
            bram_addr => (others => '0'),
            bram_data => (others => '0'),
            bram_we   => '0',

            -- MCC I/O
            InputA  => InputA,
            InputB  => InputB,
            OutputA => OutputA,
            OutputB => OutputB,
            OutputC => OutputC
        );

end architecture bpd_forge;

--------------------------------------------------------------------------------
-- Usage Instructions
--------------------------------------------------------------------------------
--
-- 1. FORGE Control Initialization Sequence ("RUN"):
--
--    a) Power-on: Control0 = 0x00000000
--       → All disabled (safe default)
--
--    b) MCC loader sets Control0[31] = 1
--       → forge_ready=1 (R - deployment complete)
--
--    c) User enables module via GUI: Control0[30] = 1
--       → user_enable=1 (U)
--
--    d) User enables clock: Control0[29] = 1
--       → clk_enable=1 (N)
--
--    e) Module operates: global_enable = R AND U AND N AND loader_done
--
-- 2. Lifecycle Control (CR0[2:0]):
--
--    CR0[2] = arm_enable   : Level-sensitive, IDLE → ARMED when high
--    CR0[1] = fault_clear  : Edge-triggered, FAULT → INITIALIZING on 0→1
--    CR0[0] = sw_trigger   : Edge-triggered, ARMED → FIRING on 0→1
--
--    Edge-triggered signals have hardware auto-clear (4 cycle pulse width)
--
-- 3. One-Off Trigger Workflow:
--
--    # Enable module
--    set_control(0, 0xE0000000)  # RUN enabled
--
--    # Configure timing (CR2-CR10)
--    set_control(2, threshold_and_voltage)
--    set_control(4, trig_duration)
--    ...
--
--    # Arm
--    set_control(0, 0xE0000004)  # RUN + arm_enable
--
--    # Fire (software trigger) - single atomic write!
--    set_control(0, 0xE0000005)  # RUN + arm_enable + sw_trigger
--
--    # Auto-clear handles sw_trigger, or explicitly clear:
--    set_control(0, 0xE0000004)  # RUN + arm_enable (re-arm for next shot)
--
-- 4. Configuration Register Mapping (CR2-CR10):
--
--    CR2[31:16] : Input trigger voltage threshold (mV, signed)
--    CR2[15:0]  : Trigger output voltage (mV)
--    CR3[15:0]  : Intensity output voltage (mV)
--    CR4[31:0]  : Trigger pulse duration (clock cycles)
--    CR5[31:0]  : Intensity pulse duration (clock cycles)
--    CR6[31:0]  : Trigger wait timeout (clock cycles)
--    CR7[31:0]  : Cooldown interval (clock cycles)
--    CR8[31:16] : Monitor threshold voltage (mV, signed)
--    CR8[2]     : auto_rearm_enable (burst mode)
--    CR8[1]     : monitor_expect_negative
--    CR8[0]     : monitor_enable
--    CR9[31:0]  : Monitor window start delay (clock cycles)
--    CR10[31:0] : Monitor window duration (clock cycles)
--
--    Note: All timing values are pre-converted to clock cycles by Python client
--
-- 5. MCC I/O Mapping:
--
--    InputA  → External trigger input (ADC, ±5V)
--    InputB  → Probe monitor feedback (ADC, ±5V)
--    OutputA → Trigger output (DAC, ±5V)
--    OutputB → Intensity output (DAC, ±5V)
--    OutputC → FSM state debug (HVS encoding, signed 16-bit)
--
--------------------------------------------------------------------------------
