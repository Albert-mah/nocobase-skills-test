# NocoBase System Build

Use MCP tools from the `nocobase` server. Key tools:
- `nb_clean_prefix()` — clean up leftover tables/collections/workflows/routes before rebuilding
- `nb_setup_collection()` — ONE call per table (register + sync + upgrade fields + relations). Idempotent.
- **`nb_page_markup()`** — build a page from XML markup. JS nodes are description-only placeholders. Primary page building tool.
- **`nb_page_markup_file(file_path)`** — build MULTIPLE pages from a JSON file `[{tab_uid, markup}, ...]`.
- `nb_find_placeholders(scope)` — discover all JS placeholders after building pages
- `nb_inject_js(uid, code)` — replace a placeholder with real JS implementation
- **`nb_inject_js_dir(dir_path)`** — batch inject JS from `{uid}.js` files in a directory (supports retry)
- `nb_js_enhance_file(file_path)` — batch JS enhancement from a JSON file
- `nb_fields(collection_name)` — show available fields AND enum values. Use BEFORE building pages.
- `nb_execute_sql()` / `nb_execute_sql_file()` — bulk DDL and DML
- `nb_create_menu()` — create group + pages in one call

## Two-Phase Workflow

### Phase 1: Build pages with XML markup
Write XML markup defining page structure. All JS nodes (columns, blocks, items, events) are **description-only placeholders** — no actual JS code needed.

```
nb_page_markup(tab_uid, "<page collection=\"users\">...</page>")
```

### Phase 2: Implement JS individually
Discover all placeholders, then implement each one with real code:
```
nb_find_placeholders("CRM")  →  [{uid, kind, title, desc, field, collection}, ...]

# Option A: Write JS files named by UID → batch inject (recommended)
# Write each JS to js/{uid}.js, then:
nb_inject_js_dir("js/")      →  batch inject all, retry failed ones

# Option B: Inject one at a time
nb_inject_js(uid, code)       →  replace placeholder with real JS
```

Phase 2 tasks are independent — can run in parallel, retry individually.

## Page Design — Layout First

**Page design = Layout design.** Before writing markup, decide the page's grid structure first.

### Grid System

Layout uses **Ant Design 24-column grid** via `<row>` + `span` attributes.

```
24          = full width (auto for non-row elements)
12 + 12     = two equal halves
8 + 16      = 1:2 narrow + wide
16 + 8      = 2:1 wide + narrow
6 + 18      = 1:3 sidebar + main
8 + 8 + 8   = three equal thirds
10 + 14     = golden ratio split
```

**Column Stacking** — `<stack>` puts multiple blocks in one column vertically:
```xml
<row>
  <table id="tbl" span="16" fields="name,status,createdAt" />
  <stack span="8">
    <js-block title="Alert A">sidebar alert</js-block>
    <js-block title="Alert B">sidebar stats</js-block>
  </stack>
</row>
```

### Layout Patterns — MUST Use One Per Page

Every non-reference page **MUST use an explicit layout pattern**. Never let everything auto-stack full-width.

---

#### Pattern A: "KPI Strip + Split + Table" (Core Business)

Best for: 客户, 商机, 合同, 员工 — daily ops pages with rich data.

```xml
<page collection="nb_crm_customers">
  <row>
    <kpi title="客户总数" />
    <kpi title="跟进中" filter="status=跟进中" color="blue" />
    <kpi title="本月新增" filter="createdAt=thisMonth" color="green" />
  </row>
  <row>
    <js-block title="行业分布" span="10">按industry分布的水平条形图</js-block>
    <js-block title="来源分析" span="14">按source分布的图表</js-block>
  </row>
  <filter fields="name,status,industry" target="tbl" />
  <table id="tbl" fields="name,status,industry,phone,createdAt">...</table>
</page>
```

**Key**: Row 2 uses asymmetric split (10+14), not boring 12+12.

---

#### Pattern B: "Sidebar + Main" (Alert/Monitor)

Best for: 服务工单, 到期提醒, 审批 — pages where urgency drives action.

```xml
<page collection="nb_crm_tickets">
  <filter fields="subject,status,priority" target="tbl" />
  <row>
    <table id="tbl" span="16" fields="subject,status,priority,createdAt">...</table>
    <stack span="8">
      <js-block title="待处理">待处理工单列表</js-block>
      <js-block title="优先级分布">按priority统计</js-block>
    </stack>
  </row>
</page>
```

---

#### Pattern C: "Banner + Three Columns + Table" (Financial)

Best for: 回款, 报价, 薪资 — pages focused on money metrics.

