# JS Templates Index

Each file contains one JS code template with `{PLACEHOLDER}` markers.
Read the template you need, replace placeholders with real values, then call MCP.

## Column Templates — `nb_js_column(table_uid, title, code, width)`

Render custom content per table row. `ctx.record` available.

**Rules:**
- Do NOT use JS columns for select/enum fields (等级/状态/类型/优先级) — NocoBase renders colored tags natively
- DO use JS columns to make tables look **rich and informative**, matching the HTML prototype column designs
- **Read the HTML prototypes** — every `<td>` with nested `<div>` elements = needs a JS column

### ★ col-composite.js — THE primary column template (use on every main entity)

Every business entity's **primary name/title column** should be composite: bold blue title + gray subtitle info.

| Business entity | TITLE field | SUBS fields | Width |
|----------------|-------------|-------------|-------|
| 客户 | `name` | `"city","source"` | 200 |
| 商机 | `title` | `"customer_id"` (or use createdAt) | 200 |
| 合同 | `title` | `"start_date","end_date"` | 200 |
| 线索 | `contact_name` | `"company","position"` | 180 |
| 工单 | `subject` | `"description"` | 220 |
| 员工 | `name` | `"department_id","position"` | 180 |
| 产品 | `name` | `"category","spec"` | 200 |

Placeholders: `{TITLE}` = main field name, `{SUBS}` = JS string: `"field1","field2"` (supports 1-3 sub-fields)

**Example**: 客户名称 → `TITLE=name`, `SUBS="city","source"` → renders: **华为技术有限公司** / 深圳 · 转介绍

### Other column templates

| File | Renders | Use when | Placeholders |
|------|---------|----------|-------------|
| `col-currency.js` | ¥12,345.00 monospace | decimal/金额 fields | `{FIELD}`, `{THRESHOLD}` |
| `col-countdown.js` | "⏱ 还剩12天" / "⚠ 已逾期3天" | date fields + 到期/截止 concept | `{FIELD}` |
| `col-progress.js` | Colored bar + percentage | percentage/达成率/完成率 | `{FIELD}` |
| `col-stars.js` | ★★★★☆ | integer rating/评分/满意度 | `{FIELD}` |
| `col-relative-time.js` | "3小时前" / "2天前" | date + 最近/创建时间 | `{FIELD}` |
| `col-comparison.js` | Target vs actual bar | 目标 vs 实际 comparison | `{TARGET}`, `{ACTUAL}` |

### How to map HTML prototype → JS columns

Read the HTML prototype `<table>` section. For each column:
1. `<td>` with **two nested divs** (bold name + gray info) → `col-composite.js`
2. `<td>` with **¥ + monospace number** → `col-currency.js`
3. `<td>` with **"还剩X天"/"已逾期"** → `col-countdown.js`
4. `<td>` with **progress bar** → `col-progress.js`
5. `<td>` with **"N小时前"/"N天前"** → `col-relative-time.js`
6. `<td>` with **stars** → `col-stars.js`
7. `<td>` with **just a tag/badge** → skip (NocoBase native select rendering)

## Block Templates — `nb_js_block(parent, title, code)`

Page-level blocks: KPI dashboards, distribution charts, financial summaries, alert panels.
Async, `ctx.api` + `ctx.antd` available.

| File | Type | Placeholders |
|------|------|-------------|
| `block-kpi.js` | Multi-KPI row (3-4 cards) | `{COLLECTION}`, `{QUERIES}` |
| `block-distribution.js` | Status distribution bars | `{COLLECTION}`, `{FIELD}`, `{CONFIG}` |
| `block-financial.js` | Aggregate by group (bar chart) | `{COLLECTION}`, `{GROUP_FIELD}`, `{VALUE_FIELD}`, `{APPENDS}`, `{TITLE}` |
| `block-alert.js` | Expiring/overdue items list | `{COLLECTION}`, `{DATE_FIELD}`, `{NAME_FIELD}`, `{DAYS}`, `{TITLE}` |

**Sidebar blocks** — same tool (`nb_js_block`), designed for page sidebar area:

| File | Type | Placeholders |
|------|------|-------------|
| `sidebar-bars.js` | Distribution bars | `{COLLECTION}`, `{FIELD}`, `{COLOR_MAP}` |
| `sidebar-grid.js` | 2x2 grid counts | `{COLLECTION}`, `{FIELD}`, `{COLOR_MAP}` |
| `sidebar-pipeline.js` | Funnel/pipeline | `{COLLECTION}`, `{FIELD}`, `{STAGE_ORDER}` |

## Item Templates — `nb_js_item(grid_uid, title, code)`

Custom content inside detail views or forms. `ctx.record` available in detail context.

| File | Type | Placeholders |
|------|------|-------------|
| `item-lifecycle.js` | Status pipeline + progress bar | `{STATUS_FIELD}`, `{STAGES}`, `{STATUS_COLORS}` |
| `item-stats.js` | 2-4 computed statistics | `{STATS}` |
| `item-gauge.js` | Progress circle with label | `{VALUE_FIELD}`, `{TOTAL_FIELD}`, `{LABEL}` |

## Event Templates — `nb_event_flow(form_uid, event_name, code)`

Form event handlers. Three event types:
- `formValuesChange` — when any field changes (auto-calc, validation, cascading)
- `beforeRender` — when form opens (auto-fill defaults)
- `afterSubmit` — after successful submit (notifications, redirects)

| File | Event | Type | Placeholders |
|------|-------|------|-------------|
| `event-calc.js` | formValuesChange | Auto-calculate A*B→Result | `{FIELD_A}`, `{FIELD_B}`, `{RESULT}` |
| `event-mapping.js` | formValuesChange | Value→value lookup | `{TRIGGER}`, `{TARGET}`, `{MAP}` |
| `event-autofill.js` | beforeRender | Fill current user/date | `{FILLS}` |
| `event-validate.js` | formValuesChange | Cross-field validation | `{FIELD_A}`, `{FIELD_B}`, `{RULE}`, `{MESSAGE}` |
| `event-conditional.js` | formValuesChange | Conditional required fields | `{TRIGGER}`, `{TRIGGER_VALUES}`, `{TARGET_FIELDS}` |

## Placeholder Reference

| Placeholder | Format | Example |
|-------------|--------|---------|
| `{FIELD}` | field name string | `amount`, `status` |
| `{COLLECTION}` | table name | `nb_crm_customers` |
| `{COLOR_MAP}` | JS object literal | `{"高":"#ff4d4f","中":"#faad14","低":"#52c41a"}` |
| `{STAGE_ORDER}` | JS array literal | `["线索","商机","报价","成交"]` |
| `{QUERIES}` | JSON array | `[{"title":"总数","filter":{}},{"title":"活跃","filter":{"status":"活跃"},"color":"#52c41a"}]` |
| `{CONFIG}` | JS object with nested color+icon | `{"在用":{"color":"#52c41a","icon":"✅"}}` |
| `{FILLS}` | JSON array | `[{"field":"reporter","source":"currentUser"},{"field":"date","source":"today"}]` |
| `{STATS}` | JSON array | `[{"title":"原值","field":"price","prefix":"¥"}]` |
| `{MAP}` | JS object literal | `{"VIP":"A级","普通":"B级"}` |
