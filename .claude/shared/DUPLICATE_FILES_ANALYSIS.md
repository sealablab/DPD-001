# Duplicate Files Analysis and Cleanup Plan

**Date:** 2025-11-11
**Purpose:** Identify duplicate test infrastructure files and establish canonical paths
**Status:** Analysis complete, cleanup pending

---

## Executive Summary

**Problem:** Multiple duplicate files across the repository create confusion about which version to use:
- 3 copies of `conftest.py` (all identical)
- 3 copies of `run.py` (different purposes, causing confusion)
- 3 copies of `ghdl_filter.py` (all identical)

**Impact:**
- Agents don't know which file to reference
- Updates must be made in multiple places
- Conflicting invocation patterns

**Solution:** Establish canonical locations and remove/symlink duplicates

---

## File Analysis

### 1. conftest.py (3 copies - ALL IDENTICAL)

| Location | Lines | MD5 Hash | Status |
|----------|-------|----------|--------|
| `__incomfing_more_tets/more_Tests/forge_cocotb/forge_cocotb/conftest.py` | 743 | `a7cee6be6bd4938e1c61e13fb35c8480` | ❌ DUPLICATE (incoming) |
| `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/conftest.py` | 743 | `a7cee6be6bd4938e1c61e13fb35c8480` | ✅ CANONICAL |
| `libs/forge-vhdl/tests/conftest.py` | 743 | `a7cee6be6bd4938e1c61e13fb35c8480` | ❌ DUPLICATE (old) |

**Canonical Location:** `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/conftest.py`

**Reason:** This is the package location (uv-managed module)

**Cleanup Action:**
- ✅ **KEEP:** `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/conftest.py`
- ❌ **DELETE:** `__incomfing_more_tets/` entire directory (staging area, not canonical)
- ❌ **DELETE:** `libs/forge-vhdl/tests/conftest.py` (old location, superseded by package)

---

### 2. ghdl_filter.py (3 copies - ALL IDENTICAL)

| Location | Lines | MD5 Hash | Status |
|----------|-------|----------|--------|
| `__incomfing_more_tets/more_Tests/forge_cocotb/forge_cocotb/ghdl_filter.py` | 339 | `5c05dd3e89c5cab278fdd251ca293733` | ❌ DUPLICATE (incoming) |
| `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/ghdl_filter.py` | 339 | `5c05dd3e89c5cab278fdd251ca293733` | ✅ CANONICAL (module) |
| `libs/forge-vhdl/scripts/ghdl_output_filter.py` | 339 | `5c05dd3e89c5cab278fdd251ca293733` | ⚠️ KEEP (CLI script) |

**Canonical Locations:**
- **Module import:** `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/ghdl_filter.py`
- **Standalone script:** `libs/forge-vhdl/scripts/ghdl_output_filter.py`

**Reason:** Two different use cases:
1. **Module** - For importing: `from forge_cocotb.ghdl_filter import GHDLOutputFilter`
2. **Script** - For CLI piping: `python run.py | python scripts/ghdl_output_filter.py`

**Cleanup Action:**
- ✅ **KEEP:** `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/ghdl_filter.py` (module)
- ✅ **KEEP:** `libs/forge-vhdl/scripts/ghdl_output_filter.py` (CLI script)
- ❌ **DELETE:** `__incomfing_more_tets/` entire directory

**NOTE:** Module and script should stay in sync (same logic, different entry points)

---

### 3. run.py (3 copies - DIFFERENT PURPOSES)

| Location | Lines | Purpose | Status |
|----------|-------|---------|--------|
| `libs/forge-vhdl/tests/run.py` | 418 | **Generic test runner** for forge-vhdl library tests | ✅ CANONICAL (forge-vhdl) |
| `examples/basic-probe-driver/vhdl/component_tests/run.py` | 483 | **Component test runner** for BPD VHDL components | ✅ CANONICAL (BPD components) |
| `examples/basic-probe-driver/platform_tests/wrapper/run.py` | 92 | **Platform test runner** for BPD wrapper tests | ✅ CANONICAL (BPD platform) |