```xml
<page collection="nb_crm_payments">
  <js-block title="金额概览">总金额/已收/待收三个统计</js-block>
  <row>
    <js-block title="本月" span="8">本月回款金额</js-block>
    <js-block title="上月" span="8">上月回款金额</js-block>
    <js-block title="趋势" span="8">环比增长趋势</js-block>
  </row>
  <filter fields="customer_id,status" target="tbl" />
  <table id="tbl" fields="customer_id,amount,status,createdAt">...</table>
</page>
```

---

#### Pattern D: "Pipeline + Wide Table" (Pipeline/Stage)

Best for: 线索, 候选人 — stage-driven workflows.

```xml
<page collection="nb_crm_leads">
  <js-block title="漏斗">各阶段数量漏斗图</js-block>
  <row>
    <js-block title="来源分布" span="10">按source统计</js-block>
    <js-block title="转化率" span="14">各阶段转化率</js-block>
  </row>
  <filter fields="name,status,source" target="tbl" />
  <table id="tbl" fields="contact_name,company,status,source,createdAt">...</table>
</page>
```

---

#### Pattern E: "Compact" (Reference/Config)

Best for: 产品, 知识库, 部门 — simple data with minimal visualization.

```xml
<page collection="nb_crm_products">
  <filter fields="name,category" target="tbl" />
  <table id="tbl" fields="name,category,price,status,createdAt">
    <addnew fields="name*\ncategory\nprice\nstatus" />
    <edit fields="name*\ncategory\nprice\nstatus" />
  </table>
</page>
```

No JS blocks needed. Clean and functional.

---

#### Pattern F: "Dashboard + Progress" (Target/Progress)

Best for: 销售目标, 招聘进度, KPI考核 — goal tracking.

```xml
<page collection="nb_crm_targets">
  <row>
    <js-block title="整体达成" span="10">总体达成率圆形进度条</js-block>
    <js-block title="排行榜" span="14">Top N 排行列表</js-block>
  </row>
  <filter fields="name,period" target="tbl" />
  <table id="tbl" fields="name,target_amount,achieved_amount,period,createdAt">...</table>
</page>
```

---

### Layout Rules (MANDATORY)

1. **Every page MUST have an explicit layout** — use `<row>` with `span` to create multi-column layouts.
2. **At least ONE row should have 2+ blocks side by side** for non-reference pages.
3. **Use asymmetric ratios** (10+14, 8+16, 6+18) — they look better than 12+12.
4. **JS blocks go in rows 1-2** (above the fold). Filter and table go below.
5. **Filter always full-width** on its own row.
6. **Table always full-width** at the bottom.
7. **Pick a Pattern** (A-F) for each page type. Adapt it, don't ignore it.

## XML Markup Reference

### Root and Layout Tags

```xml
<page collection="nb_crm_customers">   <!-- Root: sets default collection -->
  <row>                                 <!-- Horizontal row, children split by span -->
    <... span="16" />                   <!-- Left column -->
    <stack span="8">                    <!-- Vertical stack in right column -->
      <... />
      <... />
    </stack>
  </row>
  <filter ... />                        <!-- Non-row elements → auto full-width -->
  <table ... />
</page>
```

### KPI

```xml
<kpi title="客户总数" />
<kpi title="跟进中" filter="status=跟进中" color="blue" />
<kpi title="本月新增" filter="createdAt=thisMonth" color="green" />
```

### Filter

```xml
<filter fields="name,status,industry" target="tbl" />
```
- `target` = table block's `id` for filter binding

### Table (with popups)

```xml
<table id="tbl" fields="name,status,industry,phone,createdAt" title="客户列表">
  <!-- JS column placeholders (description only, no code) -->
  <js-col type="composite" field="name" subs="city,source" title="客户">
    蓝色粗体客户名，下方灰色显示 城市·来源
  </js-col>
  <js-col type="currency" field="amount" title="金额" threshold="100000">
    ¥格式，超过10万红色高亮
  </js-col>
  <js-col type="countdown" field="end_date" title="到期">
    还剩N天/已逾期N天
  </js-col>

  <!-- AddNew form popup -->
  <addnew fields="name*|code\nstatus|industry\nphone|email">
    <event on="formValuesChange">当industry变化时自动推荐grade</event>
  </addnew>

  <!-- Edit form popup -->
  <edit fields="name*|code\nstatus|industry\nphone|email" />

  <!-- Detail popup with tabs -->
  <detail>
    <tab title="基本信息" fields="name|code\nstatus|industry\nphone|email">
      <js-item title="状态历史">客户状态变更时间线</js-item>
    </tab>
    <tab title="联系人">
      <subtable collection="nb_crm_contacts" assoc="contacts" fields="name,phone,position" />
    </tab>
  </detail>
</table>
```

