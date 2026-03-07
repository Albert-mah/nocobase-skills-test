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

Write **Page Task Table** to `notes.md`:
```
### Page Tasks
| # | Page | Collection | Tab UID | Pattern | JS Blocks | JS Cols | Status |
|---|------|-----------|---------|---------|-----------|---------|--------|
| 1 | 客户 | nb_crm_customers | — | A | 行业分布,来源分析 | composite(name,city+source) | [ ] |
```

Also write **Detail & Form Design** for Phase 3B:
- Core pages (高频, 多关联): multi-tab, 2+ js-items, subtables
- Every detail popup MUST have at least one js-item on first tab
- Secondary pages: 1-2 tabs
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