**Analysis:** These are NOT duplicates - they serve different purposes!

#### run.py #1: libs/forge-vhdl/tests/run.py (418 lines)

**Purpose:** Generic test runner for forge-vhdl library components
**Tests:** forge-vhdl utilities (clk_divider, packages, etc.)
**Features:**
- Multi-test orchestration (`--all`, `--category`)
- Test discovery from `test_configs.py`
- GHDL output filtering integration

**Invocation:**
```bash
cd libs/forge-vhdl/tests
python run.py forge_util_clk_divider
python run.py --all
```

**Canonical Use:** Testing forge-vhdl library components

---

#### run.py #2: examples/basic-probe-driver/vhdl/component_tests/run.py (483 lines)

**Purpose:** Component test runner for BPD-specific VHDL components
**Tests:** BPD FSM observer and BPD-specific components
**Features:**
- Uses forge-vhdl test infrastructure
- Local test_configs.py
- Progressive testing (P1/P2/P3)

**Invocation:**
```bash
cd examples/basic-probe-driver/vhdl/component_tests
python run.py bpd_fsm_observer
```

**Canonical Use:** Testing BPD VHDL components (isolated from platform)

---

#### run.py #3: examples/basic-probe-driver/platform_tests/wrapper/run.py (92 lines)

**Purpose:** Platform wrapper test runner (CustomWrapper MCC interface)
**Tests:** BPD integration through MCC CustomInstrument interface
**Features:**
- Simplified (single test module)
- No GHDL filtering (YET - needs integration)
- Tests CustomWrapper architecture

**Invocation:**
```bash
cd examples/basic-probe-driver/platform_tests/wrapper
python run.py
```

**Canonical Use:** Testing BPD platform integration (MCC interface)

**⚠️ ISSUE:** This runner does NOT integrate GHDL filtering (causing metavalue spam)

---

## Canonical File Locations (Reference Table)

| File Type | Canonical Location | Purpose | Import Pattern |
|-----------|-------------------|---------|----------------|
| **conftest.py** | `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/conftest.py` | Test utilities (uv-managed package) | `from forge_cocotb.conftest import setup_clock` |
| **ghdl_filter.py** (module) | `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/ghdl_filter.py` | GHDL filter module | `from forge_cocotb.ghdl_filter import GHDLOutputFilter` |
| **ghdl_output_filter.py** (script) | `libs/forge-vhdl/scripts/ghdl_output_filter.py` | GHDL filter CLI | `python \| python scripts/ghdl_output_filter.py` |
| **run.py** (forge-vhdl) | `libs/forge-vhdl/tests/run.py` | forge-vhdl library test runner | `cd libs/forge-vhdl/tests && python run.py <test>` |
| **run.py** (BPD components) | `examples/basic-probe-driver/vhdl/component_tests/run.py` | BPD component test runner | `cd examples/.../component_tests && python run.py <test>` |
| **run.py** (BPD platform) | `examples/basic-probe-driver/platform_tests/wrapper/run.py` | BPD platform test runner | `cd examples/.../wrapper && python run.py` |

---

## Cleanup Plan

### Phase 1: Delete Duplicates

```bash
# Remove entire __incomfing_more_tets staging directory
rm -rf __incomfing_more_tets/

# Remove old conftest.py in tests/ (superseded by package)
rm libs/forge-vhdl/tests/conftest.py
```

**Impact:**
- ✅ Removes 2 duplicate conftest.py files
- ✅ Removes 1 duplicate ghdl_filter.py file
- ✅ Cleans up staging directory

---

### Phase 2: Document Canonical Paths

