# NocoBase Build Checklist

Execute each step in order. After completing each step, write the result to `notes.md`.

---

## How to Use This Checklist

### Task Management — Create Task Tables

After every **planning step**, create a task table in `notes.md`. Each row = one executable unit with a status marker.

```
### Page Tasks
| # | Page | Tab UID | Pattern | Detail Spec | Status |
|---|------|---------|---------|-------------|--------|
| 1 | 客户 | lhc... | A+B | 4tabs, js-item(画像), 3 subtable | [todo] |
| 2 | 联系人 | ds3... | E | auto | [done] |
```

Markers: `[todo]` → `[done]` or `[fail]` (with error note).

### Resume After Interruption

1. Read `notes.md` — find first `[todo]`
2. Continue from that task
3. Do NOT re-execute `[done]` tasks
4. All state lives in `notes.md` — if it's not written down, it didn't happen

### Parallel Execution

Steps marked `[parallel-ok]` contain independent tasks:
- **Single agent**: Execute tasks sequentially
- **Cluster** (recommended for 5+ tasks): Dispatch each task row as a sub-agent:
  ```
  Sub-agent: "{task title}"
  1. Read notes.md for context (field names, UIDs, enum values)
  2. {step-specific instructions}
  3. Update notes.md: mark row [done] or [fail]
  ```

Cluster-friendly steps: **3.3** (page builds), **4.2** (JS implementation), **5.2** (workflows).

---

## Phase 0: Initialize [sequential]

### Step 0.1: Read requirements
- [ ] Read requirements (`*-requirements.md` — has user personas + "用户关注" + 交互期望)
- [ ] If HTML prototypes exist (`*.html` + `design-notes.md`), read them for visual patterns
- [ ] Extract: table prefix, table list, field types, relations, enums, menu structure
- [ ] Extract **per-page UX expectations**: first-screen focus, JS blocks, auto-calc needs
- [ ] Write to `notes.md`:
  ```
  # Build Notes
  ## System: {name}
  ## Prefix: {prefix}
  ## Tables: {count}
  ## Has HTML prototypes: yes/no
  ## Status: Phase 0 complete
  ```

### Step 0.2: Clean previous build (if rebuilding)
- [ ] `nb_clean_prefix("{prefix}")` — deletes collections, tables, workflows, AND routes
- [ ] `nb_delete_workflows_by_prefix("{PREFIX}-")`
- [ ] Verify: `nb_list_routes()` — old menu should be gone

---

## Phase 1: Data Modeling [sequential]

**Knowledge**: Read `knowledge/data-modeling.md`

### Step 1.1: Create all tables
- [ ] Generate DDL (NO system columns: created_at/updated_at/created_by_id/updated_by_id)
- [ ] `nb_execute_sql(ddl)` — all CREATE TABLE in one call

### Step 1.2: Register & setup collections
- [ ] For each table (parent-first): `nb_setup_collection(name, title, field_interfaces, relations)`
- [ ] **Include o2m relations on parent tables** — required for `<subtable>` in detail popups later:
  - e.g. customers → contacts (o2m), customers → opportunities (o2m)
  - Without these, detail subtables will be empty

### Step 1.3: Insert seed data
- [ ] Generate INSERT statements (5-10 rows per table, realistic Chinese data)
- [ ] `nb_execute_sql(inserts)` — parent tables first

### Step 1.4: Write notes
- [ ] Write table list + row counts + **o2m relations map** to `notes.md`

---

## Phase 2: Field Validation [parallel-ok]

### Step 2.1: Read all fields
- [ ] For each collection: `nb_fields("{collection_name}")`
- [ ] Record **exact field names + enum option values** in `notes.md`
- [ ] **Verify o2m relations**: parent collections should show o2m fields
- [ ] If missing o2m: fix via `nb_create_relation(collection, name, target, type="o2m", foreign_key)`

---

## Phase 3: Menu & Pages [sequential then parallel-ok]

**Knowledge**: Read `knowledge/page-building.md`
**Templates**: Read `templates/pages/index.md` for layout patterns

### Step 3.1: Design ALL pages — Create Page Task Table [sequential]

**Input**: Requirements "用户关注" + HTML prototypes + field names from notes.md

