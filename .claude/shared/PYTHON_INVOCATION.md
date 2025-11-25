# Python Invocation Standards for BPD-Dev-v5

**Version:** 1.0
**Last Updated:** 2025-11-11
**Audience:** AI agents and developers
**Purpose:** Unified Python/uv invocation patterns for monorepo

---

## Executive Summary

This document defines **authoritative Python invocation patterns** for BPD-Dev-v5 monorepo. All agents MUST follow these patterns when running tests, executing scripts, or importing forge_cocotb.

**Key Principle:** Use `uv` for dependency management, execute tests from their natural location, avoid manual `sys.path` manipulation.

---

## Critical Rules

1. **NEVER assume relative paths** - Always use absolute paths or project-aware detection
2. **ALWAYS use `uv run`** for Python scripts that need dependencies
3. **NEVER manually insert `sys.path`** for forge_cocotb - it's a uv-managed package
4. **ALWAYS execute tests from their containing directory** - Don't assume centralized test runners
5. **PREFER standalone run.py scripts** - Each test suite has its own runner

---

## BPD-Dev-v5 Project Structure

```
BPD-Dev-v5/                              # Project root
├── pyproject.toml                       # uv workspace root
├── libs/
│   └── forge-vhdl/
│       ├── python/
│       │   └── forge_cocotb/            # Python package (uv managed)
│       │       ├── __init__.py
│       │       ├── test_base.py
│       │       ├── conftest.py
│       │       └── ghdl_filter.py
│       └── pyproject.toml               # forge-vhdl package config
└── examples/
    └── basic-probe-driver/
        └── platform_tests/
            └── wrapper/
                ├── run.py               # Self-contained test runner
                └── test_*.py            # Test modules
```

**Key Locations:**
- **forge_cocotb**: `libs/forge-vhdl/python/forge_cocotb/`
- **Test runners**: `examples/*/platform_tests/*/run.py` (standalone scripts)
- **Project root**: `/Users/johnycsh/Forge/BPD-Dev-v5`

---

## Pattern 1: Running Tests (Recommended)

### For CocoTB Tests with Standalone run.py

**Context:** Most BPD-Dev-v5 tests use self-contained `run.py` scripts.

```bash
# Navigate to test directory first
cd examples/basic-probe-driver/platform_tests/wrapper

# Run with Python (dependencies via uv)
uv run python run.py

# With test level control
TEST_LEVEL=P2 uv run python run.py

# With GHDL filter control
GHDL_FILTER_LEVEL=none uv run python run.py

# Verbose mode
uv run python run.py --verbose
```

**Why this works:**
- `run.py` scripts handle their own imports and path resolution
- `uv run` ensures forge_cocotb dependencies are available
- Working directory is correct for relative VHDL paths

**Agent Invocation Example:**
```python
# In Bash tool call
test_dir = "examples/basic-probe-driver/platform_tests/wrapper"
cmd = f"cd {test_dir} && uv run python run.py"
```

---

## Pattern 2: Importing forge_cocotb (Correct)

### DO NOT manually manipulate sys.path

**❌ WRONG (outdated agent pattern):**
```python
# NEVER DO THIS
sys.path.insert(0, str(Path(__file__).parent.parent / "forge-vhdl" / "tests"))
from test_base import TestBase
```

**✅ CORRECT (uv-managed package):**
```python
# forge_cocotb is installed as a package via uv
from forge_cocotb import TestBase
from forge_cocotb.conftest import setup_clock, reset_active_low
from forge_cocotb.ghdl_filter import GHDLOutputFilter
```

**Why this works:**
- `uv sync` installs forge_cocotb from `libs/forge-vhdl/python/forge_cocotb`
- Python finds it via normal package resolution
- No path hacks needed

**If import fails:**
```bash
# Solution: Ensure uv sync has been run
uv sync

# Check forge_cocotb is installed
uv pip list | grep forge-cocotb
```

---

## Pattern 3: Project Root Detection

### For scripts that need absolute paths

```python
from pathlib import Path

def find_project_root() -> Path:
    """
    Find BPD-Dev-v5 project root by searching for pyproject.toml.

    Returns:
        Path to project root

    Raises:
        RuntimeError: If project root not found
    """
    current = Path(__file__).resolve()

    # Search up directory tree for pyproject.toml
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            # Verify it's BPD-Dev-v5 root (check for libs/forge-vhdl)
            if (parent / "libs" / "forge-vhdl").exists():
                return parent

    raise RuntimeError("Could not find BPD-Dev-v5 project root")

# Usage
PROJECT_ROOT = find_project_root()
VHDL_ROOT = PROJECT_ROOT / "examples" / "basic-probe-driver" / "vhdl"
```

**Agent Usage:**
```python
# Use this pattern when absolute paths are needed
PROJECT_ROOT = find_project_root()
test_sources = PROJECT_ROOT / "examples" / "basic-probe-driver" / "vhdl" / "src"
```

