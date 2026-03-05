# HTML-First Build Workflow

Three-stage pipeline for building rich NocoBase systems.

## Quick Start

```bash
# 1. Prepare working directory
SYSTEM=crm
WORKDIR=/tmp/build-$SYSTEM
mkdir -p $WORKDIR && cd $WORKDIR

# Copy shared files from examples/prompts/
PROMPTS=/path/to/examples/prompts
cp $PROMPTS/.mcp.json.example .mcp.json
cp $PROMPTS/CLAUDE.md .
cp $PROMPTS/design-prompt.md .
cp $PROMPTS/js-sandbox-reference.md .
cp $PROMPTS/js-enhance-prompt.md .
cp $PROMPTS/${SYSTEM}-requirements.md .
# (Kimi only) Agent config for subagent delegation
cp $PROMPTS/builder-agent.yaml $PROMPTS/html-analyzer-sub.yaml $PROMPTS/html-analyzer-prompt.md .

# 2. Stage 1: Design HTML prototypes
claude -p "$(cat design-prompt.md)

$(cat ${SYSTEM}-requirements.md)" --model sonnet --max-turns 30

# 3. Stage 2: Build NocoBase CRUD + outlines
#    Create prompt.txt with data model + "read *.html and design-notes.md for UX patterns"
claude -p "$(cat prompt.txt)" --model sonnet --max-turns 100

# 4. Stage 3: Implement JS enhancements
claude -p "$(cat js-enhance-prompt.md)

Read notes.md for outline UIDs. Read *.html for visual reference.
Also read js-sandbox-reference.md for code patterns." --model sonnet --max-turns 60
```

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

## Available Requirements

| System | File | Tables | Modules |
|--------|------|--------|---------|
| ITSM | `itsm-requirements.md` | 13 | IT资产/软件许可/事件/问题/变更/服务目录/服务请求/知识库/SLA |
| CRM | `crm-requirements.md` | 16 | 客户管理/销售管理/合同管理/服务支持 |
| HRM | `hrm-requirements.md` | 14 | 组织架构/考勤管理/薪酬福利/招聘培训 |

Each requirements file follows the same format: overview + user personas + modules with field lists + user concerns + interaction expectations + navigation structure.

## Stage 1: Design (HTML Prototypes)

**Input**: Business requirements (what the system does, who uses it)
**Output**: HTML prototype files + design-notes.md
**Agent**: Any AI, no NocoBase context needed

```bash
# Let AI design from requirements
claude -p "$(cat design-prompt.md) $(cat crm-requirements.md)" \
  --model sonnet --max-turns 30
```

The AI designs as a frontend developer — naturally produces rich UX:
- Status badges with colors
- Money formatting (¥)
- Date countdown (warranty expiry, contract end)
- Progress bars (target achievement, usage rate)
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
cd /tmp/build-crm
# prompt.txt should contain data model + instruction to read HTML files
claude -p "$(cat prompt.txt)" --model sonnet --max-turns 100
```

The agent:
1. Creates tables (nb_execute_sql) + registers collections (nb_setup_collection)
2. Inserts test data
3. Builds pages (nb_crud_page) — KPIs, filter, table, forms, detail popups
4. Creates JS placeholders via XML markup for each JS enhancement noted in design-notes.md
5. Creates workflows (auto-numbering, status sync)
6. Creates AI employees

### CLAUDE.md Auto-Detection

The shared `CLAUDE.md` detects HTML-First mode automatically: if `*.html` + `design-notes.md` exist in the working directory, the agent uses outline workflow instead of writing JS directly.

### Key Output: notes.md

Contains outline UIDs and their context, e.g.:
```
## Outlines Created
- 客户/状态标签 (column) uid=xxx: status-tag colors
- 商机/金额格式 (column) uid=yyy: money-format ¥
- 商机/阶段 (column) uid=zzz: status-tag with stage colors
- 商机/概率 (column) uid=aaa: progress-bar
- 工单/报告人 (item) uid=bbb: auto-fill currentUser
...
Total: 30 outlines (20 columns, 6 items, 4 blocks)
```

## Stage 3: Enhance (JS Implementation)

**Input**: Outline UIDs (from notes.md) + HTML prototypes (for visual reference)
**Output**: JS columns, JS blocks, event flows replacing outlines
**Agent**: JS-focused agent with MCP tools

```bash
cd /tmp/build-crm
claude -p "$(cat js-enhance-prompt.md)

