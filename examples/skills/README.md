# NocoBase Builder — Agent Skill Base

Build a complete NocoBase system from any requirements document.

## Quick Start

```
1. Read boot.md                     ← identity + state protocol + phase index
2. Read requirements (*-requirements.md)
3. Read phases/phase-0-init.md      ← first phase instructions
4. Execute, write progress to notes.md, read next phase when done
```

## Architecture: Three Layers

```
Layer 1: boot.md (~45 lines)              ← always loaded
Layer 2: phases/phase-N.md (~80-120 lines) ← one per phase, load on demand
Layer 3: task-templates/ (~25-30 lines)    ← sub-agent prompts, dynamically filled
```

**Why**: A sub-agent building one page needs ~30 lines of context, not 900. Each layer loads only what's needed for the current task.

### File Structure

```
examples/skills/
├── interactive.md         ← Interactive mode entry point (human + AI)
├── boot.md                ← Automated mode entry point (phase-driven build)
├── phases/                ← Layer 2: self-contained phase instructions
│   ├── phase-0-init.md
│   ├── phase-1-data.md
│   ├── phase-2-fields.md
│   ├── phase-3-pages.md        ← layout patterns + XML tag reference
│   ├── phase-3b-forms.md       ← form DSL + detail JSON format
│   ├── phase-4-js.md           ← JS sandbox + code rules + API reference
│   ├── phase-5-workflows.md
│   ├── phase-6-ai.md
│   └── phase-7-verify.md
├── task-templates/        ← Layer 3: sub-agent dispatch templates
│   ├── task-page-build.md
│   ├── task-form-refine.md
│   ├── task-js-implement.md
│   └── task-workflow.md
├── knowledge/             ← deep reference, read on demand
│   ├── nocobase-concepts.md  ← platform architecture & core concepts
│   └── troubleshooting.md    ← debug common issues
├── templates/             ← code templates, read on demand per phase
│   ├── js/index.md
│   ├── pages/index.md
│   └── workflows/index.md
└── notes.md               ← shared state across all agents
```

## Two Modes

### Interactive Mode (human + AI conversation)
1. AI reads `interactive.md` → understands role as NocoBase expert
2. AI reads `knowledge/nocobase-concepts.md` → understands the platform
3. User gives instructions step by step, AI executes with MCP tools
4. AI reads phase/template docs on demand when needed
5. Best for: iterative refinement, learning, custom builds

### Automated Mode (phase-driven build)
1. AI reads `boot.md` → finds current phase in `notes.md` → reads that phase file
2. Executes steps sequentially within each phase
3. When phase completes, reads next phase file
4. Best for: full system builds from requirements docs

### Single Agent (automated)
1. Reads `boot.md` → finds current phase in `notes.md` → reads that phase file
2. Executes steps sequentially within each phase
3. When phase completes, reads next phase file
4. Context: boot.md (~45 lines) + one phase file (~100 lines) = **~145 lines**

### Cluster (Orchestrator + Sub-Agents)
1. Orchestrator reads `boot.md` + current phase file
2. Phase planning step generates task table in `notes.md`
3. For each `[todo]` task, orchestrator fills a task template with concrete values
4. Sub-agent receives only the filled template (~30 lines) — no boot.md, no phase file
5. Sub-agent does ONE thing, writes result to `notes.md`, stops
6. Orchestrator checks all tasks, handles `[fail]`, advances phase

### Resume After Interruption
1. Read `notes.md` → find `## Status` → find first `[todo]` in task table
2. Continue from there. Do not re-execute `[done]` tasks.

## Phase Flow

```
Phase 0 → 1 → 2 → 3 → 3B → ┬─ 4 (JS)
                              ├─ 5 (Workflows)    → 7
                              └─ 6 (AI Employees)
```

Phases 4, 5, 6 are independent and can run in parallel.

## Requirements & Workdir

| File | Purpose |
|------|---------|
| `*-requirements.md` | Primary input — user personas, "用户关注", UX expectations |
| `*.txt` | Quick reference — tables, fields, enums, relations |
| `*.html` | Optional — HTML prototypes for visual targets |
| `design-notes.md` | Optional — UX patterns from prototypes |
| `notes.md` | State: progress, task tables, UIDs, field names, enum values |
