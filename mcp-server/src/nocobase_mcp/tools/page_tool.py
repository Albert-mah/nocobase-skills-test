"""Page maintenance tools — show, locate, patch, add/remove fields and columns.

Extracted from nb_page_tool.py (PageTool class).
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import get_nb_client, NB, DISPLAY_MAP, EDIT_MAP
from ..utils import uid, deep_merge, safe_json


class PageTool:
    """FlowModel page CRUD operations."""

    def __init__(self, nb: NB):
        self.nb = nb
        self._models = None
        self._routes = None

    def _load_models(self, force=False):
        if self._models and not force:
            return self._models
        r = self.nb.s.get(f"{self.nb.base}/api/flowModels:list?paginate=false")
        self._models = r.json().get("data", [])
        return self._models

    def _load_routes(self, force=False):
        if self._routes and not force:
            return self._routes
        r = self.nb.s.get(f"{self.nb.base}/api/desktopRoutes:list",
                          params={"paginate": "false", "tree": "true"})
        self._routes = r.json().get("data", [])
        return self._routes

    def _children_map(self):
        models = self._load_models()
        cm = {}
        for m in models:
            pid = m.get("parentId")
            if pid:
                cm.setdefault(pid, []).append(m)
        return cm

    def _model_by_uid(self, uid_):
        for m in self._load_models():
            if m["uid"] == uid_:
                return m
        return None

    def _find_tab_uid(self, page_title):
        routes = self._load_routes()
        for rt in routes:
            found = self._search_route(rt, page_title)
            if found:
                return found
        return None

    def _search_route(self, route, title):
        t = route.get("title") or ""
        if t == title and route.get("type") == "flowPage":
            children = route.get("children", [])
            for c in children:
                if c.get("type") == "tabs" and c.get("schemaUid"):
                    return c["schemaUid"]
            for c in children:
                if c.get("schemaUid"):
                    return c["schemaUid"]
        for child in route.get("children", []):
            found = self._search_route(child, title)
            if found:
                return found
        return None

    def _build_tree(self, root_uid, cm=None):
        if cm is None:
            cm = self._children_map()
        node = self._model_by_uid(root_uid) or {"uid": root_uid, "use": "?"}
        children = sorted(cm.get(root_uid, []), key=lambda m: m.get("sortIndex", 0))
        return {
            "uid": node["uid"],
            "use": node.get("use", "?"),
            "subKey": node.get("subKey", ""),
            "sortIndex": node.get("sortIndex", 0),
            "stepParams": node.get("stepParams", {}),
            "children": [self._build_tree(c["uid"], cm) for c in children],
        }

    def _format_tree(self, node, depth, lines):
        indent = "  " * depth
        use = node["use"]
        u = node["uid"]
        sp = node.get("stepParams", {})
        info = []
        fs = sp.get("fieldSettings", {}).get("init", {})
        if fs.get("fieldPath"):
            info.append(f"field={fs['fieldPath']}")
        if fs.get("collectionName"):
            info.append(f"coll={fs['collectionName']}")
        rs = sp.get("resourceSettings", {}).get("init", {})
        if rs.get("collectionName"):
            info.append(f"coll={rs['collectionName']}")
        cs = sp.get("cardSettings", {}).get("titleDescription", {})
        if cs.get("title"):
            info.append(f"title={cs['title']}")
        ts = sp.get("tableColumnSettings", {})
        if ts.get("title", {}).get("title"):
            info.append(f"title={ts['title']['title']}")
        detail = f" ({', '.join(info)})" if info else ""
        lines.append(f"{indent}{use} [{u}]{detail}")
        for child in node.get("children", []):
            self._format_tree(child, depth + 1, lines)

    def _find_in_tree(self, node, block, field):
        use = node["use"]
        sp = node.get("stepParams", {})
        if block and not field:
            block_map = {
                "table": "TableBlockModel", "addnew": "AddNewActionModel",
                "edit": "EditActionModel", "filter": "FilterFormModel",
                "details": "DetailsBlockModel", "form_create": "CreateFormModel",
                "form_edit": "EditFormModel",
            }
            target_use = block_map.get(block, block)
            if use == target_use:
                return node["uid"]
        if field:
            fp = sp.get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
            if fp == field:
                return node["uid"]
        for child in node.get("children", []):
            found = self._find_in_tree(child, block, field)
            if found:
                return found
        return None

    def show(self, page_title):
        tab_uid = self._find_tab_uid(page_title)
        if not tab_uid:
            return None, f"Page '{page_title}' not found"
        cm = self._children_map()
        tree = self._build_tree(tab_uid, cm)
        lines = []
        self._format_tree(tree, 0, lines)
        return tree, "\n".join(lines)

    def locate(self, page_title, block=None, field=None):
        tab_uid = self._find_tab_uid(page_title)
        if not tab_uid:
            return None
        cm = self._children_map()
        tree = self._build_tree(tab_uid, cm)
        return self._find_in_tree(tree, block, field)

    def pages(self):
        routes = self._load_routes()
        result = []
        self._collect_pages(routes, result, "")
        return result

    def _collect_pages(self, routes, result, prefix):
        for rt in routes:
            title = rt.get("title") or ""
            rtype = rt.get("type") or ""
            path = f"{prefix}/{title}" if prefix else title
            if rtype == "flowPage":
                children = rt.get("children", [])
                tab_uid = None
                for c in children:
                    if c.get("type") == "tabs" and c.get("schemaUid"):
                        tab_uid = c["schemaUid"]
                        break
                result.append({"title": title, "path": path, "tab_uid": tab_uid,
                               "route_id": rt.get("id")})
            for child in rt.get("children", []):
                self._collect_pages([child], result, path)


def register_tools(mcp: FastMCP):
    """Register page maintenance tools on the MCP server."""

    @mcp.tool()
    def nb_show_page(page_title: str) -> str:
        """Show the FlowModel structure tree of a page.

        Displays all blocks, fields, and actions in a hierarchical tree format,
        including UIDs for use with other tools.

        Args:
            page_title: Page title as shown in the sidebar menu

        Returns:
            Tree structure text or error message.

        Example:
            nb_show_page("Asset Ledger")
        """
        nb = get_nb_client()
        pt = PageTool(nb)
        tree, text = pt.show(page_title)
        if tree is None:
            return text
        return text

    @mcp.tool()
    def nb_locate_node(
        page_title: str,
        block: Optional[str] = None,
        field: Optional[str] = None,
    ) -> str:
        """Locate a specific node's UID in a page.

        Find a block or field by type and/or name, returning its UID for
        use with patch/add/remove tools.

        Args:
            page_title: Page title
            block: Block type to find: "table", "addnew", "edit", "filter",
                   "details", "form_create", "form_edit"
            field: Field name to find (e.g. "name", "status")

        Returns:
            UID of the found node, or error message.

        Example:
            nb_locate_node("Asset Ledger", block="table")
            nb_locate_node("Asset Ledger", field="status")
        """
        nb = get_nb_client()
        pt = PageTool(nb)
        uid_ = pt.locate(page_title, block=block, field=field)
        if uid_:
            return json.dumps({"uid": uid_})
        return "Not found"

    @mcp.tool()
    def nb_patch_field(uid: str, props: str) -> str:
        """Modify properties of a form field node.

        Args:
            uid: FormItemModel UID (from nb_locate_node or nb_show_page)
            props: JSON object of properties to set. Supported keys:
                - description: Help text below the field
                - defaultValue: Default value
                - placeholder: Input placeholder text
                - tooltip: Tooltip text
                - hidden: Hide field (boolean)
                - disabled: Disable field (boolean)
                - required: Required field (boolean)
                - pattern: Validation regex pattern

        Returns:
            Success or error message.

        Example:
            nb_patch_field("abc123", '{"description":"Enter full name","required":true}')
        """
        nb = get_nb_client()
        kwargs = safe_json(props)

        patch = {}
        eis = {}
        for k, v in kwargs.items():
            if k == "description":
                eis["description"] = {"description": v}
            elif k == "defaultValue":
                eis["initialValue"] = {"defaultValue": v}
            elif k == "placeholder":
                eis["placeholder"] = {"placeholder": v}
            elif k == "tooltip":
                eis["tooltip"] = {"tooltip": v}
            elif k in ("hidden", "disabled"):
                eis[k] = {k: bool(v)}
            elif k == "required":
                eis["required"] = {"required": bool(v)}
            elif k == "pattern":
                eis["pattern"] = {"pattern": v}
        if eis:
            patch["stepParams"] = {"editItemSettings": eis}
        if not patch:
            return "No valid properties to patch"

        ok = nb.update(uid, patch)
        return f"Patched {uid}: {list(kwargs.keys())}" if ok else f"Failed to patch {uid}"

    @mcp.tool()
    def nb_patch_column(uid: str, props: str) -> str:
        """Modify properties of a table column.

        Args:
            uid: TableColumnModel UID
            props: JSON object of properties. Supported keys:
                - width: Column width in pixels (int)
                - title: Column header title (str)

        Returns:
            Success or error message.

        Example:
            nb_patch_column("abc123", '{"width":120,"title":"New Title"}')
        """
        nb = get_nb_client()
        kwargs = safe_json(props)

        patch = {}
        tcs = {}
        if "width" in kwargs:
            tcs["width"] = {"width": kwargs["width"]}
        if "title" in kwargs:
            tcs["title"] = {"title": kwargs["title"]}
        if tcs:
            patch["stepParams"] = {"tableColumnSettings": tcs}
        if not patch:
            return "No valid properties to patch"

        ok = nb.update(uid, patch)
        return f"Patched column {uid}: {list(kwargs.keys())}" if ok else f"Failed to patch {uid}"

    @mcp.tool()
    def nb_add_field(form_grid_uid: str, collection: str, field: str,
                     after: Optional[str] = None, required: bool = False) -> str:
        """Add a field to an existing form.

        Args:
            form_grid_uid: FormGridModel UID (locate with nb_locate_node)
            collection: Collection name
            field: Field name to add
            after: Insert after this field name. None = append at end.
            required: Mark as required field

        Returns:
            JSON with field_uid.
        """
        nb = get_nb_client()
        pt = PageTool(nb)
        model = pt._model_by_uid(form_grid_uid)
        if not model:
            return f"FormGridModel {form_grid_uid} not found"

        cm = pt._children_map()
        children = cm.get(form_grid_uid, [])
        max_sort = max((c.get("sortIndex", 0) for c in children), default=-1) + 1

        if after:
            for c in children:
                fp = c.get("stepParams", {}).get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
                if fp == after:
                    max_sort = c.get("sortIndex", 0) + 1
                    break

        fi = nb.form_field(form_grid_uid, collection, field, max_sort, required=required)

        # Update gridSettings
        gs = model.get("stepParams", {}).get("gridSettings", {}).get("grid", {})
        rows = gs.get("rows", {})
        sizes = gs.get("sizes", {})
        new_row_id = uid()
        rows[new_row_id] = [[fi]]
        sizes[new_row_id] = [24]
        nb.update(form_grid_uid, {"stepParams": {"gridSettings": {"grid": {"rows": rows, "sizes": sizes}}}})

        return json.dumps({"field_uid": fi})

    @mcp.tool()
    def nb_remove_field(uid: str) -> str:
        """Remove a form field (FormItemModel and its children).

        Note: Does not automatically update parent FormGridModel's gridSettings.
        For a clean result, consider clean_tab + rebuild.

        Args:
            uid: FormItemModel UID to remove

        Returns:
            Success message.
        """
        nb = get_nb_client()
        count = nb.destroy_tree(uid)
        return f"Removed field {uid} ({count} nodes deleted)"

    @mcp.tool()
    def nb_add_column(table_uid: str, collection: str, field: str,
                      width: Optional[int] = None) -> str:
        """Add a column to an existing table.

        Args:
            table_uid: TableBlockModel UID
            collection: Collection name
            field: Field name for the new column
            width: Optional fixed column width in pixels

        Returns:
            JSON with column_uid.
        """
        nb = get_nb_client()
        pt = PageTool(nb)
        cm = pt._children_map()
        children = [c for c in cm.get(table_uid, []) if c.get("subKey") == "columns"]
        sort = max((c.get("sortIndex", 0) for c in children), default=-1) + 1
        cu, fu = nb.col(table_uid, collection, field, sort, width=width)
        return json.dumps({"column_uid": cu})

    @mcp.tool()
    def nb_remove_column(uid: str) -> str:
        """Remove a table column and its children.

        Args:
            uid: TableColumnModel UID to remove

        Returns:
            Success message.
        """
        nb = get_nb_client()
        count = nb.destroy_tree(uid)
        return f"Removed column {uid} ({count} nodes deleted)"

    @mcp.tool()
    def nb_list_pages() -> str:
        """List all flowPage pages with their tab UIDs and paths.

        Returns:
            Formatted list of pages.
        """
        nb = get_nb_client()
        pt = PageTool(nb)
        pages = pt.pages()
        if not pages:
            return "No pages found"
        lines = [f"{'Path':<40} {'Tab UID':<15} {'Route ID'}"]
        lines.append(f"{'─'*40} {'─'*15} {'─'*10}")
        for p in pages:
            lines.append(f"{p['path']:<40} {p['tab_uid'] or 'N/A':<15} {p['route_id']}")
        return "\n".join(lines)
