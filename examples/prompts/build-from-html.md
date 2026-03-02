# Build NocoBase System from HTML Prototypes

You have HTML prototype files that show what each page should look like.
Your job: implement the NocoBase CRUD structure + mark JS enhancements as outlines.

## Input Files

- `*.html` — HTML prototype pages (open in browser to see the design)
- `design-notes.md` — summary of all UX patterns, special renderings, auto-fill logic
- `data-model.md` — table definitions and relations (if provided separately)

## How to Use the Design Files

1. **Start with `design-notes.md`** — compact summary of all UX patterns, field renderings, and special visualizations
2. **Read `prompt.txt`** — lists all tables, fields, and outline requirements
3. **Read individual HTML files as needed** — when you need to understand a specific page's layout structure (sidebar vs full-width, block arrangement, grid patterns). Read ONE file at a time, not all at once.

For each page, extract:

1. **Layout structure** — from HTML: how blocks are arranged (sidebar? top cards? 2-column grid?)
2. **KPIs** — which statistics to show at top → `kpis_json` (only if the page actually has KPI cards)
3. **Filter bar** — which fields are searchable → `filter_fields`
4. **Table columns** — which fields to display → `table_fields`
5. **Forms** — field layout with sections → `form_fields` DSL
6. **Detail drawer** — sub-tables noted in design → `detail_json`
7. **Dashboard blocks** — charts/stats to show → `sidebar_outlines` or separate `nb_outline` calls

## What NocoBase Handles Natively (use nb_crud_page)

- KPI statistic cards (count with filter + color)
- Filter forms (text/select/date range)
- Data tables (column display, sort)
- Add/Edit forms (field layout with sections)
- Detail popups with tabs (fields + sub-tables)
- Select field options with colors (configured during nb_setup_collection)

## What Needs JS Enhancement (use nb_outline to plan)

Look at `design-notes.md` for these patterns — each one needs an outline.

### Block Outlines (kind="block") — MOST IMPORTANT

Every page group should have **at least 1-2 block outlines**. These are the dashboard panels that give business users at-a-glance insight. Look for these in the HTML prototypes:

| HTML Pattern | ctx_info Example |
|---|---|
| Distribution chart (pie/donut/bar) | `{"type":"distribution","title":"客户行业分布","collection":"nb_crm_customers","group_by":"industry","display":"pie"}` |
| Funnel / pipeline stages | `{"type":"funnel","title":"招聘漏斗","collection":"nb_hr_candidates","stage_field":"status","stages":["待筛选","面试中","已录用","已入职"]}` |
| Summary card (multi-metric) | `{"type":"summary-card","title":"本月薪资总览","collection":"nb_hr_payroll","metrics":["base_salary:sum","bonus:sum","net_salary:sum"],"period_field":"period"}` |
| Trend / timeline | `{"type":"trend","title":"合同金额趋势","collection":"nb_crm_contracts","value_field":"amount","date_field":"start_date","granularity":"month"}` |
| Expiry / alert list | `{"type":"alert-list","title":"即将到期合同","collection":"nb_hr_contracts","date_field":"end_date","warn_days":90,"display_fields":["employee.name","end_date"]}` |
| Ranking / top-N | `{"type":"ranking","title":"部门人数TOP5","collection":"nb_hr_employees","group_by":"department.name","metric":"count","limit":5}` |
| KPI dashboard (beyond simple count) | `{"type":"kpi-dashboard","title":"考勤统计","collection":"nb_hr_attendance","metrics":[{"label":"出勤率","calc":"status=正常/total"},{"label":"迟到","calc":"status=迟到"}]}` |

### Column Outlines (kind="column")

| HTML Pattern | ctx_info Example |
|---|---|
| Colored status badge/tag | `{"type":"status-tag","field":"status","colors":{"active":"green",...}}` |
| Money ¥X,XXX.XX formatting | `{"type":"money-format","field":"price"}` |
| Date countdown (还剩N天) | `{"type":"countdown","field":"warranty_date","warn_days":30}` |
| Progress bar (usage rate) | `{"type":"progress-bar","field":"used_licenses","max_field":"total_licenses"}` |
| Relative time (2小时前) | `{"type":"relative-time","field":"createdAt","warn_hours":24}` |

### Item Outlines (kind="item")

