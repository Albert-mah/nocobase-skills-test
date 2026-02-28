# NocoBase System Build

Use MCP tools from the `nocobase` server. Key batch tools:
- `nb_clean_prefix()` — clean up leftover tables/collections before rebuilding
- `nb_setup_collection()` — ONE call per table (register + sync + upgrade fields + relations). Idempotent — always call it for every table.
- `nb_crud_page()` — ONE call per page (layout + KPIs + filter + table + forms + popup)
- `nb_execute_sql()` — bulk DDL and DML. System columns (createdAt, updatedAt, etc.) are added automatically on CREATE TABLE.
- `nb_execute_sql_file()` — execute SQL from a local file (for large scripts)
- `nb_create_menu()` — create group + pages in one call

## JS Enhancement Tools

After building CRUD pages, use these tools to add rich frontend behavior:

- `nb_outline(parent, title, ctx_info, kind)` — **plan** a JS enhancement without writing code. Creates a visible placeholder card for later implementation by a JS agent. Kinds: `"block"` (chart/KPI), `"column"` (status tag, money format), `"item"` (form event/calc).
- `nb_js_column(table_uid, title, code)` — add a custom-rendered table column (status badges, ¥ formatting, countdown, progress bars). Code has access to `ctx.record`, `ctx.React`, `ctx.antd`.
- `nb_js_block(parent, title, code)` — add a custom block (charts, dashboards, rich KPI cards). Code has access to `ctx.React`, `ctx.antd`, `ctx.api`, `ctx.render()`.
- `nb_event_flow(model_uid, event_name, code)` — attach form logic (auto-calculate, auto-fill, validation). Events: `formValuesChange`, `beforeSubmit`, `afterSubmit`. Code has access to `ctx.form`, `ctx.model`.

### When to use outline vs direct JS

- Use `nb_outline()` when you want to **plan** the enhancement for a separate JS agent to implement later
- Use `nb_js_column()` / `nb_js_block()` / `nb_event_flow()` when you want to **implement** the enhancement now

## Critical Rules
1. Do NOT include created_at, updated_at, created_by_id, updated_by_id columns in SQL DDL — they are added automatically by nb_execute_sql
2. Use CREATE TABLE IF NOT EXISTS to avoid errors on re-runs
3. If nb_crud_page fails, DO NOT rebuild with individual tools. Fix the error and retry nb_crud_page.
4. Parent tables before child tables (FK order)
5. Write progress to ./notes.md after each phase
6. form_fields is a DSL string (not JSON): "--- Section\nfield1* | field2\nfield3"
7. table_fields is a JSON array: '["name","code","status","createdAt"]' — always include "createdAt"
8. kpis_json format: '[{"title":"Total"},{"title":"Active","filter":{"status":"active"},"color":"#52c41a"}]'
9. detail_json tabs: '[{"title":"Details","fields":"name | code\nstatus"},{"title":"Items","assoc":"items","coll":"child_coll","fields":["f1","f2"]}]'
10. For large INSERT data: split into one call per table (max ~20 rows per call), or write SQL to a local .sql file and use nb_execute_sql_file()
11. If a tool fails, note the error in notes.md and try an alternative approach
