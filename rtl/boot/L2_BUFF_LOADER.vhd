--------------------------------------------------------------------------------
-- File: L2_BUFF_LOADER.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-29
--
-- Description:
--   LOADER module for populating ENV_BBUFs via blind handshake protocol.
--   Receives data from Python client via Control Registers and writes to
--   1-4 BRAM buffers with CRC-16 validation.
--
-- FSM States:
--   LOAD_P0 (000000) - Setup phase: latch buffer count + expected CRCs
--   LOAD_P1 (000001) - Transfer phase: receive 1024 words per buffer
--   LOAD_P2 (000010) - Validate phase: compare running CRC vs expected
--   LOAD_P3 (000011) - Complete: ready for RET to BOOT_P1
--   FAULT   (111111) - CRC mismatch detected
--
-- Protocol:
--   1. Setup strobe falling edge: latch CR0[23:22] (bufcnt), CR1-4 (CRCs)
--   2. Data strobe falling edges: write CR1-4 to BRAMs, update running CRCs
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
--   docs/bootup-proposal/LOAD-FSM-spec.md (authoritative)
--   docs/bootup-proposal/LOADER-implementation-plan.md
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

        -- BRAM read interface (for PROG access after loading)
        bram_rd_addr : in  std_logic_vector(ENV_BBUF_ADDR_WIDTH-1 downto 0);
        bram_rd_sel  : in  std_logic_vector(1 downto 0);  -- Which buffer (0-3)
        bram_rd_data : out std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0)
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
    signal buffer_count : unsigned(1 downto 0);  -- 0=1buf, 1=2buf, 2=3buf, 3=4buf
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

    -- BRAM storage (4 buffers, inferred as block RAM)
    type bram_t is array (0 to ENV_BBUF_WORDS-1) of std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);

    signal bram_0 : bram_t := (others => (others => '0'));
    signal bram_1 : bram_t := (others => (others => '0'));
    signal bram_2 : bram_t := (others => (others => '0'));
    signal bram_3 : bram_t := (others => (others => '0'));

    -- BRAM read data
    signal bram_rd_0 : std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);
    signal bram_rd_1 : std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);
    signal bram_rd_2 : std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);
    signal bram_rd_3 : std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);

    -- Write enable
    signal bram_we : std_logic;

    -- CRC comparison result
    signal crc_match : std_logic;

    -- Validation mode signals
    signal val_delay_counter : unsigned(23 downto 0);  -- Up to 16M cycles (~134ms)
    signal val_delay_done    : std_logic;

    -- Attribute for BRAM inference
    attribute ram_style : string;
    attribute ram_style of bram_0 : signal is "block";
    attribute ram_style of bram_1 : signal is "block";
    attribute ram_style of bram_2 : signal is "block";
    attribute ram_style of bram_3 : signal is "block";

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
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                buffer_count <= (others => '0');
                expected_crc0 <= (others => '0');
                expected_crc1 <= (others => '0');
                expected_crc2 <= (others => '0');
                expected_crc3 <= (others => '0');
            elsif state = LOAD_STATE_P0 and strobe_falling = '1' then
                -- Latch buffer count from CR0[23:22]
                buffer_count <= unsigned(CR0(LOADER_BUFCNT_HI downto LOADER_BUFCNT_LO));
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
    -- BRAM Write Logic
    ----------------------------------------------------------------------------
    bram_we <= '1' when state = LOAD_STATE_P1 and strobe_falling = '1' else '0';

    -- BRAM Write Process (inferred block RAM with write enable)
    process(Clk)
    begin
        if rising_edge(Clk) then
            if bram_we = '1' then
                -- Write to all buffers in parallel
                -- (buffer_count only affects CRC validation, not writes)
                bram_0(to_integer(offset)) <= CR1;
                bram_1(to_integer(offset)) <= CR2;
                bram_2(to_integer(offset)) <= CR3;
                bram_3(to_integer(offset)) <= CR4;
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- BRAM Read Logic (for PROG access)
    ----------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            bram_rd_0 <= bram_0(to_integer(unsigned(bram_rd_addr)));
            bram_rd_1 <= bram_1(to_integer(unsigned(bram_rd_addr)));
            bram_rd_2 <= bram_2(to_integer(unsigned(bram_rd_addr)));
            bram_rd_3 <= bram_3(to_integer(unsigned(bram_rd_addr)));
        end if;
    end process;

    -- Read data mux
    with bram_rd_sel select bram_rd_data <=
        bram_rd_0 when "00",
        bram_rd_1 when "01",
        bram_rd_2 when "10",
        bram_rd_3 when "11",
        (others => '0') when others;

    ----------------------------------------------------------------------------
    -- CRC Comparison (in LOAD_P2)
    ----------------------------------------------------------------------------
    process(running_crc0, running_crc1, running_crc2, running_crc3,
            expected_crc0, expected_crc1, expected_crc2, expected_crc3,
            buffer_count)
        variable match : std_logic;
    begin
        match := '1';

        -- Always check buffer 0
        if running_crc0 /= expected_crc0 then
            match := '0';
        end if;

        -- Check additional buffers based on buffer_count
        if buffer_count >= 1 then
            if running_crc1 /= expected_crc1 then
                match := '0';
            end if;
        end if;

        if buffer_count >= 2 then
            if running_crc2 /= expected_crc2 then
                match := '0';
            end if;
        end if;

        if buffer_count >= 3 then
            if running_crc3 /= expected_crc3 then
                match := '0';
            end if;
        end if;

        crc_match <= match;
    end process;

    ----------------------------------------------------------------------------
    -- Output Assignments
    ----------------------------------------------------------------------------
    state_vector <= state;

    -- Status vector: encode useful debug info
    -- [7]   = fault indicator (for HVS sign flip)
    -- [6:4] = reserved
    -- [3:2] = buffer_count
    -- [1:0] = reserved
    status_vector(7) <= '1' when state = LOAD_STATE_FAULT else '0';
    status_vector(6 downto 4) <= (others => '0');
    status_vector(3 downto 2) <= std_logic_vector(buffer_count);
    status_vector(1 downto 0) <= (others => '0');

    -- Control outputs
    loader_fault    <= '1' when state = LOAD_STATE_FAULT else '0';
    loader_complete <= '1' when state = LOAD_STATE_P3 else '0';

end architecture rtl;
