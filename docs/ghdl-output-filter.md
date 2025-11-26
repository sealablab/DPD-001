# GHDL Output Filter

**Last Updated:** 2025-11-04 (migrated 2025-01-28)  
**Maintainer:** Moku Instrument Forge Team

> **Migration Note:** This document was migrated from FORGE-V5 and updated to match DPD-001 implementation.  
> **Implementation:** `tests/sim/ghdl_filter.py`  
> **Integration:** `tests/sim/run.py` (FilteredOutput class)

---

Intelligently filters GHDL simulator output to reduce verbosity by 80-98% while preserving all critical information (errors, failures, test results).

## **Key Innovations:** 
- Operates at Python stream level (wraps stdout/stderr), filtering output in real-time
- Even C code (GHDL) output is filtered when redirected through Python streams
- Preserves all errors, failures, and test results while suppressing noise

## See Also
- [Progressive Testing](progressive-testing.md) - Test level philosophy
- [Test Architecture](test-architecture/) - Component test design patterns

---

## Usage

### Automatic Integration

The filter is automatically applied in `tests/sim/run.py`:

```python
from ghdl_filter import GHDLOutputFilter, FilterLevel

# Set filter level from environment (default: NORMAL)
filter_level_str = os.environ.get("GHDL_FILTER", "normal").lower()
if filter_level_str == "aggressive":
    filter_level = FilterLevel.AGGRESSIVE
elif filter_level_str == "normal":
    filter_level = FilterLevel.NORMAL
elif filter_level_str == "minimal":
    filter_level = FilterLevel.MINIMAL
else:
    filter_level = FilterLevel.NONE

# Apply filter during test execution
with filtered_output(filter_level=filter_level):
    runner.test(...)  # All GHDL output is filtered
```

### Environment Control

```bash
# Maximum suppression (default for P1)
export GHDL_FILTER=aggressive

# Balanced filtering (default)
export GHDL_FILTER=normal

# Light touch
export GHDL_FILTER=minimal

# No filtering (debugging)
export GHDL_FILTER=none
```

**Note:** DPD-001 uses `GHDL_FILTER` environment variable (not `GHDL_FILTER_LEVEL`)

---

## Filter Levels

### FilterLevel.AGGRESSIVE (90-98% reduction)

**Filters:**
- All metavalue warnings (`metavalue detected`)
- All null/uninitialized warnings (`null argument`)
- All initialization warnings (`@0ms`, `@0fs`)
- All vector truncated warnings (MASSIVE volume - 12,000+ lines)
- GHDL internal messages (`ghdl:info`)
- Duplicate warnings
- GHDL elaboration noise

**Preserves:**
- Errors (always)
- Failures (always)
- PASS/FAIL results
- Test names
- Assertion failures
- Test headers and separators

### FilterLevel.NORMAL (80-90% reduction)

**Filters:**
- Metavalue warnings
- Null warnings
- Initialization warnings
- Vector truncated warnings
- Duplicate warnings

**Preserves:**
- Errors, failures, results
- First occurrence of warnings
- Unique warnings

### FilterLevel.MINIMAL (50-70% reduction)

**Filters:**
- Repeated metavalue warnings (keeps first)
- Vector truncated warnings (too noisy)
- Severe duplicates only

**Preserves:**
- Everything else
- First occurrence of each warning type

### FilterLevel.NONE (0% reduction)

**No filtering** - raw GHDL output (for debugging filter itself)

---

## Implementation Details

### Filter Patterns

**FILTER patterns (what to suppress):**

The implementation in `tests/sim/ghdl_filter.py` uses these pattern categories:

```python
METAVALUE_PATTERNS = [
    r".*NUMERIC_STD\.[A-Z_]+: metavalue detected.*",
    r".*metavalue detected, returning.*",
    r".*\(assertion warning\): NUMERIC_STD.*metavalue.*",
    r".*STD_LOGIC_.*: metavalue detected.*",
    r".*INFO cocotb:.*NUMERIC_STD\.[A-Z_]+: metavalue detected.*",
    r".*INFO cocotb:.*metavalue detected.*",
]

TRUNCATED_PATTERNS = [
    r".*NUMERIC_STD\.TO_SIGNED: vector truncated.*",
    r".*NUMERIC_STD\.TO_UNSIGNED: vector truncated.*",
    r".*INFO cocotb:.*vector truncated.*",
]

NULL_PATTERNS = [
    r".*NUMERIC_STD\.[A-Z_]+: null argument detected.*",
    r".*null argument detected, returning.*",
    r".*\(assertion warning\): NUMERIC_STD.*null.*",
    r".*INFO cocotb:.*null argument detected.*",
]

INIT_PATTERNS = [
    r".*@0ms.*assertion.*",
    r".*@0fs.*assertion.*",
    r".*at 0 ns.*warning.*",
    r"^\s*0\.00ns.*metavalue.*",
]

GHDL_INTERNAL_PATTERNS = [
    r".*ghdl:info: simulation.*",
    r".*ghdl:info: elaboration.*",
    r".*ghdl:info: back annotation.*",
    r".*bound check.*",
]
```

