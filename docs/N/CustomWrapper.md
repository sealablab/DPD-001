---
created: 2025-11-27
modified: 2025-11-30 18:48:11
accessed: 2025-11-30 18:39:16
---
# [CustomWrapper](https://apis.liquidinstruments.com/mcc/wrapper.html)

The **Custom Wrapper** is the interface (or contract) that lets users mix-and-match instruments on the Moku platform. It is the **current standard** for Moku Cloud Compile (MCC) deployments.

# See Also
## [cloudcompile](moku_trim_examples/instruments/cloudcompile.md)
## [mim](moku_md/instruments/mim.md)


## Entity Signature

**Standard CustomWrapper entity:**

```vhdl
entity CustomWrapper is
    port (
        -- Clock and Reset
        Clk    : in  std_logic;
        Reset  : in  std_logic;
        
        -- Input signals (ADC data, signed 16-bit)
        InputA : in  signed(15 downto 0);
        InputB : in  signed(15 downto 0);
        InputC : in  signed(15 downto 0); --InputC not always available
        
        -- Output signals (DAC data, signed 16-bit)
        OutputA : out signed(15 downto 0);
        OutputB : out signed(15 downto 0);
        OutputC : out signed(15 downto 0); -- OutputC not always available
        
        -- Control registers (32-bit each, from Moku platform)
        -- Note: std_logic_vector, NOT signed!
        -- Total: 16 registers (Control0-15) in standard implementation
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
end entity CustomWrapper;
```

**Key Points:**
- **Inputs/Outputs:** `signed(15 downto 0)` - 16-bit signed integers (representing ±5V range for Moku:Go)
- **Control Registers:** `std_logic_vector(31 downto 0)` - 32-bit unsigned vectors 
- **Total Registers:** 16 registers (Control0-15) in standard implementation

---
# See Also
# [BootWrapper](docs/N/BootWrapper.md)
# [CustomInstrument](docs/N/CustomInstrument.md)


 
---

