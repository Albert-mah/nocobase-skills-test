# NocoBase MCP Skills

Let AI agents (Claude Code, etc.) operate NocoBase directly — data modeling, page building, workflow creation, and AI employee management through MCP tools, guided by Skills. Agents can autonomously build complete business systems from a single prompt.

## Architecture

```
┌────────────────────────────────────────────────┐
│                  AI Agent                       │
│  ┌────────────┐    ┌─────────────────────────┐ │
│  │  Skills     │    │      MCP Server         │ │
│  │ (Knowledge) │───>│      (Capability)       │ │
│  │             │    │                         │ │
│  │ data-       │    │ nb_setup_collection     │ │
│  │ modeling    │    │ nb_crud_page            │ │
│  │             │    │ nb_create_workflow      │ │
│  │ page-       │    │ nb_create_ai_employee   │ │
│  │ building    │    │ nb_inspect_all          │ │
│  │             │    │ ...55 tools             │ │
│  │ ai-employee │    │                         │ │
│  └────────────┘    └───────────┬──────────────┘ │
└────────────────────────────────┼────────────────┘
                                 │ HTTP API
                      ┌──────────▼──────────┐
                      │     NocoBase         │
                      │  (Docker or local)   │
                      │  ┌──────────────┐   │
                      │  │  FlowModel   │   │
                      │  │  API         │   │
                      │  └──────────────┘   │
                      │  ┌──────────────┐   │
                      │  │  PostgreSQL  │   │
                      │  └──────────────┘   │
                      └─────────────────────┘
```

- **MCP Server** = Capability layer — 55 API tools (atomic + batch)
- **Skills** = Knowledge layer — guide AI to use tools in correct workflow order
- **Examples** = Reference implementations — complete demo systems with scripts

## Prerequisites: NocoBase Environment

> **If you don't have NocoBase running**, follow the Docker setup below first.

### Docker Quick Start (Recommended)

```bash
# Create project directory
mkdir nocobase-app && cd nocobase-app

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3'
services:
  app:
    image: nocobase/nocobase:latest
    ports:
      - "14000:80"
    environment:
      - APP_KEY=your-secret-key-change-this
      - DB_DIALECT=postgres
      - DB_HOST=db
      - DB_PORT=5432
      - DB_DATABASE=nocobase
      - DB_USER=nocobase
      - DB_PASSWORD=nocobase
    depends_on:
      - db
    volumes:
      - app-storage:/app/storage
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: nocobase
      POSTGRES_PASSWORD: nocobase
      POSTGRES_DB: nocobase
    ports:
      - "5435:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
volumes:
  app-storage:
  db-data:
EOF

# Start NocoBase
docker compose up -d

# Wait for initialization (first boot takes ~2 minutes)
echo "Waiting for NocoBase to start..."
until curl -s http://localhost:14000/api/app:getLang > /dev/null 2>&1; do
  sleep 5
  echo "  Still starting..."
done
echo "NocoBase is ready at http://localhost:14000"
```

**Default credentials:**
- URL: `http://localhost:14000`
- Email: `admin@nocobase.com`
- Password: `admin123`

### Required Plugins

After first login, enable these plugins in NocoBase admin:
- **AI** — AI employee features (required for ai-employee skill)
- **API keys** — API authentication

### Verify Setup

```bash
# Test API connectivity
curl -s http://localhost:14000/api/app:getLang | head -c 50
# Should return: {"data":{"lang":"en-US",...}}
```

## Quick Start

### 1. Install MCP Server

```bash
cd mcp-server
pip install -e .
# or with uv:
uv pip install -e .
```

### 2. Configure Claude Code

Copy `.mcp.json.example` to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "nocobase": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-server", "nocobase-mcp"],
      "env": {
        "NB_URL": "http://localhost:14000",
        "NB_USER": "admin@nocobase.com",
        "NB_PASSWORD": "admin123",
        "NB_DB_URL": "postgresql://nocobase:nocobase@localhost:5435/nocobase"
      }
    }
  }
}
```

### 3. Add Skills

Copy the `skills/` directory to your project, or symlink it:

```bash
ln -s /path/to/skills ~/.claude/skills/nocobase
```

### 4. Use It

```
You: Create a project management system with projects, tasks, and categories.

