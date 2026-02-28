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

    # ── Page Inspect ──────────────────────────────────────────────

    def inspect(self, page_title):
        """Generate a compact visual representation of a page's structure."""
        tab_uid = self._find_tab_uid(page_title)
        if not tab_uid:
            return f"Page '{page_title}' not found"
        cm = self._children_map()
        tree = self._build_tree(tab_uid, cm)
        lines = [f"[{page_title}] tab={tab_uid}"]
        # Find the BlockGridModel
        grids = [c for c in tree.get("children", []) if "BlockGrid" in c.get("use", "")]
        if not grids:
            lines.append("  (empty page — no BlockGridModel)")
            return "\n".join(lines)
        grid = grids[0]
        gs = grid.get("stepParams", {}).get("gridSettings", {}).get("grid", {})
        rows = gs.get("rows", {})
        sizes = gs.get("sizes", {})
        # Map uid → child node for quick lookup
        block_map = {c["uid"]: c for c in grid.get("children", [])}
        # Build row display
        row_items = sorted(rows.items(), key=lambda kv: list(rows.keys()).index(kv[0]))
        for ri, (row_id, cols) in enumerate(row_items):
            row_sizes = sizes.get(row_id, [24] * len(cols))
            is_last = ri == len(row_items) - 1
            prefix = "└─" if is_last else "├─"
            size_str = "|".join(str(s) for s in row_sizes)
            # Collect block descriptions for this row
            col_descs = []
            sub_lines = []  # extra lines for table details
            for ci, col_uids in enumerate(cols):
                for buid in col_uids:
                    node = block_map.get(buid)
                    if not node:
                        col_descs.append(f"[? {buid[:8]}]")
                        continue
                    desc, extras = self._describe_block(node, cm)
                    col_descs.append(desc)
                    sub_lines.extend(extras)
            blocks_str = " ".join(col_descs)
            lines.append(f"  {prefix} ROW {ri+1} ({size_str}): {blocks_str}")
            # Sub-lines (table details) indented under the row
            pad = "  │  " if not is_last else "     "
            for sl in sub_lines:
                lines.append(f"  {pad}  {sl}")
        # Check for AI shortcuts
        shortcuts = [c for c in tree.get("children", [])
                     if "AIEmployeeShortcut" in c.get("use", "")]
        if shortcuts:
            names = []
            for sc in shortcuts:
                for ch in sc.get("children", []):
                    sp = ch.get("stepParams", {})
                    un = sp.get("aiEmployeeShortcutSettings", {}).get("init", {}).get("aiEmployee", "")
                    if un:
                        names.append(un)
            if names:
                lines.append(f"  🤖 AI Shortcuts: {', '.join(names)}")
        return "\n".join(lines)

    def _describe_block(self, node, cm):
        """Return (short_desc, [extra_lines]) for a block node."""
        use = node.get("use", "")
        sp = node.get("stepParams", {})
        children = sorted(cm.get(node["uid"], []), key=lambda m: m.get("sortIndex", 0))
        extras = []

        if "TableBlock" in use:
            coll = sp.get("resourceSettings", {}).get("init", {}).get("collectionName", "?")
            title = sp.get("cardSettings", {}).get("titleDescription", {}).get("title", "")
            # Get column names
            col_children = sorted(cm.get(node["uid"], []), key=lambda m: m.get("sortIndex", 0))
            col_names = []
            addnew_info = edit_info = detail_info = None
            for ch in col_children:
                ch_use = ch.get("use", "")
                if "TableColumn" in ch_use and "Actions" not in ch_use:
                    fp = ch.get("stepParams", {}).get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
                    if fp:
                        col_names.append(fp)
                    else:
                        ct = ch.get("stepParams", {}).get("tableColumnSettings", {}).get("title", {}).get("title", "")
                        col_names.append(f"[JS:{ct}]" if "JS" in ch_use else ct or "?")
                elif "JSColumn" in ch_use:
                    ct = ch.get("stepParams", {}).get("tableColumnSettings", {}).get("title", {}).get("title", "")
                    col_names.append(f"[JS:{ct}]")
                elif "AddNew" in ch_use:
                    addnew_info = self._describe_action(ch, cm)
                elif "ActionsColumn" in ch_use or "TableActions" in ch_use:
                    # Look inside for EditAction and detail popup
                    for act in sorted(cm.get(ch["uid"], []), key=lambda m: m.get("sortIndex", 0)):
                        if "Edit" in act.get("use", ""):
                            edit_info = self._describe_action(act, cm)
                elif "Filter" in ch_use:
                    pass  # handled separately
            cols_str = ",".join(col_names[:8])
            if len(col_names) > 8:
                cols_str += f"...+{len(col_names)-8}"
            title_str = f' "{title}"' if title else ""
            desc = f"[Table{title_str} {coll}: {cols_str}]"
            # Check for detail popup on first column
            detail_info = self._find_detail_popup(col_children, cm)
            if addnew_info:
                extras.append(f"├─ AddNew: {addnew_info}")
            if edit_info:
                extras.append(f"├─ Edit: {edit_info}")
            if detail_info:
                extras.append(f"└─ Detail: {detail_info}")
            return desc, extras

        if "JSBlock" in use:
            title = sp.get("cardSettings", {}).get("titleDescription", {}).get("title", "")
            return f'[KPI "{title}"]', []

        if "FilterForm" in use:
            # Get filter field names
            filter_children = sorted(cm.get(node["uid"], []), key=lambda m: m.get("sortIndex", 0))
            field_names = []
            target = None
            for fc in filter_children:
                for ffc in sorted(cm.get(fc["uid"], []), key=lambda m: m.get("sortIndex", 0)):
                    fsp = ffc.get("stepParams", {})
                    ffis = fsp.get("filterFormItemSettings", {}).get("init", {})
                    fn = ffis.get("filterField", {}).get("name", "")
                    if fn:
                        field_names.append(fn)
                    if not target:
                        target = ffis.get("defaultTargetUid", "")
            fields_str = ",".join(field_names) if field_names else "?"
            return f"[Filter: {fields_str}]", []

        if "Details" in use and "Item" not in use:
            coll = sp.get("resourceSettings", {}).get("init", {}).get("collectionName", "?")
            return f"[Details {coll}]", []

        # Generic fallback
        short_use = use.replace("Model", "")
        return f"[{short_use}]", []

    def _describe_action(self, action_node, cm):
        """Describe an AddNew/Edit action's form fields."""
        # Traverse: Action → ChildPage → ChildPageTab → BlockGrid → Form → FormGrid → FormItems
        children = cm.get(action_node["uid"], [])
        for ch in children:
            if "ChildPage" in ch.get("use", ""):
                return self._describe_form_tree(ch, cm)
        return "?"

    def _describe_form_tree(self, node, cm):
        """Walk a ChildPage/Form tree and count fields."""
        children = cm.get(node["uid"], [])
        for ch in children:
            use = ch.get("use", "")
            if "Form" in use and "Grid" not in use and "Item" not in use and "Filter" not in use:
                # Found the form — count its items
                return self._count_form_fields(ch, cm)
            result = self._describe_form_tree(ch, cm)
            if result != "?":
                return result
        return "?"

    def _count_form_fields(self, form_node, cm):
        """Count FormItemModel and DividerItemModel in a form."""
        # Form → FormGrid → Items
        children = cm.get(form_node["uid"], [])
        for ch in children:
            if "FormGrid" in ch.get("use", "") or "DetailsGrid" in ch.get("use", ""):
                items = cm.get(ch["uid"], [])
                fields = [i for i in items if "FormItem" in i.get("use", "") or "DetailsItem" in i.get("use", "")]
                dividers = [i for i in items if "Divider" in i.get("use", "")]
                field_names = []
                for f in sorted(fields, key=lambda x: x.get("sortIndex", 0))[:5]:
                    fp = f.get("stepParams", {}).get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
                    if fp:
                        field_names.append(fp)
                preview = ", ".join(field_names)
                if len(fields) > 5:
                    preview += f", ...+{len(fields)-5}"
                div_str = f", {len(dividers)} dividers" if dividers else ""
                return f"{len(fields)} fields{div_str} ({preview})"
        return "?"

    def _find_detail_popup(self, col_children, cm):
        """Find detail popup attached to click-to-open column."""
        for col in col_children:
            if "TableColumn" not in col.get("use", "") or "Actions" in col.get("use", ""):
                continue
            dfs = col.get("stepParams", {}).get("displayFieldSettings", {})
            if not dfs.get("clickToOpen", {}).get("clickToOpen"):
                continue
            # Found click-to-open column — look for its display field's popup
            for dch in cm.get(col["uid"], []):
                popup_sp = dch.get("stepParams", {}).get("popupSettings", {}).get("openView", {})
                popup_uid = popup_sp.get("uid")
                mode = popup_sp.get("mode", "drawer")
                size = popup_sp.get("size", "?")
                if popup_uid:
                    return self._describe_popup(popup_uid, cm, mode, size)
        return None

    def _describe_popup(self, popup_uid, cm, mode, size):
        """Describe a detail popup's tab structure."""
        children = cm.get(popup_uid, [])
        tabs = [c for c in children if "ChildPageTab" in c.get("use", "")]
        if not tabs:
            return f"({mode},{size}) empty"
        tab_descs = []
        for tab in sorted(tabs, key=lambda t: t.get("sortIndex", 0)):
            tab_title = tab.get("stepParams", {}).get("pageTabSettings", {}).get("tab", {}).get("title", "?")
            # Look inside for block types
            tab_children = cm.get(tab["uid"], [])
            block_types = []
            for tc in tab_children:
                if "BlockGrid" in tc.get("use", ""):
                    for bc in cm.get(tc["uid"], []):
                        bu = bc.get("use", "")
                        if "Details" in bu:
                            n = len([i for i in cm.get(bc["uid"], [])
                                     if "Grid" in i.get("use", "")])
                            block_types.append("Details")
                        elif "Table" in bu:
                            coll = bc.get("stepParams", {}).get("resourceSettings", {}).get("init", {}).get("collectionName", "?")
                            block_types.append(f"SubTable:{coll}")
                        elif "JS" in bu:
                            block_types.append("JS")
            content = ", ".join(block_types) if block_types else "empty"
            tab_descs.append(f'"{tab_title}"({content})')
        return f"({mode},{size}) [{' | '.join(tab_descs)}]"


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
    def nb_inspect_page(page_title: str) -> str:
        """Inspect a page and return a compact visual layout summary.

        Shows the actual rendered structure: rows, columns, KPIs, tables,
        filters, forms, and detail popups in an easy-to-read format.

        Args:
            page_title: Page title as shown in the sidebar menu

        Returns:
            Compact visual layout of the page structure.

        Example:
            nb_inspect_page("客户列表")
            nb_inspect_page("资产台账")
        """
        nb = get_nb_client()
        pt = PageTool(nb)
        return pt.inspect(page_title)

    @mcp.tool()
    def nb_inspect_all(prefix: Optional[str] = None) -> str:
        """Inspect all pages and return a compact summary of each.

        Args:
            prefix: Optional menu path prefix to filter (e.g. "CRM", "仓储管理")

        Returns:
            Compact inspection of all matching pages.
        """
        nb = get_nb_client()
        pt = PageTool(nb)
        all_pages = pt.pages()
        if prefix:
            all_pages = [p for p in all_pages if p["path"].startswith(prefix)]
        results = []
        for page in all_pages:
            results.append(pt.inspect(page["title"]))
            results.append("")
        return "\n".join(results) if results else "No pages found"

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
