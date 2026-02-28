# NocoBase System Build

Use MCP tools from the `nocobase` server. Key batch tools:
- `nb_clean_prefix()` — clean up leftover tables/collections before rebuilding
- `nb_setup_collection()` — ONE call per table (register + sync + upgrade fields + relations). Idempotent — always call it for every table.
- `nb_crud_page()` — ONE call per page (layout + KPIs + filter + table + forms + popup)
- `nb_execute_sql()` — bulk DDL and DML. System columns (createdAt, updatedAt, etc.) are added automatically on CREATE TABLE.
- `nb_execute_sql_file()` — execute SQL from a local file (for large scripts)
- `nb_create_menu()` — create group + pages in one call

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
