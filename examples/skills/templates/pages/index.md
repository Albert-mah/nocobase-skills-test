# Page Layout Templates

Each template is a JSON file for `nb_compose_page_file`. Read the template, replace `{PLACEHOLDER}` with real values.

## Pattern → Template → JS Template Mapping

This is the critical link: requirements pattern → which template file → which JS templates fill the placeholders.

| Pattern | Template File | Layout | When to Use | JS Templates to Fill |
|---------|--------------|--------|-------------|---------------------|
| **A: KPI Strip** | `crud-kpi.json` | KPI(24) → Filter(24) → Table(24) | Core business pages with "打开页面关注 XX 总数/数量" | `block-kpi.js` → `{KPI_CODE}` |
| **B: Sidebar** | `crud-sidebar.json` | Filter(24) → Table(16)+Sidebar(8) | Alert/monitor pages: "到期提醒", "待处理", "分布统计" in sidebar | `sidebar-bars.js` or `block-alert.js` or `block-distribution.js` → `{SIDEBAR_CODE_A/B}` |
| **C: Financial** | `crud-kpi.json` + 3 metrics | Banner(24) → 3×Metric(8) → Filter(24) → Table(24) | Financial pages: "金额汇总", "各状态金额" | `block-financial.js` → banner; `block-kpi.js` → metrics |
| **D: Pipeline** | `crud-pipeline.json` | Pipeline(24) → Dist(10)+Stats(14) → Filter(24) → Table(24) | Stage-driven: "漏斗", "阶段", "转化率" | `sidebar-pipeline.js` → `{PIPELINE_CODE}`; `block-distribution.js` → `{DIST_CODE}` |
| **E: Simple** | `crud-simple.json` | Filter(24) → Table(24) | Reference/config data with no KPIs | none |
| **F: Dashboard** | `crud-dashboard.json` | Progress(10)+Ranking(14) → Filter(24) → Table(24) | Target tracking: "达成率", "进度", "排行" | `block-kpi.js` (circle progress) → `{PROGRESS_CODE}` |

## How to Use (Step by Step)

1. **Determine pattern** from requirements "用户关注" section (use mapping rules in checklist Step 3.1)
2. **Read the template JSON file** for that pattern
3. **Read the JS template files** listed in "JS Templates to Fill" column above
4. **Replace placeholders**: collection names, field names, filter values, JS code
5. **Add `js_columns`** to the table block (see below)
6. Write to a pages_batch file, call `nb_compose_page_file`

## Table Block — js_columns (Business-Driven)

Add js_columns in Phase 3 when the table has fields that **NocoBase cannot render natively**. Do NOT force js_columns on every table.

### Decision process — read HTML prototypes first!

**Step 1**: Read the HTML prototype `*.html` for this page. Look at the `<table>` columns.
**Step 2**: For each `<td>`, determine if it needs a JS column (see mapping below).
**Step 3**: Add matching js_columns to the table block.

### ★ MOST IMPORTANT: Every entity's primary column = col-composite.js

Look at the HTML prototypes — every entity's first column shows **bold title + gray subtitle**:
- 客户: "华为技术有限公司" + "深圳 · 转介绍"
- 商机: "企业云服务采购项目" + "创建于 2024-01-15"
- 合同: "云服务年度合同" + "2024-01-01 ~ 2024-12-31"
- 工单: "系统宕机无法访问" + "影响全部业务，需立即处理"

**Every non-reference table SHOULD have a composite primary column.** Read `../js/col-composite.js`.

### HTML `<td>` → JS column mapping

| HTML prototype pattern | Template | Skip? |
|----------------------|----------|-------|
| Two nested `<div>` (bold name + gray info) | `col-composite.js` | |
| ¥ + monospace number | `col-currency.js` | |
| "还剩X天" / "已逾期X天" countdown | `col-countdown.js` | |
| Progress bar + percentage | `col-progress.js` | |
| "N小时前" / "N天前" relative time | `col-relative-time.js` | |
| Stars / rating | `col-stars.js` | |
| Target vs actual bar | `col-comparison.js` | |
| Colored tag/badge (等级/状态/类型) | **SKIP** — NocoBase native | ✓ |
| Plain text | **SKIP** — NocoBase native | ✓ |
| Relation name | **SKIP** — NocoBase native | ✓ |

### Example — CRM 合同 table:

```json
{
  "id": "tbl", "type": "table", "collection": "nb_crm_contracts",
  "fields": ["title","customer_id","status","amount","end_date","createdAt"],
  "js_columns": [
    {"title": "合同", "code": "...col-composite.js: TITLE=title, SUBS='start_date','end_date'...", "width": 200},
    {"title": "金额", "code": "...col-currency.js: FIELD=amount, THRESHOLD=500000...", "width": 120},
    {"title": "到期", "code": "...col-countdown.js: FIELD=end_date...", "width": 100}
  ]
}
```
Note: `status` → select field → SKIP. `customer_id` → relation → SKIP.

## Sidebar Block JS — Ready-to-Use Patterns

For `crud-sidebar.json`, fill `{SIDEBAR_CODE_A}` and `{SIDEBAR_CODE_B}` with one of these:

### Distribution Bars (sidebar-bars.js)
Shows field value distribution as horizontal progress bars. Great for: industry distribution, status breakdown, category split.
```
Read ../js/sidebar-bars.js → replace {COLLECTION}, {FIELD}, {COLOR_MAP}
```

### Alert List (block-alert.js)
Shows items approaching a date deadline. Great for: contract expiry, ticket SLA, approval deadlines.
```
Read ../js/block-alert.js → replace {COLLECTION}, {DATE_FIELD}, {NAME_FIELD}, {DAYS}, {TITLE}
```

### Pipeline Funnel (sidebar-pipeline.js)
Shows stage counts in funnel order. Great for: lead stages, candidate status, opportunity pipeline.
```
Read ../js/sidebar-pipeline.js → replace {COLLECTION}, {FIELD}, {STAGE_ORDER}
```

### Grid Counts (sidebar-grid.js)
Shows 2×2 grid of category counts. Great for: type breakdown, priority counts.
```
Read ../js/sidebar-grid.js → replace {COLLECTION}, {FIELD}, {COLOR_MAP}
```

## Placeholders Reference

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{TAB_UID}` | Tab UID from nb_create_menu | `"abc123def456"` |
| `{COLLECTION}` | Collection name | `"nb_crm_customers"` |
| `{TABLE_FIELDS}` | JSON array of column names | `["name","status","createdAt"]` |
| `{FILTER_FIELDS}` | JSON array of searchable fields | `["name","status"]` |
| `{FORM_FIELDS}` | DSL string for add/edit forms | `"name*\nstatus\nremark"` |
| `{DETAIL_TABS}` | Detail popup tab definitions | `[{"title":"Info","fields":"name\|status"}]` |