**PRESERVE patterns (never filter):**

```python
PRESERVE_PATTERNS = [
    r".*\bERROR\b.*",                    # Errors
    r".*\bFAIL.*",                       # Failures
    r".*\bPASS.*",                       # Successes
    r".*assertion error.*",              # Real errors
    r".*assertion failure.*",            # Real failures
    r".*TEST.*COMPLETE.*",               # Test status
    r".*ALL TESTS.*",                    # Summary
    r"^\s*Test \d+:.*",                  # Test headers
    r"^={3,}.*",                         # Separator lines
    r".*✓.*",                            # Success marks
    r".*✗.*",                            # Failure marks
    r".*INFO cocotb:.*P[0-9]+.*TESTS.*", # Test level headers
    r".*INFO cocotb:.*T[0-9]+:.*",       # Test case headers
    r".*cocotb\.customwrapper.*",       # Custom wrapper test output
    r".*Clock started.*",                # Setup messages
    r".*Reset complete.*",               # Setup messages
    r".*FORGE control.*",                # Important test steps
]
```

### Stream-Level Filtering

**FilteredOutput wrapper class:**

The DPD-001 implementation uses a stream wrapper approach:

```python
class FilteredOutput(io.TextIOBase):
    """Wraps a stream and filters output through GHDLOutputFilter"""
    
    def __init__(self, original, filter_instance):
        self.original = original
        self.filter = filter_instance
    
    def write(self, text):
        if not self.filter.should_filter(text.rstrip('\n')):
            self.original.write(text)
        return len(text)
```

**Context manager integration:**

```python
@contextmanager
def filtered_output(filter_level):
    """Context manager that redirects stdout/stderr through the GHDL filter."""
    if filter_level == FilterLevel.NONE:
        yield
        return
    
    ghdl_filter = GHDLOutputFilter(level=filter_level)
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    
    filtered_stdout = FilteredOutput(orig_stdout, ghdl_filter)
    filtered_stderr = FilteredOutput(orig_stderr, ghdl_filter)
    
    try:
        sys.stdout = filtered_stdout
        sys.stderr = filtered_stderr
        yield
    finally:
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
        if ghdl_filter.stats.filtered_lines > 0:
            ghdl_filter.print_summary(orig_stdout)
```

**Why this works:** Python's stream redirection captures all output (including from C code like GHDL) when it's written through Python's stdout/stderr file objects.

---

## Duplicate Detection

**Hash-based deduplication with seen set:**

```python
self.seen_warnings: Set[str] = set()

def normalize_warning(self, line: str) -> Optional[str]:
    """Normalize a warning line for deduplication."""
    if "warning" not in line.lower() and "assertion" not in line.lower():
        return None
    
    # Remove timestamps and line numbers
    normalized = re.sub(r'@?\d+(\.\d+)?\s*(ms|us|ns|ps|fs)', '', line)
    normalized = re.sub(r':\d+:\d+', '', normalized)
    normalized = ' '.join(normalized.split())
    
    return normalized if normalized else None

def should_filter(self, line: str) -> bool:
    # Check for duplicate warnings
    normalized = self.normalize_warning(line)
    if normalized and normalized in self.seen_warnings:
        self.stats.duplicate_warnings += 1
        return True
    elif normalized:
        self.seen_warnings.add(normalized)
```

---

## Statistics Tracking

