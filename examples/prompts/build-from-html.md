# Build NocoBase System from HTML Prototypes

You have HTML prototype files that show what each page should look like.
Your job: implement the NocoBase CRUD structure + mark JS enhancements as outlines.

## Input Files

- `*.html` — HTML prototype pages (open in browser to see the design)
- `design-notes.md` — summary of all UX patterns, special renderings, auto-fill logic
- `data-model.md` — table definitions and relations (if provided separately)

## How to Read the HTML Prototypes

Each HTML file shows a complete page design. Extract from it:

1. **KPIs** — count cards at the top → map to `kpis_json` parameter
2. **Filter bar** — search fields → map to `filter_fields` parameter
3. **Table columns** — column headers → map to `table_fields` parameter
4. **Forms** — add/edit form sections → map to `form_fields` DSL parameter
5. **Detail drawer** — tabs with sub-tables → map to `detail_json` parameter

## What NocoBase Handles Natively (use nb_crud_page)

- KPI statistic cards (count with filter + color)
- Filter forms (text/select/date range)
- Data tables (column display, sort)
- Add/Edit forms (field layout with sections)
- Detail popups with tabs (fields + sub-tables)
- Select field options with colors (configured during nb_setup_collection)

## What Needs JS Enhancement (use nb_outline to plan)

Look at `design-notes.md` for these patterns — each one needs an outline:

| HTML Pattern | Outline Kind | ctx_info Type |
|---|---|---|
| Colored status badge/tag | `"column"` | `{"type":"status-tag","field":"status","colors":{"active":"green",...}}` |
| Money ¥X,XXX.XX formatting | `"column"` | `{"type":"money-format","field":"price"}` |
| Date countdown (还剩N天) | `"column"` | `{"type":"countdown","field":"warranty_date","warn_days":30}` |
| Progress bar (usage rate) | `"column"` | `{"type":"progress-bar","field":"used_licenses","max_field":"total_licenses","thresholds":[80,95]}` |
| Row highlighting (P1 red) | `"column"` | `{"type":"row-highlight","condition":{"priority":"P1"},"style":"red-border"}` |
| Relative time (2小时前) | `"column"` | `{"type":"relative-time","field":"createdAt","warn_hours":24}` |
| Auto-fill current user | `"item"` | `{"type":"auto-fill","field":"reporter","value":"currentUser.nickname","event":"afterRender"}` |
| Auto-calculate formula | `"item"` | `{"type":"auto-calc","event":"formValuesChange","formula":"qty*price","target":"total"}` |
| Cascading field select | `"item"` | `{"type":"cascade","trigger":"asset_id","fill":{"location":"asset.location"}}` |
| Chart / visualization | `"block"` | `{"type":"chart","chart_type":"pie","title":"Distribution","collection":"...","group_by":"category"}` |

## Execution Order

Phase 0: `nb_clean_prefix("nb_itsm_")` if rebuilding
Phase 1: `nb_execute_sql` (all CREATE TABLE) → `nb_setup_collection` × N
Phase 2: `nb_execute_sql` × N (INSERT test data, split by table)
Phase 3: `nb_create_menu` → `nb_crud_page` × N → `nb_outline` × N (JS enhancements)
Phase 4: Workflows
Phase 5: AI Employees

### Phase 3 Detail: Page Building + Outline

For each page:
1. Call `nb_crud_page(...)` with KPIs, filter, table, form, detail extracted from HTML
2. Read the return value — it contains UIDs for table, form grid, etc.
3. For each special rendering noted in design-notes.md, call `nb_outline(uid, title, ctx_info, kind)`

Example for IT Assets page:
```
# 1. Build CRUD structure
result = nb_crud_page("IT资产", "nb_itsm_assets", ...)

# 2. Plan JS enhancements (outlines)
nb_outline(table_uid, "状态", '{"type":"status-tag","field":"status","colors":{"使用中":"green","闲置":"blue","维修中":"orange","已报废":"red","已丢失":"grey"}}', kind="column")
nb_outline(table_uid, "采购价", '{"type":"money-format","field":"purchase_price"}', kind="column")
nb_outline(table_uid, "保修到期", '{"type":"countdown","field":"warranty_date","warn_days":30}', kind="column")
nb_outline(form_grid, "自动填充使用人", '{"type":"auto-fill","field":"assigned_to","value":"currentUser.nickname"}', kind="item")
```

## Notes

- The HTML prototypes are the "design spec" — extract structure from them, not from imagination
- Every special rendering in design-notes.md should have a corresponding outline
- The outlines don't need JS code — just enough context for a JS agent to implement later
- Write progress and outline counts to ./notes.md after each page
