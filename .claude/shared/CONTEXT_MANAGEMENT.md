# Context Management Strategy

**Version:** 1.0
**Purpose:** Token optimization and tiered loading for AI agents
**Audience:** AI agents working in this monorepo

---

## Overview

This monorepo uses a **three-tier context loading strategy** to optimize token usage while ensuring AI agents have necessary information at the right time.

**Token Budget:** 200k tokens total
- System + tools: ~16k tokens (8%)
- Target for messages: ~100k tokens (50%)
- Reserved buffer: ~84k tokens (42%)

**Problem:** Loading all documentation upfront wastes tokens on information not needed for current task.

**Solution:** Tiered loading - start minimal, drill down as needed.

---

## Three-Tier Loading Strategy

### Tier 1: Always Load First (~500-1000 tokens)

**Purpose:** Quick orientation, navigation to deeper context

**Load these first:**
1. **Monorepo `llms.txt`** (213 lines)
   - Repository structure overview
   - Delegation strategy (monorepo → tools → libs)
   - Common workflows summary
   - Git submodule navigation

2. **Agent prompt** (specific to task)
   - deployment-orchestrator (if hardware deployment task)
   - hardware-debug (if debugging task)
   - etc.

**What you get:**
- High-level architecture
- Where to find detailed info (pointers to Tier 2)
- Common questions answered immediately
- Decision tree for what to load next

**Example - Starting work:**
```
AI Agent loads:
1. llms.txt (213 lines) → "This is a monorepo with tools/ and libs/ submodules"
2. deployment-orchestrator/agent.md → "I coordinate hardware deployment workflows"

AI Agent knows:
- Repository structure (v2.0 flat architecture)
- What agents are available
- Where to find type definitions (tools/forge-codegen/basic_serialized_datatypes)
- How to delegate tasks
```

---

### Tier 2: Load When Designing/Integrating (~2000-5000 tokens)

**Purpose:** Deep context for specific domains, cross-library integration

**Load these when:**
- Designing new code generation (need type system details)
- Understanding VHDL components (need architecture patterns)
- Debugging integration issues (need cross-library patterns)
- Working with platform specifications (need hardware details)

**Tier 2 Documents:**

1. **CLAUDE.md files** (submodules)
   - `tools/forge-codegen/CLAUDE.md` - Type system and code generation deep dive
   - `libs/forge-vhdl/CLAUDE.md` - VHDL components and testing patterns
   - `libs/moku-models/CLAUDE.md` - Platform integration patterns
   - `libs/riscure-models/CLAUDE.md` - Probe safety patterns

2. **Shared knowledge docs**
   - `CONTEXT_MANAGEMENT.md` (this file) - Meta-strategy
   - `ARCHITECTURE_OVERVIEW.md` - v2.0 architecture details

3. **Agent prompts** (when delegating)
   - deployment-orchestrator - Hardware deployment workflows
   - hardware-debug - FSM debugging and monitoring

**What you get:**
- Design rationale (why these types? why this architecture?)
- Integration patterns (how libraries interact)
- Complete workflows (step-by-step guides)
- Common pitfalls and solutions

**Example - Designing new instrument:**
```
AI Agent already loaded Tier 1.

User: "I want to create an instrument with voltage and timing controls"

AI Agent loads Tier 2:
1. tools/forge-codegen/CLAUDE.md → "23 types available, voltage types explained, conversion formulas"
2. libs/moku-models/CLAUDE.md → "Voltage ranges by platform, safety constraints"
3. ARCHITECTURE_OVERVIEW.md → "v2.0 clean architecture patterns"

AI Agent now has:
- Type system details (which voltage type to use?)
- Platform constraints (will this work on moku_go?)
- Architecture patterns (how submodules integrate)
```

---

### Tier 3: Load For Implementation (~10000+ tokens)

**Purpose:** Source code, implementation details, debugging

**Load these when:**
- Actually writing/editing code
- Debugging specific errors
- Understanding implementation internals
- Fixing bugs in generated code

**Tier 3 Sources:**

1. **Source code files**
   - `tools/forge-codegen/forge_codegen/models/package.py` - Pydantic models
   - `tools/forge-codegen/forge_codegen/generator/codegen.py` - VHDL generation
   - `tools/forge-codegen/forge_codegen/basic_serialized_datatypes/types.py` - Type definitions
   - `libs/forge-vhdl/vhdl/**/*.vhd` - VHDL components

2. **Template files**
   - `tools/forge-codegen/forge_codegen/templates/shim.vhd.j2` - Shim layer template
   - `tools/forge-codegen/forge_codegen/templates/main.vhd.j2` - Main template

