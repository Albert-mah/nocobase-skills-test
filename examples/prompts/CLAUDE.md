# NocoBase System Build

Use MCP tools from the `nocobase` server. Key batch tools:
- `nb_clean_prefix()` — clean up leftover tables/collections/workflows before rebuilding. Also delete the old menu group route manually if it exists.
- `nb_setup_collection()` — ONE call per table (register + sync + upgrade fields + relations). Idempotent — always call it for every table.
- `nb_crud_page()` — ONE call per page (layout + KPIs + filter + table + forms + popup). Returns JSON with `table_uid`, `create_form`, `edit_form` UIDs. Supports `sidebar_outlines` for Dashboard-style layout.
- **`nb_crud_page_file(file_path)`** — build MULTIPLE pages from a JSON file. **PREFERRED over nb_crud_page** when building 3+ pages — avoids tool-call parameter limits. Write a JSON array of page definitions to a file, then call once. Each page can include `sidebar_outlines` for rich layout.
- `nb_fields(collection_name)` — show all available fields for a collection. Use BEFORE building forms/tables to verify field names.
- `nb_execute_sql()` — bulk DDL and DML. System columns (createdAt, updatedAt, etc.) are added automatically on CREATE TABLE.
- `nb_execute_sql_file()` — execute SQL from a local file (for large scripts)
- `nb_create_menu()` — create group + pages in one call

## Build Mode Detection

Check your working directory at startup:

- **HTML-First mode**: If `*.html` files + `design-notes.md` exist → use outline workflow (Phase 3 = CRUD + `nb_outline`, no direct JS). A separate JS agent will implement later.
- **Classic mode**: If no HTML files → use 6-phase workflow (Phase 6 = direct JS implementation).

The rest of this document applies to both modes. Differences are noted in each section.

## Field Validation

The tools have built-in field validation. When you use `nb_crud_page`, it will **warn** (not block) if a field name doesn't exist in the collection. Use this workflow:

1. **Before building forms/tables**: Call `nb_fields("collection_name")` to see all available field names and types
2. **Use exact field names** from `nb_fields` output — don't guess from the prompt description
3. **Check warnings** in `nb_crud_page` result — if you see "field not found" warnings, fix the field names and rebuild

## JS Enhancement — Principles

After building CRUD pages, enhance the system with rich frontend behavior. **Built-in NocoBase blocks always take priority over custom JS.** Only use JS when built-in blocks cannot achieve the desired result.

### When to use built-in vs JS

| Need | Use |
|------|-----|
| List/filter/sort records | Built-in TableBlockModel (already in nb_crud_page) |
| Show record details | Built-in DetailsBlockModel (already in nb_crud_page detail_json) |
| Create/edit forms | Built-in CreateFormModel/EditFormModel (already in nb_crud_page) |
| Sub-tables in detail popup | Built-in: add assoc tab in detail_json |
| Status color tags in table | JS column: `nb_js_column` |
| Money/date formatting in table | JS column: `nb_js_column` |
| Business dashboard / multi-metric summary | JS block: `nb_js_block` |
| Cross-collection aggregation / charts | JS block: `nb_js_block` (API + antd rendering) |
| Auto-fill / auto-calculate in forms | Event flow: `nb_event_flow` |

### JS Tools

- `nb_js_column(table_uid, title, code)` — custom-rendered table column
- `nb_js_block(parent, title, code)` — custom block (dashboards, charts, summary cards)
- `nb_event_flow(model_uid, event_name, code)` — form logic (auto-calc, auto-fill, validation)
- `nb_outline(parent, title, ctx_info, kind)` — planning placeholder for JS (used in HTML-First mode)

### nb_outline — Planning Placeholders (HTML-First Mode)

In HTML-First mode, **do NOT write JS code directly**. Instead, create outlines that describe what the JS should do. A dedicated JS agent will implement them later.

```
nb_outline(parent, title, ctx_info, kind)
  parent:   table_uid (column) | grid_uid (block) | form_grid_uid (item)
  title:    display name (e.g., "状态标签", "金额格式化")
  ctx_info: JSON string with context: {"type":"status-tag","field":"status","colors":{"active":"green",...}}
  kind:     "column" | "block" | "item"
```

**Common ctx_info types** (read from design-notes.md):

**Block outlines (kind="block") — CREATE THESE FIRST, 1-2 per page group:**