---

## Pattern 4: Test Discovery and Execution

### For agents that need to find and run tests

```python
from pathlib import Path

def find_test_runners(project_root: Path) -> list[Path]:
    """
    Find all run.py test runners in the project.

    Args:
        project_root: Path to BPD-Dev-v5 root

    Returns:
        List of paths to run.py files
    """
    test_runners = []

    # Search in examples/*/platform_tests/*/run.py
    examples_dir = project_root / "examples"
    if examples_dir.exists():
        for run_py in examples_dir.rglob("run.py"):
            # Verify it's in a platform_tests directory
            if "platform_tests" in str(run_py):
                test_runners.append(run_py)

    return test_runners

# Usage
PROJECT_ROOT = find_project_root()
runners = find_test_runners(PROJECT_ROOT)

for runner in runners:
    test_dir = runner.parent
    print(f"Found test runner: {test_dir}")
    # Execute: cd {test_dir} && uv run python run.py
```

---

## Pattern 5: Environment Variables

### Control test behavior without code changes

**Available Environment Variables:**

```bash
# Test Level Control
TEST_LEVEL=P1_BASIC          # Default: P1 tests only
TEST_LEVEL=P2_INTERMEDIATE   # P2 comprehensive tests
TEST_LEVEL=P3_COMPREHENSIVE  # P3 full coverage

# GHDL Output Filtering
GHDL_FILTER_LEVEL=aggressive  # Default: filter noise (98% reduction)
GHDL_FILTER_LEVEL=moderate    # Some filtering
GHDL_FILTER_LEVEL=none        # No filtering (debugging)

# CocoTB Verbosity
COCOTB_VERBOSITY=INFO        # Default
COCOTB_VERBOSITY=DEBUG       # More output
```

**Agent Invocation:**
```bash
# Run P2 tests with no filtering (debug mode)
cd examples/basic-probe-driver/platform_tests/wrapper
TEST_LEVEL=P2_INTERMEDIATE GHDL_FILTER_LEVEL=none uv run python run.py
```

---

## Pattern 6: Bash Tool Integration (for Agents)

### Executing tests from agent code

**Template:**
```python
# In agent code (when invoking Bash tool)

test_directory = "examples/basic-probe-driver/platform_tests/wrapper"
test_level = "P1_BASIC"  # or "P2_INTERMEDIATE", "P3_COMPREHENSIVE"

# Basic invocation
cmd = f"cd {test_directory} && uv run python run.py"

# With test level
cmd = f"cd {test_directory} && TEST_LEVEL={test_level} uv run python run.py"

# With debug mode
cmd = f"cd {test_directory} && GHDL_FILTER_LEVEL=none uv run python run.py"

# Agent executes via Bash tool
# result = bash(cmd, description="Run P1 CocoTB tests")
```

**Verification:**
```bash
# After test execution, verify success
cd {test_directory} && echo $?  # 0 = success, non-zero = failure
```

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Assuming centralized test runner

```bash
# WRONG - assumes tests/run.py exists at project root
uv run python tests/run.py <module>
```

**Fix:** Use standalone run.py in test directories.

---

### ❌ Mistake 2: Manual sys.path for forge_cocotb

```python
# WRONG - manual path insertion
sys.path.insert(0, str(Path(__file__).parent.parent / "forge-vhdl" / "tests"))
from test_base import TestBase
```

**Fix:** Use normal import (uv manages it).

---

### ❌ Mistake 3: Relative paths without context

```python
# WRONG - relative path without knowing cwd
vhdl_sources = Path("vhdl/src/BPD_forge_shim.vhd")
```

**Fix:** Use project root detection or absolute paths.

---

### ❌ Mistake 4: Running tests from wrong directory

```bash
# WRONG - run.py expects to be executed from its directory
cd /Users/johnycsh/Forge/BPD-Dev-v5
uv run python examples/basic-probe-driver/platform_tests/wrapper/run.py
# ^ This will fail! VHDL paths are relative to run.py location
```

**Fix:** `cd` to test directory first.

---

## Project-Specific Notes

### BPD-Dev-v5 Test Layout

**Current structure:**
```
examples/basic-probe-driver/platform_tests/
├── wrapper/
│   ├── run.py                    # Self-contained runner
│   ├── test_progressive.py       # Progressive orchestrator
│   └── test_wrapper_tests/
│       ├── P1_wrapper_basic.py
│       ├── wrapper_constants.py
│       └── __init__.py
└── simulation/
    └── (future CocoTB tests)
```

**Test execution:**
```bash
# From project root
cd examples/basic-probe-driver/platform_tests/wrapper
uv run python run.py  # Runs P1 by default
```

---

## Reference: Current Working run.py Pattern

**From:** `examples/basic-probe-driver/platform_tests/wrapper/run.py`

