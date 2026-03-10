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

### DETAIL TAB 规则

`nb_set_detail` 会自动校验 — 多个 tab 没有 `assoc` 子表关联时工具拒绝执行。

**Tab 1 = "概况"**：主表全部字段用 `--- Section` 分组 + js_items
**Tab 2+ = 仅子表**：每个 o2m 关系一个 tab（必须有 `assoc` 和 `coll`）

同一张表的字段 → 同一个 tab 用 Section 分组。关联子表记录 → 独立 tab。

For each core business page:
1. Refine addnew/edit forms with sections (Fields DSL below)
2. Replace detail popup — first tab = ALL main fields + js_items, subtable tabs only for o2m
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
  {"title": "概况",
   "fields": "--- 基本信息\nname|code\nstatus|grade\n--- 联系方式\nphone|email\n--- 备注\nremarks",
   "js_items": [{"title": "画像", "desc": "等级标签+状态+建档天数"}]},
  {"title": "联系人", "assoc": "contacts", "coll": "nb_crm_contacts",
   "fields": ["name","phone","position"]}
]
```

**注意**：第一个 tab 的 fields 必须包含主表全部可显示字段，用 `---` 分区。
没有子表关系的实体（如工资条、加班记录）只需要 1 个 tab。

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
