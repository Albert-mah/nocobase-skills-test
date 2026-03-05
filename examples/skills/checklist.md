# NocoBase Build Checklist

Execute each step in order. After completing each step, write the result to `notes.md`.
Steps marked `[parallel-ok]` can be dispatched to sub-agents. Otherwise just do them sequentially.

---

## Phase 0: Initialize [sequential]

### Step 0.1: Read requirements
- [ ] Read the requirements document — must be the `-requirements.md` version (has user personas + "用户关注" + 交互期望), NOT the `.txt` version (just table lists)
- [ ] If HTML prototypes (`*.html`) + `design-notes.md` exist in workdir, read them — they define the page UX
- [ ] Extract: table prefix, table list, field types, relations, enums, menu structure
- [ ] Extract **per-page UX expectations**: what users see first, what needs JS blocks, what needs auto-calc
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
- [ ] `nb_clean_prefix("{prefix}")`
- [ ] `nb_list_routes()` → `nb_delete_route()` for old menu groups
- [ ] `nb_delete_workflows_by_prefix("{PREFIX}-")`

---

## Phase 1: Data Modeling [sequential]

**Knowledge**: Read `knowledge/data-modeling.md`

### Step 1.1: Create all tables
- [ ] Generate DDL (NO system columns: created_at/updated_at/created_by_id/updated_by_id)
- [ ] `nb_execute_sql(ddl)` — all CREATE TABLE in one call

### Step 1.2: Register & setup collections
- [ ] For each table (parent-first): `nb_setup_collection(name, title, field_interfaces, relations)`

### Step 1.3: Insert seed data
- [ ] Generate INSERT statements (5-10 rows per table, realistic Chinese data)
- [ ] `nb_execute_sql(inserts)` — parent tables first

### Step 1.4: Write notes
- [ ] Write table list + row counts to `notes.md`

---

## Phase 2: Field Validation [parallel-ok]

### Step 2.1: Read all fields
- [ ] For each collection: `nb_fields("{collection_name}")`
- [ ] Record **exact field names + enum values** in `notes.md` — Phase 3 and 4 depend on this

---

## Phase 3: Menu & Pages [sequential then parallel-ok]

**Knowledge**: Read `knowledge/page-building.md`
**Templates**: Read `templates/pages/index.md` for layout templates + JS template mapping

### Step 3.1: Design each page
- [ ] Re-read requirements `-requirements.md` → each page's "用户关注" section
- [ ] If HTML prototypes exist: read `design-notes.md` for UX patterns
- [ ] For each page, use the mapping rules below to determine pattern + template + JS:

**Page pattern mapping rules — requirements → template:**

| Requirement pattern | Pattern | Template file | JS blocks to use |
|---|---|---|---|
| "打开页面关注" + total/count/数量 KPIs | **A: KPI Strip** | `crud-kpi.json` | `block-kpi.js` for KPI row |
| "到期提醒" / "待处理" / sidebar alerts | **B: Sidebar** | `crud-sidebar.json` | `block-alert.js` or `sidebar-bars.js` for sidebar |
| "分布统计" / "比例" in sidebar | **B: Sidebar** | `crud-sidebar.json` | `sidebar-bars.js` or `sidebar-grid.js` for sidebar |
| "金额汇总" / 多个金额 metric | **C: Financial** | build from A + 3 metrics | `block-financial.js` for banner |
| "阶段" / "漏斗" / "转化率" | **D: Pipeline** | `crud-pipeline.json` | `sidebar-pipeline.js` + `block-distribution.js` |
| Simple config/reference data | **E: Simple** | `crud-simple.json` | none |
| "达成率" / "进度" / "排行" / "目标" | **F: Dashboard** | `crud-dashboard.json` | progress circle + ranking JS |

**Multiple patterns**: A page can combine patterns. E.g., "KPI + sidebar distribution" = use KPI strip (Pattern A) in row 1, then sidebar (Pattern B) for table area.

- [ ] Write page plan to `notes.md` with columns: Page | Pattern | Template | JS blocks | js_columns

### Step 3.2: Create menu structure [sequential]
- [ ] `nb_create_menu(group_title, parent_id, pages_json)` for each group
- [ ] Record tab UIDs in `notes.md`

### Step 3.3: Build page content [parallel-ok]

**Process for each page:**
1. Read the **template JSON file** from `templates/pages/` (per Step 3.1 plan)
2. Read the **JS template files** listed in `templates/pages/index.md` "JS Templates to Fill" column
3. Replace placeholders: collection, fields, filters, JS code
4. **Add `js_columns`** to the table block — read column templates from `templates/js/col-*.js`
5. Write to pages_batch JSON file

- [ ] For each batch (4-5 pages): write JSON file → `nb_compose_page_file(path)`
- [ ] Record create_form + edit_form UIDs in `notes.md`

