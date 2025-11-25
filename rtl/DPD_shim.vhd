--------------------------------------------------------------------------------
-- File: DPD_shim.vhd
-- Modified: 2025-11-14
--
-- Description:
--   Register mapping shim for Demo Probe Driver (DPD) ForgeApp.
--   Maps raw Control Registers (CR20-CR30) to friendly signal names
--   and instantiates the application main entity.
--
-- Layer 2 of 3-Layer Forge Architecture:
--   Layer 1: DPD.vhd (TOP)
--   Layer 2: DPD_shim.vhd (THIS FILE - register mapping)
--   Layer 3: DPD_main.vhd (hand-written app logic)
--
-- Register Mapping:
--   CR1[0]     : arm_enable - Arm FSM (IDLE → ARMED transition)
--   CR1[1]     : sw_trigger - Software trigger (edge-detected, ARMED → FIRING)
--   CR1[2]     : auto_rearm_enable - Re-arm after cooldown
--   CR1[3]     : fault_clear - Clear fault state (edge-detected)
--   CR1[31:4]  : Reserved
--   CR2[31:16] : Input trigger voltage threshold (mV, signed)
--   CR2[15:0]  : Trigger output voltage (mV)
--   CR3[15:0]  : Intensity output voltage (mV)
--   CR4[31:0]  : Trigger pulse duration (clock cycles)
--   CR5[31:0]  : Intensity pulse duration (clock cycles)
--   CR6[31:0]  : Trigger wait timeout (clock cycles)
--   CR7[31:0]  : Cooldown interval (clock cycles)
--   CR8[31:0]  : Monitor control and threshold
--                CR8[1:0]   - Monitor control (enable, expect_negative)
--                CR8[15:2]  - Reserved
--                CR8[31:16] - Monitor threshold voltage (mV, signed)
--   CR9[31:0]  : Monitor window start delay (clock cycles)
--   CR10[31:0] : Monitor window duration (clock cycles)
--
-- References:
--   - forge_common_pkg.vhd (FORGE_READY control scheme)
--   - external_Example/DS1140_polo_shim.vhd (pattern reference)
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
        -- FORGE Control Signals (from MCC_TOP_forge_loader or CustomWrapper)
        ------------------------------------------------------------------------
        forge_ready  : in  std_logic;  -- CR0[31] - Set by loader
        user_enable  : in  std_logic;  -- CR0[30] - User control
        clk_enable   : in  std_logic;  -- CR0[29] - Clock gating
        loader_done  : in  std_logic;  -- BRAM loader FSM done signal

        ------------------------------------------------------------------------
        -- Application Registers (from MCC_TOP_forge_loader)
        -- Raw Control Registers CR1-CR10 (MCC provides CR0-CR15)
        ------------------------------------------------------------------------
        app_reg_1 : in  std_logic_vector(31 downto 0);
        app_reg_2 : in  std_logic_vector(31 downto 0);
        app_reg_3 : in  std_logic_vector(31 downto 0);
        app_reg_4 : in  std_logic_vector(31 downto 0);
        app_reg_5 : in  std_logic_vector(31 downto 0);
        app_reg_6 : in  std_logic_vector(31 downto 0);
        app_reg_7 : in  std_logic_vector(31 downto 0);
        app_reg_8 : in  std_logic_vector(31 downto 0);
        app_reg_9 : in  std_logic_vector(31 downto 0);
        app_reg_10 : in  std_logic_vector(31 downto 0);

        ------------------------------------------------------------------------
        -- BRAM Interface (from forge_bram_loader FSM)
        ------------------------------------------------------------------------
        bram_addr   : in  std_logic_vector(11 downto 0);  -- 4KB address space
        bram_data   : in  std_logic_vector(31 downto 0);  -- 32-bit data
        bram_we     : in  std_logic;                      -- Write enable

        ------------------------------------------------------------------------
        -- MCC I/O (from CustomWrapper)
        -- Native MCC types: signed(15 downto 0) for all ADC/DAC channels
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
    -- Template-Level Application Register Signals (Generic Naming)
    -- These use app_reg_* prefix for template reusability
    ----------------------------------------------------------------------------

    -- Lifecycle control
    signal app_reg_arm_enable           : std_logic;  -- Arm FSM (IDLE→ARMED transition)
    signal app_reg_sw_trigger           : std_logic;  -- Software trigger input (CR1[4])
    signal app_reg_auto_rearm_enable    : std_logic;  -- Re-arm after cooldown
    signal app_reg_fault_clear          : std_logic;  -- Clear fault state

    -- Input trigger control
    signal app_reg_input_trigger_threshold_high : signed(15 downto 0);  -- Threshold high (mV)
    signal app_reg_input_trigger_threshold_low  : signed(15 downto 0);  -- Threshold low (mV, -50mV hysteresis)

    -- Trigger output control
    signal app_reg_trig_out_voltage     : signed(15 downto 0);    -- Voltage (mV)
    signal app_reg_trig_out_duration    : unsigned(31 downto 0);  -- Duration (clock cycles)

    -- Intensity output control
    signal app_reg_intensity_voltage    : signed(15 downto 0);    -- Voltage (mV)
    signal app_reg_intensity_duration   : unsigned(31 downto 0);  -- Duration (clock cycles)

    -- Timing control
    signal app_reg_trigger_wait_timeout : unsigned(31 downto 0);  -- Timeout (clock cycles)
    signal app_reg_cooldown_interval    : unsigned(31 downto 0);  -- Cooldown (clock cycles)

    -- Monitor/feedback
    signal app_reg_monitor_enable            : std_logic;              -- Enable comparator
    signal app_reg_monitor_expect_negative   : std_logic;              -- Polarity select
    signal app_reg_monitor_threshold_voltage : signed(15 downto 0);    -- Threshold (mV)
    signal app_reg_monitor_window_start      : unsigned(31 downto 0);  -- Window delay (clock cycles)
    signal app_reg_monitor_window_duration   : unsigned(31 downto 0);  -- Window length (clock cycles)

    ----------------------------------------------------------------------------
    -- Global Enable Signal
    -- Combines all FORGE_READY control bits for safe operation
    ----------------------------------------------------------------------------
    signal global_enable : std_logic;

    ----------------------------------------------------------------------------
    -- Hardware Trigger Signals
    ----------------------------------------------------------------------------
    signal hw_trigger_out : std_logic;  -- Pulse from voltage threshold trigger
    signal hw_trigger_above_threshold : std_logic;  -- Level indicator
    signal hw_trigger_crossing_count : unsigned(15 downto 0);  -- Diagnostic counter

    ----------------------------------------------------------------------------
    -- Software Trigger Edge Detection
    ----------------------------------------------------------------------------
    signal sw_trigger_prev : std_logic;  -- Previous state for edge detection
    signal sw_trigger_edge : std_logic;  -- Rising edge pulse (1 cycle)
    signal combined_trigger : std_logic;  -- hw_trigger OR sw_trigger

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
    --
    -- Lifecycle controls (arm_enable, fault_clear, etc.) always pass through
    -- because they are real-time control signals, not configuration.
    --
    -- See: N/network-register-sync.md for design rationale
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
    global_enable <= combine_forge_ready(forge_ready, user_enable, clk_enable, loader_done);

    ----------------------------------------------------------------------------
    -- Register Synchronization: Control Registers → app_reg_* signals
    --
    -- IMPORTANT: Implements Network Synchronization Protocol
    --   - Lifecycle controls (CR1): Always updated (real-time control signals)
    --   - Configuration params (CR2-CR10): Only updated when sync_safe='1'
    --
    -- This prevents race conditions from async network register updates.
    -- Configuration changes only take effect when FSM is in INITIALIZING state.
    --
    -- See: N/network-register-sync.md for design rationale
    ----------------------------------------------------------------------------
    REGISTER_SYNC: process(Clk, Reset)
    begin
        if Reset = '1' then
            -- Initialize all app_reg_* signals to safe defaults
            app_reg_arm_enable           <= '0';
            app_reg_sw_trigger           <= '0';
            app_reg_auto_rearm_enable    <= '0';
            app_reg_fault_clear          <= '0';
            sw_trigger_prev              <= '0';
            app_reg_input_trigger_threshold_high <= to_signed(950, 16);   -- Default 950mV
            app_reg_input_trigger_threshold_low  <= to_signed(900, 16);   -- Default 900mV (50mV hysteresis)
            app_reg_trig_out_voltage     <= (others => '0');
            app_reg_trig_out_duration    <= to_unsigned(12500, 32);    -- Safe default 100ns @ 125MHz
            app_reg_intensity_voltage    <= (others => '0');
            app_reg_intensity_duration   <= to_unsigned(25000, 32);    -- Safe default 200ns @ 125MHz
            app_reg_trigger_wait_timeout <= to_unsigned(250000000, 32); -- Safe default 2s @ 125MHz
            app_reg_cooldown_interval    <= to_unsigned(1250, 32);     -- Safe default 10μs @ 125MHz
            app_reg_monitor_enable            <= '1';                  -- Enabled by default
            app_reg_monitor_expect_negative   <= '1';                  -- Negative polarity
            app_reg_monitor_threshold_voltage <= to_signed(-200, 16);  -- -200mV default
            app_reg_monitor_window_start      <= (others => '0');
            app_reg_monitor_window_duration   <= to_unsigned(625000, 32); -- 5μs @ 125MHz

        elsif rising_edge(Clk) then

            ----------------------------------------------------------------
            -- LIFECYCLE CONTROLS (CR1): Always updated
            -- These are real-time control signals that must work in any state
            ----------------------------------------------------------------
            app_reg_arm_enable        <= app_reg_1(0);
            app_reg_sw_trigger        <= app_reg_1(1);
            app_reg_auto_rearm_enable <= app_reg_1(2);
            app_reg_fault_clear       <= app_reg_1(3);

            -- Edge detection for software trigger (always active)
            sw_trigger_prev <= app_reg_sw_trigger;

            ----------------------------------------------------------------
            -- CONFIGURATION PARAMETERS (CR2-CR10): Only when sync_safe='1'
            -- Gated to prevent mid-operation parameter changes
            ----------------------------------------------------------------
            if sync_safe = '1' then
                -- CR2: Input trigger threshold [31:16] + Trigger output voltage [15:0]
                app_reg_input_trigger_threshold_high <= signed(app_reg_2(31 downto 16));
                app_reg_input_trigger_threshold_low  <= signed(app_reg_2(31 downto 16)) - to_signed(50, 16);  -- 50mV hysteresis
                app_reg_trig_out_voltage  <= signed(app_reg_2(15 downto 0));

                -- CR3: Intensity output voltage
                app_reg_intensity_voltage <= signed(app_reg_3(15 downto 0));

                -- CR4: Trigger pulse duration (clock cycles)
                app_reg_trig_out_duration <= unsigned(app_reg_4);

                -- CR5: Intensity pulse duration (clock cycles)
                app_reg_intensity_duration <= unsigned(app_reg_5);

                -- CR6: Trigger wait timeout (clock cycles)
                app_reg_trigger_wait_timeout <= unsigned(app_reg_6);

                -- CR7: Cooldown interval (clock cycles)
                app_reg_cooldown_interval <= unsigned(app_reg_7);

                -- CR8: Monitor control and threshold
                app_reg_monitor_enable          <= app_reg_8(0);
                app_reg_monitor_expect_negative <= app_reg_8(1);
                app_reg_monitor_threshold_voltage <= signed(app_reg_8(31 downto 16));

                -- CR9: Monitor window start delay (clock cycles)
                app_reg_monitor_window_start <= unsigned(app_reg_9);

                -- CR10: Monitor window duration (clock cycles)
                app_reg_monitor_window_duration <= unsigned(app_reg_10);
            end if;
            -- When sync_safe='0', configuration params hold their previous values

        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Software Trigger Edge Detection (Combinational)
    --
    -- Converts CR1[4] level into 1-cycle pulse on rising edge
    ----------------------------------------------------------------------------
    sw_trigger_edge <= app_reg_sw_trigger and not sw_trigger_prev;

    ----------------------------------------------------------------------------
    -- Combined Trigger Logic
    --
    -- FSM accepts triggers from EITHER hardware comparator OR software register
    ----------------------------------------------------------------------------
    combined_trigger <= hw_trigger_out or sw_trigger_edge;

    ----------------------------------------------------------------------------
    -- Instantiate Hardware Trigger Core
    --
    -- Generates 1-cycle pulse when InputA crosses voltage threshold
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
    --
    -- Direct mapping: app_reg_* signals to DPD_main ports
    -- Main app is MCC-agnostic, uses domain-specific naming
    ----------------------------------------------------------------------------
    DPD_MAIN_INST: entity WORK.DPD_main
        generic map (
            CLK_FREQ_HZ => 125000000  -- Moku:Go clock frequency
        )
        port map (
            -- Clock and Control
            Clk    => Clk,
            Reset  => Reset,
            Enable => global_enable,
            ClkEn  => '1',  -- Always enabled for now

            -- Direct mapping: DPD_main ports ← app_reg_* signals
            arm_enable           => app_reg_arm_enable,
            ext_trigger_in       => combined_trigger,  -- Hardware OR software trigger
            trigger_wait_timeout => app_reg_trigger_wait_timeout,
            auto_rearm_enable    => app_reg_auto_rearm_enable,
            fault_clear          => app_reg_fault_clear,

            trig_out_voltage     => app_reg_trig_out_voltage,
            trig_out_duration    => app_reg_trig_out_duration,

            intensity_voltage    => app_reg_intensity_voltage,
            intensity_duration   => app_reg_intensity_duration,

            cooldown_interval    => app_reg_cooldown_interval,

            probe_monitor_feedback    => InputB,
            monitor_enable            => app_reg_monitor_enable,
            monitor_threshold_voltage => app_reg_monitor_threshold_voltage,
            monitor_expect_negative   => app_reg_monitor_expect_negative,
            monitor_window_start      => app_reg_monitor_window_start,
            monitor_window_duration   => app_reg_monitor_window_duration,

            -- BRAM Interface (reserved for future use)
            bram_addr => bram_addr,
            bram_data => bram_data,
            bram_we   => bram_we,

            -- Physical I/O (2 outputs from DPD_main)
            OutputA => OutputA,
            OutputB => OutputB,

            -- Debug outputs (for HVS encoding in shim)
            state_vector  => state_vector_from_main,
            status_vector => status_vector_from_main
        );

    ----------------------------------------------------------------------------
    -- Instantiate Hierarchical Voltage Encoder (HVS)
    --
    -- Encodes 6-bit state + 8-bit status into OutputC using HVS scheme:
    -- - 200 digital units per state (visible on scope)
    -- - ±100 digital units status offset (fine-grained debug)
    -- - Negative voltage when status[7]=1 (fault indication)
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

