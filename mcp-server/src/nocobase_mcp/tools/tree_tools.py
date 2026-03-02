"""Tree-based page tools — get/save full FlowModel trees, template extract/apply.

These tools complement the tree_builder module by exposing tree operations
as MCP tools for AI agents.
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import get_nb_client
from ..tree_builder import TreeBuilder
from ..utils import safe_json


def register_tools(mcp: FastMCP):
    """Register tree-based page tools on the MCP server."""

    @mcp.tool()
    def nb_get_tree(parent_uid: str, sub_key: str = "grid") -> str:
        """Get the complete FlowModel tree under a parent node (with nested subModels).

        Returns the full page tree as JSON — useful for inspecting page structure,
        extracting templates, or debugging layout issues.

        Args:
            parent_uid: UID of the parent FlowModel (e.g. tab UID)
            sub_key: Sub key to query (default "grid")

        Returns:
            JSON with the complete tree structure including all nested subModels.

        Example:
            nb_get_tree("tab_uid_abc123")
        """
        nb = get_nb_client()
        tree = nb.get_tree(parent_uid, sub_key)
        if tree is None:
            return json.dumps({"error": f"No tree found under {parent_uid} with subKey={sub_key}"})
        return json.dumps(tree, ensure_ascii=False)

    @mcp.tool()
    def nb_page_tree(tab_uid: str, tree_json: str) -> str:
        """Save a complete FlowModel page tree in one API call.

        Cleans existing content under the tab first, then submits the entire
        tree structure via flowModels:save with nested subModels.

        Args:
            tab_uid: Tab UID (from nb_create_page or nb_create_menu)
            tree_json: Complete tree JSON string. Must be a valid FlowModel tree
                      with uid, use, stepParams, and optionally subModels.

        Returns:
            JSON with save result and node count.

        Example:
            nb_page_tree("tab123", '{"uid":"abc","use":"BlockGridModel","stepParams":{},"subModels":{...}}')
        """
        nb = get_nb_client()
        tree_data = safe_json(tree_json)
        if not isinstance(tree_data, dict):
            return json.dumps({"error": "tree_json must be a JSON object"})

        # Clean existing content
        count = nb.clean_tab(tab_uid)

        # Save the tree
        r = nb._post("api/flowModels:save", json={
            **tree_data,
            "parentId": tab_uid,
            "subKey": "grid",
            "subType": "object",
        })
        if r.ok:
            return json.dumps({
                "status": "ok",
                "cleaned_nodes": count,
                "root_uid": tree_data.get("uid", "?"),
            })
        return json.dumps({"error": f"Save failed: {r.text[:300]}"})

    @mcp.tool()
    def nb_extract_template(tab_uid: str, collection: str, name: str) -> str:
        """Extract a reusable page template from an existing page.

        Gets the full page tree, then parameterizes it by replacing collection
        names and UIDs with placeholders.

        Args:
            tab_uid: Tab UID of the source page
            collection: Collection name used in the page (will become __COLLECTION__)
            name: Template name for identification

        Returns:
            JSON template that can be applied to other collections via nb_apply_template.

        Example:
            nb_extract_template("tab123", "nb_crm_customers", "crm_crud_template")
        """
        nb = get_nb_client()
        tree = nb.get_tree(tab_uid)
        if tree is None:
            return json.dumps({"error": f"No tree found under tab {tab_uid}"})

        template = TreeBuilder.extract_template(tree, collection, name)
        return json.dumps(template, ensure_ascii=False)

    @mcp.tool()
    def nb_apply_template(
        tab_uid: str,
        template_json: str,
        collection: str,
        field_map: Optional[dict] = None,
    ) -> str:
        """Apply a page template to create a new page for a different collection.

        Takes a template (from nb_extract_template) and instantiates it with
        a new collection name and optional field name mapping.

        Args:
            tab_uid: Tab UID for the new page
            template_json: Template JSON (from nb_extract_template)
            collection: Target collection name
            field_map: Optional dict mapping source field names to target field names.
                      Example: {"customer_name": "supplier_name", "industry": "category"}

        Returns:
            JSON with save result.

        Example:
            nb_apply_template("newtab123", '<template_json>', "nb_crm_suppliers",
                field_map={"customer_name": "supplier_name"})
        """
        nb = get_nb_client()
        template = safe_json(template_json)
        if not isinstance(template, dict):
            return json.dumps({"error": "template_json must be a JSON object"})

        fm = safe_json(field_map) if field_map else None
        tree_data = TreeBuilder.apply_template(template, collection, fm)

        # Clean and save
        count = nb.clean_tab(tab_uid)
        r = nb._post("api/flowModels:save", json={
            **tree_data,
            "parentId": tab_uid,
            "subKey": "grid",
            "subType": "object",
        })
        if r.ok:
            return json.dumps({
                "status": "ok",
                "cleaned_nodes": count,
                "collection": collection,
                "root_uid": tree_data.get("uid", "?"),
            })
        return json.dumps({"error": f"Save failed: {r.text[:300]}"})