**js_columns — read HTML prototypes, match column patterns.** See `templates/pages/index.md` and `templates/js/index.md`.

**Process**: Read HTML prototype `<table>` → for each `<td>` with rich rendering → pick the matching col-*.js template.

**★ Primary column** — almost every entity table's first column should be `col-composite.js` (bold blue name + gray subtitle). Look at how HTML prototypes render the primary name column (nested divs = composite).

| HTML pattern → js_column template |
|---|
| Bold name + gray subtitle (nested divs) → `col-composite.js` ★ most common |
| ¥ monospace number → `col-currency.js` |
| "还剩X天" / "已逾期" → `col-countdown.js` |
| progress bar + % → `col-progress.js` |
| "N小时前" / "N天前" → `col-relative-time.js` |
| stars/rating → `col-stars.js` |
| **Colored tag (select/enum)** → **SKIP, NocoBase native** |
| **Plain text / relation name** → **SKIP, NocoBase native** |

**Build order**: Reference pages first (Pattern E, simple), then Core/Pipeline/Financial (Pattern A-D, complex).

### Step 3.4: Verify pages [sequential]
- [ ] `nb_inspect_all("{prefix}")` — check structure
- [ ] Confirm: non-Reference pages have JS blocks AND js_columns, not just filter+table
- [ ] If a page has "用户关注" but only filter+table → fix it with the correct pattern

---

## Phase 4: JS Enhancement [parallel-ok — RECOMMEND sub-agents]

**Knowledge**: Read `knowledge/js-sandbox.md`
**Templates**: Read `templates/js/index.md` for available patterns

**Phase 4 adds JS that WASN'T built in Phase 3.** Phase 3 should have already created: page-level JS blocks (KPI, sidebar, distribution) and inline js_columns in table blocks. Phase 4 adds: additional standalone blocks, detail popup items, event flows, and any missing columns.

This phase benefits most from parallel execution. Each JS task is independent and involves writing + testing code.

### Recommended: Dispatch sub-agents for JS work

For **each JS task** (block, column, item, or event flow), dispatch a sub-agent that:
1. Reads the template file from `templates/js/`
2. Reads the relevant field info from `notes.md`
3. Writes the JS code (replacing template placeholders with real values)
4. Calls the MCP tool (`nb_js_block`, `nb_js_column`, `nb_js_item`, or `nb_event_flow`)
5. Calls `nb_read_node(uid, "js")` to verify the code was saved correctly
6. If the code is wrong or the tool failed, fix and retry

Each sub-agent handles **one JS task end-to-end** (write → deploy → verify). This is better than one agent doing all JS, because:
- JS code is error-prone — each agent can focus on getting one piece right
- Debugging is isolated — a failure in one doesn't block others
- Context stays small — each agent only needs field info for one table/page

**Sub-agent prompt template**:
```
You are a JS developer for NocoBase. Your task:

Table: {collection_name}
Fields: {relevant fields from notes.md}
Task: {description, e.g. "Add currency column for 'amount' field, threshold ¥100,000"}
Template: Read templates/js/col-currency.js, replace {FIELD} with "amount", {THRESHOLD} with 100000
Tool: nb_js_column(table_uid="{uid}", title="{title}", code="{filled code}", width=120)
Verify: nb_read_node("{resulting_uid}", "js") — confirm code is correct

If it fails, read the error and fix the code.
```

### Five JS extension types

| Type | Tool | Template prefix | Where it goes |
|------|------|----------------|---------------|
| **Block** | `nb_js_block(parent, title, code)` | `block-*`, `sidebar-*` | Page-level (KPI, charts, sidebars) |
| **Column** | `nb_js_column(table_uid, title, code, width)` | `col-*` | Table column |
| **Item** | `nb_js_item(grid_uid, title, code)` | `item-*` | Detail/form popup |
| **Event** | `nb_event_flow(form_uid, event_name, code)` | `event-*` | Form behavior |
| **Update** | `nb_update_js(uid, code, title)` | — | Modify any existing JS node |

### Rules
- **NO js_columns for select/enum/tag fields** (等级/状态/类型/优先级/来源) — NocoBase renders colored tags natively. This is the #1 mistake to avoid.
- JS columns ONLY for: currency ¥, countdown, progress bar, stars, relative-time, composite, comparison — things NocoBase CANNOT render natively
- Event flow targets must be **create_form** or **edit_form** UIDs (from notes.md Phase 3)
- Event names: `formValuesChange` (field changes), `beforeRender` (form opens), `afterSubmit` (after save)

### Step 4.1: Plan JS enhancements
- [ ] Review each page's "用户关注" from requirements
- [ ] For each page, apply the mapping rules below to identify needed JS tasks
- [ ] List all JS tasks with type, target UID, and template file
- [ ] Write plan to `notes.md`

