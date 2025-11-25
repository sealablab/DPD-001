--------------------------------------------------------------------------------
-- File: DPD_main.vhd
-- Author: Moku Instrument Forge Team
-- Date: 2025-11-05
-- Version: 2.0 (Layer 3 - MCC-agnostic refactor)
--
-- Description:
--   Five-state FSM for Demo Probe Driver following forge-vhdl standards.
--   This is Layer 3 of the Forge architecture - completely MCC-agnostic.
--
-- Platform: Moku:Go
-- Clock Frequency: 125 MHz (8 ns period)
--
-- FSM States (std_logic_vector encoding - Verilog compatible):
--   INITIALIZING (000000) - Latching and validating registers after reset/fault
--   IDLE         (000001) - Waiting for arm signal
--   ARMED        (000010) - Waiting for trigger or timeout
--   FIRING       (000011) - Driving outputs (trigger + intensity pulses)
--   COOLDOWN     (000100) - Thermal safety delay between pulses
--   FAULT        (111111) - Sticky fault state (requires fault_clear)
--
-- Layer 3 of 3-Layer Forge Architecture:
--   Layer 1: MCC_TOP_forge_loader.vhd (static, shared)
--   Layer 2: DPD_forge_shim.vhd (generated, register mapping)
--   Layer 3: DPD_main.vhd (THIS FILE - application logic)
--
-- References:
--   - DPD_forge_shim.vhd (shim layer)
--   - forge_common_pkg.vhd (FORGE_READY control scheme)
--   - libs/forge-vhdl/CLAUDE.md (coding standards)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;

entity DPD_main is
    generic (
        CLK_FREQ_HZ : integer := 125000000  -- Moku:Go clock frequency
    );
    port (
        ------------------------------------------------------------------------
        -- Standard Control Signals (MCC-Agnostic)
        -- Priority Order: Reset > ClkEn > Enable
        ------------------------------------------------------------------------
        Clk    : in  std_logic;
        Reset  : in  std_logic;  -- Active-high reset (forces safe state)
        Enable : in  std_logic;  -- Functional enable (gates work)
        ClkEn  : in  std_logic;  -- Clock enable (freezes sequential logic)

        ------------------------------------------------------------------------
        -- Application Signals (Friendly Names)
        -- Mapped from Control Registers by shim layer
        ------------------------------------------------------------------------
        -- Arming and lifecycle
        arm_enable           : in std_logic;               -- Arm the FSM (IDLE → ARMED)
        ext_trigger_in       : in std_logic;               -- External trigger (ARMED → FIRING)
        trigger_wait_timeout : in unsigned(31 downto 0);  -- Max wait in ARMED (clock cycles)
        auto_rearm_enable    : in std_logic;               -- Re-arm after cooldown
        fault_clear          : in std_logic;               -- Clear fault state

        -- Output controls (trigger path)
        trig_out_voltage     : in signed(15 downto 0);    -- Trigger voltage (mV)
        trig_out_duration    : in unsigned(31 downto 0);  -- Trigger pulse width (clock cycles)

        -- Output controls (intensity path)
        intensity_voltage    : in signed(15 downto 0);    -- Intensity voltage (mV)
        intensity_duration   : in unsigned(31 downto 0);  -- Intensity pulse width (clock cycles)

        -- Timing controls
        cooldown_interval    : in unsigned(31 downto 0);  -- Cooldown period (clock cycles)

        -- Monitor/feedback
        probe_monitor_feedback    : in signed(15 downto 0);  -- ADC feedback (mV)
        monitor_enable            : in std_logic;             -- Enable comparator
        monitor_threshold_voltage : in signed(15 downto 0);  -- Threshold (mV)
        monitor_expect_negative   : in std_logic;             -- Polarity select
        monitor_window_start      : in unsigned(31 downto 0); -- Window delay (clock cycles)
        monitor_window_duration   : in unsigned(31 downto 0); -- Window length (clock cycles)

        ------------------------------------------------------------------------
        -- BRAM Interface (Reserved for future use)
        ------------------------------------------------------------------------
        bram_addr : in  std_logic_vector(11 downto 0);
        bram_data : in  std_logic_vector(31 downto 0);
        bram_we   : in  std_logic;

        ------------------------------------------------------------------------
        -- MCC I/O (Native MCC Types)
        -- OutputA: Trigger output to probe (16-bit signed DAC, ±5V)
        -- OutputB: Intensity/amplitude to probe (16-bit signed DAC, ±5V)
        ------------------------------------------------------------------------
        OutputA : out signed(15 downto 0);
        OutputB : out signed(15 downto 0);

        ------------------------------------------------------------------------
        -- Debug Outputs (for HVS encoding in shim layer)
        -- Following FORGE standard: export state + status for hierarchical encoding
        ------------------------------------------------------------------------
        state_vector  : out std_logic_vector(5 downto 0);  -- FSM state (0-63)
        status_vector : out std_logic_vector(7 downto 0)   -- App status (bit 7 = fault)
    );
