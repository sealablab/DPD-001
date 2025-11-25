--------------------------------------------------------------------------------
-- File: DPD.vhd
-- Author: Moku Instrument Forge Team
-- Date: 2025-11-18
-- Version: 3.1 (TOP level file)
--
-- Description:
--   CustomWrapper architecture for Basic Probe Driver using Forge 3-layer pattern.
--   Implements FORGE_READY control scheme (CR0[31:29]) for safe MCC integration.
--
-- FORGE Control Scheme (CR0[31:29]):
--   CR0[31] = forge_ready  - Set by MCC loader after deployment
--   CR0[30] = user_enable  - User control (GUI toggle)
--   CR0[29] = clk_enable   - Clock gating control
--   loader_done            - BRAM loader completion (tied to '1' for now)
--
-- Register Mapping:
--   CR0[31:29] → FORGE control bits (3-bit handshaking)
--   CR1-CR10   → Application registers (10 registers)
--
-- Architecture:
--   Layer 1: (DPD.vhd - This file) ('TOP')
--   Layer 2: DPD_shim.vhd (register mapping)
--   Layer 3: DPD_forge_main.vhd (FSM logic)
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
    ----------------------------------------------------------------------------
    signal forge_ready  : std_logic;
    signal user_enable  : std_logic;
    signal clk_enable   : std_logic;
    signal loader_done  : std_logic;

begin

    ----------------------------------------------------------------------------
    -- Extract FORGE Control Bits from Control0
    --
    -- CR0[31] = forge_ready  (set by loader after deployment)
    -- CR0[30] = user_enable  (user control)
    -- CR0[29] = clk_enable   (clock gating)
    ----------------------------------------------------------------------------
    forge_ready <= Control0(31);
    user_enable <= Control0(30);
    clk_enable  <= Control0(29);

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
    --   1. Receives FORGE control signals
    --   2. Maps app_reg_1..app_reg_11 to friendly names
    --   3. Computes global_enable via combine_forge_ready()
    --   4. Instantiates DPD_forge_main (Layer 3)
    ----------------------------------------------------------------------------
    DPD_SHIM_INST: entity WORK.DPD_shim
        port map (
            -- Clock and Reset
            Clk   => Clk,
            Reset => Reset,

            -- FORGE Control (3-bit handshaking scheme)
            forge_ready  => forge_ready,
            user_enable  => user_enable,
            clk_enable   => clk_enable,
            loader_done  => loader_done,

            -- Application Registers (CR1-CR10)
            app_reg_1  => Control1,
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
-- 1. FORGE Control Initialization Sequence:
--
--    a) Power-on: Control0 = 0x00000000
--       → forge_ready=0, user_enable=0, clk_enable=0
--       → Module disabled (safe default)
--
--    b) MCC loader sets Control0[31] = 1
--       → forge_ready=1 (deployment complete)
--
--    c) User enables module via GUI: Control0[30] = 1
--       → user_enable=1
--
--    d) User enables clock: Control0[29] = 1
--       → clk_enable=1
--
--    e) Module operates: global_enable = forge_ready AND user_enable AND clk_enable AND loader_done
--
-- 2. Application Register Mapping (CR1-CR10):
--
--    CR1[3:0]   : Lifecycle control (arm_enable, [reserved], auto_rearm, fault_clear)
--    CR2[31:16] : Input trigger voltage threshold (mV, signed, 50mV hysteresis)
--    CR2[15:0]  : Trigger output voltage (mV)
--    CR3[15:0]  : Intensity output voltage (mV)
--    CR4[31:0]  : Trigger pulse duration (clock cycles)
--    CR5[31:0]  : Intensity pulse duration (clock cycles)
--    CR6[31:0]  : Trigger wait timeout (clock cycles)
--    CR7[31:0]  : Cooldown interval (clock cycles)
--    CR8[31:0]  : Monitor control and threshold
--                 CR8[1:0]   - Monitor control (enable, expect_negative)
--                 CR8[15:2]  - Reserved
--                 CR8[31:16] - Monitor threshold voltage (mV, signed)
--    CR9[31:0]  : Monitor window start delay (clock cycles)
--    CR10[31:0] : Monitor window duration (clock cycles)
--
--    Note: All timing values are pre-converted to clock cycles by Python client (clk_utils.py)
--
-- 3. MCC I/O Mapping:
--
--    InputA  → External trigger input (ADC, ±5V)
--    InputB  → Probe monitor feedback (ADC, ±5V)
--    OutputA → Trigger output (DAC, ±5V)
--    OutputB → Intensity output (DAC, ±5V)
--    OutputC → FSM state debug (signed 16-bit)
--
--------------------------------------------------------------------------------