Claude: (activates data-modeling skill → executes SQL → registers → syncs → upgrades → relations)

You: Build pages for the project management module.

Claude: (activates page-building skill → creates menu → builds each page with tables, forms, KPIs, popups)
```

## MCP Tools (55)

### Data Modeling (10)
| Tool | Description |
|------|-------------|
| `nb_setup_collection` | **Batch**: register + sync + upgrade + relations in one call (idempotent) |
| `nb_execute_sql` | Execute SQL against PostgreSQL (auto-adds system columns on CREATE TABLE) |
| `nb_execute_sql_file` | Execute SQL from a local file (for large scripts) |
| `nb_clean_prefix` | Delete all collections + tables matching a prefix (for clean rebuilds) |
| `nb_register_collection` | Register DB table as NocoBase collection |
| `nb_sync_fields` | Sync DB columns + create system fields (debounced) |
| `nb_upgrade_field` | Change field interface (input -> select, etc.) |
| `nb_create_relation` | Create m2o/o2m/m2m/o2o relation |
| `nb_list_collections` | List registered collections |
| `nb_list_fields` | List fields of a collection |

### Routes/Menu (5)
| Tool | Description |
|------|-------------|
| `nb_create_group` | Create sidebar folder |
| `nb_create_page` | Create page with tab(s) |
| `nb_create_menu` | Create group + pages in one call |
| `nb_list_routes` | Show menu tree |
| `nb_delete_route` | Delete menu item |

### Page Building (14)
| Tool | Description |
|------|-------------|
| `nb_crud_page` | **Batch**: complete CRUD page (KPI + filter + table + forms + popup) in one call |
| `nb_page_layout` | Initialize page grid (idempotent) |
| `nb_table_block` | Create data table |
| `nb_addnew_form` | Create "Add New" form |
| `nb_edit_action` | Create "Edit" action |
| `nb_detail_popup` | Create detail popup with tabs |
| `nb_filter_form` | Create search/filter bar |
| `nb_kpi_block` | Create KPI statistic card |
| `nb_js_block` | Create custom JS block |
| `nb_js_column` | Create custom JS table column |
| `nb_set_layout` | Arrange blocks in grid |
| `nb_clean_tab` | Clear page content |
| `nb_outline` | Create planning placeholder block |
| `nb_event_flow` | Add form event flow (formValuesChange) |

### Page Inspection & Maintenance (12)
| Tool | Description |
|------|-------------|
| `nb_inspect_page` | Visual layout summary of a page |
| `nb_inspect_all` | Batch inspect all pages (with optional prefix filter) |
| `nb_show_page` | Show page structure tree |
| `nb_read_node` | Read full node config (events, JS, linkage) |
| `nb_locate_node` | Find block/field UID |
| `nb_patch_field` | Modify form field properties |
| `nb_patch_column` | Modify table column properties |
| `nb_add_field` | Add field to form |
| `nb_remove_field` | Remove field from form |
| `nb_add_column` | Add column to table |
| `nb_remove_column` | Remove column from table |
| `nb_list_pages` | List all pages |

### AI Employee (7)
| Tool | Description |
|------|-------------|
| `nb_create_ai_employee` | Create AI chatbot assistant |
| `nb_list_ai_employees` | List AI employees |
| `nb_get_ai_employee` | Get AI employee details |
| `nb_update_ai_employee` | Update AI employee config |
| `nb_delete_ai_employee` | Delete AI employee |
| `nb_ai_shortcut` | Add floating avatar to page |
| `nb_ai_button` | Add AI button to table action bar |

### Workflow (7)
| Tool | Description |
|------|-------------|
| `nb_create_workflow` | Create workflow with trigger (collection/schedule/action) |
| `nb_add_node` | Add node (condition/update/create/query/sql/request/loop/end) |
| `nb_enable_workflow` | Enable or disable a workflow |
| `nb_list_workflows` | List workflows with optional filtering |
| `nb_get_workflow` | Get workflow details including nodes |
| `nb_delete_workflow` | Delete a workflow |
| `nb_delete_workflows_by_prefix` | Batch delete by title prefix |

## Skills

| Skill | Description |
|-------|-------------|
| `nocobase-data-modeling` | 7-step workflow: SQL → register → sync → upgrade → relations → data |
| `nocobase-page-building` | Page construction: menu → layout → table → filter → KPI → form → popup → JS |
| `nocobase-workflow` | Workflow automation: triggers → conditions → data operations → SQL → scheduling |
| `nocobase-ai-employee` | AI employee CRUD + page integration (shortcuts + buttons) |

## Scripted Demo: Asset Management

A hand-crafted reference implementation in `examples/asset-management/`:

- **23 tables** across 4 modules (base data, fixed assets, consumables, vehicles)
- **20 pages** with KPIs, tables, forms, 12 detail popups
- **13 workflows** (auto-numbering, status sync, inventory alerts, etc.)
- **27 event flows** (form calculations, auto-fill)
- **21 JS columns** (status tags, money formatting, date countdown)
- **4 AI employees** with page integration (47 FlowModel nodes)
- **102 rows** seed data covering all tables

### Run the Demo

```bash
cd examples/asset-management

