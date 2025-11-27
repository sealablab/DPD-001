# Shared Test Infrastructure - DEPRECATED

> **DEPRECATED:** This directory is now a backward compatibility shim.
> New code should import from `tests/lib` and `tests/adapters` instead.

## Migration

**Old imports (deprecated):**
```python
from shared.constants import P1Timing, SIM_HVS_TOLERANCE
from shared.async_adapter import CocoTBAsyncHarness
```

**New imports (recommended):**
```python
from lib import P1Timing, SIM_HVS_TOLERANCE
from adapters import CocoTBAsyncHarness
```

## New Structure

```
tests/
├── lib/                    # Test library (constants, utilities)
│   ├── hw.py               # Hardware constants (from py_tools)
│   ├── clk.py              # Clock utilities (from py_tools)
│   ├── dpd_config.py       # DPDConfig dataclass
│   ├── timing.py           # P1Timing, P2Timing
│   ├── tolerances.py       # Tolerances
│   └── timeouts.py         # Timeouts
├── adapters/               # Platform adapters
│   ├── base.py             # Abstract base classes
│   ├── cocotb.py           # CocoTBAsyncHarness
│   └── moku.py             # MokuAsyncHarness
└── shared/                 # DEPRECATED - shims only
    ├── constants.py        # Re-exports from lib
    └── async_adapter.py    # Re-exports from adapters
```

## Files in This Directory

All files in this directory are backward compatibility shims that re-export from the new locations:

- **`constants.py`** - Re-exports from `tests/lib`
- **`async_adapter.py`** - Re-exports from `tests/adapters`

## Removal Timeline

These shims will be removed once all imports have been updated to use the new paths.
