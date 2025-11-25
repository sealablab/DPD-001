# CocoTB Progressive Test Designer

Quick reference for the test design agent.

## Purpose

Design progressive test architectures for forge-vhdl components (utilities, packages, debugging modules).

## What This Agent Does

✅ **Analyzes** VHDL components for testability
✅ **Designs** P1/P2/P3 test strategies
✅ **Plans** test wrappers for CocoTB compatibility
✅ **Calculates** expected values matching VHDL arithmetic
✅ **Defines** test infrastructure (constants, helpers, orchestrators)

## What This Agent Does NOT Do

❌ **Run tests** - Delegate to cocotb-progressive-test-runner
❌ **Debug GHDL** - Delegate to runner
❌ **Integration testing** - Delegate to cocotb-integration-test
❌ **Write production VHDL** - Only test wrappers

## Usage

```bash
# Load agent via Claude Code
# Provide: VHDL component to test
# Get: Test architecture document + design artifacts
```

## Key Principles

1. **P1 must be <20 lines** - 2-4 essential tests only
2. **Match VHDL arithmetic** - Python expected values use integer division
3. **CocoTB type constraints** - Only std_logic, signed, unsigned at entity ports
4. **Progressive sizing** - P1 small/fast, P2 realistic, P3 comprehensive

## Handoff

When design complete, hand off to **cocotb-progressive-test-runner** with:
- Test architecture document
- Constants file design
- Test module pseudocode
- Test wrapper VHDL (if needed)

## See Also

- `agent.md` - Full agent specification
- `CLAUDE.md` - Testing standards
- `docs/COCOTB_TROUBLESHOOTING.md` - Type constraints

