# FORGE-V5 Documentation Migration Ranking

**Source:** `/Users/johnycsh/Forge/BPD-Dev-v5/docs/FORGE-V5`  
**Target:** DPD-001 (refactored from BPD-Dev-v5)  
**Date:** 2025-01-28  
**Purpose:** Rank files by migration priority and staleness risk

---

## Executive Summary

**Total Files Reviewed:** 15+ files across 10 directories  
**High Priority:** 2 files  
**Medium Priority:** 3 files  
**Low Priority:** 5 files  
**Skip/Archive:** 5+ files  

**Key Findings:**
- Most core concepts (progressive testing, GHDL filtering, CocoTB) are **already implemented** in DPD-001
- Platform specifications are **superseded** by `moku-models-v4` submodule
- Test architecture docs contain **stale constants** (200 vs 3277) that need verification
- Several files are **too generic** or **already covered** by existing docs

---

## Migration Priority Rankings

### 🔴 HIGH PRIORITY - Migrate with Verification

#### 1. **Architecture/Test-Architecture/forge_hierarchical_encoder_test_design.md**
**Priority:** ⭐⭐⭐⭐⭐  
**Risk Level:** 🟡 MEDIUM (stale constants detected)

**Why Migrate:**
- Comprehensive test design document for `forge_hierarchical_encoder`
- Contains detailed test strategy (P1/P2/P3 breakdown)
- Includes expected value calculation formulas
- Documents CocoTB access patterns for signed types

**Staleness Concerns:**
- ⚠️ **CRITICAL:** References `DIGITAL_UNITS_PER_STATE = 200` but DPD-001 uses `3277`
- ⚠️ Test examples use old constant in calculations
- ⚠️ Date: 2025-11-07 (may predate constant update)

**Verification Required:**
- [ ] Verify current `DIGITAL_UNITS_PER_STATE` value in `rtl/forge_hierarchical_encoder.vhd`
- [ ] Update all test examples to use 3277 instead of 200
- [ ] Recalculate expected values in test cases
- [ ] Check if status offset calculation (0.78125) is still correct

**Migration Action:**
- Migrate to `docs/test-architecture/forge_hierarchical_encoder_test_design.md`
- Update all constants to match current implementation
- Add note about constant evolution (200 → 3277)

---

#### 2. **GHDL/GHDL Output Filter.md**
**Priority:** ⭐⭐⭐⭐  
**Risk Level:** 🟢 LOW (implementation exists, doc may be outdated)

**Why Migrate:**
- Documents GHDL output filtering strategy
- Explains filter levels (AGGRESSIVE, NORMAL, MINIMAL, NONE)
- Documents OS-level file descriptor redirection approach
- Contains usage examples and debugging tips

**Staleness Concerns:**
- ⚠️ DPD-001 already has `tests/sim/ghdl_filter.py` implementation
- ⚠️ Need to verify if current implementation matches documented approach
- ⚠️ May reference old file paths or patterns

**Verification Required:**
- [ ] Compare documented filter patterns with `tests/sim/ghdl_filter.py`
- [ ] Verify filter levels match (AGGRESSIVE, NORMAL, MINIMAL, NONE)
- [ ] Check if OS-level redirection is still used or if approach changed
- [ ] Verify integration with `tests/sim/run.py` matches documentation

**Migration Action:**
- Migrate to `docs/ghdl-output-filter.md`
- Update file paths to match DPD-001 structure
- Add cross-reference to `tests/sim/ghdl_filter.py`
- Note any implementation differences

---

### 🟡 MEDIUM PRIORITY - Migrate with Updates

#### 3. **Progressive Testing/README.md**
**Priority:** ⭐⭐⭐  
**Risk Level:** 🟢 LOW (concept already implemented)

**Why Migrate:**
- Documents core progressive testing philosophy
- Explains P1/P2/P3/P4 test levels
- References agent pipeline integration

**Staleness Concerns:**
- ⚠️ Very brief (only 12 lines)
- ⚠️ DPD-001 already implements progressive testing
- ⚠️ May reference old project structure

**Verification Required:**
- [ ] Check if P4 level exists in DPD-001 (only P1-P3 seen)
- [ ] Verify test level naming matches (P1_BASIC, P2_INTERMEDIATE, etc.)
- [ ] Confirm agent pipeline references are still valid

**Migration Action:**
- Migrate to `docs/progressive-testing.md`
- Expand with DPD-001-specific examples
- Add links to actual test files
- Update agent references if needed

---

#### 4. **CocoTB/README.md**
**Priority:** ⭐⭐  
**Risk Level:** 🟢 LOW (basic info only)

**Why Migrate:**
- Basic CocoTB introduction
- Notes about FORGE-V5 ecosystem usage
- Mentions `cocotb-tests` directory convention

**Staleness Concerns:**
- ⚠️ Very brief (only 19 lines)
- ⚠️ DPD-001 uses `tests/sim/` not `cocotb-tests/`
- ⚠️ May be too generic to be valuable

**Verification Required:**
- [ ] Check if directory naming convention matters
- [ ] Verify if any FORGE-V5-specific CocoTB patterns are documented