For each page, decide:
1. **Layout pattern** (A-F, see CLAUDE.md)
2. **JS blocks** for page-level charts/stats
3. **JS columns** for table display enhancement
4. **Detail popup design** (see rules below)
5. **Events** for form auto-calculation
6. **Subtable prerequisites**: verify parent has o2m relation

**Write a Page Task Table to `notes.md`**:

```
### Page Tasks

| # | Page | Collection | Pattern | KPI | JS Blocks | JS Cols | Detail Design | Events | Status |
|---|------|-----------|---------|-----|-----------|---------|---------------|--------|--------|
| 1 | 客户 | nb_crm_customers | A+B | 5 | 行业分布,等级分布,状态分布 | composite(name) | Tab基本信息: fields + js-item(客户画像: 等级标签+行业+状态+来源+建档天数); Tab联系人: subtable(contacts); Tab商机: subtable(opportunities); Tab合同: subtable(contracts) | 0 | [todo] |
| 2 | 联系人 | nb_crm_contacts | E | 0 | - | - | auto | 0 | [todo] |
| 3 | 商机 | nb_crm_opportunities | A+C+D | 4 | 销售漏斗 | composite(title),currency(amount),progress(probability),countdown(expected_date) | Tab基本信息: fields + js-item(商机进度: 阶段进度条+概率+倒计时+金额); Tab报价: subtable(quotes); Tab跟进: subtable(activities) | 2(阶段→概率映射) | [todo] |
```

**Detail Popup Design Rules**:

| Page type | Detail popup approach |
|-----------|---------------------|
| Core business (高频访问，数据关联多) | Multi-tab: 基本信息(fields + `<js-item>`) + 关联数据(`<subtable>` per relation) |
| Secondary (中频访问) | 1-2 tabs: fields + optional subtable |
| Reference/Config (配置数据) | Auto-generated (omit `<detail>` → auto from addnew fields) |

