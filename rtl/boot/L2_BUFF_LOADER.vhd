--------------------------------------------------------------------------------
-- File: L2_BUFF_LOADER.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-29
--
-- Description:
--   LOADER module for populating ENV_BBUFs via blind handshake protocol.
--   Outputs parallel write signals for B0_BOOT_TOP to write to its BRAMs.
--   CRC-16 validation ensures data integrity.
--
-- Architecture Note:
--   BRAMs are owned by B0_BOOT_TOP, not this module. This module outputs:
--   - wr_data_0..3: Parallel data from CR1-CR4
--   - wr_addr: Word offset (0-1023)
--   - wr_we: Write enable (asserted on strobe falling edge in P1)
--
-- FSM States:
--   LOAD_P0 (000000) - Setup phase: latch expected CRCs from CR1-4
--   LOAD_P1 (000001) - Transfer phase: receive 1024 words per buffer
--   LOAD_P2 (000010) - Validate phase: compare running CRC vs expected
--   LOAD_P3 (000011) - Complete: ready for RET to BOOT_P1
--   FAULT   (111111) - CRC mismatch detected
--
-- Protocol:
--   1. Setup strobe falling edge: latch CR1-4 as expected CRCs
--   2. Data strobe falling edges: output CR1-4 + addr + WE, update running CRCs
--   3. After 1024 strobes: transition to LOAD_P2, compare CRCs
--   4. CRC match -> LOAD_P3; mismatch -> FAULT
--
-- Validation Mode:
--   When VALIDATION_MODE = true, CRC checking is bypassed and the module
--   auto-advances P0→P1→P2→P3 using a configurable delay counter. This
--   allows hardware validation of state transitions without needing to
--   implement the full transfer protocol.
--
-- Reference:
--   docs/boot/BBUF-ALLOCATION-DRAFT.md (authoritative)
--   docs/LOAD-FSM-spec.md
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;
use WORK.forge_common_pkg.all;

entity L2_BUFF_LOADER is
    generic (
        -- Validation mode: skip CRC checks, auto-advance through states
        VALIDATION_MODE : boolean := false;

        -- Delay cycles per state in validation mode (default: 1ms @ 125MHz)
        VALIDATION_DELAY_CYCLES : natural := 125000
    );
    port (
        -- Clock and Reset
        Clk   : in std_logic;
        Reset : in std_logic;

        -- Control Registers from CustomWrapper
        CR0 : in std_logic_vector(31 downto 0);
        CR1 : in std_logic_vector(31 downto 0);
        CR2 : in std_logic_vector(31 downto 0);
        CR3 : in std_logic_vector(31 downto 0);
        CR4 : in std_logic_vector(31 downto 0);

        -- State outputs (for HVS encoding by parent)
        state_vector  : out std_logic_vector(5 downto 0);
        status_vector : out std_logic_vector(7 downto 0);

        -- Control signals to BOOT
        loader_fault    : out std_logic;  -- Asserted in FAULT state
        loader_complete : out std_logic;  -- Asserted in LOAD_P3 state

        -- BRAM write interface (parallel writes to B0_BOOT_TOP's BRAMs)
        wr_data_0 : out std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);  -- CR1 → BBUF0
        wr_data_1 : out std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);  -- CR2 → BBUF1
        wr_data_2 : out std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);  -- CR3 → BBUF2
        wr_data_3 : out std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);  -- CR4 → BBUF3
        wr_addr   : out std_logic_vector(ENV_BBUF_ADDR_WIDTH-1 downto 0);  -- Word offset
        wr_we     : out std_logic  -- Write enable (on strobe falling edge in P1)
    );
end entity L2_BUFF_LOADER;

architecture rtl of L2_BUFF_LOADER is

    -- FSM State
    signal state      : std_logic_vector(5 downto 0);
    signal state_next : std_logic_vector(5 downto 0);

    -- Strobe edge detection
    signal strobe_prev    : std_logic;
    signal strobe_falling : std_logic;

    -- Configuration latched during setup
    signal expected_crc0 : std_logic_vector(15 downto 0);
    signal expected_crc1 : std_logic_vector(15 downto 0);
    signal expected_crc2 : std_logic_vector(15 downto 0);
    signal expected_crc3 : std_logic_vector(15 downto 0);

    -- Transfer state
    signal offset : unsigned(ENV_BBUF_ADDR_WIDTH-1 downto 0);  -- 0-1023

    -- Running CRCs (one per buffer)
    signal running_crc0 : std_logic_vector(15 downto 0);
    signal running_crc1 : std_logic_vector(15 downto 0);
    signal running_crc2 : std_logic_vector(15 downto 0);
    signal running_crc3 : std_logic_vector(15 downto 0);

    -- CRC calculator outputs (4 parallel instances)
    signal crc_out0 : std_logic_vector(15 downto 0);
    signal crc_out1 : std_logic_vector(15 downto 0);
    signal crc_out2 : std_logic_vector(15 downto 0);
    signal crc_out3 : std_logic_vector(15 downto 0);

    -- Write enable (internal signal, exposed as wr_we port)
    signal bram_we : std_logic;

    -- CRC comparison result
    signal crc_match : std_logic;

    -- Validation mode signals
    signal val_delay_counter : unsigned(23 downto 0);  -- Up to 16M cycles (~134ms)
    signal val_delay_done    : std_logic;

