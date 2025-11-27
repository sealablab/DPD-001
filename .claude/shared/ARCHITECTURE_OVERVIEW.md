# Architecture Overview v2.0

**Version:** 2.0.0
**Purpose:** Clean, flat architecture for Moku custom instrument development
**Audience:** Humans and AI agents navigating this system
**Updated:** 2025-11-04

---

## The Elegant Architecture

This monorepo demonstrates a **clean separation architecture** with **flat foundational libraries** and **self-contained tools**, supported by a **3-tier documentation system** optimized for token-efficient AI context loading.

**Key Innovation:** Eliminated nested submodules in favor of clear separation between tools and libraries.

---

## 1. Repository Structure (Flat Hierarchy)

```
moku-instrument-forge-mono-repo/                 # Monorepo orchestrator
│
├── tools/                                        # Development tools
│   └── forge-codegen/                            # Submodule: YAML → VHDL generator
│       ├── llms.txt                              # Tier 1: Quick ref
│       ├── CLAUDE.md                             # Tier 2: Complete guide
│       ├── forge_codegen/
│       │   ├── basic_serialized_datatypes/       # INTERNAL: Type system
│       │   │   ├── types.py                      # 23 types (voltage/time/bool)
│       │   │   ├── mapper.py                     # RegisterMapper algorithm
│       │   │   └── converters.py                 # Python ↔ VHDL conversions
│       │   ├── generator/                        # YAML → VHDL generation
│       │   ├── models/                           # Pydantic data models
│       │   ├── templates/                        # Jinja2 VHDL templates
│       │   └── vhdl/                             # Frozen type packages (v1.0)
│       ├── tests/                                # 69 tests
│       └── docs/                                 # Specialized guides
│
├── libs/                                         # Foundational libraries (FLAT)
│   ├── forge-vhdl/                               # Submodule: VHDL utilities
│   │   ├── llms.txt                              # Tier 1: Component catalog
│   │   ├── CLAUDE.md                             # Tier 2: Design patterns
│   │   └── vhdl/
│   │       ├── packages/                         # Common types, voltage utilities
│   │       ├── debugging/                        # FSM observer
│   │       └── utilities/                        # Clock dividers, counters
│   │
│   ├── moku-models/                              # Submodule: Platform specs
│   │   ├── llms.txt                              # Tier 1: Platform catalog
│   │   ├── CLAUDE.md                             # Tier 2: Integration patterns
│   │   └── moku_models/
│   │       ├── platforms/                        # Go/Lab/Pro/Delta specs
│   │       ├── routing.py                        # MokuConnection models
│   │       └── moku_config.py                    # MokuConfig (deployment)
│   │
│   └── riscure-models/                           # Submodule: Probe specs
│       ├── llms.txt                              # Tier 1: Probe catalog
│       ├── CLAUDE.md                             # Tier 2: Safety patterns
│       └── riscure_models/
│           ├── probes.py                         # DS1120A/DS1140A specs
│           └── validation.py                     # Voltage safety
│
├── forge/                                        # LEGACY: Deprecated (kept for reference)
│   └── [nested submodule structure]             # Old architecture
│
└── .claude/                                      # AI agent coordination
    ├── agents/                                   # Monorepo-level agents
    ├── commands/                                 # Slash commands
    ├── workflows/                                # Reusable workflows
    └── shared/                                   # Shared knowledge
        └── ARCHITECTURE_OVERVIEW.md              # This file
```

---

## 2. The Core Principles

### Principle 1: Clean Separation

