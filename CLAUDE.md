# NocoBase MCP Skills — Agent Instructions

## What This Repo Does

This repo lets AI agents operate NocoBase through MCP tools + Skills knowledge.
- **MCP Server** (mcp-server/) — 48 atomic API tools
- **Skills** (skills/) — workflow guides for data modeling, page building, AI employees
- **Examples** (examples/) — complete demo systems with scripts

## Quick Start for Agents

### 1. Check NocoBase Environment

Before any NocoBase operation, verify the environment:
```bash
curl -s http://localhost:14000/api/app:getLang | head -c 50
```

If this fails, the user needs to set up NocoBase first. Ask them:
> "NocoBase is not running. Would you like me to help set up a Docker environment?"

Then follow the Docker setup in README.md.

### 2. Environment Variables

All scripts use these env vars (with defaults):
- `NB_URL` — NocoBase URL (default: `http://localhost:14000`)
- `NB_USER` — Login email (default: `admin@nocobase.com`)
- `NB_PASSWORD` — Login password (default: `admin123`)
- `NB_DB_URL` — PostgreSQL URL (default: `postgresql://nocobase:nocobase@localhost:5435/nocobase`)

### 3. MCP Server Setup

```bash
cd mcp-server
pip install -e .
```

Configure `.mcp.json` in your project (see `.mcp.json.example`).

### 4. Skills

Skills are knowledge files that guide AI to use MCP tools correctly:
- `skills/nocobase-data-modeling/skill.md` — SQL → register → sync → upgrade → relations
- `skills/nocobase-page-building/skill.md` — menu → layout → blocks → forms → popups
- `skills/nocobase-workflow/skill.md` — Workflow triggers, conditions, data ops, scheduling
- `skills/nocobase-ai-employee/skill.md` — AI employee CRUD + page integration

## Running the Asset Management Demo

The AM demo in `examples/asset-management/` is a complete reference implementation.

**Full rebuild pipeline** (in order):
```bash
cd examples/asset-management

# Step 1: Data modeling (23 tables)
python3 nb-am-setup.py --drop

# Step 2: Field upgrades (44 enum fields)
python3 nb-am-field-upgrade.py

# Step 3: Page building (20 pages, ~2000 nodes)
python3 nb-am-pages.py

# Step 4: Workflows (13 automated workflows)
python3 nb-am-workflows.py

# Step 5: Event flows (27 form calculations)
python3 nb-am-events.py

# Step 6: JS columns (21 status tags + KPI cards)
python3 nb-am-js-blocks.py

# Step 7: AI employees (4 chatbot assistants)
python3 nb-am-ai-employees.py

# Step 8: Seed data (102 test records)
python3 nb-am-seed-data.py
```

Each step is idempotent and can be re-run safely.

## Critical API Patterns

### FlowModel API is Full Replace
`flowModels:update` does **full replace**, not incremental merge.
Always: GET → deep merge → PUT. Never send partial data.

### SQL + API Hybrid
- SQL for bulk table/column creation (fast)
- API for metadata: collection registration, field interface upgrades, UI configuration

### Route Types
- **Group** (folder): `nb_create_group()` — sidebar folder, NO content
- **Page**: `nb_create_page()` — actual content (tables, forms, etc.)
- Groups contain pages. Pages cannot contain pages.

## File Reference

| Path | Purpose |
|------|---------|
| `mcp-server/` | MCP server with 41 tools |
| `skills/` | 3 skill knowledge files |
| `examples/asset-management/` | Complete AM demo (8 scripts) |
| `examples/asset-management/nb_page_builder.py` | Reusable page builder library |
| `examples/asset-management/nb_workflow_builder.py` | Reusable workflow builder library |
| `examples/asset-management/nb-setup.py` | Base NocoBase client + collection tools |
| `docs/api-patterns.md` | API research notes |