3. **Test files** (when debugging)
   - `tools/forge-codegen/tests/test_*.py` - Code generation tests
   - `libs/forge-vhdl/tests/test_*.py` - VHDL component tests

**What you get:**
- Actual implementation code
- VHDL templates
- Test examples
- Line-by-line logic

**Example - Debugging VHDL generation:**
```
AI Agent already loaded Tier 1 & 2.

User: "The generated shim file has wrong bit slices"

AI Agent loads Tier 3:
1. tools/forge-codegen/forge_codegen/generator/codegen.py → "How bit slices are calculated"
2. tools/forge-codegen/forge_codegen/templates/shim.vhd.j2 → "Template logic for bit extraction"
3. Generated output file → "Actual generated output to inspect"

AI Agent can now:
- Trace bit slice calculation
- Compare template vs output
- Identify bug in generation logic
```

---

## Decision Tree: What to Load When

### Starting a New Task

```
User request arrives
    ↓
Load Tier 1 (always)
    ↓
Is this a quick question? (type lookup, platform check, etc.)
    ↓ Yes → Answer from Tier 1
    ↓ No
    ↓
Does this involve design/integration?
    ↓ Yes → Load Tier 2 (CLAUDE.md, workflows)
    ↓ No
    ↓
Does this involve implementation/debugging?
    ↓ Yes → Load Tier 3 (source code)
```

### Examples by Question Type

**Quick Questions (Tier 1 only):**
- "What types are available?"
  - Answer from llms.txt → "25 types, see basic-app-datatypes/llms.txt"

- "What platforms exist?"
  - Answer from llms.txt → "moku_go, moku_lab, moku_pro, moku_delta"

- "How do I deploy a probe?"
  - Answer from probe-design-orchestrator → "Delegate to deployment-context"

**Design Questions (Tier 1 + 2):**
- "Which voltage type should I use for a 0-3V output?"
  - Tier 1: llms.txt → "Check basic-app-datatypes"
  - Tier 2: basic-app-datatypes/CLAUDE.md → "Use voltage_output_05v_s16 (0-5V range, clamped in VHDL)"

- "How do I integrate multiple library constraints?"
  - Tier 1: llms.txt → "Check MODELS_INDEX.md"
  - Tier 2: MODELS_INDEX.md → "Cross-library integration patterns"
  - Tier 2: moku-models/CLAUDE.md → "Platform voltage limits"
  - Tier 2: riscure-models/CLAUDE.md → "Probe safety checks"

**Implementation Questions (Tier 1 + 2 + 3):**
- "Why is my VHDL shim generating wrong bit slices?"
  - Tier 1: llms.txt → "Check forge-codegen documentation"
  - Tier 2: tools/forge-codegen/CLAUDE.md → "VHDL generation pipeline explained"
  - Tier 3: tools/forge-codegen/forge_codegen/generator/codegen.py → "Actual bit slice calculation code"
  - Tier 3: tools/forge-codegen/forge_codegen/templates/shim.vhd.j2 → "Template to inspect"

---

## Token Budget Guidelines

### Conservative Approach (Recommended)

**Always load:**
- Tier 1: ~1k tokens (llms.txt + agent prompt)

**Load as needed:**
- Tier 2: Add ~2-5k tokens per CLAUDE.md or agent prompt
- Tier 3: Add ~5-10k tokens per source file

**Example budget:**
```
Tier 1: 1k tokens (base)
Tier 2:
  - basic-app-datatypes/CLAUDE.md: +2k
  - PROBE_WORKFLOW.md: +1k
  - forge-context agent: +3k
Total so far: 7k tokens (3.5% of budget)

Tier 3 (if needed):
  - tools/forge-codegen/forge_codegen/generator/codegen.py: +5k
  - tools/forge-codegen/forge_codegen/templates/shim.vhd.j2: +2k
Total: 14k tokens (7% of budget)

Still have 186k tokens available (93%)
```

### Aggressive Approach (When Confident)

If you know exactly what's needed:
- Skip Tier 1 delegation, load Tier 2/3 directly
- Useful for follow-up questions in same session

**Example:**
```
User: "Now fix the bit slice calculation"

AI Agent (already in context):
- Skip Tier 1 (already loaded)
- Skip Tier 2 (already loaded forge-context)
- Load Tier 3 directly: codegen.py

Saves reloading 6k tokens
```

---

## Common Workflows & Token Usage

### Workflow 1: New Probe Development

**Steps:**
1. Load Tier 1 (llms.txt, probe-design-orchestrator)
2. Load Tier 2 (PROBE_WORKFLOW.md)
3. User edits YAML (no new loading)
4. Delegate to forge-context (load forge-context agent ~3k tokens)
5. Package generated (inspect manifest.json ~1k tokens)
6. User writes VHDL (load Tier 3 templates ~2k tokens)