```python
#!/usr/bin/env python3
"""CocoTB Test Runner for BPD Platform Wrapper Tests"""

import sys
from pathlib import Path

# forge_cocotb is imported normally (uv-managed)
try:
    from cocotb_tools.runner import get_runner
except ImportError:
    print("❌ CocoTB not found! Install with: uv sync")
    sys.exit(1)

# VHDL paths relative to THIS file's location
VHDL_ROOT = Path(__file__).parent.parent.parent / "vhdl"

# Test configuration
test_module = "test_progressive"  # Progressive orchestrator
hdl_toplevel = "customwrapper_bpd_forge"

# Run tests
runner = get_runner("ghdl")
runner.build(
    vhdl_sources=vhdl_sources,
    hdl_toplevel=hdl_toplevel,
    # ...
)
runner.test(
    hdl_toplevel=hdl_toplevel,
    test_module=test_module,
)
```

**Key Insights:**
- ✅ No sys.path manipulation
- ✅ Paths relative to run.py location
- ✅ Imports work via uv package management
- ✅ Self-contained (no external runner needed)

---

## Agent Checklist

Before writing code that invokes Python:

- [ ] Use `uv run python` for all Python scripts
- [ ] Execute tests from their directory (`cd <test_dir> && uv run python run.py`)
- [ ] Use environment variables for test control (TEST_LEVEL, GHDL_FILTER_LEVEL)
- [ ] Import forge_cocotb normally (no sys.path hacks)
- [ ] Use project root detection for absolute paths (when needed)
- [ ] Verify test directory structure before execution

---

## Quick Reference Commands

```bash
# Run P1 tests (default)
cd examples/basic-probe-driver/platform_tests/wrapper && uv run python run.py

# Run P2 tests
cd examples/basic-probe-driver/platform_tests/wrapper && TEST_LEVEL=P2_INTERMEDIATE uv run python run.py

# Debug mode (no GHDL filtering)
cd examples/basic-probe-driver/platform_tests/wrapper && GHDL_FILTER_LEVEL=none uv run python run.py

# Check forge_cocotb installation
uv pip list | grep forge

# Sync dependencies
uv sync
```

---

## Canonical Test Infrastructure Locations

**IMPORTANT:** After duplicate cleanup (2025-11-11), only use these canonical locations:

### forge_cocotb Package (Import from here)

**Location:** `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/`

```python
from forge_cocotb.conftest import setup_clock, reset_active_low, mcc_set_regs
from forge_cocotb.ghdl_filter import GHDLOutputFilter, FilterLevel
from forge_cocotb.test_base import TestBase
```

**Files:**
- ✅ `conftest.py` - Test utilities (setup_clock, reset helpers, MCC helpers)
- ✅ `ghdl_filter.py` - GHDL output filter module
- ✅ `test_base.py` - TestBase class with verbosity control

**DO NOT use these (deleted/superseded):**
- ❌ `libs/forge-vhdl/tests/conftest.py` (deleted - use package version)
- ❌ `__incomfing_more_tets/` (deleted - staging directory)

### Test Runners (Execute from their directory)

**1. forge-vhdl Library Tests:**
```bash
cd libs/forge-vhdl/tests
python run.py <test_name>
python run.py --all
```

**Purpose:** Testing forge-vhdl library components (clk_divider, packages, etc.)

**2. BPD Component Tests:**
```bash
cd examples/basic-probe-driver/vhdl/component_tests
python run.py <test_name>
```

**Purpose:** Testing BPD-specific VHDL components (FSM observer, etc.)

**3. BPD Platform Tests:**
```bash
cd examples/basic-probe-driver/platform_tests/wrapper
uv run python run.py
```

**Purpose:** Testing BPD platform integration (MCC CustomInstrument interface)

**Note:** Each run.py serves a distinct purpose - they are NOT duplicates!

---

## GHDL Output Filtering

**Status:** Integrated into platform test runner (2025-11-11)

**Usage:**
```bash
cd examples/basic-probe-driver/platform_tests/wrapper

# Default (aggressive filtering)
uv run python run.py

# No filtering (debug mode)
GHDL_FILTER_LEVEL=none uv run python run.py
```

**Note:** GHDL warnings at end of output still appear (simulator-level, after Python exits). For complete filtering, pipe through grep:

```bash
uv run python run.py 2>&1 | grep -v "metavalue detected"
```

---

## Version History

**1.1 (2025-11-11):**
- Added canonical test infrastructure section
- Documented duplicate file cleanup
- Added GHDL filter integration notes
- Clarified 3 distinct run.py purposes

**1.0 (2025-11-11):**
- Initial documentation
- Defined patterns 1-6
- Added agent checklist
- Documented BPD-Dev-v5 structure

---

**Maintained By:** BPD-Dev-v5 Development Team
**Reference:** This document is authoritative for all Python invocation in BPD-Dev-v5