**Tools vs Libraries:**
- **tools/** - Code generation, build tools
- **libs/** - Reusable foundational libraries
- **forge/** - Legacy (deprecated)

**Benefits:**
- Clear responsibility boundaries
- No nested submodule complexity
- Independent versioning
- Simplified git workflow

### Principle 2: Self-Contained Authoritative Modules

Each library is a **self-contained truth bubble**:

#### forge-codegen (Code Generation Authority)

**Location:** `tools/forge-codegen/`
**Repository:** https://github.com/sealablab/moku-instrument-forge-codegen

```
forge_codegen/
├── basic_serialized_datatypes/    # INTERNAL (not separate repo)
│   ├── types.py                   # BasicAppDataTypes enum (23 types)
│   ├── mapper.py                  # RegisterMapper (packing algorithm)
│   └── converters.py              # Python ↔ VHDL conversions
├── generator/
│   ├── codegen.py                 # YAML → VHDL generation
│   └── type_utilities.py          # VHDL package generator
└── templates/
    ├── shim.vhd.j2                # Register interface
    └── main.vhd.j2                # Application template
```

**Authority:** Type system, register packing, VHDL generation
**Key Design:** basic_serialized_datatypes is **internal** (flattened from separate repo)
**Why Internal:** Tight coupling, no external users, version-locked with generator

#### forge-vhdl (VHDL Component Authority)

**Location:** `libs/forge-vhdl/`
**Repository:** https://github.com/sealablab/moku-instrument-forge-vhdl

```
forge-vhdl/
├── vhdl/
│   ├── packages/        # Common types, voltage utilities
│   ├── debugging/       # FSM observer
│   └── utilities/       # Clock dividers, counters
└── docs/                # Component documentation
```

**Authority:** Reusable VHDL components, voltage type system
**Zero dependencies:** Pure VHDL, works standalone
**Used by:** Generated VHDL code references these packages

#### moku-models (Platform Specification Authority)

**Location:** `libs/moku-models/`
**Repository:** https://github.com/sealablab/moku-models

```
moku_models/
├── platforms/
│   ├── moku_go.py       # MOKU_GO_PLATFORM (125 MHz, ±25V ADC)
│   ├── moku_lab.py      # MOKU_LAB_PLATFORM (500 MHz, ±5V ADC)
│   ├── moku_pro.py      # MOKU_PRO_PLATFORM (1.25 GHz, ±20V ADC)
│   └── moku_delta.py    # MOKU_DELTA_PLATFORM (5 GHz, ±20V ADC)
├── routing.py           # MokuConnection models
└── moku_config.py       # MokuConfig (deployment)
```

**Authority:** Clock frequencies, voltage ranges, I/O configurations, routing
**Zero deployment logic:** Pure Pydantic models, no Moku API calls
**Composable:** Works with other libraries for validation

#### riscure-models (Probe Hardware Authority)

**Location:** `libs/riscure-models/`
**Repository:** https://github.com/sealablab/riscure-models

```
riscure_models/
├── probes.py
│   ├── DS1120A_PLATFORM     # Nano FI-2104
│   └── DS1140A_PLATFORM     # VC Glitcher
└── validation.py
    └── is_voltage_compatible()    # Safety validation
```

**Authority:** Probe electrical specs, voltage safety, port definitions
**Composable:** Works with moku-models for wiring validation
**Safety-first:** Prevents hardware damage through voltage validation

### Principle 3: Three-Tier Documentation System

Every component follows progressive disclosure:

**Tier 1: llms.txt** (~500-1000 tokens)
- Quick facts and exports
- Basic usage examples
- Pointers to Tier 2

**Tier 2: CLAUDE.md** (~3-5k tokens)
- Complete design rationale
- Integration patterns
- Development workflows
- Authoritative reference

**Tier 3: Source Code** (~5-10k tokens per file)
- Implementation details
- Pydantic models
- Tests

**AI Agent Strategy:**
```
Quick question?     → Load llms.txt (500 tokens, 0.25% budget)
Design question?    → Load CLAUDE.md (3k tokens, 1.5% budget)
Implementation?     → Load source code (10k tokens, 5% budget)
Still have 95% of context budget remaining!
```

### Principle 4: Composability Without Coupling

Libraries are **independent but composable**:

```python
# Each library is self-contained
from forge_codegen.basic_serialized_datatypes import BasicAppDataTypes
from moku_models import MOKU_GO_PLATFORM
from riscure_models import DS1120A_PLATFORM

# Compose at integration layer for validation
voltage_type = BasicAppDataTypes.VOLTAGE_OUTPUT_05V_S16  # ±5V
moku_output = MOKU_GO_PLATFORM.get_analog_output_by_id('OUT1')  # 10Vpp
probe_input = DS1120A_PLATFORM.get_port_by_id('digital_glitch')  # 0-3.3V TTL

# Each is authoritative for its domain
# Composition validates integration
```

**Key Insight:** Libraries don't import each other. Integration patterns documented in each CLAUDE.md.

### Principle 5: Never Guess, Always Trust

Foundational libraries are **authoritative sources of truth**:

```python
# ❌ BAD: AI Agent guesses
"I think Moku:Go runs at 100MHz..."
"Maybe there's a voltage_10v_s16 type?"
"The probe probably accepts 5V..."

# ✅ GOOD: AI Agent reads authority
AI loads: libs/moku-models/llms.txt
→ "Moku:Go = 125 MHz (authoritative)"

AI loads: tools/forge-codegen/llms.txt
→ "23 types exist. voltage_10v_s16 is NOT one of them."

AI loads: libs/riscure-models/llms.txt
→ "DS1120A digital_glitch = 0-3.3V TTL only"
```

### Principle 6: Token-Efficient Context Loading

**Progressive disclosure minimizes token usage:**

```
Quick lookup (3× llms.txt):
  ~1.5k tokens (0.75% of budget)

Design work (llms.txt + 1× CLAUDE.md):
  ~4.5k tokens (2.25% of budget)

Deep implementation (llms.txt + CLAUDE.md + source):
  ~12k tokens (6% of budget)

Still have 188k tokens available (94%)!
```

---

## 3. Cross-Library Integration Patterns

### Pattern 1: Type ← Platform Validation

**Use case:** Validate that a type is compatible with platform output

```python
from forge_codegen.basic_serialized_datatypes import BasicAppDataTypes, TYPE_REGISTRY
from moku_models import MOKU_GO_PLATFORM

# Get type metadata
voltage_type = BasicAppDataTypes.VOLTAGE_OUTPUT_05V_S16
metadata = TYPE_REGISTRY[voltage_type]
# → voltage_range: "±5V"

# Get platform DAC specs
platform = MOKU_GO_PLATFORM
dac_output = platform.get_analog_output_by_id('OUT1')
# → voltage_range_vpp: 10.0 (±5V)

# Validation
assert metadata.voltage_range == "±5V"
assert dac_output.voltage_range_vpp == 10.0
print("✓ Type compatible with platform")
```

**Libraries involved:** forge-codegen (type authority), moku-models (platform authority)

### Pattern 2: Platform ← Probe Wiring Safety

**Use case:** Validate safe connection between Moku output and probe input

```python
from moku_models import MOKU_GO_PLATFORM
from riscure_models import DS1120A_PLATFORM

# Moku output spec
moku_out = MOKU_GO_PLATFORM.get_analog_output_by_id('OUT1')
# → voltage_range_vpp = 10.0 (can output 0-3.3V TTL mode)

# Probe input spec
probe_in = DS1120A_PLATFORM.get_port_by_id('digital_glitch')
# → voltage_min=0V, voltage_max=3.3V

# Safety check
voltage = 3.3  # TTL mode
if probe_in.is_voltage_compatible(voltage):
    print("✓ Safe connection (use TTL mode, not raw DAC)")
else:
    print("✗ UNSAFE - voltage exceeds probe limits")
```

**Libraries involved:** moku-models (Moku output authority), riscure-models (probe safety authority)

### Pattern 3: Type ← Probe Compatibility

**Use case:** Validate type usage for probe control

```python
from forge_codegen.basic_serialized_datatypes import BasicAppDataTypes
from riscure_models import DS1120A_PLATFORM

# User specifies control type
trigger_type = BasicAppDataTypes.BOOLEAN
# → 1-bit boolean

# Probe trigger spec
probe = DS1120A_PLATFORM
trigger_port = probe.get_port_by_id('digital_glitch')
# → Expects TTL signal (boolean-compatible)

print("✓ BOOLEAN type compatible with probe TTL trigger")
```

**Libraries involved:** forge-codegen (type authority), riscure-models (probe authority)

---

## 4. Information Flow: The Truth Cascade

### Example 1: Quick Type Lookup

```
User: "What voltage types exist?"
    ↓
AI Agent loads: tools/forge-codegen/llms.txt (Tier 1, ~700 tokens)
    ↓
Answer: "23 types available. 12 voltage, 10 time, 1 boolean.
         voltage_output_05v_s16 for ±5V DAC output..."
    ↓
Done. 99.65% of token budget remaining.
```

### Example 2: Wiring Safety Validation

```
User: "Is my Moku → probe wiring safe?"
    ↓
AI Agent loads: libs/moku-models/llms.txt (Tier 1, ~600 tokens)
AI Agent loads: libs/riscure-models/llms.txt (Tier 1, ~600 tokens)
    ↓
Check: Moku:Go OUT1 = 10Vpp (±5V) vs DS1120A = 0-3.3V TTL
    ↓
Potential issue detected
    ↓
AI Agent loads: libs/moku-models/CLAUDE.md (Tier 2, +3k tokens)
    ↓
Find integration pattern: "TTL mode outputs 3.3V"
    ↓
Answer: "Use TTL mode on Moku output (3.3V), not raw DAC (±5V).
         Safe connection confirmed."
    ↓
Done. Total: 4.2k tokens (2.1% of budget)
```

### Example 3: Adding New Type

```
User: "How do I add a new voltage type for ±10V?"
    ↓
AI Agent loads: tools/forge-codegen/llms.txt (Tier 1, ~700 tokens)
    ↓
Sees: "23 types defined. For adding types, see CLAUDE.md"
    ↓
AI Agent loads: tools/forge-codegen/CLAUDE.md (Tier 2, +4k tokens)
    ↓
Find section: "Adding New Types"
    ↓
Answer: "1. Add to BasicAppDataTypes enum in types.py
         2. Add metadata to TYPE_REGISTRY in metadata.py
         3. Add conversion function in converters.py
         4. Add VHDL function to frozen packages
         5. Add tests
         6. Update llms.txt catalog
         7. Submit PR to forge-codegen repo"
    ↓
Done. Total: 4.7k tokens (2.35% of budget)
```

### Example 4: Generate VHDL from YAML

```
User: "Generate VHDL for my probe spec"
    ↓
AI Agent loads: tools/forge-codegen/llms.txt (Tier 1, ~700 tokens)
    ↓
Sees usage: "python -m forge_codegen.generator.codegen spec.yaml"
    ↓
Run generation command
    ↓
Success: shim.vhd + main.vhd generated
    ↓
Done. Total: 700 tokens (0.35% of budget)
```

---

## 5. Git Workflow (Simplified)

### The Beauty of Flat Structure

**No nested submodules to manage!**

Old (complex):
```bash
# Navigate 3 levels deep
cd forge/libs/moku-models/
git checkout -b feat
# ... commit to submodule
# Navigate back 2 levels
cd ../..
git add libs/moku-models  # Update reference
# Navigate back 1 level
cd ..
git add forge  # Update parent reference
```

New (simple):
```bash
# Direct access
cd libs/moku-models/
git checkout -b feat
# ... commit to submodule
cd ../..
git add libs/moku-models  # Update reference
# Done!
```

### Modifying a Library

**Example: Update moku-models**

```bash
# 1. Work in submodule
cd libs/moku-models/
git checkout -b feat/add-delta-platform
# ... edit code ...
git commit -m "feat: Add Moku:Delta platform specs"
git push origin feat/add-delta-platform

# 2. Create PR in moku-models repo, merge it

# 3. Update monorepo reference
cd ../..
git pull  # Get latest
cd libs/moku-models/
git checkout main
git pull origin main
cd ../..
git add libs/moku-models/
git commit -m "chore: Update moku-models to include Delta platform"
git push
```

### Modifying forge-codegen

**Example: Add new type**

```bash
# 1. Work in submodule
cd tools/forge-codegen/
git checkout -b feat/add-frequency-type
# ... edit forge_codegen/basic_serialized_datatypes/ ...
git commit -m "feat: Add frequency_mhz_u16 type"
git push origin feat/add-frequency-type

# 2. Create PR, merge it

# 3. Update monorepo reference
cd ../..
git add tools/forge-codegen/
git commit -m "chore: Update forge-codegen with frequency type"
git push
```

**Key rules:**
- ✅ Always commit in submodule FIRST
- ✅ Then update submodule reference in monorepo
- ✅ Each submodule has its own repo, issues, PRs
- ✅ No nested submodule complexity!

---

## 6. Development Workflow

### Using forge-codegen

```bash
# Install
cd tools/forge-codegen/
pip install -e .

# Generate VHDL from YAML spec
python -m forge_codegen.generator.codegen spec.yaml --output-dir generated/

# Run tests
pytest tests/
```

### Working with Libraries

```python
# Import platform specs
from moku_models import MOKU_GO_PLATFORM, MokuConfig, MokuConnection

# Create deployment config
config = MokuConfig(
    platform=MOKU_GO_PLATFORM,
    slots={1: SlotConfig(instrument='CloudCompile', bitstream='app.tar')},
    routing=[MokuConnection(source='IN1', destination='Slot1InA')]
)

# Import probe specs
from riscure_models import DS1120A_PLATFORM

# Check voltage safety
probe_port = DS1120A_PLATFORM.get_port_by_id('digital_glitch')
if probe_port.is_voltage_compatible(3.3):
    print("✓ Safe to connect")
```

---

## 7. Documentation Ecosystem

### Monorepo Level

```
llms.txt                              # Entry point, navigation
README.md                             # Human-friendly overview
ARCHITECTURE_V2_COMPLETE.md          # Migration details
WORKFLOW_GUIDE.md                    # Operational workflows
```

### Coordination Layer (.claude/)

```
.claude/
├── agents/                           # Monorepo-level AI agents
│   ├── probe-design-orchestrator/
│   ├── deployment-orchestrator/
│   └── hardware-debug/
├── commands/                         # Slash commands
├── workflows/                        # Reusable workflows
└── shared/                           # Shared knowledge
    ├── ARCHITECTURE_OVERVIEW.md      # This file
    ├── CONTEXT_MANAGEMENT.md         # Token optimization
    └── PROBE_WORKFLOW.md             # Procedures
```

### Submodule Documentation

Each submodule follows 3-tier pattern:

| Submodule | Quick Ref | Full Guide |
|-----------|-----------|------------|
| forge-codegen | [llms.txt](../../tools/forge-codegen/llms.txt) | [CLAUDE.md](../../tools/forge-codegen/CLAUDE.md) |
| forge-vhdl | [llms.txt](../../libs/forge-vhdl/llms.txt) | [CLAUDE.md](../../libs/forge-vhdl/CLAUDE.md) |
| moku-models | [llms.txt](../../libs/moku-models/llms.txt) | [CLAUDE.md](../../libs/moku-models/CLAUDE.md) |
| riscure-models | [llms.txt](../../libs/riscure-models/llms.txt) | [CLAUDE.md](../../libs/riscure-models/CLAUDE.md) |

---

## 8. Architecture Evolution

### From v1.0 to v2.0

**v1.0 (LEGACY):**
- 4-level nested submodule hierarchy
- basic-app-datatypes as separate nested repo
- moku-models/riscure-models nested in forge/libs/
- Complex git workflow (3-level navigation)

**v2.0 (CURRENT):**
- Flat 2-level structure (monorepo → submodules)
- basic_serialized_datatypes flattened into forge-codegen (internal)
- All foundational libs as peers in libs/
- Simplified git workflow
- Clear separation (tools/ vs libs/)

**Migration:** 2025-11-04
**Benefits:**
- ✅ 50% simpler git operations
- ✅ Clear responsibility boundaries
- ✅ No nested submodule complexity
- ✅ Better naming (forge_codegen vs "forge")
- ✅ Easier onboarding

### What Stayed the Same

**Preserved principles:**
- 3-tier documentation system
- Progressive disclosure / token efficiency
- Authoritative source of truth pattern
- Composability without coupling
- "Never guess, always trust"

---

## 9. Design Principles Summary

### 1. Clean Separation
- Tools in tools/ (code generation)
- Libraries in libs/ (foundational)
- Legacy in forge/ (deprecated)

### 2. Flat Hierarchy
- No nested submodules
- All foundational libs are peers
- Simplified navigation

### 3. Tiered Documentation
- llms.txt (quick ref) → CLAUDE.md (deep dive) → source code
- Load minimally, expand as needed
- Token budget optimization

### 4. Self-Contained Modules
- Each submodule is standalone
- Zero cross-dependencies
- Composable at integration layer

### 5. Single Source of Truth
- Types → forge-codegen (authoritative)
- Platforms → moku-models (authoritative)
- Probes → riscure-models (authoritative)
- VHDL → forge-vhdl (authoritative)

### 6. Context Efficiency
- Start with ~1.5k tokens (Tier 1)
- Expand to ~5k tokens (Tier 2)
- Deep dive to ~15k tokens (Tier 3)
- Reserve 185k tokens (92.5% of budget)

---

## 10. The Elegant Summary

This system achieves:

✅ **Clean flat structure** (tools/ vs libs/, no nesting)
✅ **4 self-contained authoritative modules** (forge-codegen, forge-vhdl, moku-models, riscure-models)
✅ **3-tier documentation system** (llms.txt → CLAUDE.md → source)
✅ **Token-efficient AI context loading** (start ~1.5k, expand as needed)
✅ **Composability without coupling** (modules don't import each other)
✅ **Never guess, always trust** (authoritative sources of truth)
✅ **Simplified git workflow** (no nested submodules)
✅ **Clear separation of concerns** (tools, libraries, legacy)

**The magic:** Clean architecture scales elegantly. AI agents navigate with minimal tokens. Humans understand intuitively. Complexity eliminated, not hidden.

---

**Version:** 2.0.0
**Last Updated:** 2025-11-04
**Maintained By:** moku-instrument-forge team
**Migration:** See ARCHITECTURE_V2_COMPLETE.md