- `fields`: comma-separated column list. Always include "createdAt". Invalid fields auto-skipped.
- `first_click`: default true. Set `first_click="false"` to disable.
- `<addnew>` / `<edit>`: Fields DSL in `fields` attribute.
- `<detail>`: Omit for auto-generated detail popup from addnew fields.

### JS Column Placeholders (`<js-col>`)

Write only **description** — no actual JS code. Implemented in Phase 2 via `nb_inject_js`.

DSL types (auto-generates placeholder code with visual card):

| type | Description | Extra attrs |
|------|------------|-------------|
| `composite` | Bold title + gray subtitle | `subs="field1,field2"` |
| `currency` | ¥ formatted amount | `threshold="100000"` |
| `countdown` | Days remaining/overdue | — |
| `progress` | Progress bar + percentage | — |
| `relative_time` | "N小时前" / "N天前" | — |
| `stars` | Star rating ★★★★☆ | — |
| `comparison` | Target vs actual bar | `target="field"` `actual="field"` |

### JS Block Placeholders (`<js-block>`)

Page-level JS block — description only, implemented in Phase 2.

```xml
<js-block title="行业分布">按industry统计客户数量，水平条形图</js-block>
```

### JS Item Placeholders (`<js-item>`)

Inside detail/form popup — description only, implemented in Phase 2.

```xml
<js-item title="状态时间线">显示从新客户→跟进中→已签约的变更历史</js-item>
```

### Event Placeholders (`<event>`)

Inside `<addnew>` or `<edit>` — description only, implemented in Phase 2.

```xml
<event on="formValuesChange">当industry变化时自动推荐grade</event>
<event on="beforeRender">打开表单时自动填充当前用户和日期</event>
```

### Standalone Blocks

```xml
<form collection="nb_crm_feedback" fields="customer*\ncontent*\nrating" mode="create" title="提交反馈" />
<detail-block collection="nb_crm_customers" fields="name|code\nstatus|industry" title="客户详情" />
```

## Fields DSL Syntax

- `name` — single field, full width
- `name*` — required field
- `name | code` — two fields side by side (12+12)
- `name:16 | code:8` — explicit widths (total=24)
- `--- Section Title` — divider with label
- `---` — plain divider

## Field Validation

1. **Before building pages**: Call `nb_fields("collection_name")` for EVERY collection. **Save output to notes.md** — you need exact field names AND enum values for JS blocks.
2. **Use exact field names and enum values** — don't guess. JS filter values MUST match the actual data.
3. **Auto-skip invalid fields**: The builder automatically skips fields that don't exist (with warnings). But always verify field names first.
4. **Check warnings** in results — if you see "skipped N invalid fields", fix your field names and rebuild.

## JS Implementation (Phase 2)

### Workflow

1. After building all pages with `nb_page_markup`, discover placeholders:
   ```
   nb_find_placeholders("CRM")
   ```
   Returns: `[{uid, kind, title, desc, field, collection, parent_uid}, ...]`

2. For each placeholder, write real JS and inject:
   ```
   nb_inject_js(uid, code)                    # for blocks, columns, items
   nb_inject_js(uid, code, event_name="formValuesChange")  # for events
   ```

3. Or batch via file:
   ```
   nb_js_enhance_file(file_path)
   ```
   File format: `[{"action":"update","uid":"xxx","code":"...","title":"..."}, ...]`

### JS Sandbox

**Columns & Blocks**: `ctx.React`, `ctx.antd` (full Ant Design 5), `ctx.api`, `ctx.render(el)`, `ctx.record` (columns), `ctx.themeToken`
**Event Flows**: `ctx.form` (.values, .setFieldsValue), `ctx.model` (.currentUser), events: formValuesChange, beforeRender, afterSubmit

### JS Code Rules
1. Single string — no backticks inside the code
2. Always declare: `const h = ctx.React.createElement;`
3. Wrap in `(async () => { ... })();` for async blocks
4. Null-check: `(ctx.record || {}).field` in columns, `ctx.form?.values || {}` in events
5. `ctx.render()` exactly once in columns and blocks
6. No external imports — only ctx.React, ctx.antd, ctx.api
7. **No Card wrapper in JS blocks** — NocoBase already wraps JS blocks in a card

### JS Column Types — When to Use

| Type | Use for | NocoBase native? |
|------|---------|:---:|
| composite | Bold name + gray subtitle | No → use JS |
| currency | ¥ formatted numbers | No → use JS |
| countdown | Days remaining/overdue | No → use JS |
| progress | Progress bar + percentage | No → use JS |
| relative_time | "N小时前" / "N天前" | No → use JS |
| stars | Star rating | No → use JS |
| comparison | Target vs actual | No → use JS |
| **select/enum** (状态/类型/优先级) | **Colored tags** | **Yes → SKIP** |
| **plain text / relation name** | **Text display** | **Yes → SKIP** |

### API Quick Reference

