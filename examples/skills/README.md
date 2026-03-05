# NocoBase Builder — Agent Skill Base

Build a complete NocoBase system from any requirements document. Follow the checklist step-by-step.

## Quick Start

```
1. Read this file                    ← you are here
2. Read requirements (the -requirements.md version, NOT .txt)
3. Read checklist.md                 ← step-by-step with checkboxes
4. Execute each step, mark progress in notes.md
```

## Architecture

```
examples/skills/
├── README.md          ← Entry point (this file)
├── checklist.md       ← Executable checklist — the core
├── coordinator.md     ← Multi-agent coordination patterns (optional)
├── executor.md        ← Minimal sub-agent prompt (optional)
├── knowledge/         ← Skill docs — read on demand per step
│   ├── data-modeling.md      → nb_setup_collection etc.
│   ├── page-building.md      → nb_compose_page etc.
│   ├── js-sandbox.md         → ctx API, antd components
│   ├── workflows.md          → nb_create_workflow etc.
│   └── ai-employees.md       → nb_create_ai_employee etc.
└── templates/         ← Code templates — read & fill on demand
    ├── js/index.md           → 12 JS column/sidebar/event templates
    ├── pages/index.md        → 5 page layout templates
    └── workflows/index.md    → 4 workflow templates
```

## Requirements: Two Formats

| Format | File | Use |
|--------|------|-----|
| **Rich requirements** | `*-requirements.md` | Primary input — has user personas, "用户关注", UX expectations, interaction design |
| **Table list** | `*.txt` | Quick reference — just tables, fields, enums, relations |

**Always use `-requirements.md`** as the primary input. The "用户关注" sections define what each page should look like beyond basic CRUD.

## HTML Prototypes (Optional but Recommended)

If available in workdir:
- `*.html` — visual page prototypes (Tailwind CSS, realistic data)
- `design-notes.md` — structured UX patterns summary

These give agents concrete visual targets: status badges, charts, sidebars, auto-calc, color schemes.
Generated via `examples/prompts/design-prompt.md` → Stage 1.

## How Agents Use This

### Single Agent (no cluster)
1. Read `checklist.md`, execute sequentially
2. Steps marked `[parallel-ok]` — just do them one by one
3. Phase 4 (JS): write each JS piece, deploy, verify, then next

### Cluster Agent (with sub-agents)
1. Read `checklist.md`, dispatch sub-agents where marked
2. **Phase 4 (JS) is the key parallelization point** — dispatch one sub-agent per JS task (column/sidebar/event). Each sub-agent writes code, deploys, and verifies independently.
3. Phase 2 (fields), Phase 5 (workflows), Phase 6 (AI) also parallelize well

### Resume After Interruption
1. Read `notes.md` — find last completed step
2. Continue from next unchecked step
3. All state is in `notes.md`

## Workdir Convention

```
{workdir}/
├── .mcp.json              # MCP server config (required)
├── *-requirements.md      # Input: rich requirements (primary)
├── *.txt                  # Input: table list (quick reference)
├── *.html                 # Optional: HTML prototypes
├── design-notes.md        # Optional: UX patterns from prototypes
├── notes.md               # Progress tracker + shared state
└── pages_batch{N}.json    # Intermediate: page definitions
```

## Template Library

| Category | Index | Count | Description |
|----------|-------|-------|-------------|
| JS Enhancement | `templates/js/index.md` | 22 | Blocks (4), sidebars (3), columns (7), items (3), events (5) |
| Page Layouts | `templates/pages/index.md` | 5 | CRUD patterns (KPI, sidebar, pipeline, simple, dashboard) |
| Workflows | `templates/workflows/index.md` | 4 | Auto-number, status sync, default value, date reminder |

## File Reference

| File | When to Read |
|------|-------------|
| `checklist.md` | Always — your execution guide |
| `knowledge/data-modeling.md` | Phase 1 |
| `knowledge/page-building.md` | Phase 3 — tool reference |
| `templates/pages/index.md` | **Phase 3 — page templates + pattern→template→JS mapping** |
| `templates/js/index.md` | Phase 3 (js_columns) + Phase 4 (blocks, items, events) |
| `knowledge/js-sandbox.md` | Phase 4 |
| `knowledge/workflows.md` | Phase 5 |
| `knowledge/ai-employees.md` | Phase 6 |
| `examples/prompts/design-prompt.md` | Pre-Phase 0 — generate HTML prototypes |
