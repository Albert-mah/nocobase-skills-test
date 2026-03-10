# Phase 3: Menu & Pages

## Tools

| Tool | Purpose |
|------|---------|
| nb_create_menu(title, parent_id, pages, icon) | Create menu group + pages, returns tab UIDs |
| nb_page_markup(tab_uid, markup) | Build one page from XML |
| nb_page_markup_file(file_path) | Build multiple pages from JSON file |
| nb_inspect_all(prefix) | Verify built pages |

## Step 3.1: Design ALL Pages [sequential]

Read requirements + HTML prototypes. For each page, decide layout pattern and JS blocks.
**Read `ref/layout-patterns.md` now** — it has patterns A-F and XML tag reference.

### LAYOUT RULES (CRITICAL — violations make pages look like plain CRUD)

1. **Every non-reference page MUST use `<row>` with `span`** — table + sidebar 布局
2. **Sidebar 必须有 `<js-block>` 图表/统计** — 不能只有表格
3. **KPI strip `<row>` 在最上面** — 3-5 个 `<kpi>` 并排
4. **Filter 紧贴 table 上方**
5. **禁止全宽堆叠** — 不能所有元素都 span=24 纵向排列

```xml
<!-- ✅ 正确：table + sidebar -->
<row>
  <table id="tbl" span="16" fields="..." />
  <stack span="8">
    <js-block title="XX分布">按XX字段分组统计饼图</js-block>
    <js-block title="XX趋势">近30天折线图</js-block>
  </stack>
</row>

<!-- ❌ 错误：纯 CRUD，没有图表和布局 -->
<filter fields="..." target="tbl" />
<table id="tbl" fields="..." />
```

Write **Page Task Table** to `notes.md`:
```
### Page Tasks
| # | Page | Collection | Tab UID | Pattern | JS Blocks | JS Cols | Status |
|---|------|-----------|---------|---------|-----------|---------|--------|
| 1 | 客户 | nb_crm_customers | — | A | 行业分布,来源分析 | composite(name,city+source) | [ ] |
```

Also write **Detail & Form Design** for Phase 3B:
- Core pages (高频, 多关联): 第一个tab放全部字段+js-items, 子表独立tab
- Every detail popup first tab MUST have at least one js-item
- Secondary pages: 1 tab (全字段+1 js-item)
- Reference/Config: auto (skip in Phase 3B)

## Step 3.2: Create Menu [sequential]

Always create **top-level group** first, then sub-groups:
```
nb_create_menu("CRM", null, [])                    → gid
nb_create_menu("客户管理", gid, ["客户","联系人"])   → sub-group + pages
```

Fill Tab UID column in Page Task Table.

## Step 3.3: Build Pages [each page = 1 task]

For each `[ ]` row, build the page with `nb_page_markup(tab_uid, xml)`.
**Build order**: Reference/Config pages first (simple), then Core pages.
Mark `[x]` after each page.

## Step 3.4: Verify [sequential]

- `nb_inspect_all("{prefix}")` — check structure
- Fix broken: `nb_clean_tab(tab_uid)` → rebuild
- Update notes.md: all `[x]`, `## Status: Phase 3 complete`, `## Next: phases/phase-3b-forms.md`

## After Phase 3

Summarize to user: pages built, menu structure, `nb_inspect_all` output.
Ask: "页面骨架已搭好，你可以在 NocoBase 里看看效果。有需要调整的吗？"
Wait for user response.

Next → `phases/phase-3b-forms.md`