begin

    ----------------------------------------------------------------------------
    -- CRC-16 Calculator Instances (4 parallel, one per buffer)
    ----------------------------------------------------------------------------
    CRC_CALC_0: entity WORK.loader_crc16
        port map (
            crc_in  => running_crc0,
            data_in => CR1,
            crc_out => crc_out0
        );

    CRC_CALC_1: entity WORK.loader_crc16
        port map (
            crc_in  => running_crc1,
            data_in => CR2,
            crc_out => crc_out1
        );

    CRC_CALC_2: entity WORK.loader_crc16
        port map (
            crc_in  => running_crc2,
            data_in => CR3,
            crc_out => crc_out2
        );

    CRC_CALC_3: entity WORK.loader_crc16
        port map (
            crc_in  => running_crc3,
            data_in => CR4,
            crc_out => crc_out3
        );

    ----------------------------------------------------------------------------
    -- Strobe Edge Detection
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                strobe_prev <= '0';
            else
                strobe_prev <= CR0(LOADER_STROBE_BIT);
            end if;
        end if;
    end process;

    strobe_falling <= strobe_prev and not CR0(LOADER_STROBE_BIT);

    ----------------------------------------------------------------------------
    -- FSM State Register
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                state <= LOAD_STATE_P0;
            else
                state <= state_next;
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- FSM Next State Logic
    ----------------------------------------------------------------------------
    NORMAL_FSM: if not VALIDATION_MODE generate
        process(state, strobe_falling, offset, crc_match)
        begin
            state_next <= state;  -- Default: hold state

            case state is
                when LOAD_STATE_P0 =>
                    -- Setup phase: wait for setup strobe
                    if strobe_falling = '1' then
                        state_next <= LOAD_STATE_P1;
                    end if;

                when LOAD_STATE_P1 =>
                    -- Transfer phase: receive 1024 words
                    if strobe_falling = '1' then
                        if offset = to_unsigned(ENV_BBUF_WORDS - 1, offset'length) then
                            -- Last word received, go to validation
                            state_next <= LOAD_STATE_P2;
                        end if;
                        -- Otherwise stay in P1, offset increments in sequential process
                    end if;

                when LOAD_STATE_P2 =>
                    -- Validate phase: check CRCs (combinatorial, immediate)
                    if crc_match = '1' then
                        state_next <= LOAD_STATE_P3;
                    else
                        state_next <= LOAD_STATE_FAULT;
                    end if;

                when LOAD_STATE_P3 =>
                    -- Complete: hold until RET (handled by BOOT parent)
                    null;

                when LOAD_STATE_FAULT =>
                    -- Fault: hold until fault_clear (handled by BOOT parent)
                    null;

                when others =>
                    state_next <= LOAD_STATE_FAULT;
            end case;
        end process;
    end generate NORMAL_FSM;

    ----------------------------------------------------------------------------
    -- Validation Mode FSM: Auto-advance P0→P1→P2→P3 with delay
    ----------------------------------------------------------------------------
    VALIDATION_FSM: if VALIDATION_MODE generate
        process(state, val_delay_done)
        begin
            state_next <= state;  -- Default: hold state

            case state is
                when LOAD_STATE_P0 =>
                    -- Auto-advance to P1 after delay
                    if val_delay_done = '1' then
                        state_next <= LOAD_STATE_P1;
                    end if;

                when LOAD_STATE_P1 =>
                    -- Auto-advance to P2 after delay
                    if val_delay_done = '1' then
                        state_next <= LOAD_STATE_P2;
                    end if;

                when LOAD_STATE_P2 =>
                    -- Auto-advance to P3 after delay (skip CRC check)
                    if val_delay_done = '1' then
                        state_next <= LOAD_STATE_P3;
                    end if;

                when LOAD_STATE_P3 =>
                    -- Complete: hold until RET (handled by BOOT parent)
                    null;

                when LOAD_STATE_FAULT =>
                    -- Fault: hold until fault_clear (handled by BOOT parent)
                    null;

                when others =>
                    state_next <= LOAD_STATE_FAULT;
            end case;
        end process;

        -- Validation delay counter
        process(Clk)
        begin
            if rising_edge(Clk) then
                if Reset = '1' then
                    val_delay_counter <= to_unsigned(VALIDATION_DELAY_CYCLES, val_delay_counter'length);
                elsif state /= state_next then
                    -- State is about to change, reload counter
                    val_delay_counter <= to_unsigned(VALIDATION_DELAY_CYCLES, val_delay_counter'length);
                elsif val_delay_counter > 0 then
                    val_delay_counter <= val_delay_counter - 1;
                end if;
            end if;
        end process;

        val_delay_done <= '1' when val_delay_counter = 0 else '0';
    end generate VALIDATION_FSM;

    -- In normal mode, validation signals are unused
    NORMAL_VAL: if not VALIDATION_MODE generate
        val_delay_done <= '0';
    end generate NORMAL_VAL;

    ----------------------------------------------------------------------------
    -- Configuration Latch (on setup strobe in P0)
    -- Latches expected CRCs from CR1-CR4 (lower 16 bits of each)
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                expected_crc0 <= (others => '0');
                expected_crc1 <= (others => '0');
                expected_crc2 <= (others => '0');
                expected_crc3 <= (others => '0');
            elsif state = LOAD_STATE_P0 and strobe_falling = '1' then
                -- Latch expected CRCs from CR1-CR4 (lower 16 bits of each)
                expected_crc0 <= CR1(15 downto 0);
                expected_crc1 <= CR2(15 downto 0);
                expected_crc2 <= CR3(15 downto 0);
                expected_crc3 <= CR4(15 downto 0);
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Offset Counter (increments on each data strobe in P1)
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' or state = LOAD_STATE_P0 then
                offset <= (others => '0');
            elsif state = LOAD_STATE_P1 and strobe_falling = '1' then
                offset <= offset + 1;
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Running CRC Update (on each data strobe in P1)
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' or (state = LOAD_STATE_P0 and strobe_falling = '1') then
                -- Initialize running CRCs to 0xFFFF
                running_crc0 <= CRC16_INIT;
                running_crc1 <= CRC16_INIT;
                running_crc2 <= CRC16_INIT;
                running_crc3 <= CRC16_INIT;
            elsif state = LOAD_STATE_P1 and strobe_falling = '1' then
                -- Update running CRCs with computed values
                running_crc0 <= crc_out0;
                running_crc1 <= crc_out1;
                running_crc2 <= crc_out2;
                running_crc3 <= crc_out3;
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Write Enable (asserted on strobe falling edge during P1)
    ----------------------------------------------------------------------------
    bram_we <= '1' when state = LOAD_STATE_P1 and strobe_falling = '1' else '0';

    ----------------------------------------------------------------------------
    -- CRC Comparison (in LOAD_P2)
    -- Always validates all 4 buffer CRCs (design decision: always 4 buffers)
    ----------------------------------------------------------------------------
    process(running_crc0, running_crc1, running_crc2, running_crc3,
            expected_crc0, expected_crc1, expected_crc2, expected_crc3)
        variable match : std_logic;
    begin
        match := '1';

        -- Check all 4 buffer CRCs
        if running_crc0 /= expected_crc0 then
            match := '0';
        end if;

        if running_crc1 /= expected_crc1 then
            match := '0';
        end if;

        if running_crc2 /= expected_crc2 then
            match := '0';
        end if;

        if running_crc3 /= expected_crc3 then
            match := '0';
        end if;

        crc_match <= match;
    end process;

    ----------------------------------------------------------------------------
    -- Output Assignments
    ----------------------------------------------------------------------------
    state_vector <= state;

    -- Status vector: encode useful debug info
    -- [7]   = fault indicator (for HVS sign flip)
    -- [6:0] = reserved (formerly had buffer_count, now always 4 buffers)
    status_vector(7) <= '1' when state = LOAD_STATE_FAULT else '0';
    status_vector(6 downto 0) <= (others => '0');

    -- Control outputs
    loader_fault    <= '1' when state = LOAD_STATE_FAULT else '0';
    loader_complete <= '1' when state = LOAD_STATE_P3 else '0';

    -- BRAM write interface outputs
    -- Data: direct from Control Registers (CR1→BBUF0, CR2→BBUF1, etc.)
    wr_data_0 <= CR1;
    wr_data_1 <= CR2;
    wr_data_2 <= CR3;
    wr_data_3 <= CR4;

    -- Address: current offset (0-1023)
    wr_addr <= std_logic_vector(offset);

    -- Write enable: asserted on strobe falling edge in P1
    wr_we <= bram_we;

end architecture rtl;