| Pattern | ctx_info Example |
|---------|-----------------|
| Distribution chart | `{"type":"distribution","title":"客户行业分布","collection":"xxx","group_by":"industry","display":"pie"}` |
| Funnel / stages | `{"type":"funnel","title":"商机漏斗","collection":"xxx","stage_field":"stage","stages":["接洽","报价","谈判","赢单"]}` |
| Summary card | `{"type":"summary-card","title":"薪资总览","collection":"xxx","metrics":["base_salary:sum","net_salary:sum"]}` |
| Trend over time | `{"type":"trend","title":"合同趋势","collection":"xxx","value_field":"amount","date_field":"start_date"}` |
| Alert / expiry list | `{"type":"alert-list","title":"即将到期","collection":"xxx","date_field":"end_date","warn_days":90}` |
| Ranking / top-N | `{"type":"ranking","title":"部门TOP5","collection":"xxx","group_by":"dept","metric":"count","limit":5}` |
| KPI dashboard | `{"type":"kpi-dashboard","title":"考勤统计","collection":"xxx","metrics":[{"label":"出勤率","calc":"..."}]}` |

**Column outlines (kind="column"):**

| Pattern | ctx_info Example |
|---------|-----------------|
| Status color tag | `{"type":"status-tag","field":"status","colors":{"在用":"green","闲置":"blue"}}` |
| Money ¥ format | `{"type":"money-format","field":"amount"}` |
| Date countdown | `{"type":"countdown","field":"end_date","warn_days":30}` |
| Progress bar | `{"type":"progress-bar","field":"used","max_field":"total"}` |

**Item outlines (kind="item"):**

| Pattern | ctx_info Example |
|---------|-----------------|
| Auto-fill user | `{"type":"auto-fill","field":"reporter","value":"currentUser.nickname"}` |
| Auto-calculate | `{"type":"auto-calc","formula":"qty*price","target":"total"}` |

**Phase 3 workflow in HTML-First mode**:
1. Read `design-notes.md` for dashboard/chart patterns on each page group
2. Write page JSON with `sidebar_outlines` — include block outlines directly in each page definition for Dashboard-style layout (table span=15, sidebar span=9)
3. Call `nb_crud_page_file(file_path)` once to build all pages with integrated sidebar blocks
4. Create column outlines for status/money/countdown/progress columns (attach to table_uid)
5. Create item outlines for auto-fill/auto-calc form events (attach to create_form/edit_form)
6. Record ALL outline UIDs in notes.md with their ctx_info

**Layout guideline**: Not every page needs sidebar blocks. Use `sidebar_outlines` for main pages in each group (e.g., 客户, 商机, 合同, 工单). Simple CRUD pages (联系人, 知识库, 产品) can skip them.

### JS Sandbox — What You Have

All JS runs in a sandboxed `ctx` object. **No external imports** (no ECharts, no CDN, no require/import).

**Columns & Blocks:**
- `ctx.React` — full React (createElement, useState, useEffect, Fragment, etc.)
- `ctx.antd` — **full Ant Design 5**: Tag, Badge, Progress, Statistic, Card, Row, Col, Space, Table, Descriptions, Alert, Timeline, Steps, Divider, Typography, Avatar, List, Tooltip, Tabs, etc.
- `ctx.api` — `ctx.api.request({url, params, method, data})` to query any collection
- `ctx.render(element)` — **must call exactly once**
- `ctx.record` — current row (in columns only)
- `ctx.themeToken` — antd theme tokens (colorPrimary, colorSuccess, etc.)

**Event Flows:**
- `ctx.form` — Formily form: `.values`, `.setFieldsValue({...})`, `.query('field').take()`
- `ctx.model` — `ctx.model?.currentUser?.nickname` (NOT ctx.currentUser)
- Events: `formValuesChange`, `beforeRender`, `afterSubmit`

### JS Block Design — Rich Business Dashboards

**Don't** just render a single number (e.g. "Total: 42"). That's what KPI blocks in `nb_crud_page` already do.

**Do** create blocks that provide **business insight**. Each block should fetch data via `ctx.api.request()` and render a meaningful visualization. Here are 7 proven patterns — pick the ones that match your system's business logic:

1. **Distribution** — Horizontal bar chart using antd Progress bars. Group records by a field, show count/percentage per group. Good for: industry distribution, status breakdown, category split.
2. **Funnel** — Decreasing-width bars showing stage conversion. Good for: sales pipeline, recruitment stages, ticket resolution flow.
3. **Summary Card** — Row/Col grid of antd Statistic components with calculated totals. Good for: financial summaries (total revenue, average deal size), HR summaries (headcount by status).
4. **Trend** — Group records by month/quarter, show values over time using styled divs or antd Progress. Good for: contract amounts, revenue, hiring pace.
5. **Alert List** — antd List/Table showing records approaching a deadline. Filter by date < today+N. Good for: expiring contracts, overdue tasks, upcoming renewals.
6. **Ranking** — antd Table sorted by a metric, showing top N items. Good for: top customers by revenue, top departments by headcount, best performing sales reps.
7. **KPI Dashboard** — Multi-metric panel combining counts, rates, and comparisons. Goes beyond simple KPI count blocks. Good for: attendance rates, satisfaction scores, achievement percentages.

**Key constraints:**
- No ECharts / external charting libs — use antd Progress, div-width percentages, or colored segments
- No GROUP BY in NocoBase list API — use `paginate: false` to fetch all, then aggregate in JS
- API calls are async — wrap in `(async () => { ... })()` and use `ctx.render()` after data is ready
- For related data: `appends: ['relation_name']` in API params

### Event Flow: Getting the right model_uid

`nb_event_flow` must target a **CreateFormModel** or **EditFormModel** UID (not an action UID).

Get these from `nb_crud_page` result:
```
result = nb_crud_page(...)
# result["create_form"] → UID for AddNew form events
# result["edit_form"]   → UID for Edit form events
```

Record these UIDs in notes.md after each `nb_crud_page` call so you can use them in Phase 6.

### JS Code Rules
1. All code must be a **single string** — no ES6 template literals (backticks) inside
2. Always wrap in `(async () => { ... })();` for event flows and async blocks
3. Always null-check: `(ctx.record || {}).fieldName` in columns, `ctx.form?.values || {}` in events
4. `ctx.render()` must be called **exactly once** in columns and blocks
5. No external imports — only ctx.React, ctx.antd, ctx.api

## Critical Rules
1. Do NOT include created_at, updated_at, created_by_id, updated_by_id columns in SQL DDL — they are added automatically by nb_execute_sql
2. Use CREATE TABLE IF NOT EXISTS to avoid errors on re-runs
2b. **Phase 0 — Clean before rebuild**: If the system tables already exist (e.g. rebuilding after a failed round), run `nb_clean_prefix("nb_crm_")` FIRST to drop old tables, collections, routes, and workflows. This prevents duplicate menus, orphan workflows, and stale data.
3. **Prefer `nb_crud_page_file` for building 3+ pages**: write all page definitions to a `.json` file, then call once. This avoids tool-call parameter limits. If nb_crud_page fails with "Invalid arguments", switch to `nb_crud_page_file` immediately — do NOT fall back to individual tools (nb_page_layout, nb_kpi_block, etc.) as they create orphaned nodes.
4. Parent tables before child tables (FK order)
5. Write progress to ./notes.md after each phase
6. form_fields is a DSL string (not JSON): "--- Section\nfield1* | field2\nfield3"
7. table_fields is a JSON array: '["name","code","status","createdAt"]' — always include "createdAt"
8. kpis_json format: '[{"title":"Total"},{"title":"Active","filter":{"status":"active"},"color":"#52c41a"}]'
9. detail_json tabs: '[{"title":"Details","fields":"name | code\nstatus"},{"title":"Items","assoc":"items","coll":"child_coll","fields":["f1","f2"]}]'
10. For large INSERT data: split into one call per table (max ~20 rows per call), or write SQL to a local .sql file and use nb_execute_sql_file()
11. If a tool fails, note the error in notes.md and try an alternative approach
12. **Before Phase 3 (pages)**: call `nb_fields()` on key collections to verify exact field names exist
13. **After Phase 3**: record `create_form` and `edit_form` UIDs from nb_crud_page results in notes.md for Phase 6
14. **HTML-First mode**: Start from `design-notes.md` (compact summary) for field/rendering rules. You MAY read individual HTML files when you need to understand a specific page's layout structure (e.g., whether blocks go in sidebar, above table, or as 2-column grid). Do NOT read all HTML files at once — read one at a time as needed. If a `Task` tool is available (Kimi subagent system), prefer delegating HTML reading to the `html-analyzer` sub-agent — it returns a concise layout spec without polluting your context. After building pages, create outlines for JS enhancements. Do NOT write JS code — the JS agent handles that in Stage 3.
