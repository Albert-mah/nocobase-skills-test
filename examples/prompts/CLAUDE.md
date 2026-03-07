# NocoBase System Build

This file is a **workdir CLAUDE.md template**. Copy to your workdir and it will be auto-loaded by Claude Code / Kimi.

For the full skill base (layered prompts, phase files, task templates), see `examples/skills/`.

## Entry Point

Read `examples/skills/boot.md` — then follow the phase index.

## Quick Reference (for workdir CLAUDE.md)

When using this as a workdir CLAUDE.md, paste the content of `boot.md` below so the agent has it on start:

---

# NocoBase System Builder

You build NocoBase systems using MCP tools from the `nocobase` server.

## MCP Tool Categories

- **Data**: nb_execute_sql, nb_setup_collection, nb_fields, nb_clean_prefix
- **Pages**: nb_page_markup, nb_page_markup_file, nb_create_menu, nb_crud_page
- **Forms**: nb_auto_forms, nb_set_form, nb_set_detail
- **JS**: nb_auto_js, nb_find_placeholders, nb_inject_js, nb_inject_js_dir
- **Workflows**: nb_create_workflow, nb_add_node, nb_enable_workflow
- **AI**: nb_create_ai_employee, nb_ai_shortcut, nb_ai_button
- **Debug**: nb_inspect_all, nb_page_map, nb_fields

## State: notes.md

All state lives in `notes.md`. This is your memory across sessions and agents.

**On start**: Read notes.md → find `## Status` → read phase file → find first `[todo]` → execute.
**On every step**: Write results immediately. Mark tasks `[done]` or `[fail]`. Record UIDs, field names, enum values.
**On phase complete**: Update `## Status: Phase N complete` → read next phase file.

## Phases

Read phase instructions from `examples/skills/phases/`:

| # | File | After | Parallel? |
|---|------|-------|-----------|
| 0 | phase-0-init.md | — | no |
| 1 | phase-1-data.md | 0 | no |
| 2 | phase-2-fields.md | 1 | per collection |
| 3 | phase-3-pages.md | 2 | per page |
| 3B | phase-3b-forms.md | 3 | per form |
| 4 | phase-4-js.md | 3B | per placeholder |
| 5 | phase-5-workflows.md | 1 | per workflow |
| 6 | phase-6-ai.md | 3 | per employee |
| 7 | phase-7-verify.md | 4+5+6 | no |

## Rules (always apply)

1. NO system columns in DDL (created_at, updated_at, created_by_id, updated_by_id)
2. Clean before rebuild: `nb_clean_prefix("prefix")`
3. Write progress to notes.md after EVERY step
4. If a tool fails, note the error — do not retry more than once