Read notes.md for outline UIDs. Read *.html for visual reference.
Also read js-sandbox-reference.md for code patterns." --model sonnet --max-turns 60
```

The agent:
1. Reads notes.md for outline UIDs and their ctx_info descriptions
2. Implements each placeholder using `nb_inject_js(uid, code)` per placeholder
3. Uses HTML prototypes as visual reference for color schemes and rendering

See `js-enhance-prompt.md` for the full prompt template.
See `js-sandbox-reference.md` for all JS code patterns (status tags, money, countdown, charts, etc.).

## Directory Template

```
/tmp/build-{system}/
├── .mcp.json                # MCP server config (copy from .mcp.json.example)
├── CLAUDE.md                # Agent instructions (shared, auto-detects HTML-First mode)
├── {system}-requirements.md # Stage 1 input (business requirements)
├── design-prompt.md         # Stage 1 prompt template
├── design-notes.md          # Stage 1 output (UX patterns summary)
├── 01-{page-name}.html      # Stage 1 output (HTML prototypes)
├── 02-{page-name}.html      # ...
├── prompt.txt               # Stage 2 build prompt (data model + HTML refs)
├── js-enhance-prompt.md     # Stage 3 prompt template
├── js-sandbox-reference.md  # Stage 3 JS code patterns
├── notes.md                 # Stage 2 output (progress + outline UIDs)
├── build.log                # Agent execution log
├── builder-agent.yaml       # (Kimi) Main agent config with subagent
├── html-analyzer-sub.yaml   # (Kimi) HTML analyzer subagent config
└── html-analyzer-prompt.md  # (Kimi) HTML analyzer system prompt
```

## Kimi Agent Variant

For Kimi instead of Claude:

```bash
# Stage 2 (Kimi) — with agent config (recommended)
cd /tmp/build-crm
cp /path/to/examples/prompts/builder-agent.yaml .
cp /path/to/examples/prompts/html-analyzer-sub.yaml .
cp /path/to/examples/prompts/html-analyzer-prompt.md .
kimi --agent-file builder-agent.yaml -w . -p "$(cat prompt.txt)" --yolo --max-steps-per-turn 200

# Stage 2 (Kimi) — without agent config (simpler)
kimi -w . -p "$(cat prompt.txt)" --yolo --max-steps-per-turn 200

# With watchdog for auto-restart
/tmp/kimi-watchdog.sh /tmp/build-crm "$(cat prompt.txt)" /tmp/kimi-crm.log
```

Note: Kimi uses `--max-steps-per-turn` instead of `--max-turns`.

### Kimi Agent Config

The `builder-agent.yaml` enables Kimi's **subagent system** (Ralph mode). The builder agent can delegate HTML analysis to a specialized subagent:

- **builder-agent.yaml** — main agent config, extends default, uses CLAUDE.md as system prompt
- **html-analyzer-sub.yaml** — subagent for reading HTML prototypes and returning structured layout specs
- **html-analyzer-prompt.md** — subagent system prompt (layout analysis rules)

This lets the builder agent delegate HTML reading to a sub-agent, keeping the main context clean for NocoBase tool calls. The sub-agent reads one HTML file at a time and returns a concise layout spec (grid rows, block positions, sidebar vs full-width).

**Kimi config requirement**: Ensure `max_ralph_iterations >= 3` in `~/.kimi/config.toml`:
```toml
[loop_control]
max_ralph_iterations = 3
```

## Test Results

### ITSM End-to-End (2026-03-01)

| Stage | Time | Output |
|-------|------|--------|
| Stage 1: HTML Design | ~30 min | 4 HTML prototypes (665-717 lines each) + design-notes.md |
| Stage 2: NocoBase Build | ~20 min | 13 tables, 148 test rows, 10 pages, 20 outlines, 5 workflows, 2 AI |
| Stage 3: JS Enhance | ~5 min | 15 JS columns + 4 event flows (19/20 implemented) |
| **Total** | **~55 min** | **Complete ITSM with rich UX** |

### CRM Round 8 — Classic Mode (2026-03-02)

| Metric | Result |
|--------|--------|
| Tables | 16 |
| Pages | 15 |
| JS Blocks | 4 (行业分布/阶段漏斗/金额趋势/响应时效) |
| JS Columns | 8 |
| Event Flows | 4 |
| Time | ~28 min |

### Comparison: Classic vs HTML-First

| Aspect | Classic (crm.txt) | HTML-First (pipeline) |
|--------|-------------------|-----------------------|
| AI thinking mode | Database admin | Frontend designer |
| Design review | Read DSL text | Open HTML in browser |
| UX richness | Prompt-dependent | Systematic (design-notes → outlines) |
| Separation | Design + impl mixed | Design → Build → Enhance |
| JS planning | Not planned | Outlines mark every JS point |
| Reusability | Prompt = one-shot | HTML = reusable design spec |
| Stakeholder review | Developer-only | HTML viewable by product/business |
