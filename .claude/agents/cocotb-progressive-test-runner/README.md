# CocoTB Progressive Test Runner

Quick reference for the test execution agent.

## Purpose

Implement and execute CocoTB tests for forge-vhdl components (utilities, packages, debugging modules).

## What This Agent Does

✅ **Implements** Python test code from design specs
✅ **Executes** tests via CocoTB + GHDL
✅ **Debugs** test failures (signal access, timing, GHDL errors)
✅ **Iterates** on implementation until tests pass
✅ **Validates** output quality (<20 lines P1)

## What This Agent Does NOT Do

❌ **Design test architecture** - Receive from cocotb-progressive-test-designer
❌ **Write production VHDL** - Only test wrappers
❌ **Integration testing** - Delegate to cocotb-integration-test
❌ **Redesign test strategy** - Follow designer's plan

## Usage

```bash
# Receive test design from designer agent
# Implement: Constants, P1 tests, orchestrator, test_configs.py entry
# Execute from repo root: uv run python cocotb_tests/run.py <component>
# Debug: Fix failures, iterate until all green
# Commit: After each fix/milestone (incremental commits)
```

## Critical Constraints

**Python Environment:**
- Use `uv` for Python package management
- Virtual environment managed in `.venv/`
- All dependencies specified in `pyproject.toml`

**CRITICAL - First-Time Setup:**
```bash
# ALWAYS use the setup script for initial setup
./scripts/setup.sh

# DO NOT run 'uv sync' alone - it won't install workspace members!
```

**Why?** The workspace contains 3 Python packages (forge_cocotb, forge_platform, forge_tools)
that must be installed in editable mode. The setup script does this automatically.
Running `uv sync` alone will install dependencies but NOT the workspace packages,
causing `ModuleNotFoundError: No module named 'forge_cocotb'`.

**Git Strategy:**
- Commit after each test implementation, bug fix, or milestone
- Use descriptive commit messages
- Follow conventional commits format

**Execution Pattern:**
```bash
# From repo root
uv run python cocotb_tests/run.py <component>
```

## Key Responsibilities

1. **Constants file** - Implement from design spec
2. **P1 test module** - Implement test methods
3. **Progressive orchestrator** - Standard pattern
4. **test_configs.py entry** - Add component
5. **Test execution** - Run and debug
6. **Output validation** - Ensure <20 lines

## Common Debugging

**Signed integer access:**
```python
# ✅ CORRECT
output = int(dut.voltage_out.value.signed_integer)
```

**Integer division:**
```python
# ✅ CORRECT (match VHDL truncation)
offset = (value * 100) // 128
```

**Reset polarity:**
```python
# Check VHDL: reset='1' or rst_n='0'?
await reset_active_high(dut)  # or reset_active_low(dut)
```

## Exit Criteria

- [ ] All P1 tests pass (green)
- [ ] Output <20 lines
- [ ] Runtime <5 seconds
- [ ] No GHDL errors/warnings

## See Also

- `agent.md` - Full agent specification
- `CLAUDE.md` - Testing standards
- `docs/COCOTB_TROUBLESHOOTING.md` - Debugging guide
