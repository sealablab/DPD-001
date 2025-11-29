--------------------------------------------------------------------------------
-- File: DPD_shim.vhd
-- Modified: 2025-11-26
-- Version: 4.0 (API-breaking refactor - CR0 lifecycle consolidation)
--
-- Description:
--   Register mapping shim for Demo Probe Driver (DPD) ForgeApp.
--   Receives lifecycle signals directly from TOP, maps CR2-CR10 to friendly
--   names, and instantiates the application main entity.
--
-- API Version 4.0 Changes:
--   - Lifecycle controls (arm_enable, fault_clear, sw_trigger) now arrive
--     as direct signals from TOP layer (extracted from CR0)
--   - Removed app_reg_0 and app_reg_1 ports
--   - Removed sw_trigger_enable and hw_trigger_enable (not needed)
--   - auto_rearm_enable now extracted from CR8[2]
--   - Edge detection with auto-clear (pulse stretcher) for sw_trigger/fault_clear
--
-- Layer 2 of 3-Layer Forge Architecture:
--   Layer 1: DPD.vhd (TOP - extracts CR0 bits)
--   Layer 2: DPD_shim.vhd (THIS FILE - register mapping, edge detection)
--   Layer 3: DPD_main.vhd (FSM logic)
--
-- CR0 Bit Layout (extracted at TOP, passed as signals):
--   CR0[31:29] = FORGE control (forge_ready, user_enable, clk_enable)
--   CR0[2]     = arm_enable (level-sensitive)
--   CR0[1]     = fault_clear (edge-triggered, auto-clear)
--   CR0[0]     = sw_trigger (edge-triggered, auto-clear)
--
-- Configuration Register Mapping (CR2-CR10, sync-safe gated):
--   CR2[31:16] = input_trigger_voltage_threshold (mV)
--   CR2[15:0]  = trig_out_voltage (mV)
--   CR3[15:0]  = intensity_voltage (mV)
--   CR4[31:0]  = trig_out_duration (cycles)
--   CR5[31:0]  = intensity_duration (cycles)
--   CR6[31:0]  = trigger_wait_timeout (cycles)
--   CR7[31:0]  = cooldown_interval (cycles)
--   CR8[31:16] = monitor_threshold_voltage (mV)
--   CR8[2]     = auto_rearm_enable
--   CR8[1]     = monitor_expect_negative
--   CR8[0]     = monitor_enable
--   CR9[31:0]  = monitor_window_start (cycles)
--   CR10[31:0] = monitor_window_duration (cycles)
--
-- References:
--   - forge_common_pkg.vhd (FORGE_READY control scheme)
--   - rtl/DPD-RTL.yaml (authoritative specification)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;
use WORK.forge_common_pkg.all;