**Update PYTHON_INVOCATION.md:**
```markdown
## Canonical Test Infrastructure Locations

**forge_cocotb package (uv-managed):**
- `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/conftest.py`
- `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/ghdl_filter.py`
- `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/test_base.py`

**Test runners (project-specific):**
- forge-vhdl library: `libs/forge-vhdl/tests/run.py`
- BPD components: `examples/basic-probe-driver/vhdl/component_tests/run.py`
- BPD platform: `examples/basic-probe-driver/platform_tests/wrapper/run.py`

**Import pattern:**
```python
from forge_cocotb.conftest import setup_clock, reset_active_low
from forge_cocotb.ghdl_filter import GHDLOutputFilter
from forge_cocotb.test_base import TestBase
```

**DO NOT use sys.path manipulation!**
```

---

### Phase 3: Fix BPD Platform Tests (Integrate GHDL Filter)

**Problem:** `examples/basic-probe-driver/platform_tests/wrapper/run.py` doesn't use GHDL filter

**Current Output:** ~60 lines (metavalue warnings)
**Target Output:** <20 lines (P1 standard)

**Solution:** Integrate GHDL filter into platform test runner

**Implementation Options:**

**Option A: Pipe through CLI script (simple)**
```bash
cd examples/basic-probe-driver/platform_tests/wrapper
python run.py 2>&1 | python ../../../../libs/forge-vhdl/scripts/ghdl_output_filter.py
```

**Option B: Import module in run.py (better)**
```python
# In run.py:
from forge_cocotb.ghdl_filter import GHDLOutputFilter, FilterLevel
import sys

# After runner.test():
filter_level = os.environ.get('GHDL_FILTER_LEVEL', 'aggressive')
filter = GHDLOutputFilter(FilterLevel(filter_level))
# Apply filter to output
```

**Recommendation:** Option B (integrate into run.py)

---

## Agent Update Requirements

### Update .claude/shared/PYTHON_INVOCATION.md

Add section:

```markdown
## Canonical Test Infrastructure

**IMPORTANT:** Only use these canonical locations:

**forge_cocotb Package (Import from here):**
- `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/conftest.py`
- `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/ghdl_filter.py`
- `libs/forge-vhdl/python/forge_cocotb/forge_cocotb/test_base.py`

**Test Runners (Execute from their directory):**
1. **forge-vhdl library tests:**
   ```bash
   cd libs/forge-vhdl/tests
   python run.py <test_name>
   ```

2. **BPD component tests:**
   ```bash
   cd examples/basic-probe-driver/vhdl/component_tests
   python run.py <test_name>
   ```

3. **BPD platform tests:**
   ```bash
   cd examples/basic-probe-driver/platform_tests/wrapper
   python run.py
   ```

**DO NOT:**
- ❌ Use `libs/forge-vhdl/tests/conftest.py` (deleted)
- ❌ Use `__incomfing_more_tets/` (staging, not canonical)
- ❌ Add `sys.path` manipulation (use uv imports)
```

---

## Validation Checklist

After cleanup:

- [ ] Only 1 conftest.py exists (in forge_cocotb package)
- [ ] Only 2 ghdl_filter files exist (module + CLI script)
- [ ] All 3 run.py files serve distinct purposes
- [ ] __incomfing_more_tets/ directory removed
- [ ] PYTHON_INVOCATION.md updated with canonical paths
- [ ] BPD platform tests integrate GHDL filter
- [ ] All tests still pass after cleanup

---

## Summary

**Root Cause:** Migration from old structure to forge_cocotb package left behind duplicates

**Current State:**
- ✅ forge_cocotb is properly packaged (uv-managed)
- ⚠️ Old files still present (causing confusion)
- ⚠️ GHDL filter not integrated in platform tests

**Action Items:**
1. Delete duplicates (conftest.py, __incomfing_more_tets/)
2. Integrate GHDL filter into platform test runner
3. Update PYTHON_INVOCATION.md with canonical paths
4. Verify all tests pass

**Expected Benefit:**
- Clear canonical file locations
- No confusion about which file to use
- Reduced output (60 lines → <20 lines for P1 tests)
- Agents reference correct paths

---

**Last Updated:** 2025-11-11
**Maintained By:** BPD-Dev-v5 Development Team
