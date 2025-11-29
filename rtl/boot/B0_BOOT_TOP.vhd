--------------------------------------------------------------------------------
-- File: B0_BOOT_TOP.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-29
--
-- Description:
--   BOOT subsystem top-level module implementing the CustomWrapper architecture.
--   This is the dispatcher FSM that routes control to BIOS, LOADER, or PROG
--   based on CR0[28:25] module select bits.
--
-- FSM States:
--   BOOT_P0 (000000) - Initial/Reset state, waiting for RUN gate
--   BOOT_P1 (000001) - Settled/Dispatcher, waiting for module select
--   BIOS_ACTIVE (000010) - Control transferred to BIOS module
--   LOAD_ACTIVE (000011) - Control transferred to LOADER module
--   PROG_ACTIVE (000100) - Control transferred to PROG (one-way)
--   FAULT (111111) - Boot fault (invalid state or error)
--
-- Module Select Commands (CR0[28:25]):
--   RUNP (P=1) - Transfer to PROG (one-way, cannot return)
--   RUNB (B=1) - Transfer to BIOS (can return via RET)
--   RUNL (L=1) - Transfer to LOADER (can return via RET)
--   RUNR (R=1) - Soft reset back to BOOT_P0
--
-- Architecture:
--   This module owns the ENV_BBUF BRAMs (via LOADER instantiation) and
--   provides combinatorial output muxing to avoid clock delay on outputs.
--
-- Reference:
--   docs/BOOT-FSM-spec.md (authoritative)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;
use WORK.forge_common_pkg.all;
use WORK.forge_hierarchical_encoder;

-- This is the BootWrapper architecture for BOOT subsystem
-- Implements the standard Moku CloudCompile interface
-- Note: Uses BootWrapper entity (not CustomWrapper) to avoid GHDL collision
architecture boot_forge of BootWrapper is

    -- BOOT FSM state
    signal boot_state      : std_logic_vector(5 downto 0);
    signal boot_state_next : std_logic_vector(5 downto 0);

    -- RUN gate signals
    signal run_active : std_logic;

    -- Module select signals
    signal sel_prog   : std_logic;
    signal sel_bios   : std_logic;
    signal sel_loader : std_logic;
    signal sel_reset  : std_logic;
    signal ret_active : std_logic;

    -- LOADER signals
    signal loader_state    : std_logic_vector(5 downto 0);
    signal loader_status   : std_logic_vector(7 downto 0);
    signal loader_fault    : std_logic;
    signal loader_complete : std_logic;

    -- BRAM read interface (for PROG access)
    signal bram_rd_addr : std_logic_vector(ENV_BBUF_ADDR_WIDTH-1 downto 0);
    signal bram_rd_sel  : std_logic_vector(1 downto 0);
    signal bram_rd_data : std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);

    -- Output signals from each module
    signal boot_output_a   : signed(15 downto 0);
    signal boot_output_b   : signed(15 downto 0);
    signal boot_output_c   : signed(15 downto 0);

    signal loader_output_c : signed(15 downto 0);
    signal bios_output_c   : signed(15 downto 0);
    signal prog_output_a   : signed(15 downto 0);
    signal prog_output_b   : signed(15 downto 0);
    signal prog_output_c   : signed(15 downto 0);

    -- HVS encoding: map internal states to global S values
    signal boot_hvs_s_global   : std_logic_vector(5 downto 0);  -- BOOT: S=0-7
    signal loader_hvs_s_global : std_logic_vector(5 downto 0);  -- LOADER: S=16-23
    signal bios_hvs_s_global  : std_logic_vector(5 downto 0);  -- BIOS: S=8-15
    signal bios_status        : std_logic_vector(7 downto 0);   -- BIOS status

    -- HVS encoding: map BOOT internal states to global S values (0-7)
    signal boot_hvs_s_global : std_logic_vector(5 downto 0);  -- Global S value for BOOT
    signal boot_status       : std_logic_vector(7 downto 0);   -- Status vector for HVS
    signal boot_hvs_output   : signed(15 downto 0);            -- Encoded HVS output

    -- PROG enable (for DPD_shim)
    signal prog_enable : std_logic;

