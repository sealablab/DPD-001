# DPD-001 Build System

Quick start guide for building and synthesizing the unified BOOT+DPD bitstream.

## Prerequisites

- **GHDL** (v0.37+) - VHDL compiler with automatic dependency resolution
- **Make** - Build automation
- **Moku CloudCompile account** - For generating bitstreams

### Installing GHDL

**macOS (Homebrew):**
```bash
brew install ghdl
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install ghdl
```

**Verify installation:**
```bash
ghdl --version
# Should show GHDL 0.37 or newer
```

---

## Quick Start

### Development Workflow

**1. Compile the design:**
```bash
make compile
```

This automatically:
- Imports all VHDL source files
- Resolves dependencies
- Compiles in the correct order
- Elaborates the `CustomWrapper` top-level entity

**Output:**
```
Importing VHDL sources...
Auto-resolving dependencies and compiling CustomWrapper...
analyze rtl/forge_common_pkg.vhd
analyze rtl/boot/loader_crc16.vhd
... (GHDL handles the order automatically)
✓ Compilation successful!
  CustomWrapper (unified BOOT+DPD) ready for simulation
```

**2. Clean build artifacts:**
```bash
make clean
```

---

## Synthesis Workflow (Moku CloudCompile)

Moku CloudCompile requires all VHDL files in a **single flat directory** (no subdirectories). The Makefile handles this automatically.

### Step 1: Create Synthesis Package

```bash
make synth-prep
```

This creates a `synth/` directory with all production VHDL files flattened:

```
synth/
├── B0_BOOT_TOP.vhd
├── B1_BOOT_BIOS.vhd
├── DPD_main.vhd
├── DPD_shim.vhd
├── DPD.vhd
├── DPD-RTL.yaml                              # Metadata
├── forge_common_pkg.vhd
├── forge_hierarchical_encoder.vhd
├── L2_BUFF_LOADER.vhd
├── loader_crc16.vhd
└── moku_voltage_threshold_trigger_core.vhd
```

**Total: 10 VHDL files (~143 KB)**

### Step 2: Upload to Moku CloudCompile

