--------------------------------------------------------------------------------
-- File: B1_BOOT_BIOS.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-29
--
-- Description:
--   BIOS module stub for hardware validation. Implements a minimal 3-state FSM
--   (IDLE → RUN → DONE) that produces observable HVS voltage transitions.

--  NOTE:  In validation/STUB mode, BIOS auto-advances through states with a configurable
--   delay counter, allowing oscilloscope observation of state transitions.

-- Concerns / #TODOS
-- - @C / @JC we need to authoritatively decide how to handle the 'boot/bios/loader' 'boot time' constants and definitions. Since we allow BIOS/LOADER->BOOT transitions, these interfaces, though designed to be conceptually independent, may actually have a little bit of cross module bit level symbol references. After we make CR0->BOOT_CR0 things will improve in that regard 


-- FSM States:
--   BIOS_IDLE  (S=8)  - Entry state after dispatch from BOOT_P1
--   BIOS_RUN   (S=9)  - Executing (auto-advances after delay)
--   BIOS_DONE  (S=10) - Complete, waiting for RET to return to BOOT_P1
--   BIOS_FAULT (S=11) - Error state (reserved for future use)
--
-- Validation Behavior:
--   1. Enter IDLE when dispatched from BOOT
--   2. Auto-transition IDLE → RUN after 1 cycle
--   3. Count down delay counter in RUN state
--   4. Transition RUN → DONE when counter expires
--   5. Assert bios_complete, wait for RET
--
-- Reference:
--   docs/boot/BOOT-HW-VALIDATION-PLAN.md
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;
use WORK.forge_common_pkg.all;

entity B1_BOOT_BIOS is
    generic (
        
        -- @C: Renamed this generic for clarity on use-case 
        -- Delay cycles in RUN state before transitioning to DONE
        -- Default: 125000 cycles = 1ms @ 125MHz (observable on scope)
        BIOS_STUB_DELAY_CYCLES : natural := 125000 

    );
    port (
        -- Clock and Reset
        Clk   : in std_logic;
        Reset : in std_logic;

        -- Enable signal from BOOT (high when BOOT_STATE = BIOS_ACTIVE)
        bios_enable : in std_logic;

        -- State outputs (for HVS encoding by parent)
        state_vector  : out std_logic_vector(5 downto 0);
        status_vector : out std_logic_vector(7 downto 0);

        -- Control signals to BOOT
        bios_complete : out std_logic   -- Asserted in DONE state
    );
end entity B1_BOOT_BIOS;

architecture rtl of B1_BOOT_BIOS is

    -- FSM State
    signal state      : std_logic_vector(5 downto 0);
    signal state_next : std_logic_vector(5 downto 0);

    -- Delay counter for RUN state
    signal delay_counter : unsigned(23 downto 0);  -- Up to 16M cycles (~134ms)

    -- Enable edge detection (to detect fresh dispatch)
    signal bios_enable_prev : std_logic;
    signal bios_enable_rise : std_logic;

begin

    ----------------------------------------------------------------------------
    -- Enable Edge Detection
    -- Detect rising edge of bios_enable to know when freshly dispatched
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                bios_enable_prev <= '0';
            else
                bios_enable_prev <= bios_enable;
            end if;
        end if;
    end process;

    bios_enable_rise <= bios_enable and not bios_enable_prev;

    ----------------------------------------------------------------------------
    -- FSM State Register
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                state <= BIOS_STATE_IDLE;
            elsif bios_enable = '0' then
                -- When disabled (RET or RUN gate removed), reset to IDLE
                state <= BIOS_STATE_IDLE;
            else
                state <= state_next;
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- FSM Next State Logic
    ----------------------------------------------------------------------------
    process(state, bios_enable_rise, delay_counter)
    begin
        state_next <= state;  -- Default: hold state

        case state is
            when BIOS_STATE_IDLE =>
                -- Fresh dispatch: immediately go to RUN
                if bios_enable_rise = '1' then
                    state_next <= BIOS_STATE_RUN;
                end if;

            when BIOS_STATE_RUN =>
                -- Wait for delay counter to expire
                if delay_counter = 0 then
                    state_next <= BIOS_STATE_DONE;
                end if;

            when BIOS_STATE_DONE =>
                -- Hold until bios_enable goes low (RET handled by parent)
                null;

            when BIOS_STATE_FAULT =>
                -- Hold in fault state
                null;

            when others =>
                state_next <= BIOS_STATE_FAULT;
        end case;
    end process;

    ----------------------------------------------------------------------------
    -- Delay Counter
    -- Counts down from BIOS_STUB_DELAY_CYCLES when in RUN state
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' or state = BIOS_STATE_IDLE then
                -- Load counter when entering IDLE (ready for next RUN)
                delay_counter <= to_unsigned(BIOS_STUB_DELAY_CYCLES, delay_counter'length);
            elsif state = BIOS_STATE_RUN and delay_counter > 0 then
                delay_counter <= delay_counter - 1;
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Output Assignments
    ----------------------------------------------------------------------------
    state_vector <= state;

    -- Status vector: encode useful debug info
    -- [7]   = fault indicator (for HVS sign flip)
    -- [6:0] = reserved (can add run_count, etc.)
    status_vector(7) <= '1' when state = BIOS_STATE_FAULT else '0';
    status_vector(6 downto 0) <= (others => '0');

    -- Control outputs
    bios_complete <= '1' when state = BIOS_STATE_DONE else '0';

end architecture rtl;