entity DPD_shim is
    port (
        ------------------------------------------------------------------------
        -- Clock and Reset
        ------------------------------------------------------------------------
        Clk         : in  std_logic;
        Reset       : in  std_logic;  -- Active-high reset

        ------------------------------------------------------------------------
        -- FORGE Control Signals (from TOP layer)
        ------------------------------------------------------------------------
        forge_ready  : in  std_logic;  -- CR0[31] - Set by loader
        user_enable  : in  std_logic;  -- CR0[30] - User control
        clk_enable   : in  std_logic;  -- CR0[29] - Clock gating
        loader_done  : in  std_logic;  -- BRAM loader FSM done signal

        ------------------------------------------------------------------------
        -- Lifecycle Control Signals (from TOP layer, extracted from CR0)
        -- These arrive as direct signals for immediate processing
        ------------------------------------------------------------------------
        arm_enable   : in  std_logic;  -- CR0[2] - Level-sensitive
        fault_clear  : in  std_logic;  -- CR0[1] - Edge-triggered
        sw_trigger   : in  std_logic;  -- CR0[0] - Edge-triggered

        ------------------------------------------------------------------------
        -- Configuration Registers (CR2-CR10, sync-safe gated)
        ------------------------------------------------------------------------
        app_reg_2  : in  std_logic_vector(31 downto 0);
        app_reg_3  : in  std_logic_vector(31 downto 0);
        app_reg_4  : in  std_logic_vector(31 downto 0);
        app_reg_5  : in  std_logic_vector(31 downto 0);
        app_reg_6  : in  std_logic_vector(31 downto 0);
        app_reg_7  : in  std_logic_vector(31 downto 0);
        app_reg_8  : in  std_logic_vector(31 downto 0);
        app_reg_9  : in  std_logic_vector(31 downto 0);
        app_reg_10 : in  std_logic_vector(31 downto 0);

        ------------------------------------------------------------------------
        -- BRAM Interface (from forge_bram_loader FSM)
        ------------------------------------------------------------------------
        bram_addr   : in  std_logic_vector(11 downto 0);
        bram_data   : in  std_logic_vector(31 downto 0);
        bram_we     : in  std_logic;

        ------------------------------------------------------------------------
        -- MCC I/O (from CustomWrapper)
        ------------------------------------------------------------------------
        InputA      : in  signed(15 downto 0);
        InputB      : in  signed(15 downto 0);
        OutputA     : out signed(15 downto 0);
        OutputB     : out signed(15 downto 0);
        OutputC     : out signed(15 downto 0)
    );
end entity DPD_shim;

architecture rtl of DPD_shim is

    ----------------------------------------------------------------------------
    -- Pulse Stretcher Width (for edge-triggered signals with auto-clear)
    -- 4 cycles @ 125 MHz = 32 ns - ensures edge is captured even with
    -- clock domain crossing variations
    ----------------------------------------------------------------------------
    constant PULSE_WIDTH : integer := 4;

    ----------------------------------------------------------------------------
    -- Configuration Register Signals (sync-safe gated)
    ----------------------------------------------------------------------------

    -- Input trigger control
    signal app_reg_input_trigger_threshold_high : signed(15 downto 0);
    signal app_reg_input_trigger_threshold_low  : signed(15 downto 0);

    -- Trigger output control
    signal app_reg_trig_out_voltage     : signed(15 downto 0);
    signal app_reg_trig_out_duration    : unsigned(31 downto 0);

    -- Intensity output control
    signal app_reg_intensity_voltage    : signed(15 downto 0);
    signal app_reg_intensity_duration   : unsigned(31 downto 0);

    -- Timing control
    signal app_reg_trigger_wait_timeout : unsigned(31 downto 0);
    signal app_reg_cooldown_interval    : unsigned(31 downto 0);

    -- Mode configuration (from CR8)
    signal app_reg_auto_rearm_enable    : std_logic;

    -- Monitor/feedback
    signal app_reg_monitor_enable            : std_logic;
    signal app_reg_monitor_expect_negative   : std_logic;
    signal app_reg_monitor_threshold_voltage : signed(15 downto 0);
    signal app_reg_monitor_window_start      : unsigned(31 downto 0);
    signal app_reg_monitor_window_duration   : unsigned(31 downto 0);

    ----------------------------------------------------------------------------
    -- Global Enable Signal
    ----------------------------------------------------------------------------
    signal global_enable : std_logic;

    ----------------------------------------------------------------------------
    -- Edge Detection and Pulse Stretcher Signals
    ----------------------------------------------------------------------------

    -- Software trigger edge detection and pulse stretcher
    signal sw_trigger_prev      : std_logic := '0';
    signal sw_trigger_edge      : std_logic;
    signal sw_trigger_pulse_cnt : integer range 0 to PULSE_WIDTH := 0;
    signal sw_trigger_stretched : std_logic;

    -- Fault clear edge detection and pulse stretcher
    signal fault_clear_prev      : std_logic := '0';
    signal fault_clear_edge      : std_logic;
    signal fault_clear_pulse_cnt : integer range 0 to PULSE_WIDTH := 0;
    signal fault_clear_stretched : std_logic;

    ----------------------------------------------------------------------------
    -- Hardware Trigger Signals
    ----------------------------------------------------------------------------
    signal hw_trigger_out : std_logic;
    signal hw_trigger_above_threshold : std_logic;
    signal hw_trigger_crossing_count : unsigned(15 downto 0);

    ----------------------------------------------------------------------------
    -- Combined Trigger Signal
    ----------------------------------------------------------------------------
    signal combined_trigger     : std_logic;
    signal combined_trigger_reg : std_logic;

    ----------------------------------------------------------------------------
    -- Debug Signals (for HVS encoding)
    ----------------------------------------------------------------------------
    signal state_vector_from_main  : std_logic_vector(5 downto 0);
    signal status_vector_from_main : std_logic_vector(7 downto 0);

    ----------------------------------------------------------------------------
    -- Network Register Synchronization
    --
    -- Configuration parameters are only updated when main FSM is in INITIALIZING
    -- state (STATE_SYNC_SAFE). This prevents race conditions from async network
    -- register updates during active operation.
    ----------------------------------------------------------------------------
    signal sync_safe : std_logic;