**Total:** ~10k tokens (5% budget)

---

### Workflow 2: Type System Lookup

**Steps:**
1. Load Tier 1 (llms.txt)
2. Answer from basic-app-datatypes/llms.txt reference

**Total:** ~1k tokens (0.5% budget)

---

### Workflow 3: Debugging VHDL Generation

**Steps:**
1. Load Tier 1 (llms.txt, probe-design-orchestrator)
2. Load Tier 2 (forge-context agent ~3k tokens)
3. Load Tier 3 (codegen.py ~5k, templates ~2k, generated VHDL ~3k)

**Total:** ~14k tokens (7% budget)

---

### Workflow 4: Cross-Library Integration Question

**Steps:**
1. Load Tier 1 (llms.txt)
2. Load Tier 2 (MODELS_INDEX.md ~1.5k)
3. Load Tier 2 (relevant CLAUDE.md files ~2-3k each)

**Total:** ~8-10k tokens (4-5% budget)

---

## Anti-Patterns to Avoid

### ❌ Loading Everything Upfront
```
AI Agent: "Let me load all CLAUDE.md files, all agent prompts, all source code..."
Result: 50k+ tokens wasted, nothing left for conversation
```

**Instead:**
```
AI Agent: "Load llms.txt first. User asked about types → load basic-app-datatypes/llms.txt only."
Result: 1k tokens used, 199k available
```

---

### ❌ Re-loading Same Content
```
User: "What about voltage types?"
AI Agent: Loads basic-app-datatypes/CLAUDE.md (2k tokens)

User: "And time types?"
AI Agent: Loads basic-app-datatypes/CLAUDE.md again (2k tokens wasted)
```

**Instead:**
```
AI Agent: "Already have basic-app-datatypes/CLAUDE.md in context, reference it directly."
Result: 0 additional tokens
```

---

### ❌ Loading Source Code for Questions
```
User: "What's the YAML schema for datatypes?"
AI Agent: Loads tools/forge-codegen/forge_codegen/models/package.py (5k tokens)
```

**Instead:**
```
AI Agent: "Check Tier 2: tools/forge-codegen/CLAUDE.md has schema documentation."
Result: 3k tokens (CLAUDE.md) vs 5k (source code)
```

---

## Best Practices

### 1. Start Minimal
Always load Tier 1 first. Don't assume you need deeper context.

### 2. Load Just-In-Time
Load Tier 2/3 only when needed for current question.

### 3. Reuse Context
If already loaded, reference it. Don't reload.

### 4. Prefer Documentation Over Code
Tier 2 (CLAUDE.md, agent prompts) is more concise than Tier 3 (source code).

### 5. Delegate Appropriately
Don't load forge agent prompts if you can delegate to them directly.

---

## Special Cases

### Multi-File Questions

**User:** "How do voltage types work across all libraries?"

**Approach:**
1. Load Tier 1 (llms.txt) → "Three libraries: basic-app-datatypes, moku-models, riscure-models"
2. Load Tier 2 (MODELS_INDEX.md) → "Cross-library integration section"
3. Load Tier 2 (basic-app-datatypes/CLAUDE.md) → "Voltage type definitions"
4. Load Tier 2 (moku-models/CLAUDE.md) → "Platform voltage constraints"
5. Load Tier 2 (riscure-models/CLAUDE.md) → "Probe voltage safety"

**Total:** ~8k tokens for complete answer

---

### Debugging Sessions

**User:** "My probe deployment failed"

**Approach:**
1. Load Tier 1 (probe-design-orchestrator)
2. Delegate to deployment-context (load deployment-context agent ~3k)
3. If deployment-context needs platform details → load moku-models/llms.txt (~1k)
4. If error is in VHDL → load Tier 3 source code

**Token usage scales with debugging depth**

---

## Meta-Strategy: When to Use This Document

**Load CONTEXT_MANAGEMENT.md when:**
- Starting a complex multi-file task
- Unsure what documentation to load
- Optimizing token usage
- Debugging "context too large" issues

**Don't load when:**
- Simple single-file questions
- Already know exactly what to load
- Following established workflow

---

## Summary

**Three Tiers:**
1. **Tier 1** (~1k tokens) - Always load, quick orientation
2. **Tier 2** (~2-5k tokens) - Load for design/integration
3. **Tier 3** (~5-10k tokens) - Load for implementation/debugging

**Decision Tree:**
- Quick question? → Tier 1 only
- Design question? → Tier 1 + 2
- Implementation? → Tier 1 + 2 + 3

**Best Practice:**
Start minimal, load just-in-time, reuse context, prefer docs over code.

---

**Last Updated:** 2025-11-03
**Maintained By:** moku-instrument-forge team
