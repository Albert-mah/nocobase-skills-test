# NocoBase MCP Skills

Let AI agents (Claude Code, etc.) operate NocoBase directly — data modeling, page building, workflow creation, and AI employee management through MCP tools, guided by Skills.

## Architecture

```
┌────────────────────────────────────────────────┐
│                  AI Agent                       │
│  ┌────────────┐    ┌─────────────────────────┐ │
│  │  Skills     │    │      MCP Server         │ │
│  │ (Knowledge) │───>│      (Capability)       │ │
│  │             │    │                         │ │
│  │ data-       │    │ nb_execute_sql          │ │
│  │ modeling    │    │ nb_register_collection  │ │
│  │             │    │ nb_table_block          │ │
│  │ page-       │    │ nb_addnew_form          │ │
│  │ building    │    │ nb_set_layout           │ │
│  │             │    │ ...41 tools             │ │
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

- **MCP Server** = Capability layer — 41 atomic API tools
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

## MCP Tools (41)

### Data Modeling (7)
| Tool | Description |
|------|-------------|
| `nb_execute_sql` | Execute SQL against PostgreSQL |
| `nb_register_collection` | Register DB table as NocoBase collection |
| `nb_sync_fields` | Sync DB columns + create system fields |
| `nb_upgrade_field` | Change field interface (input → select, etc.) |
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

### Page Building (11)
| Tool | Description |
|------|-------------|
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

### Page Maintenance (9)
| Tool | Description |
|------|-------------|
| `nb_show_page` | Show page structure tree |
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

### Outline/Event (2)
| Tool | Description |
|------|-------------|
| `nb_outline` | Create planning placeholder block |
| `nb_event_flow` | Add form event flow (formValuesChange) |

## Skills

| Skill | Description |
|-------|-------------|
| `nocobase-data-modeling` | 7-step workflow: SQL → register → sync → upgrade → relations → data |
| `nocobase-page-building` | Page construction: menu → layout → table → filter → KPI → form → popup → JS |
| `nocobase-ai-employee` | AI employee CRUD + page integration (shortcuts + buttons) |

## Example: Asset Management Demo

A complete enterprise asset management system in `examples/asset-management/`:

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
