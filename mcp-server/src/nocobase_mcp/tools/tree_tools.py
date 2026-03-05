"""Tree-based page tools — compose pages from free-form block definitions.

These tools complement the tree_builder module by exposing tree operations
as MCP tools for AI agents.
"""

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import get_nb_client
from ..tree_builder import TreeBuilder
from ..utils import safe_json, resolve_file


def register_tools(mcp: FastMCP):
    """Register tree-based page tools on the MCP server."""

    @mcp.tool()
    def nb_compose_page(tab_uid: str, blocks_json: str,
                        layout_json: Optional[str] = None) -> str:
        """Build a page from free-form block definitions — any blocks, any layout.

        Unlike nb_crud_page which forces a KPI+Filter+Table+Form pattern,
        compose_page lets you freely combine any blocks in any layout.

        Args:
            tab_uid: Tab UID (from nb_create_page or nb_create_menu)
            blocks_json: JSON array of block definitions. Each block:
                - id:   label for layout reference (default "block_0", etc.)
                - type: "table" | "filter" | "form" | "detail" | "js" | "kpi" | "outline"
                Block-specific fields:
                  table:   collection, fields (list), title?, first_click? (default true),
                           addnew_fields? (DSL str), edit_fields? (DSL str),
                           detail_tabs? (list of tab defs),
                           js_columns? — DSL format (preferred):
                             [{"type":"composite","title":"客户","field":"name","subs":["city","source"]},
                              {"type":"currency","title":"金额","field":"amount","threshold":100000},
                              {"type":"countdown","title":"到期","field":"end_date"},
                              {"type":"progress","title":"概率","field":"probability"},
                              {"type":"relative_time","title":"最近","field":"createdAt"},
                              {"type":"stars","title":"评分","field":"satisfaction"},
                              {"type":"comparison","title":"达成","target":"target_amount","actual":"actual_amount"}]
                             Legacy format also supported: {"title":"...","code":"raw JS","width":120}
                  filter:  collection, fields (list), target (block id to filter)
                  form:    collection, fields (DSL str), mode ("create"|"edit"),
                           title?, required? (list)
                  detail:  collection, fields (DSL str), title?
                  js:      title, code
                  kpi:     title, collection, filter?, color?
                  outline: title, ctx_info (dict)
            layout_json: Optional JSON layout — rows of [ref, span] pairs.
                ref = block_id (str) or [id_a, id_b, ...] (stacked column).
                Span uses Ant 24-grid. Omit for auto-stack full-width.
                Column stacking example: [["tbl",16],[["sidebar_a","sidebar_b"],8]]
                puts tbl left (16 wide) and sidebar_a/b stacked right (8 wide).

        Returns:
            JSON with block UIDs, form UIDs, node count, and any warnings.

        Example — dashboard + table with sidebar:
            blocks = [
                {"id":"chart","type":"js","title":"Industry Distribution","code":"..."},
                {"id":"search","type":"filter","collection":"nb_crm_customers",
                 "fields":["name","status"],"target":"tbl"},
                {"id":"tbl","type":"table","collection":"nb_crm_customers",
                 "fields":["name","status","phone","createdAt"],
                 "addnew_fields":"name*|code\\nstatus|industry",
                 "detail_tabs":[{"title":"Info","fields":"name|code\\nstatus"}]}
            ]
            layout = [[["search",24]],[["chart",8],["tbl",16]]]

        Example — simple form page:
            blocks = [
                {"id":"form","type":"form","collection":"nb_crm_feedback",
                 "fields":"--- Customer\\ncustomer*\\n--- Feedback\\ncontent*\\nrating",
                 "mode":"create","title":"Submit Feedback","required":["customer","content"]}
            ]
        """
        nb = get_nb_client()
        blocks = safe_json(blocks_json)
        if not isinstance(blocks, list):
            return json.dumps({"error": "blocks_json must be a JSON array"})
        if not blocks:
            return json.dumps({"error": "blocks list is empty"})

        layout = None
        if layout_json:
            layout = safe_json(layout_json)
            if not isinstance(layout, list):
                return json.dumps({"error": "layout_json must be a JSON array of rows"})

        # Clean existing content
        nb.clean_tab(tab_uid)

        # Build tree in memory
        tb = TreeBuilder(nb)
        try:
            root, meta = tb.compose_page(tab_uid, blocks, layout)
        except Exception as e:
            return json.dumps({"error": str(e)})

        # Save all nodes
        filter_manager = meta.pop("_filter_manager", None)
        nb.save_tree(root, tab_uid, filter_manager=filter_manager)

        # Build result
        result = {k: v for k, v in meta.items() if not k.startswith("_")}
        if nb.warnings:
            result.setdefault("warnings", []).extend(nb.warnings)
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool()
    def nb_compose_page_file(file_path: str) -> str:
        """Build multiple pages from a JSON file using free-form block composition.

        Write a JSON file with an array of page definitions, then call this tool.
        Each page uses the same format as nb_compose_page.

        Args:
            file_path: Path to a JSON file containing an array of page definitions.
                Each item: {
                    "tab_uid": "...",
                    "blocks": [...],     // same as nb_compose_page blocks_json
                    "layout": [...]      // optional, same as nb_compose_page layout_json
                }

        Returns:
            JSON with results for each page.

        Example file content:
            [
              {
                "tab_uid": "abc123",
                "blocks": [
                  {"id":"tbl","type":"table","collection":"customers",
                   "fields":["name","status"],"addnew_fields":"name*\\nstatus"},
                  {"id":"search","type":"filter","collection":"customers",
                   "fields":["name"],"target":"tbl"}
                ],
                "layout": [[["search",24]],[["tbl",24]]]
              }
            ]
        """
        try:
            file_path = resolve_file(file_path)
        except FileNotFoundError as e:
            return json.dumps({"error": str(e)})

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                pages = json.load(f)
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"Invalid JSON: {e}"})

        if not isinstance(pages, list):
            return json.dumps({"error": "File must contain a JSON array"})

        results = []
        for i, page in enumerate(pages):
            try:
                tab = page.get("tab_uid", "")
                blocks = page.get("blocks", [])
                if not tab or not blocks:
                    results.append({"index": i, "error": "Missing tab_uid or blocks"})
                    continue

                layout_str = json.dumps(page["layout"]) if page.get("layout") else None
                r = nb_compose_page(
                    tab_uid=tab,
                    blocks_json=json.dumps(blocks),
                    layout_json=layout_str,
                )
                parsed = json.loads(r)
                parsed["index"] = i
                results.append(parsed)
            except Exception as e:
                results.append({"index": i, "error": str(e)})

        built = len([r for r in results if "error" not in r])
        failed = len([r for r in results if "error" in r])
        return json.dumps({
            "pages_built": built,
            "pages_failed": failed,
            "results": results,
        })