```python
@dataclass
class FilterStats:
    """Track filtering statistics"""
    total_lines: int = 0
    filtered_lines: int = 0
    metavalue_warnings: int = 0
    truncated_warnings: int = 0
    null_warnings: int = 0
    initialization_warnings: int = 0
    duplicate_warnings: int = 0

def print_summary(self, output_stream=sys.stdout):
    """Print filtering summary statistics."""
    reduction_pct = (self.stats.filtered_lines / self.stats.total_lines * 100) \
        if self.stats.total_lines > 0 else 0
    
    output_stream.write(f"\n[GHDL Output Filter - Level: {self.level.value}]\n")
    output_stream.write(f"  Total lines: {self.stats.total_lines}\n")
    output_stream.write(f"  Filtered: {self.stats.filtered_lines} ({reduction_pct:.1f}% reduction)\n")
    # ... detailed breakdown ...
```

---

## Testing the Filter

```bash
# Run with aggressive filtering (default for P1)
cd tests/sim
python run.py

# Compare with no filtering
GHDL_FILTER=none python run.py

# See the difference!
```

**Example Output Reduction:**
- **Before filtering:** ~12,500 lines (mostly vector truncated warnings)
- **After aggressive filtering:** ~55 lines (99.6% reduction)
- **Preserved:** All test results, errors, and important messages

---

## Debugging the Filter

If you suspect the filter is removing important information:

1. **Run with NONE level:**
   ```bash
   GHDL_FILTER=none python run.py
   ```

2. **Check PRESERVE patterns:**
   - Errors, failures, PASS/FAIL are NEVER filtered
   - If you see output, it passed PRESERVE patterns

3. **Add custom PRESERVE pattern:**
   ```python
   # In tests/sim/ghdl_filter.py
   PRESERVE_PATTERNS = [
       # ... existing patterns ...
       r".*my_custom_pattern.*",  # Never filter this
   ]
   ```

4. **Test incrementally:**
   - Start with NONE (no filtering)
   - Move to MINIMAL (light filtering)
   - Move to NORMAL (balanced)
   - Move to AGGRESSIVE (maximum)

---

## Performance Impact

**Negligible** - filtering adds <10ms overhead per test run.

**Measured on Apple M1:**
- P1 test without filter: 0.89s
- P1 test with filter: 0.90s
- Overhead: ~1%

The filter processes lines in real-time as they're written, so there's minimal buffering overhead.

---

## Maintenance

### Adding New Filter Patterns

```python
# In tests/sim/ghdl_filter.py
TRUNCATED_PATTERNS = [
    # ... existing patterns ...
    r".*new_pattern_to_filter.*",  # Your new pattern
]
```

### Adding New Preserve Patterns

```python
PRESERVE_PATTERNS = [
    # ... existing patterns ...
    r".*important_pattern.*",  # Never filter
]
```

**Pattern precedence:** PRESERVE always wins over FILTER

### Updating Filter Levels

Filter levels are defined in the `FilterLevel` enum and implemented in `GHDLOutputFilter.should_filter()`. To add a new level:

1. Add enum value to `FilterLevel`
2. Add case in `should_filter()` method
3. Update this documentation

---

## DPD-001 Specific Notes

**Implementation Location:**
- Filter class: `tests/sim/ghdl_filter.py`
- Integration: `tests/sim/run.py` (uses `filtered_output()` context manager)

**Environment Variable:**
- DPD-001 uses `GHDL_FILTER` (not `GHDL_FILTER_LEVEL`)
- Values: `aggressive`, `normal`, `minimal`, `none`

**Auto-Selection:**
- Default: `normal` (balanced filtering)
- Can be overridden via `GHDL_FILTER` environment variable
- Verbosity level can also influence selection (see `run.py`)

**Integration Pattern:**
```python
# In tests/sim/run.py
from ghdl_filter import GHDLOutputFilter, FilterLevel

# Determine filter level
filter_level = determine_filter_level()  # From env or verbosity

# Apply during test execution
with filtered_output(filter_level=filter_level):
    cocotb.runner.run_tests(...)
```

---

## Migration Notes

**Source:** FORGE-V5 `/docs/FORGE-V5/GHDL/GHDL Output Filter.md`  
**Migration Date:** 2025-01-28  
**Changes:**
- Updated file paths to match DPD-001 structure (`tests/sim/ghdl_filter.py`)
- Updated environment variable name (`GHDL_FILTER` vs `GHDL_FILTER_LEVEL`)
- Updated integration pattern to match DPD-001's stream wrapper approach
- Added DPD-001 specific notes section
- Verified filter patterns match current implementation

---

**Last Updated:** 2025-01-28  
**Maintainer:** Moku Instrument Forge Team  
**Status:** Migrated and verified against DPD-001 implementation

