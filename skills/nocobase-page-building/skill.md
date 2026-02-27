---
name: nocobase-page-building
description: Guide AI to build NocoBase pages — menus, tables, forms, popups, KPIs, JS blocks, outlines, event flows
triggers:
  - 搭建页面
  - 创建菜单
  - 页面
  - 区块
  - page
  - build page
  - create menu
  - table block
  - form
  - outline
  - 大纲
tools:
  - nb_create_group
  - nb_create_page
  - nb_create_menu
  - nb_list_routes
  - nb_delete_route
  - nb_page_layout
  - nb_table_block
  - nb_addnew_form
  - nb_edit_action
  - nb_detail_popup
  - nb_filter_form
  - nb_kpi_block
  - nb_js_block
  - nb_js_column
  - nb_set_layout
  - nb_clean_tab
  - nb_outline
  - nb_event_flow
  - nb_show_page
  - nb_locate_node
  - nb_patch_field
  - nb_patch_column
  - nb_add_field
  - nb_remove_field
  - nb_add_column
  - nb_remove_column
  - nb_list_pages
---

# NocoBase Page Building

You are guiding the user to build pages in NocoBase using FlowModel API. Follow this exact workflow.

## Key Concepts

### Group vs Page
- **Group** (📁): Folder in sidebar. NO content, only holds children.
- **Page** (📄): Has actual content (tables, forms, etc.). Must be under a group.

### FlowModel Tree Structure
```
Tab (RouteModel)
  └── BlockGridModel (layout container)
        ├── TableBlockModel (table)
        │     ├── TableColumnModel (column) → DisplayFieldModel
        │     ├── AddNewActionModel → ChildPageModel → CreateFormModel
        │     ├── TableActionsColumnModel → EditActionModel
        │     └── FilterActionModel, RefreshActionModel
        ├── FilterFormBlockModel (search bar)
        ├── JSBlockModel (custom JS content)
        └── ...more blocks
```

### CRITICAL: FlowModel API is Full Replace
The `flowModels:update` API does a **full replace**, not incremental merge. The client always does GET → deep_merge → PUT internally. Never send partial data.

## Workflow

### Phase 1: Menu Structure

Use `nb_create_menu` for the simplest approach:

```
nb_create_menu("Asset Management", top_group_id,
    '[["Asset Ledger","databaseoutlined"],["Purchases","shoppingcartoutlined"]]',
    group_icon="bankoutlined")
```

This creates a group + pages in one call, returning `{"Asset Ledger": "tab_uid_1", "Purchases": "tab_uid_2"}`.

Or build manually:
1. `nb_create_group("Module Name", parent_id)` — creates the folder
2. `nb_create_page("Page Name", group_id)` — creates each page

### Phase 2: Page Content (Per Page)

For each page, follow this order:

#### Step 1: Create Page Layout
```
nb_page_layout("tab_uid")  →  returns grid_uid
```
This cleans existing content (idempotent) and creates a BlockGridModel.

#### Step 2: Create KPI Cards (Optional)
```
nb_kpi_block(grid, "Total", "nb_pm_projects")
nb_kpi_block(grid, "Active", "nb_pm_projects", filter_='{"status":"active"}', color="#52c41a")
```

#### Step 3: Create Filter/Search Bar
```
nb_filter_form(grid, "nb_pm_projects", '["name","code","description"]', target_uid=table_uid)
```
Note: Create filter AFTER table (needs table_uid for target), but place it ABOVE in layout.

#### Step 4: Create Table Block
```
nb_table_block(grid, "nb_pm_projects",
    '["name","code","status","priority","createdAt"]',
    first_click=true, title="Projects")
```
Returns: `{table_uid, addnew_uid, actcol_uid}`

#### Step 5: Create AddNew Form
```
nb_addnew_form(addnew_uid, "nb_pm_projects",
    "--- Basic Info\nname* | code\nstatus | priority\n--- Details\ndescription")
```

**Fields DSL syntax:**
- `name` — single field, full width
- `name*` — required field
- `name | code` — two fields side by side (auto 12+12)
- `name:16 | code:8` — explicit widths (total=24)
- `--- Section Title` — divider with label
- `---` — plain divider

#### Step 6: Create Edit Action
```
nb_edit_action(actcol_uid, "nb_pm_projects",
    "--- Basic Info\nname* | code\nstatus | priority\n--- Details\ndescription")
```

#### Step 7: Set Layout
```
nb_set_layout(grid_uid, '[
    [["kpi1",6],["kpi2",6],["kpi3",6],["kpi4",6]],
    [["filter1"]],
    [["table1"]]
]')
```

Layout rules:
- Each row is an array of `[uid, span]` pairs
- Spans use Ant Design grid (total = 24 per row)
- `[["uid"]]` or `[["uid",24]]` = full width
- `[["a",12],["b",12]]` = two equal columns

#### Step 8: Detail Popup (Optional)
```
nb_detail_popup(click_field_uid, "nb_pm_projects", '[
    {"title":"Info", "fields":"--- Basic\\nname | code\\nstatus"},
    {"title":"Tasks", "assoc":"tasks", "coll":"nb_pm_tasks", "fields":["name","status"]}
]', mode="drawer", size="large")
```