end entity DPD_main;

architecture rtl of DPD_main is

    ----------------------------------------------------------------------------
    -- FSM State Constants (6-bit encoding for fsm_observer compatibility)
    ----------------------------------------------------------------------------
    constant STATE_INITIALIZING : std_logic_vector(5 downto 0) := "000000";  -- 0: Register latch/validation
    constant STATE_IDLE         : std_logic_vector(5 downto 0) := "000001";  -- 1: Waiting for arm signal
    constant STATE_ARMED        : std_logic_vector(5 downto 0) := "000010";  -- 2: Waiting for trigger
    constant STATE_FIRING       : std_logic_vector(5 downto 0) := "000011";  -- 3: Driving outputs
    constant STATE_COOLDOWN     : std_logic_vector(5 downto 0) := "000100";  -- 4: Thermal safety delay
    constant STATE_FAULT        : std_logic_vector(5 downto 0) := "111111";  -- 63: Sticky fault

    ----------------------------------------------------------------------------
    -- State Machine Signals
    ----------------------------------------------------------------------------
    signal state      : std_logic_vector(5 downto 0) := STATE_INITIALIZING;  -- Power-up safe default
    signal next_state : std_logic_vector(5 downto 0);

    ----------------------------------------------------------------------------
    -- Note: All timing parameters now arrive as clock cycles from Python client
    -- No conversion needed - these signals map directly to input ports
    ----------------------------------------------------------------------------

    ----------------------------------------------------------------------------
    -- Latched Register Values
    -- These are captured atomically in INITIALIZING state to prevent race
    -- conditions from asynchronous network register updates
    ----------------------------------------------------------------------------
    signal latched_trig_out_voltage     : signed(15 downto 0);
    signal latched_trig_out_duration    : unsigned(31 downto 0);
    signal latched_intensity_voltage    : signed(15 downto 0);
    signal latched_intensity_duration   : unsigned(31 downto 0);
    signal latched_trigger_wait_timeout : unsigned(31 downto 0);
    signal latched_cooldown_interval    : unsigned(31 downto 0);

    ----------------------------------------------------------------------------
    -- Timing Counters
    ----------------------------------------------------------------------------
    signal armed_timer       : unsigned(31 downto 0);  -- Timeout in ARMED state
    signal trig_out_timer    : unsigned(31 downto 0);  -- Trigger pulse counter
    signal intensity_timer   : unsigned(31 downto 0);  -- Intensity pulse counter
    signal cooldown_timer    : unsigned(31 downto 0);  -- Cooldown counter
    signal monitor_start_timer : unsigned(31 downto 0); -- Monitor window delay
    signal monitor_duration_timer : unsigned(31 downto 0); -- Monitor window length

    ----------------------------------------------------------------------------
    -- Control Flags
    ----------------------------------------------------------------------------
    signal monitor_window_open : std_logic; -- Monitor window is active
    signal firing_complete   : std_logic;  -- Both pulses finished
    signal timeout_occurred  : std_logic;  -- Armed timeout exceeded
    signal cooldown_complete : std_logic;  -- Cooldown elapsed

    ----------------------------------------------------------------------------
    -- Monitor/Comparator Signals
    ----------------------------------------------------------------------------
    signal threshold_crossed : std_logic;  -- Comparator output
    signal monitor_triggered : std_logic;  -- Latch for threshold crossing

    ----------------------------------------------------------------------------
    -- Fault Detection
    ----------------------------------------------------------------------------
    signal fault_detected    : std_logic;  -- Safety violation flag
    signal fault_clear_prev  : std_logic;  -- Edge detection
    signal fault_clear_edge  : std_logic;  -- Rising edge of fault_clear

    ----------------------------------------------------------------------------
    -- Output Signals
    ----------------------------------------------------------------------------
    signal trig_out      : signed(15 downto 0);
    signal intensity_out : signed(15 downto 0);

    ----------------------------------------------------------------------------
    -- Debug Signals (registered for clean scope output)
    ----------------------------------------------------------------------------
    signal status_reg : std_logic_vector(7 downto 0);