begin

    ----------------------------------------------------------------------------
    -- Sync-Safe Detection
    -- Configuration updates only allowed when main FSM is in INITIALIZING state
    ----------------------------------------------------------------------------
    sync_safe <= '1' when state_vector_from_main = STATE_SYNC_SAFE else '0';

    ----------------------------------------------------------------------------
    -- Global Enable Computation
    --
    -- All 4 conditions must be met for app to operate:
    --   1. forge_ready  = 1  (loader has deployed bitstream)
    --   2. user_enable  = 1  (user has enabled module)
    --   3. clk_enable   = 1  (clock gating enabled)
    --   4. loader_done  = 1  (BRAM loading complete)
    ----------------------------------------------------------------------------
    -- Since BOOT subsystem already handles RUN gating, we just need all control signals active
    global_enable <= forge_ready and user_enable and clk_enable and loader_done;

    ----------------------------------------------------------------------------
    -- Edge Detection with Pulse Stretcher (Auto-Clear)
    --
    -- Converts edge-triggered signals (sw_trigger, fault_clear) into
    -- guaranteed-width pulses. This ensures the FSM captures the edge
    -- even with network timing variations.
    --
    -- Behavior:
    --   1. Detect rising edge (0→1) on input
    --   2. Start counter at PULSE_WIDTH
    --   3. Output '1' while counter > 0
    --   4. Auto-clear: output returns to '0' after PULSE_WIDTH cycles
    ----------------------------------------------------------------------------
    EDGE_DETECT_PULSE_STRETCH: process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                sw_trigger_prev      <= '0';
                sw_trigger_pulse_cnt <= 0;
                fault_clear_prev      <= '0';
                fault_clear_pulse_cnt <= 0;
            else
                -- Software trigger edge detection
                sw_trigger_prev <= sw_trigger;
                if sw_trigger = '1' and sw_trigger_prev = '0' then
                    -- Rising edge detected - start pulse
                    sw_trigger_pulse_cnt <= PULSE_WIDTH;
                elsif sw_trigger_pulse_cnt > 0 then
                    -- Count down pulse width
                    sw_trigger_pulse_cnt <= sw_trigger_pulse_cnt - 1;
                end if;

                -- Fault clear edge detection
                fault_clear_prev <= fault_clear;
                if fault_clear = '1' and fault_clear_prev = '0' then
                    -- Rising edge detected - start pulse
                    fault_clear_pulse_cnt <= PULSE_WIDTH;
                elsif fault_clear_pulse_cnt > 0 then
                    -- Count down pulse width
                    fault_clear_pulse_cnt <= fault_clear_pulse_cnt - 1;
                end if;
            end if;
        end if;
    end process;

    -- Stretched pulse outputs (auto-clear after PULSE_WIDTH cycles)
    sw_trigger_stretched  <= '1' when sw_trigger_pulse_cnt > 0 else '0';
    fault_clear_stretched <= '1' when fault_clear_pulse_cnt > 0 else '0';

    -- Edge detection outputs (single cycle pulse for FSM transition)
    sw_trigger_edge  <= '1' when (sw_trigger = '1' and sw_trigger_prev = '0') else '0';
    fault_clear_edge <= '1' when (fault_clear = '1' and fault_clear_prev = '0') else '0';

    ----------------------------------------------------------------------------
    -- Configuration Register Synchronization (CR2-CR10)
    --
    -- IMPORTANT: Implements Network Synchronization Protocol
    --   - Configuration params (CR2-CR10): Only updated when sync_safe='1'
    --
    -- This prevents race conditions from async network register updates.
    -- Configuration changes only take effect when FSM is in INITIALIZING state.
    ----------------------------------------------------------------------------
    CONFIG_SYNC: process(Clk, Reset)
    begin
        if Reset = '1' then
            -- Initialize to safe defaults
            app_reg_input_trigger_threshold_high <= to_signed(950, 16);
            app_reg_input_trigger_threshold_low  <= to_signed(900, 16);
            app_reg_trig_out_voltage     <= (others => '0');
            app_reg_trig_out_duration    <= to_unsigned(12500, 32);
            app_reg_intensity_voltage    <= (others => '0');
            app_reg_intensity_duration   <= to_unsigned(25000, 32);
            app_reg_trigger_wait_timeout <= to_unsigned(250000000, 32);
            app_reg_cooldown_interval    <= to_unsigned(1250, 32);
            app_reg_auto_rearm_enable    <= '0';
            app_reg_monitor_enable            <= '1';
            app_reg_monitor_expect_negative   <= '1';
            app_reg_monitor_threshold_voltage <= to_signed(-200, 16);
            app_reg_monitor_window_start      <= (others => '0');
            app_reg_monitor_window_duration   <= to_unsigned(625000, 32);
            combined_trigger_reg <= '0';

        elsif rising_edge(Clk) then

            ----------------------------------------------------------------
            -- Combined Trigger (always updated)
            -- FSM accepts triggers from hardware OR software paths
            ----------------------------------------------------------------
            combined_trigger_reg <= combined_trigger;

            ----------------------------------------------------------------
            -- Configuration Parameters (CR2-CR10): Only when sync_safe='1'
            ----------------------------------------------------------------
            if sync_safe = '1' then
                -- CR2: Input trigger threshold [31:16] + Trigger output voltage [15:0]
                app_reg_input_trigger_threshold_high <= signed(app_reg_2(31 downto 16));
                app_reg_input_trigger_threshold_low  <= signed(app_reg_2(31 downto 16)) - to_signed(50, 16);
                app_reg_trig_out_voltage  <= signed(app_reg_2(15 downto 0));

                -- CR3: Intensity output voltage
                app_reg_intensity_voltage <= signed(app_reg_3(15 downto 0));

                -- CR4: Trigger pulse duration
                app_reg_trig_out_duration <= unsigned(app_reg_4);

                -- CR5: Intensity pulse duration
                app_reg_intensity_duration <= unsigned(app_reg_5);

                -- CR6: Trigger wait timeout
                app_reg_trigger_wait_timeout <= unsigned(app_reg_6);

                -- CR7: Cooldown interval
                app_reg_cooldown_interval <= unsigned(app_reg_7);

                -- CR8: Monitor control + auto_rearm_enable
                app_reg_monitor_enable          <= app_reg_8(0);
                app_reg_monitor_expect_negative <= app_reg_8(1);
                app_reg_auto_rearm_enable       <= app_reg_8(2);  -- NEW: from CR8[2]
                app_reg_monitor_threshold_voltage <= signed(app_reg_8(31 downto 16));

                -- CR9: Monitor window start delay
                app_reg_monitor_window_start <= unsigned(app_reg_9);

                -- CR10: Monitor window duration
                app_reg_monitor_window_duration <= unsigned(app_reg_10);
            end if;

        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Combined Trigger Logic
    --
    -- FSM accepts triggers from EITHER hardware comparator OR software signal.
    -- No enable gates needed - FSM state naturally gates trigger response.
    ----------------------------------------------------------------------------
    combined_trigger <= '1' when (hw_trigger_out = '1' or sw_trigger_stretched = '1') else '0';

    ----------------------------------------------------------------------------
    -- Instantiate Hardware Trigger Core
    --
    -- Generates 1-cycle pulse when InputA crosses voltage threshold.
    -- Always enabled when global_enable is active - FSM state gates response.
    ----------------------------------------------------------------------------
    HW_TRIGGER_INST: entity WORK.moku_voltage_threshold_trigger_core
        port map (
            clk              => Clk,
            reset            => Reset,
            voltage_in       => InputA,
            threshold_high   => app_reg_input_trigger_threshold_high,
            threshold_low    => app_reg_input_trigger_threshold_low,
            enable           => global_enable,
            mode             => '0',  -- Rising edge mode
            trigger_out      => hw_trigger_out,
            above_threshold  => hw_trigger_above_threshold,
            crossing_count   => hw_trigger_crossing_count
        );

    ----------------------------------------------------------------------------
    -- Instantiate Application Main Entity
    ----------------------------------------------------------------------------
    DPD_MAIN_INST: entity WORK.DPD_main
        generic map (
            CLK_FREQ_HZ => 125000000
        )
        port map (
            -- Clock and Control
            Clk    => Clk,
            Reset  => Reset,
            Enable => global_enable,
            ClkEn  => '1',

            -- Lifecycle controls (from TOP via shim processing)
            arm_enable           => arm_enable,  -- Direct from TOP (level-sensitive)
            ext_trigger_in       => combined_trigger_reg,
            trigger_wait_timeout => app_reg_trigger_wait_timeout,
            auto_rearm_enable    => app_reg_auto_rearm_enable,  -- From CR8[2]
            fault_clear          => fault_clear_stretched,  -- Edge-detected with auto-clear

            -- Output configuration
            trig_out_voltage     => app_reg_trig_out_voltage,
            trig_out_duration    => app_reg_trig_out_duration,
            intensity_voltage    => app_reg_intensity_voltage,
            intensity_duration   => app_reg_intensity_duration,
            cooldown_interval    => app_reg_cooldown_interval,

            -- Monitor configuration
            probe_monitor_feedback    => InputB,
            monitor_enable            => app_reg_monitor_enable,
            monitor_threshold_voltage => app_reg_monitor_threshold_voltage,
            monitor_expect_negative   => app_reg_monitor_expect_negative,
            monitor_window_start      => app_reg_monitor_window_start,
            monitor_window_duration   => app_reg_monitor_window_duration,

            -- BRAM Interface (reserved)
            bram_addr => bram_addr,
            bram_data => bram_data,
            bram_we   => bram_we,

            -- Physical I/O
            OutputA => OutputA,
            OutputB => OutputB,

            -- Debug outputs (for HVS encoding)
            state_vector  => state_vector_from_main,
            status_vector => status_vector_from_main
        );

    ----------------------------------------------------------------------------
    -- Instantiate Hierarchical Voltage Encoder (HVS)
    --
    -- Encodes 6-bit state + 8-bit status into OutputC using HVS scheme
    ----------------------------------------------------------------------------
    HVS_ENCODER_INST: entity WORK.forge_hierarchical_encoder
        port map (
            clk           => Clk,
            reset         => Reset,
            state_vector  => state_vector_from_main,
            status_vector => status_vector_from_main,
            voltage_out   => OutputC
        );

end architecture rtl;