| HTML Pattern | ctx_info Example |
|---|---|
| Auto-fill current user | `{"type":"auto-fill","field":"reporter","value":"currentUser.nickname"}` |
| Auto-calculate formula | `{"type":"auto-calc","formula":"qty*price","target":"total"}` |
| Cascading field select | `{"type":"cascade","trigger":"asset_id","fill":{"location":"asset.location"}}` |

## Execution Order

Phase 0: `nb_clean_prefix("nb_itsm_")` if rebuilding
Phase 1: `nb_execute_sql` (all CREATE TABLE) → `nb_setup_collection` × N
Phase 2: `nb_execute_sql` × N (INSERT test data, split by table)
Phase 3: `nb_create_menu` → `nb_crud_page_file` (all pages in one file) → `nb_outline` × N (JS enhancements)
Phase 4: Workflows
Phase 5: AI Employees

### Phase 3 Detail: Page Building + Outline

**Step 1: Build ALL pages at once using `nb_crud_page_file`**

Write a JSON file with all page definitions, then call `nb_crud_page_file(file_path)` once.
This is MUCH more reliable than calling `nb_crud_page` per page (avoids parameter encoding issues).

**Dashboard-style layout with `sidebar_outlines`**: Include block outlines directly in the page JSON to get a rich layout where outline blocks appear in a sidebar column (span=9) next to the table (span=15), instead of stacked at the bottom.

```bash
# Write all page definitions to a JSON file
cat > ./pages.json << 'EOF'
[
  {
    "tab_uid": "abc123",
    "collection": "nb_itsm_assets",
    "table_fields": ["name","code","status","location","createdAt"],
    "form_fields": "--- 基本信息\nname* | code\nstatus | location\n--- 备注\ndescription",
    "filter_fields": ["name","status"],
    "kpis_json": [{"title":"资产总数"},{"title":"使用中","filter":{"status":"使用中"},"color":"#52c41a"}],
    "sidebar_outlines": [
      {"title":"资产类型分布","ctx_info":{"type":"distribution","collection":"nb_itsm_assets","group_by":"asset_type","display":"pie"}},
      {"title":"即将过保资产","ctx_info":{"type":"alert-list","collection":"nb_itsm_assets","date_field":"warranty_date","warn_days":30}}
    ]
  },
  {
    "tab_uid": "def456",
    "collection": "nb_itsm_tickets",
    "table_fields": ["ticket_no","title","status","priority","createdAt"],
    "form_fields": "--- 基本信息\nticket_no* | title*\npriority | status\n--- 描述\ndescription",
    "filter_fields": ["title","status","priority"]
  }
]
EOF
```

Then call: `nb_crud_page_file("./pages.json")`

The result contains `grid_uid`, `table_uid`, `create_form`, `edit_form`, and `sidebar_outline_uids` for each page.

**Layout result**:
- Pages **with** `sidebar_outlines`: `[KPIs] → [Filter] → [Table span=15 | Sidebar span=9]`
- Pages **without** `sidebar_outlines`: `[KPIs] → [Filter] → [Table span=24]`
- Not every page needs sidebar blocks — simple CRUD pages (contacts, knowledge base) can skip them.

**Step 2: Create column + item outlines for each page**

Using the UIDs from Step 1:
1. **Column outlines** — status tags, money, countdown, progress bars. Attach to table_uid.
2. **Item outlines** — auto-fill, auto-calc, cascade. Attach to create_form/edit_form UID.

(Block outlines are already created via `sidebar_outlines` in Step 1.)

Example:
```
# After nb_crud_page_file returns results for IT Assets page:
# result = {"grid_uid": "xxx", "table_uid": "yyy", "create_form": "zzz", "sidebar_outline_uids": [...]}

# Column outlines (table rendering)
nb_outline(table_uid, "状态", '{"type":"status-tag","field":"status","colors":{"使用中":"green","闲置":"blue","维修中":"orange","已报废":"red"}}', kind="column")
nb_outline(table_uid, "采购价", '{"type":"money-format","field":"purchase_price"}', kind="column")
nb_outline(table_uid, "保修到期", '{"type":"countdown","field":"warranty_date","warn_days":30}', kind="column")

# 4. Item outlines (form events)
nb_outline(form_grid, "自动填充使用人", '{"type":"auto-fill","field":"assigned_to","value":"currentUser.nickname"}', kind="item")
```

## Notes

- The HTML prototypes are the "design spec" — extract structure from them, not from imagination
- Every special rendering in design-notes.md should have a corresponding outline
- The outlines don't need JS code — just enough context for a JS agent to implement later
- Write progress and outline counts to ./notes.md after each page