1. Log into [Moku CloudCompile](https://cloudcompile.liquidinstruments.com/)
2. Create a new project or open existing
3. Upload all files from `synth/` directory:
   - **Drag and drop** all `synth/*.vhd` files into the web interface
   - Include `DPD-RTL.yaml` (metadata for register mapping)

4. Configure synthesis:
   - **Target**: Moku:Go
   - **Top-level entity**: `CustomWrapper`
   - **Clock frequency**: 125 MHz

5. Click **Synthesize**

### Step 3: Download Bitstream

Once synthesis completes (~5-10 minutes):
1. Download the `.tar` bitstream package
2. Save to project root (e.g., `dpd-bits.tar`)

### Step 4: Clean Up

```bash
make synth-clean
```

Removes the `synth/` directory (it's gitignored, so this is optional).

---

## Makefile Targets

### Primary Targets

| Target | Description |
|--------|-------------|
| `make compile` | Compile all VHDL files with auto-dependency resolution (default) |
| `make clean` | Remove GHDL build artifacts (*.o, *.cf, binaries) |
| `make synth-prep` | Create flat `synth/` directory for MCC upload |
| `make synth-clean` | Remove `synth/` directory |
| `make help` | Show all available targets with descriptions |

### Advanced Targets

| Target | Description |
|--------|-------------|
| `make elaborate` | Elaborate design without full compilation (faster, assumes already analyzed) |

---

## How It Works: GHDL Auto-Dependency Resolution

The Makefile uses GHDL's **import + make** workflow to automatically handle dependencies:

```bash
ghdl -i rtl/*.vhd rtl/boot/*.vhd    # Import (index) all source files
ghdl -m CustomWrapper               # Make (compile + elaborate) top entity
```

**GHDL automatically:**
1. Analyzes library dependencies (e.g., `forge_common_pkg` before `DPD_shim`)
2. Compiles files in the correct order
3. Elaborates the top-level entity

**No manual dependency ordering required!** Just add new files to `RTL_SOURCES` in the Makefile.

---

## Architecture Overview

The unified bitstream provides runtime-configurable switching between subsystems:

```
CustomWrapper (MCC interface)
  └─ DPD.vhd (thin wrapper)
      └─ B0_BOOT_TOP.vhd (BOOT dispatcher)
          ├─ B1_BOOT_BIOS.vhd (diagnostics)
          ├─ L2_BUFF_LOADER.vhd (buffer population)
          └─ DPD_shim.vhd → DPD_main.vhd (probe driver application)
```

### Runtime Switching via CR0

| Command | CR0 Value | Action |
|---------|-----------|--------|
| `RUN` | `0xE0000000` | Initialize → BOOT_P1 (dispatcher ready) |
| `RUNP` | `0xF0000000` | Activate DPD application (one-way) |
| `RUNB` | `0xE8000000` | Activate BIOS diagnostics |
| `RUNL` | `0xE4000000` | Activate buffer loader |
| `RUNR` | `0xE2000000` | Soft reset to BOOT_P0 |
| `RET` | `0xE1000000` | Return to dispatcher (from BIOS/LOADER only) |

See `docs/BOOT-FSM-spec.md` for complete state machine specification.

---

## File Structure

```
DPD-001/
├── rtl/                              # VHDL source files
│   ├── DPD.vhd                       # Top-level wrapper (Layer 0)
│   ├── DPD_shim.vhd                  # Register mapping (Layer 2, PROG mode)
│   ├── DPD_main.vhd                  # FSM application logic (Layer 3)
│   ├── forge_common_pkg.vhd          # Common types/constants
│   ├── forge_hierarchical_encoder.vhd # HVS voltage encoding
│   ├── moku_voltage_threshold_trigger_core.vhd
│   ├── CustomWrapper_test_stub.vhd   # Test entity (excluded from synth)
│   └── boot/                         # BOOT subsystem
│       ├── B0_BOOT_TOP.vhd           # BOOT dispatcher (Layer 1)
│       ├── B1_BOOT_BIOS.vhd          # BIOS module
│       ├── L2_BUFF_LOADER.vhd        # Buffer loader
│       ├── loader_crc16.vhd          # CRC-16 validation
│       └── BootWrapper_test_stub.vhd # Test entity
├── Makefile                          # Build automation
├── BUILD.md                          # This file
└── synth/                            # Generated by `make synth-prep` (gitignored)
```

---

## Troubleshooting

### GHDL Version Too Old

**Error:**
```
ghdl: unknown command 'gen-depends'
```

**Solution:** Upgrade to GHDL 0.37 or newer:
```bash
brew upgrade ghdl    # macOS
# or
sudo apt-get update && sudo apt-get install --only-upgrade ghdl
```

### Compilation Errors

**Error:**
```
rtl/DPD_shim.vhd:55:10:error: unit "forge_common_pkg" not found
```

**Cause:** GHDL couldn't find a dependency.

**Solution:**
1. Ensure all files are listed in `RTL_SOURCES` in Makefile
2. Check for typos in library/package names
3. Run `make clean && make compile` to rebuild from scratch

### Empty Design Unit Error

**Error:**
```
rtl/boot/P3_PROG_START.vhd:18:1:error: design file is empty
```

**Cause:** Empty placeholder file included in compilation.

**Solution:** These files are already excluded in the Makefile. If you see this error, remove the file from `RTL_SOURCES`.

### Synthesis Upload Issues

**Issue:** MCC rejects upload due to subdirectories

**Solution:** Always use `make synth-prep` to create a flat directory structure. Do **not** upload files directly from `rtl/` and `rtl/boot/` - they must be flattened first.

---

## Development Tips

### Adding New VHDL Files

1. Create your file in `rtl/` or `rtl/boot/`
2. Add to `RTL_SOURCES` in Makefile (for compilation)
3. Add to `SYNTH_SOURCES` in Makefile (for synthesis packaging)
4. Run `make compile` - GHDL handles dependency order automatically

### CocoTB Simulation Testing

The build system is compatible with existing CocoTB tests:

```bash
cd tests/sim/boot_fsm
python run.py           # Test BOOT subsystem

cd tests/sim/dpd
python run.py           # Test DPD application
```

Tests use `BootWrapper` and `CustomWrapper` entities respectively.

### Hardware Debugging

After loading bitstream onto Moku:Go, use HVS encoding to observe FSM state via OutputC:

- **BOOT_P0**: 0.000V (initial state)
- **BOOT_P1**: 0.030V (dispatcher ready)
- **DPD_IDLE**: 0.5V (PROG mode active)
- **DPD_ARMED**: 1.0V
- **DPD_FIRING**: 1.5V
- **DPD_COOLDOWN**: 2.0V

**Key transition:** BOOT_P1 → DPD_IDLE shows as **0.03V → 0.5V** on oscilloscope, confirming successful RUNP handoff.

---

## References

- **BOOT-FSM Specification:** `docs/BOOT-FSM-spec.md`
- **DPD API Reference:** `docs/api-v4.md`
- **Integration Architecture:** `handoffs/20251129/INTEGRATION-Architecture-Design.md`
- **Main Documentation:** `CLAUDE.md`

---

## Getting Help

```bash
make help    # Show all Makefile targets
```

For issues with:
- **Build system**: Check this file (BUILD.md)
- **VHDL architecture**: See `CLAUDE.md` and `docs/`
- **CocoTB tests**: See `tests/README.md`
- **MCC synthesis**: Contact Liquid Instruments support

---

**Last Updated:** 2025-11-29
**Build System Version:** 5.0 (unified BOOT+DPD with auto-dependency resolution)