**Detail popup modes:**
- `mode="drawer"` + `size="large"` — side panel, good for business detail pages
- `mode="drawer"` + `size="medium"` — smaller side panel, for reference data
- `mode="dialog"` + `size="small"` — modal dialog, for quick views

**Finding the click field UID:**
The first column in a table created with `first_click=true` is clickable. Use the click_field_uid from the column's DisplayFieldModel. The field_name passed to the find function must match the first column's field name.

**Multi-tab detail popup with sub-tables:**
```json
[
    {"title": "Details", "blocks": [
        {"type": "details", "fields": "--- Section 1\\nfield1 | field2\\nfield3"}
    ]},
    {"title": "Sub Items", "assoc": "items", "coll": "nb_order_items",
     "fields": ["name", "quantity", "price", "createdAt"]}
]
```
Note: The `assoc` sub-table requires an o2m relation to be defined between the parent and child collections.

#### Step 9: Outlines — Plan JS Capabilities (Recommended)
Use `nb_outline` to plan JS blocks/columns without writing actual code.
A dedicated JS agent implements them later.
```
# KPI outline (page-level block)
nb_outline(grid, "Active Count", '{"type":"kpi","collection":"assets","filter":{"status":"active"}}')

# Table JS column outline
nb_outline(table_uid, "Status Tag", '{"type":"status-tag","field":"status","colors":{"active":"green"}}', kind="column")

# Event flow outline (in form)
nb_outline(form_grid, "Auto Total", '{"type":"event-flow","event":"formValuesChange","formula":"qty*price"}', kind="item")
```

#### Step 10: Event Flows (Optional)
```
nb_event_flow(form_uid, "formValuesChange",
    "const v=ctx.form?.values||{}; if(v.qty&&v.price) ctx.form.setFieldsValue({total:v.qty*v.price});")
```

#### Step 11: JS Columns — Direct Implementation (Alternative to Outlines)
```
nb_js_column(table_uid, "Status",
    "const s=(ctx.record||{}).status;ctx.render(ctx.React.createElement(ctx.antd.Tag,{color:s==='active'?'green':'red'},s||'-'))",
    width=100)
```

### Phase 3: Verify
```
nb_show_page("Page Title")  # Check the structure tree
```

## Common Patterns

### Standard CRUD Page
1. `page_layout` → grid
2. `kpi_block` × N → kpi cards
3. `table_block` → table + addnew + actcol
4. `filter_form` → search bar (target=table)
5. `addnew_form` → new record form
6. `edit_action` → edit record form
7. `set_layout` → arrange: KPIs row → filter → table
8. Optionally: `detail_popup`, `js_column`

### KPI Row Pattern
```
kpi1 = nb_kpi_block(grid, "Total", collection)
kpi2 = nb_kpi_block(grid, "Active", collection, filter_='{"status":"active"}', color="#52c41a")
kpi3 = nb_kpi_block(grid, "Pending", collection, filter_='{"status":"pending"}', color="#faad14")
# Then in layout: [["kpi1",8],["kpi2",8],["kpi3",8]]
```

### Multi-Block Detail Popup
```json
[
    {"title": "Overview", "blocks": [
        {"type": "details", "title": "Info", "fields": "name | code\nstatus"},
        {"type": "js", "title": "Stats", "code": "ctx.render(...)"}
    ], "sizes": [14, 10]},
    {"title": "Tasks", "assoc": "tasks", "coll": "nb_pm_tasks",
     "fields": ["name", "status", "createdAt"]}
]
```

### Page Modification (Incremental)
For tweaking existing pages, use the page maintenance tools:
```
nb_show_page("Page Title")           # See the structure
nb_locate_node("Page Title", field="status")  # Find a node
nb_patch_field(uid, '{"required":true}')       # Modify it
nb_add_column(table_uid, collection, "new_field")  # Add column
nb_remove_column(column_uid)                        # Remove column
```

## Ant Design Icons
Common icons for menus: `homeoutlined`, `settingoutlined`, `databaseoutlined`,
`shoppingcartoutlined`, `bankoutlined`, `tooloutlined`, `formoutlined`,
`barchartoutlined`, `piechartoutlined`, `idcardoutlined`, `caroutlined`,
`containeroutlined`, `clusteroutlined`, `apartmentoutlined`, `environmentoutlined`,
`shopoutlined`, `controloutlined`, `appstoreoutlined`, `inboxoutlined`,
`deleteoutlined`, `swapoutlined`, `sendoutlined`

## Status Tag Colors
For `ctx.antd.Tag` in JS columns/blocks:
- Green: active, completed, approved → `color: 'green'` or `'#52c41a'`
- Blue: in progress, processing → `color: 'blue'` or `'#1890ff'`
- Orange: pending, warning → `color: 'orange'` or `'#faad14'`
- Red: error, rejected, overdue → `color: 'red'` or `'#ff4d4f'`
- Default: draft, inactive → `color: 'default'`
