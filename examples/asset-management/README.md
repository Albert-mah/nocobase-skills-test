# Asset Management Demo

A complete enterprise asset management system built entirely through NocoBase MCP tools.

## What's Included

- **23 tables** across 4 modules (base data, fixed assets, consumables, vehicles)
- **20 pages** with KPIs, tables, forms, 12 detail popups
- **13 workflows** (auto-numbering, status sync, inventory alerts, etc.)
- **27 event flows** (form calculations, auto-fill)
- **21 JS columns** (status tags, money formatting, date countdown)
- **4 AI employees** with page integration (47 FlowModel nodes)
- **102 rows** seed data covering all tables

## Prerequisites

1. NocoBase running (see main README for Docker setup)
2. Python 3.10+
3. `requests` and `psycopg2-binary` packages:
   ```bash
   pip install requests psycopg2-binary
   ```

## Run the Demo

Execute scripts in order:

```bash
# Step 1: Create 23 tables + register + sync + relations
python3 nb-am-setup.py --drop

# Step 2: Upgrade 44 enum fields (input → select/multipleSelect)
python3 nb-am-field-upgrade.py

# Step 3: Build 20 pages (~2000 FlowModel nodes)
python3 nb-am-pages.py

# Step 4: Create 13 automated workflows
python3 nb-am-workflows.py

# Step 5: Add 27 form event flows
python3 nb-am-events.py

# Step 6: Add 21 JS status columns + KPI cards
python3 nb-am-js-blocks.py

# Step 7: Create 4 AI employees + page shortcuts/buttons
python3 nb-am-ai-employees.py

# Step 8: Insert 102 test data records
python3 nb-am-seed-data.py
```

## Clean & Rebuild

```bash
# Clean workflows and AI employees first
python3 nb-am-workflows.py clean
python3 nb-am-ai-employees.py clean

# Delete the top-level route group in NocoBase UI
# Or find and delete via: nb_list_routes → nb_delete_route

# Rebuild tables (--drop recreates, --skip-data skips seed)
python3 nb-am-setup.py --drop --skip-data

# Then re-run steps 2-8
```

## Module Structure

### M1: Base Data (4 tables)
- Companies, Departments, Locations, Suppliers

### M2: Fixed Assets (7 tables)
- Assets, Categories, Purchase Requests, Transfers, Repairs, Disposals, Inventories

### M3: Consumables (4 tables)
- Consumables, Consumable Categories, Consumable Requests, Stock Records

### M4: Vehicles (8 tables)
- Vehicles, Vehicle Categories, Insurance, Drivers, Vehicle Requests, Trips, Maintenance, Costs

## Key Files

| File | Purpose |
|------|---------|
| `nb-am-setup.py` | Data modeling: 23 tables with SQL + API registration |
| `nb-am-field-upgrade.py` | Upgrade 44 fields from input to select/enum |
| `nb-am-pages.py` | Build 20 pages with full UI (tables, forms, popups, KPIs) |
| `nb-am-workflows.py` | 13 business workflows (auto-numbering, alerts, etc.) |
| `nb-am-events.py` | 27 form event flows (calculations, auto-fill) |
| `nb-am-js-blocks.py` | 21 JS columns + KPI cards (dynamic discovery) |
| `nb-am-ai-employees.py` | 4 AI chatbot employees + page integration |
| `nb-am-seed-data.py` | 102 test records across all tables |
| `nb-am-testdata.sql` | Raw SQL for test data (alternative to Python script) |
| `nb_page_builder.py` | Reusable FlowPage builder library |
| `nb_workflow_builder.py` | Reusable workflow builder library |
| `nb-setup.py` | Base NocoBase client + collection registration tools |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NB_URL` | `http://localhost:14000` | NocoBase URL |
| `NB_USER` | `admin@nocobase.com` | Login email |
| `NB_PASSWORD` | `admin123` | Login password |
| `NB_DB_URL` | `postgresql://nocobase:nocobase@localhost:5435/nocobase` | PostgreSQL direct URL |
