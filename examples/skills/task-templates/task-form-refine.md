# Task: Refine {FORM_TYPE} for "{PAGE_NAME}"

## Context
- Table UID: {TABLE_UID}
- Collection: {COLLECTION}
- Form type: {FORM_TYPE}
- Available fields: {AVAILABLE_FIELDS}
- Current coverage: {COVERAGE}%

## For addnew/edit

Design field layout with logical sections and side-by-side pairs:
```
--- 基本信息
name* | code
status | grade
--- 联系方式
phone | email
--- 备注
remarks
```

{EVENTS_SPEC}

Call `nb_set_form("{TABLE_UID}", "{FORM_TYPE}", dsl_string{, events_json})`

## For detail — TREAT AS A FULL PAGE

The detail popup is the user's workspace for this record. Design it thoroughly.

**First tab** = record home page:
1. `js_items` — visual summary card at the top (key metrics/status at a glance)
2. `fields` — ALL fields grouped with `---` sections, paired with `|`

**Subsequent tabs** = one per o2m relation:

{PLANNED_TABS}

O2M relations: {O2M_LIST}

Build detail_json array:
```json
[
  {"title": "基本信息",
   "fields": "--- 概况\nname|code\nstatus|grade\n--- 联系方式\nphone|email\n--- 备注\nremarks",
   "js_items": [{"title": "概况卡片", "desc": "关键指标的可视化摘要"}]},
  {"title": "联系人", "assoc": "contacts", "coll": "target_coll",
   "fields": ["name","phone","email","position"]}
]
```

Call `nb_set_detail("{TABLE_UID}", detail_json)`

## Steps
1. Design the layout following context above
2. Call the appropriate tool
3. Update notes.md: mark Form Tasks row as `[done]` or `[fail]`