**Mapping rules — when to use each template:**

| Requirement pattern | Template | Example |
|---|---|---|
| "打开页面关注" + counts/totals | `block-kpi.js` | 员工总数/在职/离职 → KPI strip |
| "分布统计" / "比例" / "漏斗" | `block-distribution.js` | 性别分布, 学历分布, 状态漏斗 |
| "金额汇总" / "按X统计金额" | `block-financial.js` | 各部门薪资总额 |
| "到期提醒" / "N天内" alert | `block-alert.js` | 合同90天内到期列表 |
| decimal/金额 field + "¥格式" | `col-currency.js` | 薪资, 预算, 期望薪资 |
| date field + "倒计时" / "剩余天数" | `col-countdown.js` | 合同到期日, 截止日期 |
| "进度条" / "使用率" / "达成率" | `col-progress.js` | 编制使用率, 目标达成率 |
| date field + "相对时间" / "入职N年" | `col-relative-time.js` | 入职日期, 创建时间 |
| "评分" / "星级" | `col-stars.js` | 满意度评分 |
| "状态流转" / "阶段可视化" in detail | `item-lifecycle.js` | 候选人状态流, 商机阶段 |
| "自动计算" formula in form | `event-calc.js` | 实发=基本+奖金-扣除 |
| "自动填充" current user/date | `event-autofill.js` | 审批人, 创建日期 |
| field A changes → update field B mapping | `event-mapping.js` | 阶段→概率 |

**Rule**: Every non-Reference page should have at least 1 JS block (KPI or distribution). If a page has "打开页面关注" in requirements, it MUST have a `block-kpi.js`.

### Step 4.2: Implement JS blocks [parallel-ok, recommend sub-agents]
For each page block (KPI strip, distribution chart, financial summary, alert panel, sidebar):
- [ ] Read template `templates/js/block-{type}.js` or `sidebar-{type}.js`
- [ ] Replace placeholders → complete code
- [ ] `nb_js_block(parent_uid, title, code)`
- [ ] Verify: `nb_read_node(uid, "js")`

### Step 4.3: Implement JS columns [parallel-ok, recommend sub-agents]
For each column:
- [ ] Read template `templates/js/col-{type}.js`
- [ ] Replace placeholders → complete code
- [ ] `nb_js_column(table_uid, title, code, width)` or batch via `nb_js_enhance_file`
- [ ] Verify: `nb_read_node(uid, "js")`

### Step 4.4: Implement JS items [parallel-ok, recommend sub-agents]
For each detail/form custom item (lifecycle, stats, gauge):
- [ ] Read template `templates/js/item-{type}.js`
- [ ] Replace placeholders → complete code
- [ ] `nb_js_item(grid_uid, title, code)`
- [ ] Verify: `nb_read_node(uid, "js")`

### Step 4.5: Implement event flows [parallel-ok, recommend sub-agents]
For each form event:
- [ ] Read template `templates/js/event-{type}.js`
- [ ] Replace placeholders
- [ ] `nb_event_flow(form_uid, event_name, code)` — use correct event_name per template
- [ ] Use **create_form** or **edit_form** UID from notes.md

### Step 4.6: Verify JS [sequential]
- [ ] `nb_inspect_all("{prefix}")` — check all JS applied
- [ ] Mark each item done/fail in `notes.md`

---

## Phase 5: Workflows [parallel-ok]

**Knowledge**: Read `knowledge/workflows.md`
**Templates**: Read `templates/workflows/index.md`

### Step 5.1: Plan workflows
- [ ] From requirements, identify:
  - Auto-numbering (which tables need sequence IDs?)
  - Status sync (which changes cascade to related tables?)
  - Auto-calculation (which should happen server-side vs client event flow?)
  - Date reminders (which date fields need advance warnings?)
- [ ] Write plan to `notes.md`

### Step 5.2: Create workflows [parallel-ok]
For each workflow:
- [ ] Read template from `templates/workflows/`
- [ ] `nb_create_workflow` → `nb_add_node` (× N) → `nb_enable_workflow`
- [ ] Record workflow ID in `notes.md`

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
- [ ] Update `notes.md` with summary:
  ```
  ## Summary
  Tables: {N}, Pages: {N}, JS columns: {N}, Sidebars: {N}
  Event flows: {N}, Workflows: {N}, AI employees: {N}
  ## Status: COMPLETE
  ```

---

## notes.md — The Notebook

Your shared state file. Three purposes:
1. **Progress tracker** — which steps done/pending/fail
2. **Data store** — UIDs, field names, enum values for later steps
3. **Resume point** — read notes.md to continue after interruption

**Rules**:
- Write after EVERY step
- Use `[done]` / `[todo]` / `[fail]` markers
- Include UIDs and exact values — later steps depend on them