begin

    ----------------------------------------------------------------------------
    -- RUN Gate and Module Select Extraction
    ----------------------------------------------------------------------------
    run_active <= '1' when Control0(RUN_READY_BIT) = '1' and
                           Control0(RUN_USER_BIT) = '1' and
                           Control0(RUN_CLK_BIT) = '1'
                  else '0';

    sel_prog   <= Control0(SEL_PROG_BIT);
    sel_bios   <= Control0(SEL_BIOS_BIT);
    sel_loader <= Control0(SEL_LOADER_BIT);
    sel_reset  <= Control0(SEL_RESET_BIT);
    ret_active <= Control0(RET_BIT);

    ----------------------------------------------------------------------------
    -- LOADER Instantiation
    ----------------------------------------------------------------------------
    LOADER_INST: entity WORK.L2_BUFF_LOADER
        port map (
            Clk   => Clk,
            Reset => Reset,
            CR0   => Control0,
            CR1   => Control1,
            CR2   => Control2,
            CR3   => Control3,
            CR4   => Control4,
            state_vector  => loader_state,
            status_vector => loader_status,
            loader_fault    => loader_fault,
            loader_complete => loader_complete,
            bram_rd_addr => bram_rd_addr,
            bram_rd_sel  => bram_rd_sel,
            bram_rd_data => bram_rd_data
        );

    ----------------------------------------------------------------------------
    -- LOADER HVS Encoding: Map internal states to global S values (16-23)
    ----------------------------------------------------------------------------
    process(loader_state)
    begin
        case loader_state is
            when LOAD_STATE_P0 =>
                loader_hvs_s_global <= std_logic_vector(to_unsigned(LOADER_HVS_S_P0, 6));
            when LOAD_STATE_P1 =>
                loader_hvs_s_global <= std_logic_vector(to_unsigned(LOADER_HVS_S_P1, 6));
            when LOAD_STATE_P2 =>
                loader_hvs_s_global <= std_logic_vector(to_unsigned(LOADER_HVS_S_P2, 6));
            when LOAD_STATE_P3 =>
                loader_hvs_s_global <= std_logic_vector(to_unsigned(LOADER_HVS_S_P3, 6));
            when LOAD_STATE_FAULT =>
                loader_hvs_s_global <= std_logic_vector(to_unsigned(LOADER_HVS_S_FAULT, 6));
            when others =>
                loader_hvs_s_global <= std_logic_vector(to_unsigned(LOADER_HVS_S_P0, 6));
        end case;
    end process;

    -- LOADER HVS Encoder
    LOADER_HVS_ENCODER: entity WORK.forge_hierarchical_encoder
        generic map (
            DIGITAL_UNITS_PER_STATE  => HVS_PRE_STATE_UNITS,
            DIGITAL_UNITS_PER_STATUS => real(HVS_PRE_STATUS_UNITS)
        )
        port map (
            clk           => Clk,
            reset         => Reset,
            state_vector  => loader_hvs_s_global,
            status_vector => loader_status,
            voltage_out   => loader_output_c
        );

    ----------------------------------------------------------------------------
    -- BIOS Stub (placeholder for future implementation)
    ----------------------------------------------------------------------------
    -- For now, BIOS outputs HVS using global S=8 (BIOS_ACTIVE base state)
    -- TODO: When BIOS is implemented, map its internal states to S=8-15
    bios_hvs_s_global <= std_logic_vector(to_unsigned(8, 6));  -- S=8: BIOS_ACTIVE
    bios_status <= (others => '0');
    
    BIOS_HVS_ENCODER: entity WORK.forge_hierarchical_encoder
        generic map (
            DIGITAL_UNITS_PER_STATE  => HVS_PRE_STATE_UNITS,
            DIGITAL_UNITS_PER_STATUS => real(HVS_PRE_STATUS_UNITS)
        )
        port map (
            clk           => Clk,
            reset         => Reset,
            state_vector  => bios_hvs_s_global,
            status_vector => bios_status,
            voltage_out   => bios_output_c
        );

    ----------------------------------------------------------------------------
    -- PROG (DPD_shim) Instantiation
    --
    -- In PROG_ACTIVE state, we instantiate the DPD_shim which handles:
    -- - CR2-CR10 register mapping to application signals
    -- - HVS encoding on OutputC
    -- - The actual DPD_main FSM
    ----------------------------------------------------------------------------
    prog_enable <= '1' when boot_state = BOOT_STATE_PROG_ACTIVE else '0';

    -- For now, stub outputs - in real implementation, instantiate DPD_shim
    -- and connect it here
    prog_output_a <= (others => '0');
    prog_output_b <= (others => '0');
    prog_output_c <= to_signed(4 * HVS_BOOT_UNITS_PER_STATE, 16);  -- 0.8V stub

    -- BRAM read interface (for PROG to read ENV_BBUFs)
    -- In real implementation, PROG would drive these
    bram_rd_addr <= (others => '0');
    bram_rd_sel  <= "00";

    ----------------------------------------------------------------------------
    -- BOOT FSM State Register
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                boot_state <= BOOT_STATE_P0;
            else
                boot_state <= boot_state_next;
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- BOOT FSM Next State Logic
    ----------------------------------------------------------------------------
    process(boot_state, run_active, sel_prog, sel_bios, sel_loader, sel_reset,
            ret_active, loader_complete, loader_fault)
    begin
        boot_state_next <= boot_state;  -- Default: hold state

        case boot_state is
            when BOOT_STATE_P0 =>
                -- Initial state: wait for RUN gate
                if run_active = '1' then
                    boot_state_next <= BOOT_STATE_P1;
                end if;

            when BOOT_STATE_P1 =>
                -- Dispatcher: wait for module select
                if run_active = '0' then
                    -- RUN gate removed, go back to P0
                    boot_state_next <= BOOT_STATE_P0;
                elsif sel_prog = '1' then
                    -- RUNP: one-way transfer to PROG
                    boot_state_next <= BOOT_STATE_PROG_ACTIVE;
                elsif sel_bios = '1' then
                    -- RUNB: transfer to BIOS
                    boot_state_next <= BOOT_STATE_BIOS_ACTIVE;
                elsif sel_loader = '1' then
                    -- RUNL: transfer to LOADER
                    boot_state_next <= BOOT_STATE_LOAD_ACTIVE;
                elsif sel_reset = '1' then
                    -- RUNR: soft reset back to P0
                    boot_state_next <= BOOT_STATE_P0;
                end if;

            when BOOT_STATE_BIOS_ACTIVE =>
                -- BIOS active: wait for RET
                if run_active = '0' then
                    boot_state_next <= BOOT_STATE_P0;
                elsif ret_active = '1' then
                    boot_state_next <= BOOT_STATE_P1;
                end if;

            when BOOT_STATE_LOAD_ACTIVE =>
                -- LOADER active: monitor for completion or fault
                if run_active = '0' then
                    boot_state_next <= BOOT_STATE_P0;
                elsif loader_fault = '1' then
                    boot_state_next <= BOOT_STATE_FAULT;
                elsif ret_active = '1' and loader_complete = '1' then
                    -- Only allow return after LOADER completes
                    boot_state_next <= BOOT_STATE_P1;
                end if;

            when BOOT_STATE_PROG_ACTIVE =>
                -- PROG active: one-way, no return
                -- Only RUN gate removal can exit (to P0)
                if run_active = '0' then
                    boot_state_next <= BOOT_STATE_P0;
                end if;
                -- Note: PROG doesn't support RET

            when BOOT_STATE_FAULT =>
                -- Fault state: wait for RUN gate removal to reset
                if run_active = '0' then
                    boot_state_next <= BOOT_STATE_P0;
                end if;

            when others =>
                boot_state_next <= BOOT_STATE_FAULT;
        end case;
    end process;

    ----------------------------------------------------------------------------
    -- BOOT Status Vector
    ----------------------------------------------------------------------------
    boot_status(7) <= '1' when boot_state = BOOT_STATE_FAULT else '0';
    boot_status(6 downto 4) <= (others => '0');
    boot_status(3 downto 0) <= boot_state(3 downto 0);

    ----------------------------------------------------------------------------
    -- BOOT HVS Encoding: Map internal states to global S values (0-7)
    ----------------------------------------------------------------------------
    process(boot_state)
    begin
        case boot_state is
            when BOOT_STATE_P0 =>
                boot_hvs_s_global <= std_logic_vector(to_unsigned(BOOT_HVS_S_P0, 6));
            when BOOT_STATE_P1 =>
                boot_hvs_s_global <= std_logic_vector(to_unsigned(BOOT_HVS_S_P1, 6));
            when BOOT_STATE_FAULT =>
                boot_hvs_s_global <= std_logic_vector(to_unsigned(BOOT_HVS_S_FAULT, 6));
            when others =>
                -- BIOS_ACTIVE, LOAD_ACTIVE, PROG_ACTIVE don't use BOOT HVS
                -- (they use their own encoders or are out of scope)
                boot_hvs_s_global <= std_logic_vector(to_unsigned(BOOT_HVS_S_P0, 6));
        end case;
    end process;

    -- BOOT HVS Encoder
    BOOT_HVS_ENCODER: entity WORK.forge_hierarchical_encoder
        generic map (
            DIGITAL_UNITS_PER_STATE  => HVS_PRE_STATE_UNITS,
            DIGITAL_UNITS_PER_STATUS => real(HVS_PRE_STATUS_UNITS)
        )
        port map (
            clk           => Clk,
            reset         => Reset,
            state_vector  => boot_hvs_s_global,
            status_vector => boot_status,
            voltage_out   => boot_hvs_output
        );

    -- BOOT HVS output (fault handling via status[7] sign flip in encoder)
    boot_output_c <= boot_hvs_output;

    -- BOOT doesn't drive OutputA/B
    boot_output_a <= (others => '0');
    boot_output_b <= (others => '0');

    ----------------------------------------------------------------------------
    -- Output Muxing (Combinatorial)
    --
    -- Routes outputs based on current BOOT state.
    -- PROG gets full control of all outputs.
    -- BIOS and LOADER only drive OutputC for HVS.
    -- BOOT_P0/P1 drive OutputC with BOOT HVS.
    ----------------------------------------------------------------------------
    process(boot_state, boot_output_a, boot_output_b, boot_output_c,
            bios_output_c, loader_output_c,
            prog_output_a, prog_output_b, prog_output_c)
    begin
        case boot_state is
            when BOOT_STATE_PROG_ACTIVE =>
                -- PROG controls all outputs
                OutputA <= prog_output_a;
                OutputB <= prog_output_b;
                OutputC <= prog_output_c;

            when BOOT_STATE_BIOS_ACTIVE =>
                -- BIOS only controls OutputC
                OutputA <= (others => '0');
                OutputB <= (others => '0');
                OutputC <= bios_output_c;

            when BOOT_STATE_LOAD_ACTIVE =>
                -- LOADER only controls OutputC
                OutputA <= (others => '0');
                OutputB <= (others => '0');
                OutputC <= loader_output_c;

            when others =>
                -- BOOT_P0, BOOT_P1, FAULT: BOOT controls OutputC
                OutputA <= boot_output_a;
                OutputB <= boot_output_b;
                OutputC <= boot_output_c;
        end case;
    end process;

end architecture boot_forge;