**Migration Action:**
- Migrate to `docs/cocotb.md` (if keeping)
- Update directory references to `tests/sim/`
- Consider merging into main README if too brief

---

#### 5. **Custom Instrument/README.md**
**Priority:** ⭐⭐⭐  
**Risk Level:** 🟡 MEDIUM (terminology may have evolved)

**Why Migrate:**
- Documents "Custom Instrument" terminology (future Liquid Instruments naming)
- Shows entity signature with FORGE-mandated state/status vectors
- Documents control signal priority (Reset > ClkEn > Enable)

**Staleness Concerns:**
- ⚠️ Date: 2025-11-12 (recent, but terminology may have changed)
- ⚠️ Entity signature may not match current DPD implementation
- ⚠️ References "future" terminology - may be outdated

**Verification Required:**
- [ ] Compare entity signature with `rtl/DPD.vhd` or `rtl/CustomWrapper_test_stub.vhd`
- [ ] Verify control signal priority matches DPD implementation
- [ ] Check if "Custom Instrument" terminology is now standard

**Migration Action:**
- Migrate to `docs/custom-instrument.md`
- Update entity signature to match DPD implementation
- Add note about terminology evolution
- Cross-reference with CustomWrapper docs

---

### 🟢 LOW PRIORITY - Reference Only

#### 6. **Moku Platforms/Platforms.md**
**Priority:** ⭐⭐  
**Risk Level:** 🟡 MEDIUM (superseded by moku-models-v4)

**Why Consider:**
- Comprehensive platform comparison table
- Detailed specifications for Go/Lab/Pro/Delta
- Implementation strategy notes

**Staleness Concerns:**
- ⚠️ **SUPERSEDED:** DPD-001 has `libs/moku-models-v4/` submodule
- ⚠️ Platform specs should come from Pydantic models, not markdown
- ⚠️ Last updated: 2025-01-28 (may be newer than moku-models-v4)

**Verification Required:**
- [ ] Compare specs with `libs/moku-models-v4/moku_models/platforms/`
- [ ] Check if any implementation notes are missing from Pydantic models
- [ ] Verify datasheet versions match

**Migration Action:**
- **DO NOT MIGRATE** - reference moku-models-v4 instead
- OR migrate as `docs/platform-specs-reference.md` with note that moku-models-v4 is source of truth
- Add cross-reference to Pydantic models

---

#### 7. **Moku Platforms/README.md**
**Priority:** ⭐  
**Risk Level:** 🟢 LOW (just a note)

**Why Consider:**
- Single note that specs are in moku-models-v4 submodule

**Staleness Concerns:**
- ⚠️ Only 4 lines
- ⚠️ Redundant if we don't migrate Platforms.md

**Migration Action:**
- **SKIP** - too brief, already covered by moku-models-v4 README

---

#### 8. **Moku Platforms/Moku Go/README.md**
**Priority:** ⭐  
**Risk Level:** 🟢 LOW (just a link)

**Why Consider:**
- Link to Moku:Go datasheet

**Staleness Concerns:**
- ⚠️ Only 2 lines
- ⚠️ Datasheet link may be in moku-models-v4 already

**Migration Action:**
- **SKIP** - too brief, datasheet likely in moku-models-v4/datasheets/

---

#### 9. **N/Custom Wrapper/README.md**
**Priority:** ⭐⭐  
**Risk Level:** 🟢 LOW (basic info)

**Why Consider:**
- Documents CustomWrapper entity interface
- Shows standard control register pattern (CR0-CR15)

**Staleness Concerns:**
- ⚠️ Very brief (only entity signature)
- ⚠️ DPD-001 already implements CustomWrapper
- ⚠️ May be covered in existing docs

**Verification Required:**
- [ ] Check if CustomWrapper interface is documented elsewhere in DPD-001
- [ ] Verify entity signature matches `rtl/CustomWrapper_test_stub.vhd`

**Migration Action:**
- Migrate to `docs/custom-wrapper.md` (if not already documented)
- Expand with DPD-specific examples
- Add cross-reference to test stub

---

#### 10. **Moku Cloud Compile/README.md**
**Priority:** ⭐  
**Risk Level:** 🟢 LOW (just links)

**Why Consider:**
- Link to MCC documentation
- References CustomWrapper

**Staleness Concerns:**
- ⚠️ Only 5 lines
- ⚠️ Just external links

**Migration Action:**
- **SKIP** - too brief, external links can be added to main README if needed

---

### ⚪ SKIP/ARCHIVE - Not Needed

#### 11. **README.md** (root)
**Priority:** ⭐  
**Risk Level:** 🟢 LOW

**Why Skip:**
- Very brief overview
- References old project structure
- Mostly links to other docs

**Action:** **SKIP** - DPD-001 has its own README.md

---

#### 12. **Forge Loading System/README.md**
**Priority:** ⭐  
**Risk Level:** 🟢 LOW

**Why Skip:**
- Only 2 lines
- Mentions "optional calling convention"
- Not clear if DPD-001 uses this