begin

    ------------------------------------------------------------------------
    -- Note: Time conversions now handled by Python client (clk_utils.py)
    -- All timing parameters arrive pre-converted to clock cycles
    ------------------------------------------------------------------------

    ------------------------------------------------------------------------
    -- Edge Detector for fault_clear
    ------------------------------------------------------------------------
    FAULT_CLEAR_EDGE_PROC: process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                fault_clear_prev <= '0';
            elsif Enable = '1' and ClkEn = '1' then
                fault_clear_prev <= fault_clear;
            end if;
        end if;
    end process;

    fault_clear_edge <= fault_clear and not fault_clear_prev;

    ------------------------------------------------------------------------
    -- Monitor Comparator Logic
    --
    -- Compares probe_monitor_feedback against threshold with polarity control
    ------------------------------------------------------------------------
    MONITOR_COMPARATOR: process(probe_monitor_feedback, monitor_threshold_voltage,
                                 monitor_expect_negative)
    begin
        if monitor_expect_negative = '1' then
            -- Negative-going crossing detection (feedback < threshold)
            if probe_monitor_feedback < monitor_threshold_voltage then
                threshold_crossed <= '1';
            else
                threshold_crossed <= '0';
            end if;
        else
            -- Positive-going crossing detection (feedback > threshold)
            if probe_monitor_feedback > monitor_threshold_voltage then
                threshold_crossed <= '1';
            else
                threshold_crossed <= '0';
            end if;
        end if;
    end process;

    ------------------------------------------------------------------------
    -- State Register (Sequential)
    --
    -- Implements state transitions with active-high reset and clock enable
    ------------------------------------------------------------------------
    FSM_STATE_REG: process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                state <= STATE_INITIALIZING;  -- Reset → INITIALIZING (not IDLE)
            elsif Enable = '1' and ClkEn = '1' then
                state <= next_state;
            end if;
        end if;
    end process;

    ------------------------------------------------------------------------
    -- Next-State Logic (Combinational)
    --
    -- Implements FSM state transitions based on current state and inputs
    ------------------------------------------------------------------------
    FSM_NEXT_STATE: process(state, timeout_occurred, firing_complete,
                           cooldown_complete, auto_rearm_enable,
                           fault_clear_edge, fault_detected, arm_enable,
                           ext_trigger_in, trig_out_duration, intensity_duration,
                           trigger_wait_timeout, cooldown_interval)
    begin
        -- Default: hold current state
        next_state <= state;

        case state is
            when STATE_INITIALIZING =>
                -- Validate timing registers before transitioning to IDLE
                -- This prevents FSM from operating with zero/invalid timing values
                if (trig_out_duration > 0 and
                    intensity_duration > 0 and
                    trigger_wait_timeout > 0 and
                    cooldown_interval > 0) then
                    -- All timing registers valid → safe to proceed
                    next_state <= STATE_IDLE;
                else
                    -- Invalid configuration → fault state
                    next_state <= STATE_FAULT;
                end if;

            when STATE_IDLE =>
                -- Transition to ARMED when arm_enable asserted
                if arm_enable = '1' then
                    next_state <= STATE_ARMED;
                end if;

            when STATE_ARMED =>
                if timeout_occurred = '1' then
                    -- Timeout watchdog expired
                    next_state <= STATE_FAULT;
                elsif ext_trigger_in = '1' then
                    -- External trigger received
                    next_state <= STATE_FIRING;
                end if;

            when STATE_FIRING =>
                if firing_complete = '1' then
                    -- Both output pulses finished
                    next_state <= STATE_COOLDOWN;
                end if;

            when STATE_COOLDOWN =>
                if cooldown_complete = '1' then
                    if auto_rearm_enable = '1' then
                        -- Burst mode: re-arm automatically
                        next_state <= STATE_ARMED;
                    else
                        -- One-shot mode: return to idle
                        next_state <= STATE_IDLE;
                    end if;
                end if;

            when STATE_FAULT =>
                if fault_clear_edge = '1' then
                    -- Acknowledge fault and re-validate registers
                    next_state <= STATE_INITIALIZING;
                end if;

            when others =>
                -- Safety: any undefined state goes to FAULT
                next_state <= STATE_FAULT;

        end case;

        -- Override: any fault detection forces FAULT state
        if fault_detected = '1' then
            next_state <= STATE_FAULT;
        end if;
    end process;

    ------------------------------------------------------------------------
    -- Timing Counters (Sequential)
    --
    -- Implements all timing logic: timeouts, pulse durations, cooldown
    ------------------------------------------------------------------------
    TIMING_COUNTERS: process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                armed_timer <= (others => '0');
                trig_out_timer <= (others => '0');
                intensity_timer <= (others => '0');
                cooldown_timer <= (others => '0');
                monitor_start_timer <= (others => '0');
                monitor_duration_timer <= (others => '0');
                monitor_window_open <= '0';
                monitor_triggered <= '0';
                -- Reset latched registers to safe defaults
                latched_trig_out_voltage     <= (others => '0');
                latched_trig_out_duration    <= (others => '0');
                latched_intensity_voltage    <= (others => '0');
                latched_intensity_duration   <= (others => '0');
                latched_trigger_wait_timeout <= (others => '0');
                latched_cooldown_interval    <= (others => '0');

            elsif Enable = '1' and ClkEn = '1' then
                case state is
                    when STATE_INITIALIZING =>
                        -- Atomically latch all timing/voltage registers
                        -- This prevents race conditions from async network register updates
                        latched_trig_out_voltage     <= trig_out_voltage;
                        latched_trig_out_duration    <= trig_out_duration;
                        latched_intensity_voltage    <= intensity_voltage;
                        latched_intensity_duration   <= intensity_duration;
                        latched_trigger_wait_timeout <= trigger_wait_timeout;
                        latched_cooldown_interval    <= cooldown_interval;
                        -- Reset all counters
                        armed_timer <= (others => '0');
                        trig_out_timer <= (others => '0');
                        intensity_timer <= (others => '0');
                        cooldown_timer <= (others => '0');
                        monitor_start_timer <= (others => '0');
                        monitor_duration_timer <= (others => '0');
                        monitor_window_open <= '0';
                        monitor_triggered <= '0';

                    when STATE_IDLE =>
                        -- Reset all counters
                        armed_timer <= (others => '0');
                        trig_out_timer <= (others => '0');
                        intensity_timer <= (others => '0');
                        cooldown_timer <= (others => '0');
                        monitor_start_timer <= (others => '0');
                        monitor_duration_timer <= (others => '0');
                        monitor_window_open <= '0';
                        monitor_triggered <= '0';

                    when STATE_ARMED =>
                        -- Increment timeout counter
                        if armed_timer < latched_trigger_wait_timeout then
                            armed_timer <= armed_timer + 1;
                        end if;

                    when STATE_FIRING =>
                        -- Trigger output pulse timing
                        if trig_out_timer < latched_trig_out_duration then
                            trig_out_timer <= trig_out_timer + 1;
                        end if;

                        -- Intensity output pulse timing
                        if intensity_timer < latched_intensity_duration then
                            intensity_timer <= intensity_timer + 1;
                        end if;

                        -- Monitor window timing
                        if monitor_enable = '1' then
                            if monitor_start_timer < monitor_window_start then
                                -- Delay before window opens
                                monitor_start_timer <= monitor_start_timer + 1;
                                monitor_window_open <= '0';
                            elsif monitor_duration_timer < monitor_window_duration then
                                -- Window is open
                                monitor_duration_timer <= monitor_duration_timer + 1;
                                monitor_window_open <= '1';

                                -- Latch threshold crossing during window
                                if threshold_crossed = '1' then
                                    monitor_triggered <= '1';
                                end if;
                            else
                                -- Window closed
                                monitor_window_open <= '0';
                            end if;
                        end if;

                    when STATE_COOLDOWN =>
                        -- Increment cooldown counter
                        if cooldown_timer < latched_cooldown_interval then
                            cooldown_timer <= cooldown_timer + 1;
                        end if;

                    when STATE_FAULT =>
                        -- Hold all counters in fault state
                        null;

                    when others =>
                        -- Safety: reset counters
                        armed_timer <= (others => '0');
                        trig_out_timer <= (others => '0');
                        intensity_timer <= (others => '0');
                        cooldown_timer <= (others => '0');

                end case;
            end if;
        end if;
    end process;

    ------------------------------------------------------------------------
    -- Output Control with Safety Clamping
    ------------------------------------------------------------------------
    OUTPUT_CONTROL: process(Clk, Reset)
    begin
        if Reset = '1' then
            trig_out <= (others => '0');
            intensity_out <= (others => '0');
        elsif rising_edge(Clk) then
            if Enable = '1' then
                -- Control outputs based on FSM state
                if state = STATE_FIRING then
                    -- During FIRING: output latched voltage signals to probe
                    trig_out <= latched_trig_out_voltage;
                    intensity_out <= latched_intensity_voltage;
                else
                    -- Safe state: zero outputs
                    trig_out <= (others => '0');
                    intensity_out <= (others => '0');
                end if;
            else
                -- When disabled, force safe state
                trig_out <= (others => '0');
                intensity_out <= (others => '0');
            end if;
        end if;
    end process;

    ------------------------------------------------------------------------
    -- Debug Status Vector (Registered for HVS Encoding)
    --
    -- Provides glitch-free status output for hierarchical voltage encoding
    -- Status bits follow FORGE standard:
    --   [7] = fault_detected (MUST be fault for HVS sign flip)
    --   [6] = timeout_occurred
    --   [5] = monitor_triggered
    --   [4] = monitor_window_open
    --   [3] = firing_complete
    --   [2] = cooldown_complete
    --   [1:0] = reserved (set to '0')
    ------------------------------------------------------------------------
    STATUS_REGISTER: process(Clk, Reset)
    begin
        if Reset = '1' then
            status_reg <= (others => '0');
        elsif rising_edge(Clk) then
            if Enable = '1' then
                status_reg <= fault_detected &
                              timeout_occurred &
                              monitor_triggered &
                              monitor_window_open &
                              firing_complete &
                              cooldown_complete &
                              "00";  -- Reserved bits
            else
                status_reg <= (others => '0');
            end if;
        end if;
    end process;

    ------------------------------------------------------------------------
    -- Status Flags (Combinational)
    --
    -- Derive control flags from counter values using latched register values
    ------------------------------------------------------------------------
    timeout_occurred  <= '1' when (armed_timer >= latched_trigger_wait_timeout) else '0';
    firing_complete   <= '1' when (trig_out_timer >= latched_trig_out_duration
                                   and intensity_timer >= latched_intensity_duration
                                   and state = STATE_FIRING) else '0';
    cooldown_complete <= '1' when (cooldown_timer >= latched_cooldown_interval) else '0';

    ------------------------------------------------------------------------
    -- Fault Detection Logic
    --
    -- Detect safety violations
    ------------------------------------------------------------------------
    FAULT_DETECTION: process(state, armed_timer, latched_trigger_wait_timeout)
    begin
        fault_detected <= '0';  -- Default: no fault

        -- Detect timeout in ARMED state
        if state = STATE_ARMED and armed_timer > latched_trigger_wait_timeout then
            fault_detected <= '1';
        end if;

        -- Add additional fault conditions here as needed
    end process;

    ----------------------------------------------------------------------------
    -- Pack outputs to MCC
    ----------------------------------------------------------------------------
    OutputA <= trig_out;        -- Trigger signal to probe
    OutputB <= intensity_out;   -- Intensity/amplitude to probe

    ----------------------------------------------------------------------------
    -- Export debug signals for HVS encoding (done in shim layer)
    ----------------------------------------------------------------------------
    state_vector  <= state;      -- 6-bit FSM state
    status_vector <= status_reg; -- 8-bit registered status

    ----------------------------------------------------------------------------
    -- BRAM Reserved for Future Use
    -- Could store:
    --   - Waveform patterns for shaped pulses
    --   - Calibration data
    --   - Timing sequence tables
    --   - Multi-shot patterns
    ----------------------------------------------------------------------------

end architecture rtl;

