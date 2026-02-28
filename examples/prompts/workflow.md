# HTML-First Build Workflow

Three-stage pipeline for building rich NocoBase systems.

## Overview

```
Stage 1: Design          Stage 2: Build           Stage 3: Enhance
───────────────────      ───────────────────      ───────────────────
Business Requirements    HTML + Data Model        Outlines (from S2)
        ↓                       ↓                       ↓
   AI (any model)         NocoBase Agent           JS Agent
        ↓                       ↓                       ↓
   HTML Prototypes       CRUD + Outlines          JS Columns/Blocks
   design-notes.md       notes.md (UIDs)          Event Flows
```

## Stage 1: Design (HTML Prototypes)

**Input**: Business requirements (what the system does, who uses it)
**Output**: HTML prototype files + design-notes.md
**Agent**: Any AI, no NocoBase context needed

```bash
# Option A: Let AI design from requirements
claude -p "$(cat design-prompt.md) $(cat itsm-requirements.md)" \
  --model sonnet --max-turns 30

# Option B: Write HTML prototypes by hand (or use existing designs)
```

The AI designs as a frontend developer — naturally produces rich UX:
- Status badges with colors
- Money formatting (¥)
- Date countdown (warranty expiry, SLA)
- Progress bars (usage rate)
- Auto-fill logic (current user, cascading selects)
- Charts and visualizations

### Key Output: design-notes.md

This file summarizes all UX patterns, making it machine-readable for Stage 2:
- Which columns have special rendering (badges, money, countdown)
- Which forms have auto-fill/auto-calc logic
- Which pages have charts or visualizations
- Color schemes for all status/priority fields

## Stage 2: Build (NocoBase CRUD + Outlines)

**Input**: HTML prototypes + design-notes.md + data model definition
**Output**: Working CRUD system + outline placeholders for JS enhancements
**Agent**: NocoBase agent with MCP tools

```bash
cd /tmp/build-itsm
# Copy: .mcp.json, CLAUDE.md, prompt.txt, *.html, design-notes.md
claude -p "$(cat prompt.txt)" --model sonnet --max-turns 100
```

The agent:
1. Creates tables (nb_execute_sql) + registers collections (nb_setup_collection)
2. Inserts test data
3. Builds pages (nb_crud_page) — KPIs, filter, table, forms, detail popups
4. Creates outlines (nb_outline) for each JS enhancement noted in design-notes.md
5. Creates workflows (auto-numbering, status sync)
6. Creates AI employees

### Key Output: notes.md

Contains outline UIDs and their context, e.g.:
```
## Outlines Created
- IT资产/状态标签 (column) uid=xxx: status-tag colors
- IT资产/采购价 (column) uid=yyy: money-format ¥
- 事件管理/优先级 (column) uid=zzz: priority-badge P1-P4
- 事件管理/报告人 (item) uid=aaa: auto-fill currentUser
...
Total: 24 outlines (15 columns, 6 items, 3 blocks)
```

## Stage 3: Enhance (JS Implementation)

**Input**: Outline UIDs + original HTML prototypes (for visual reference)
**Output**: JS columns, JS blocks, event flows replacing outlines
**Agent**: JS-focused agent

```bash
# TODO: Stage 3 prompt not yet designed
# The JS agent reads outlines via nb_inspect_page, then implements each one
# using nb_js_column, nb_js_block, nb_event_flow
```

## Directory Structure

```
/tmp/build-itsm/
├── .mcp.json              # MCP server config
├── CLAUDE.md              # Agent instructions (with outline + JS tools)
├── prompt.txt             # Stage 2 build prompt (data model + HTML refs)
├── itsm-requirements.md   # Stage 1 input (optional, for re-design)
├── design-prompt.md       # Stage 1 prompt template
├── design-notes.md        # Stage 1 output (UX patterns summary)
├── 01-it-assets.html      # Stage 1 output (HTML prototype)
├── 02-incidents.html      # Stage 1 output
├── 03-changes.html        # Stage 1 output
├── 04-software.html       # Stage 1 output
├── notes.md               # Stage 2 output (progress + outline UIDs)
└── build.log              # Agent execution log
```

## Benefits Over DSL-Style Prompts

| Aspect | Old (cols/form DSL) | New (HTML-first) |
|--------|---------------------|-------------------|
| AI thinking mode | Database admin | Frontend designer |
| UX richness | Zero JS enhancements | Badges, charts, auto-calc planned |
| Design review | Read DSL text | Open HTML in browser |
| Separation | Design + impl mixed | Design → Build → Enhance |
| JS planning | Not planned | Outlines mark every JS point |
| Reusability | Prompt = one-shot | HTML = reusable design spec |