# Step 1: Create tables + register + sync + upgrade + relations
python3 nb-am-setup.py --drop

# Step 2: Ensure all enum fields are correct
python3 nb-am-field-upgrade.py

# Step 3: Build all 20 pages
python3 nb-am-pages.py

# Step 4: Create 13 workflows
python3 nb-am-workflows.py

# Step 5: Add form event flows
python3 nb-am-events.py

# Step 6: Add JS status columns
python3 nb-am-js-blocks.py

# Step 7: Create AI employees + page integration
python3 nb-am-ai-employees.py

# Step 8: Insert test data
python3 nb-am-seed-data.py
```

### Clean & Rebuild

```bash
# Clean workflows, AI employees, then rebuild
python3 nb-am-workflows.py clean
python3 nb-am-ai-employees.py clean
# Delete top-level route group in NocoBase UI or via API
python3 nb-am-setup.py --drop --skip-data
# Then re-run steps 2-8
```

## Agent-Built Demo Systems

Beyond the scripted demo above, AI agents can autonomously build complete business systems from a single prompt file. The prompt defines the data model, pages, workflows, and AI employees — the agent figures out all tool calls on its own. This tests real agent capability, not script execution.

Tested systems (each built by a single Claude agent session):

| System | Tables | Pages | Workflows | AI Employees |
|--------|--------|-------|-----------|--------------|
| CRM (客户关系管理) | 16 | 12 | 6 | 3 |
| HRM (人力资源管理) | 14 | 10 | 5 | 2 |
| EDU (教务管理) | 13 | 12 | 5 | 2 |
| ITSM (IT服务管理) | 13 | 10 | 5 | 2 |
| WMS (仓储管理) | 14 | 12 | 5 | 2 |

### Run an Agent Build

```bash
# 1. Create a build directory with prompt and MCP config
mkdir /tmp/build-crm && cd /tmp/build-crm
cp /path/to/prompts/crm-prompt.txt prompt.txt
cp /path/to/.mcp.json .mcp.json

# 2. Launch agent to build autonomously
claude -p "$(cat prompt.txt)" --model sonnet --max-turns 80 --dangerously-skip-permissions
```

The agent reads the prompt, creates all tables via `nb_setup_collection`, builds pages via `nb_crud_page`, adds workflows via `nb_create_workflow` + `nb_add_node`, and creates AI employees — typically completing in 60-80 tool calls.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NB_URL` | `http://localhost:14000` | NocoBase URL |
| `NB_USER` | `admin@nocobase.com` | Login email |
| `NB_PASSWORD` | `admin123` | Login password |
| `NB_DB_URL` | `postgresql://nocobase:nocobase@localhost:5435/nocobase` | PostgreSQL URL |

## Development

```bash
cd mcp-server
pip install -e ".[dev]"
nocobase-mcp  # starts MCP server on stdio
```

## License

MIT