**`<js-item>` design pattern** (one per core page's first tab):
```
<js-item title="视觉摘要">
  {status_field}彩色标签({enum_value1}色1/{enum_value2}色2/...) +
  {category_field}标签 +
  进度/倒计时/金额/统计 (从"用户关注"提取)
</js-item>
```

### Step 3.2: Create menu structure [sequential]
- [ ] `nb_create_menu(group_title, parent_id, pages_json)` for each group
- [ ] Fill in "Tab UID" column in Page Task Table

### Step 3.3: Build pages [parallel-ok — each page is one task]

**For each `[todo]` row in Page Task Table**:

1. Read the page's design from notes.md task table
2. **Read the HTML prototype** for this page — compare with your markup to ensure visual fidelity
3. Write XML markup (`<page>` root) following the pattern:
   - KPI row: `<kpi>` tags — **ONLY for simple count numbers** (总数, 本月新增)
   - JS blocks: `<js-block>` with description (NO code) — **for ALL charts/bars/lists/visualizations**
   - Filter: `<filter>` with `target` binding
   - Table: `<table>` with columns + `<js-col>` placeholders
   - Forms: `<addnew>` + `<edit>` with fields DSL
   - **Detail popup** (core pages):

**⚠️ CRITICAL: `<kpi>` vs `<js-block>` — #1 mistake source**
```
<kpi>  = ONE number (auto Statistic count). ONLY for KPI strip at page top.
<js-block> = ANY visualization (bars, pipeline, grid, alert, list, progress).
```
If the HTML prototype shows bars, colored distribution, funnel, alert list, timeline, or anything beyond a single number → use `<js-block>`, NEVER `<kpi>`.
Sidebar blocks (stacked in `<stack span="8">`) are ALWAYS `<js-block>`.
     ```xml
     <detail>
       <tab title="基本信息" fields="field1|field2\nfield3|field4">
         <js-item title="视觉摘要">
           描述要显示什么：标签、进度条、倒计时、统计数字
         </js-item>
       </tab>
       <tab title="关联数据A">
         <subtable collection="child_coll" assoc="o2m_field" fields="f1,f2,f3" />
       </tab>
     </detail>
     ```
   - Events: `<event on="formValuesChange">描述逻辑</event>` in `<addnew>`/`<edit>`
3. Build: `nb_page_markup(tab_uid, markup)`
4. Update notes.md: mark row `[done]`, record any warnings

**Cluster dispatch template** (each page = one sub-agent):
```
Build page "{page}" on tab {tab_uid}, collection {collection}.
Read notes.md for field names and enum values.
Design from notes.md Page Tasks row #{n}: {detail_design}
Write XML markup per CLAUDE.md pattern {pattern}, call nb_page_markup.
Mark [done] in notes.md.
```

**Page build order**: Reference/Config pages first (simple, validates pipeline), then Core pages.

### Step 3.4: Verify pages [sequential]

**Knowledge**: Read `knowledge/troubleshooting.md` if errors

- [ ] `nb_inspect_all("{prefix}")` — check structure
- [ ] For core pages: verify detail popup has planned tabs + js-items + subtables
- [ ] Every `<subtable>` must have matching o2m relation on parent (`nb_list_fields`)
- [ ] Fix broken pages: `nb_clean_tab(tab_uid)` → rebuild corrected markup
- [ ] Update Page Task Table: all should be `[done]`

---

## Phase 3B: Form & Detail Refinement [parallel-ok — each form is one task]

### Step 3B.1: Scan form quality [sequential]
- [ ] `nb_auto_forms("{PREFIX}")` — generates task table with coverage %
- [ ] Copy task table to `notes.md`

### Step 3B.2: Refine each [todo] form [parallel-ok]

For each `[todo]` addnew/edit form:
1. Read HTML prototype for the page
2. Read collection fields from `notes.md`
3. Design form layout with sections (`--- Title`) and side-by-side fields (`a | b`)
4. Call `nb_set_form(table_uid, form_type, fields_dsl, events?)`
5. Mark `[done]` in Form Task Table

For each `[todo]` detail popup:
1. Read HTML prototype + o2m relations from `notes.md`
2. Design tabs: basic info (fields + js_items) + relation tabs (subtables)
3. Call `nb_set_detail(table_uid, detail_json)`
4. Mark `[done]` in Form Task Table

**Cluster dispatch template** (each form = one sub-agent):
```
Refine {form_type} form for "{page}" table {table_uid}.
Collection: {collection}. Available fields: {fields}.
1. Read notes.md for enum values and relations
2. Design form with sections and side-by-side fields
3. Call nb_set_form / nb_set_detail
4. Mark [done] in notes.md
```

---

## Phase 4: JS Implementation [parallel-ok — RECOMMEND cluster]

**Knowledge**: Read `knowledge/js-sandbox.md`
**Templates**: Read `templates/js/index.md` for available patterns

### Step 4.1: Auto-generate JS files + Task Table [sequential]
- [ ] `nb_auto_js("{prefix}")` — auto-generates JS files + task table:
  - **Column placeholders** with templates → auto-filled JS files → `[auto]`
  - **Blocks/items/events** → stub files with description → `[todo]`
- [ ] Copy the returned task table to `notes.md`
- [ ] Review: all `[auto]` files should be ready. Focus on `[todo]` files.

If `nb_auto_js` is not available, fall back to manual:
- `nb_find_placeholders("{prefix}")` → write task table manually
- Create `js/` directory, write files per template

### Step 4.2: Implement remaining [todo] JS [parallel-ok — cluster recommended]

Only `[todo]` items need manual work (blocks, items, events).
`[auto]` items (columns) are already generated by Step 4.1.

**Column [todo]**: use template files from `templates/js/col-*.js` — replace `{PLACEHOLDER}` with real values.

**Block [todo]**: **自由编写，不要套模板**。
1. Read `templates/js/index.md` "Block JS" section — 了解渲染 API 和可用组件
2. 根据 block 描述和数据特征，选择合适的可视化方式
3. **★ 同一页面的多个 block 必须使用不同的可视化模式** — 不能全用 Statistic，不能全用横向条形图
4. 遵循 Ant Design 企业级风格，写出有信息密度的可视化

**Item/Event [todo]**: use template files from `templates/js/item-*.js` / `event-*.js`.

Write each file to `js/{uid}.js` (events: `js/{uid}__evt__{event_name}.js`).
Mark `[done]` in JS Task Table.

### Step 4.3: Deploy all JS [sequential]
- [ ] `nb_inject_js_dir("js/")` — batch inject all files (auto + manual)
- [ ] Check results — fix any failed files and re-run

### Placeholder kind → Template mapping

| Kind | Templates | Tool |
|------|-----------|------|
| column/composite | `col-composite.js` | `nb_inject_js(uid, code)` |
| column/currency | `col-currency.js` | `nb_inject_js(uid, code)` |
| column/countdown | `col-countdown.js` | `nb_inject_js(uid, code)` |
| column/progress | `col-progress.js` | `nb_inject_js(uid, code)` |
| column/relative_time | `col-relative-time.js` | `nb_inject_js(uid, code)` |
| column/stars | `col-stars.js` | `nb_inject_js(uid, code)` |
| column/comparison | `col-comparison.js` | `nb_inject_js(uid, code)` |
| block (page/sidebar) | **No template — write original code** (see `index.md` "Block JS" section) | `nb_inject_js(uid, code)` |
| item | `item-lifecycle.js`, `item-stats.js`, `item-gauge.js` | `nb_inject_js(uid, code)` |
| event | `event-calc.js`, `event-mapping.js`, `event-autofill.js` | `nb_inject_js(uid, code, event_name=...)` |

### Rules
- **NO js_columns for select/enum/tag fields** — NocoBase renders colored tags natively. #1 mistake.
- JS columns ONLY for: composite, currency, countdown, progress, relative_time, stars, comparison
- Event names: `formValuesChange`, `beforeRender`, `afterSubmit`

### Step 4.3: Verify JS [sequential]
- [ ] `nb_inspect_all("{prefix}")` — check all JS applied
- [ ] Update JS Task Table: all should be `[done]`

---

## Phase 5: Workflows [parallel-ok]

**Knowledge**: Read `knowledge/workflows.md`
**Templates**: Read `templates/workflows/index.md`

### Step 5.1: Plan workflows [sequential]
- [ ] From requirements, identify:
  - Auto-numbering (which tables need sequence IDs?)
  - Status sync (which changes cascade to related tables?)
  - Auto-calculation (server-side vs client event flow?)
  - Date reminders (which date fields need advance warnings?)
- [ ] Write **Workflow Task Table** to `notes.md`

### Step 5.2: Create workflows [parallel-ok]
For each workflow task:
- [ ] Read template from `templates/workflows/`
- [ ] `nb_create_workflow` → `nb_add_node` (× N) → `nb_enable_workflow`
- [ ] Mark `[done]` in Workflow Task Table

---

## Phase 6: AI Employees [parallel-ok]

**Knowledge**: Read `knowledge/ai-employees.md`

### Step 6.1: Create AI employees
- [ ] One per business domain
- [ ] `nb_create_ai_employee(...)` for each

### Step 6.2: Add page integrations
- [ ] `nb_ai_shortcut(tab_uid, shortcuts_json)` for floating avatars
- [ ] `nb_ai_button(table_uid, username, tasks_json)` for action buttons

---

## Phase 7: Final Verification [sequential]

- [ ] `nb_inspect_all("{prefix}")` — full system overview
- [ ] `nb_list_workflows()` — all enabled
- [ ] `nb_list_ai_employees()` — all exist
- [ ] Update `notes.md` summary:
  ```
  ## Summary
  Tables: {N}, Pages: {N}, JS placeholders: {N}, JS implemented: {N}
  Event flows: {N}, Workflows: {N}, AI employees: {N}
  ## Status: COMPLETE
  ```

---

## notes.md — The Notebook

Your shared state file. Four purposes:
1. **Progress tracker** — which phases/steps are complete
2. **Task tables** — Page Tasks, JS Tasks, Workflow Tasks (per-item status)
3. **Data store** — UIDs, field names, enum values
4. **Resume point** — after crash, find first `[todo]`, continue from there

**Rules**:
- Write after EVERY step
- Create task tables after planning steps (3.1, 4.1, 5.1)
- Use `[done]` / `[todo]` / `[fail]` markers on every task row
- Include UIDs and exact values — later steps depend on them
- On resume: scan for first `[todo]`, execute it, mark `[done]`, repeat