**Action:** **SKIP** - too brief, investigate if needed later

---

#### 13. **Multi instrument Mode/README.md**
**Priority:** ⭐  
**Risk Level:** 🟢 LOW

**Why Skip:**
- Only 3 lines
- Broken link ("Datahse")
- Just external reference

**Action:** **SKIP** - too brief, broken

---

#### 14. **Moku Platforms/Moku Lab/README.md, Moku Pro/README.md, Moku Delta/README.md**
**Priority:** ⭐  
**Risk Level:** 🟢 LOW

**Why Skip:**
- Likely just datasheet links (like Moku Go)
- Platform specs are in moku-models-v4

**Action:** **SKIP** - verify if they contain unique info, otherwise skip

---

#### 15. **Moku Instruments/README.md**
**Priority:** ⭐  
**Risk Level:** 🟢 LOW

**Why Skip:**
- Not found in directory listing
- May not exist or be empty

**Action:** **SKIP** - verify if exists, likely empty

---

## Migration Checklist

### Phase 1: High Priority (Do First) ✅ COMPLETE
- [x] **forge_hierarchical_encoder_test_design.md**
  - [x] Verify DIGITAL_UNITS_PER_STATE constant (200 vs 3277) - **CONFIRMED: 3277**
  - [x] Update all test examples with correct constants
  - [x] Recalculate expected values (all updated for 3277)
  - [x] Migrate to `docs/test-architecture/forge_hierarchical_encoder_test_design.md`
  - [x] Add staleness warning and migration notes

- [x] **GHDL Output Filter.md**
  - [x] Compare with `tests/sim/ghdl_filter.py` - **VERIFIED: Matches**
  - [x] Verify filter patterns match - **CONFIRMED: All patterns match**
  - [x] Update file paths to DPD-001 structure
  - [x] Migrate to `docs/ghdl-output-filter.md`

### Phase 2: Medium Priority (Do Second) ✅ COMPLETE
- [x] **Progressive Testing/README.md**
  - [x] Expand with DPD-001 examples - **EXPANDED: 12 lines → comprehensive guide**
  - [x] Verify P1-P3 naming matches - **CONFIRMED: P1_BASIC, P2_INTERMEDIATE, P3_COMPREHENSIVE**
  - [x] Migrate to `docs/progressive-testing.md` - **COMPLETE**

- [x] **Custom Instrument/README.md**
  - [x] Compare entity signature with DPD - **VERIFIED: DPD uses CustomWrapper, not Custom Instrument**
  - [x] Update to match current implementation - **UPDATED: Added CustomWrapper vs Custom Instrument comparison**
  - [x] Migrate to `docs/custom-instrument.md` - **COMPLETE**

- [x] **CocoTB/README.md**
  - [x] Update directory references - **UPDATED: tests/sim/ (not cocotb-tests/)**
  - [x] Expand with DPD-001 examples - **EXPANDED: 19 lines → comprehensive guide**
  - [x] Migrate to `docs/cocotb.md` - **COMPLETE**

### Phase 3: Low Priority (Reference Only)
- [ ] **Platforms.md**
  - [ ] Compare with moku-models-v4
  - [ ] Decide: migrate as reference OR skip (prefer skip)
  - [ ] If migrating, add "source of truth" note

- [ ] **Custom Wrapper/README.md**
  - [ ] Check if already documented
  - [ ] Migrate if unique info exists

### Phase 4: Skip
- [ ] Archive or delete remaining files
- [ ] Document why each was skipped

---

## Staleness Risk Summary

| File | Staleness Risk | Key Concerns |
|------|---------------|--------------|
| forge_hierarchical_encoder_test_design.md | 🟡 MEDIUM | Constants (200 vs 3277) |
| GHDL Output Filter.md | 🟢 LOW | Implementation exists, verify match |
| Progressive Testing/README.md | 🟢 LOW | Concept implemented, verify details |
| Custom Instrument/README.md | 🟡 MEDIUM | Terminology may have evolved |
| Platforms.md | 🟡 MEDIUM | Superseded by moku-models-v4 |
| Custom Wrapper/README.md | 🟢 LOW | Basic info, may be redundant |
| CocoTB/README.md | 🟢 LOW | Too brief, may be redundant |
| Others | 🟢 LOW | Too brief or just links |

---

## Recommendations

1. **Start with High Priority files** - They contain the most valuable information but need constant verification
2. **Verify before migrating** - Don't assume old docs are correct
3. **Update, don't copy** - All migrated docs should be updated to match DPD-001 structure
4. **Add staleness warnings** - If constants or patterns differ, document why
5. **Cross-reference** - Link migrated docs to actual implementation files
6. **Skip redundant docs** - Don't migrate files that are just links or too brief
7. **Prefer moku-models-v4** - Platform specs should come from Pydantic models, not markdown

---

## Next Steps

1. Review this ranking with team
2. Start Phase 1 migration (High Priority)
3. Verify constants and patterns before migrating
4. Update migrated docs to match DPD-001 structure
5. Archive or delete skipped files

---

**Document Status:** Ready for Review  
**Last Updated:** 2025-01-28

