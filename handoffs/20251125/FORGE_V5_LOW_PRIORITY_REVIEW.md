# Low Priority Files Review

**Date:** 2025-01-28  
**Purpose:** Review remaining low-priority files from FORGE-V5 migration

---

## Summary

**Files Reviewed:** 5 files  
**Recommendation: Migrate:** 2 files (with notes)  
**Recommendation: Skip:** 3 files

---

## File-by-File Assessment

### 1. N/Custom Wrapper/README.md ⭐⭐

**Content:** Basic CustomWrapper entity signature (29 lines)

**Current Status:**
- Entity signature is already documented in `docs/custom-instrument.md`
- However, `custom-instrument.md` focuses on Custom Instrument (future) vs CustomWrapper (current)
- CustomWrapper deserves its own focused document

**Recommendation:** ✅ **MIGRATE** as `docs/custom-wrapper.md`

**Rationale:**
- CustomWrapper is the current standard (DPD-001 uses it)
- Should have dedicated documentation separate from Custom Instrument
- Can expand with DPD-001-specific examples
- Cross-reference with custom-instrument.md

**Migration Plan:**
- Create `docs/custom-wrapper.md`
- Include entity signature
- Add DPD-001 implementation examples
- Document FORGE control scheme
- Add testing examples
- Cross-reference custom-instrument.md

---

### 2. Moku Cloud Compile/README.md ⭐

**Content:** Just 2 lines with links to MCC documentation

**Current Status:**
- Very brief (just external links)
- MCC link already in `docs/custom-instrument.md`
- No unique information

**Recommendation:** ❌ **SKIP** (add links to existing docs if needed)

**Rationale:**
- Too brief to warrant separate document
- Links can be added to README.md or custom-instrument.md if needed
- External documentation is better maintained by Liquid Instruments

**Action:**
- Add MCC link to `docs/custom-instrument.md` if not already present
- Consider adding to main README.md under "External Resources"

---

### 3. Moku Platforms/Moku Go/README.md ⭐

**Content:** Just datasheet link (2 lines)

**Current Status:**
- Only contains link to Moku:Go datasheet
- Datasheet likely in `libs/moku-models-v4/datasheets/`

**Recommendation:** ❌ **SKIP**

**Rationale:**
- Too brief (just a link)
- Datasheet should be in moku-models-v4 submodule
- No unique information

**Action:**
- Verify datasheet is in `libs/moku-models-v4/datasheets/`
- If not, note for future reference

---

### 4. Moku Platforms/Platforms.md ⭐⭐⭐

**Content:** Comprehensive platform specifications with implementation strategy notes (310 lines)

**Current Status:**
- **SUPERSEDED:** Platform specs are in `libs/moku-models-v4/` (Pydantic models)
- **BUT:** Contains valuable implementation strategy notes not in Pydantic models
- **VALUE:** Implementation recommendations for voltage ranges, impedance, DIO, etc.

**Recommendation:** ✅ **MIGRATE** as `docs/platform-implementation-notes.md` (reference only)

**Rationale:**
- Implementation strategy notes are valuable
- Not captured in Pydantic models (which are data-only)
- Provides context for design decisions
- Should be marked as "reference" with note that moku-models-v4 is source of truth

**Migration Plan:**
- Create `docs/platform-implementation-notes.md`
- **Add prominent note:** "Platform specifications are in `libs/moku-models-v4/`. This document contains implementation strategy notes only."
- Extract implementation strategy sections:
  - Voltage Range Handling
  - Impedance Handling
  - Digital I/O Differences
  - ADC/DAC Blending
  - Multi-Instrument Slot Counts
  - Answers to Outstanding Questions
- Remove detailed spec tables (reference moku-models-v4 instead)
- Add cross-reference to moku-models-v4

**What to Include:**
- ✅ Implementation strategy notes
- ✅ Design decision rationale
- ✅ "Answers to Outstanding Questions" section
- ❌ Detailed spec tables (use moku-models-v4)
- ❌ Platform comparison table (use moku-models-v4)

---

### 5. Moku Platforms/README.md ⭐

**Content:** Just a note that specs are in moku-models-v4 (4 lines)

**Current Status:**
- Only contains note about moku-models-v4
- Redundant if we don't migrate Platforms.md

**Recommendation:** ❌ **SKIP**

**Rationale:**
- Too brief (just a note)
- Redundant with moku-models-v4 README
- No unique information

**Action:**
- No action needed

---

## Migration Recommendations

### Priority Order

1. **Custom Wrapper** (High value, fills gap)
   - Create dedicated `docs/custom-wrapper.md`
   - Focus on current standard (CustomWrapper)
   - Cross-reference with custom-instrument.md

2. **Platform Implementation Notes** (Medium value, preserves context)
   - Create `docs/platform-implementation-notes.md`
   - Extract only implementation strategy sections
   - Mark as reference, point to moku-models-v4 for specs

### Skip List

- Moku Cloud Compile/README.md (too brief, just links)
- Moku Platforms/Moku Go/README.md (too brief, just link)
- Moku Platforms/README.md (too brief, just note)

---

## Proposed Actions

### Action 1: Create Custom Wrapper Doc

**File:** `docs/custom-wrapper.md`

**Content:**
- CustomWrapper entity signature
- DPD-001 implementation examples
- FORGE control scheme (CR0[31:29])
- Control register mapping (CR0-CR15)
- Testing with CustomWrapper_test_stub
- Cross-reference to custom-instrument.md

### Action 2: Create Platform Implementation Notes

**File:** `docs/platform-implementation-notes.md`

**Content:**
- **Prominent warning:** "Platform specs are in moku-models-v4. This doc contains implementation notes only."
- Implementation strategy sections:
  - Voltage range handling recommendations
  - Impedance handling recommendations
  - DIO differences and handling
  - ADC/DAC blending notes
  - Multi-instrument slot strategy
- Design decision rationale
- Cross-reference to moku-models-v4

### Action 3: Update Existing Docs

**Update `docs/custom-instrument.md`:**
- Ensure MCC link is present
- Cross-reference to new custom-wrapper.md

**Update `README.md`:**
- Consider adding "External Resources" section with MCC link

---

## Decision Matrix

| File | Lines | Unique Value | Migration? | Reason |
|------|-------|--------------|------------|--------|
| Custom Wrapper | 29 | ⭐⭐ Medium | ✅ Yes | Fills gap, current standard |
| Moku Cloud Compile | 2 | ⭐ None | ❌ No | Just links |
| Moku Go | 2 | ⭐ None | ❌ No | Just link |
| Platforms.md | 310 | ⭐⭐⭐ High (notes) | ✅ Yes | Implementation strategy |
| Platforms README | 4 | ⭐ None | ❌ No | Just note |

---

## Next Steps

1. **Review this assessment** - Confirm recommendations
2. **Migrate Custom Wrapper** - Create dedicated doc
3. **Migrate Platform Notes** - Extract implementation strategy
4. **Update cross-references** - Link new docs appropriately
5. **Archive skipped files** - Document why they were skipped

---

**Status:** Ready for Review  
**Last Updated:** 2025-01-28