```javascript
const h = ctx.React.createElement;

// List records:
const r = await ctx.api.request({url: 'COLLECTION:list', params: {paginate: false}});
const items = r?.data?.data || [];

// Count with filter:
const r2 = await ctx.api.request({url: 'COLLECTION:list', params: {paginate: false, filter: {status: 'EXACT_VALUE'}}});
const count = r2?.data?.data?.length || 0;

// Sum a field:
const total = items.reduce((s, r) => s + (Number(r.amount) || 0), 0);

// Format currency:
'¥' + amount.toLocaleString('zh-CN', {minimumFractionDigits: 2})
```

## JS Block Design Rules

### Compact, Not Verbose

Bad: 8 rows of progress bars for industry distribution (too tall, low info density).
Good: Horizontal tag cloud, mini bar group, or circle progress row.

### Design Principles

1. **Height budget**: Each JS block should be **120-200px tall max**. If your block is taller than the table, it's too big.
2. **Use antd Statistic** for numbers — it handles formatting and styling.
3. **Use Row + Col** inside JS blocks — the INTERNAL layout of a JS block also matters.
4. **Color palette**: Pick 4-6 colors per page. Reuse them across blocks. Don't use random colors.

### Recommended antd Components by Use Case

| Use Case | Components | Notes |
|----------|-----------|-------|
| KPI metrics | `Statistic` in `Row`+`Col` | 4-6 metrics per row, use `valueStyle` for color |
| Distribution | `Progress` (horizontal bars) | Max 5-6 items; or use `Tag` cloud for categories |
| Pipeline/Funnel | `Statistic` in `Row`+`Col` | Color-coded stages, horizontal layout |
| Alert list | `List` + `Tag` | Limit to 5-8 items, show priority via Tag color |
| Progress/Target | `Progress` (line or circle) | Circle for overall %, line for individual targets |
| Ranking | `List` + numbered items | Use `Avatar` with rank number for top 3 |

## Form Refinement (Phase 3B)

After Phase 3 page builds, forms may have incomplete fields. Use these tools to scan and refine:

- `nb_auto_forms(scope)` — scan all forms, generate task table with coverage %
- `nb_set_form(table_uid, type, dsl, events?)` — replace addnew/edit form
- `nb_set_detail(table_uid, detail_json)` — replace detail popup with tabs

### nb_set_form Example
```
nb_set_form("tbl_uid", "addnew",
    "--- 基本信息\nname*|code\nstatus|industry\n--- 联系方式\nphone|email",
    [{"on": "formValuesChange", "desc": "industry变化时推荐grade"}])
```

### nb_set_detail Example
```
nb_set_detail("tbl_uid", [
    {"title": "基本信息", "fields": "name|code\nstatus|industry",
     "js_items": [{"title": "画像", "desc": "等级标签+状态+来源"}]},
    {"title": "联系人", "assoc": "contacts",
     "coll": "nb_crm_contacts", "fields": ["name","phone"]}
])
```

## Quick CRUD Shortcut — nb_crud_page

For simple data management pages (just list + create + edit + detail), `nb_crud_page` creates a fixed layout in one call:
```
nb_crud_page(tab_uid, collection, table_fields, form_fields, filter_fields?, kpis_json?, detail_json?)
```
Use for Pattern E (reference/config) pages. For anything with JS blocks, use `nb_page_markup`.

## Critical Rules
1. Do NOT include created_at, updated_at, created_by_id, updated_by_id in DDL — added automatically
2. Use CREATE TABLE IF NOT EXISTS
3. **Clean before rebuild**: `nb_clean_prefix("nb_xxx_")`
4. **Batch page builds**: Write pages to JSON file `[{tab_uid, markup}, ...]`, call `nb_page_markup_file`. 4-5 pages per file.
5. Parent tables before child tables (FK order)
6. Write progress to ./notes.md after each phase
7. **Before building pages**: call `nb_fields()` for ALL collections, save exact field names and enum values to notes.md
8. **After building pages**: run `nb_find_placeholders` to get all JS tasks for Phase 2
9. For large INSERT data: use `nb_execute_sql_file()` with a .sql file
10. **Build order**: Reference/Config pages first (simple, quick), then Core Business and complex pages
11. **LAYOUT IS MANDATORY**: Every non-reference page MUST have `<row>` with `span` attributes. Pick Pattern A-F and adapt it.
12. **JS columns: NO select/enum fields** — NocoBase renders colored tags natively. Only use JS for: composite, currency, countdown, progress, relative_time, stars, comparison.
13. **JS block height**: Keep JS blocks compact (120-200px).
14. **Phase 2 is separate**: In XML markup, JS nodes only have descriptions. Real JS code is injected in Phase 2 via `nb_inject_js`.
