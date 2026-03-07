# Phase 3B: Form & Detail Refinement

## Tools

| Tool | Purpose |
|------|---------|
| nb_auto_forms(scope) | Scan forms, generate task table with coverage % |
| nb_set_form(table_uid, type, dsl, events?) | Replace addnew/edit form |
| nb_set_detail(table_uid, detail_json) | Replace detail popup with tabs |

## Step 3B.1: Scan Form Quality [sequential]

Call `nb_auto_forms("{PREFIX}")`. Copy task table to `notes.md`.
Cross-reference with "Detail & Form Design" from Phase 3.

## Step 3B.2: Refine Forms & Details

**Read `ref/detail-patterns.md` now** — it has detail JSON examples and design rules.

For each core business page:
1. Refine addnew/edit forms with sections (Fields DSL below)
2. Replace detail popup with multi-tab structure (detail JSON below)
3. Mark `[x]` in notes.md after each

### Fields DSL (for nb_set_form)
```
--- 基本信息
name* | code
status | grade
--- 联系方式
phone | email
```

### Detail JSON (for nb_set_detail)
```json
[
  {"title": "概况", "fields": "name|code\nstatus|grade",
   "js_items": [{"title": "画像", "desc": "等级标签+状态+建档天数"}]},
  {"title": "联系人", "assoc": "contacts", "coll": "nb_crm_contacts",
   "fields": ["name","phone","position"]}
]
```

### Events (optional)
```python
nb_set_form(table_uid, "addnew", dsl,
    [{"on": "formValuesChange", "desc": "stage变化时映射probability"}])
```

## Step 3B.3: Verify [sequential]

- Re-run `nb_auto_forms` — all should be `[ok]`
- Update notes.md: `## Status: Phase 3B complete`, `## Next: phases/phase-4-js.md`

## After Phase 3B

Summarize to user: forms refined, detail popups created.
Ask: "表单和详情弹窗已优化，点击 Add New 和表格行试试？有需要调整的吗？"
Wait for user response.

Next → `phases/phase-4-js.md`
