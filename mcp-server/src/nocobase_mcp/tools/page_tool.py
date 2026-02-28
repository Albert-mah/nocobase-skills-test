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
        """Generate a DSL-style visual representation of a page's structure.

        Output mirrors nb_crud_page input format for easy comparison.
        """
        tab_uid = self._find_tab_uid(page_title)
        if not tab_uid:
            return f"Page '{page_title}' not found"
        cm = self._children_map()
        tree = self._build_tree(tab_uid, cm)
        lines = [f"# {page_title}  (tab={tab_uid})"]
        # Find the BlockGridModel
        grids = [c for c in tree.get("children", []) if "BlockGrid" in c.get("use", "")]
        if not grids:
            lines.append("(empty page)")
            return "\n".join(lines)
        grid = grids[0]
        gs = grid.get("stepParams", {}).get("gridSettings", {}).get("grid", {})
        rows = gs.get("rows", {})
        sizes = gs.get("sizes", {})
        # Map uid → child node for quick lookup
        block_map = {c["uid"]: c for c in grid.get("children", [])}
        # Classify rows into sections
        kpi_blocks = []
        filter_block = None
        table_block = None
        other_blocks = []
        row_items = list(rows.items())
        for row_id, cols in row_items:
            row_sizes = sizes.get(row_id, [24] * len(cols))
            for ci, col_uids in enumerate(cols):
                for buid in col_uids:
                    node = block_map.get(buid)
                    if not node:
                        continue
                    use = node.get("use", "")
                    if "JSBlock" in use:
                        sp = node.get("stepParams", {})
                        title = sp.get("cardSettings", {}).get("titleDescription", {}).get("title", "")
                        kpi_blocks.append({"title": title, "row_id": row_id, "size": row_sizes[ci] if ci < len(row_sizes) else 6})
                    elif "FilterForm" in use:
                        filter_block = node
                    elif "TableBlock" in use:
                        table_block = node
                    elif "Details" in use and "Item" not in use:
                        other_blocks.append(node)

        # 1. KPI section
        if kpi_blocks:
            # Check if all KPIs share same row (side-by-side) or separate rows
            kpi_rows = set(k["row_id"] for k in kpi_blocks)
            if len(kpi_rows) == 1:
                layout = "inline"
                size_str = "|".join(str(k["size"]) for k in kpi_blocks)
            else:
                layout = "stacked"
                size_str = "24 each"
            titles = [f'"{k["title"]}"' for k in kpi_blocks]
            lines.append(f"")
            lines.append(f"## KPIs ({len(kpi_blocks)}x, {layout}, {size_str})")
            lines.append(f"   {' | '.join(titles)}")
            if layout == "stacked":
                lines.append(f"   !! LAYOUT BUG: KPIs in separate rows (should be inline)")

        # 2. Filter section
        if filter_block:
            field_names = self._extract_filter_fields(filter_block, cm)
            lines.append(f"")
            lines.append(f"## Filter")
            lines.append(f'   filter_fields: {json.dumps(field_names)}')

        # 3. Table section
        if table_block:
            sp = table_block.get("stepParams", {})
            coll = sp.get("resourceSettings", {}).get("init", {}).get("collectionName", "?")
            title = sp.get("cardSettings", {}).get("titleDescription", {}).get("title", "")
            col_children = sorted(cm.get(table_block["uid"], []), key=lambda m: m.get("sortIndex", 0))
            col_names = []
            js_cols = []
            addnew_node = edit_node = None
            for ch in col_children:
                ch_use = ch.get("use", "")
                if "JSColumn" in ch_use:
                    ct = ch.get("stepParams", {}).get("tableColumnSettings", {}).get("title", {}).get("title", "")
                    js_cols.append(ct)
                    col_names.append(f"[JS:{ct}]")
                elif "TableColumn" in ch_use and "Actions" not in ch_use:
                    fp = ch.get("stepParams", {}).get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
                    if fp:
                        col_names.append(fp)
                    else:
                        ct = ch.get("stepParams", {}).get("tableColumnSettings", {}).get("title", {}).get("title", "")
                        col_names.append(ct or "?")
                elif "AddNew" in ch_use:
                    addnew_node = ch
                elif "ActionsColumn" in ch_use or "TableActions" in ch_use:
                    for act in sorted(cm.get(ch["uid"], []), key=lambda m: m.get("sortIndex", 0)):
                        if "Edit" in act.get("use", ""):
                            edit_node = act
            lines.append(f"")
            title_str = f' "{title}"' if title else ""
            lines.append(f"## Table{title_str}  ({coll})")
            # Output as JSON array matching table_fields format
            plain_cols = [c for c in col_names if not c.startswith("[JS:")]
            lines.append(f'   table_fields: {json.dumps(plain_cols)}')
            if js_cols:
                lines.append(f'   js_columns: {json.dumps(js_cols)}')

            # 4. AddNew form
            if addnew_node:
                dsl = self._extract_form_dsl(addnew_node, cm)
                lines.append(f"")
                lines.append(f"   ### AddNew")
                for dl in dsl.split("\n"):
                    lines.append(f"       {dl}")

            # 5. Edit form
            if edit_node:
                dsl = self._extract_form_dsl(edit_node, cm)
                lines.append(f"")
                lines.append(f"   ### Edit")
                for dl in dsl.split("\n"):
                    lines.append(f"       {dl}")

            # 6. Detail popup
            detail_info = self._find_detail_popup(col_children, cm)
            if detail_info:
                lines.append(f"")
                lines.append(f"   ### Detail Popup")
                for dl in detail_info.split("\n"):
                    lines.append(f"       {dl}")

            # 7. AI button on table
            ai_button = [ch for ch in col_children if "AIEmployee" in ch.get("use", "")]
            if ai_button:
                for ab in ai_button:
                    absp = ab.get("stepParams", {})
                    abis = absp.get("aiEmployeeButtonSettings", {}).get("init", {})
                    ai_user = abis.get("aiEmployee", "?")
                    lines.append(f"   AI Button: {ai_user}")

        # 8. AI shortcuts
        shortcuts = [c for c in tree.get("children", [])
                     if "AIEmployeeShortcut" in c.get("use", "")]
        if shortcuts:
            names = []
            for sc in shortcuts:
                for ch in sc.get("children", []):
                    sp = ch.get("stepParams", {})
                    ss = sp.get("aiEmployeeShortcutSettings", {}).get("init", {})
                    un = ss.get("aiEmployee", "")
                    label = ss.get("label", "")
                    if un:
                        names.append(f"{un}:{label}" if label else un)
            if names:
                lines.append(f"")
                lines.append(f"## AI Shortcuts: {', '.join(names)}")

        return "\n".join(lines)

    def _extract_filter_fields(self, filter_node, cm):
        """Extract filter field names from a FilterFormModel."""
        filter_children = sorted(cm.get(filter_node["uid"], []), key=lambda m: m.get("sortIndex", 0))
        field_names = []
        for fc in filter_children:
            for ffc in sorted(cm.get(fc["uid"], []), key=lambda m: m.get("sortIndex", 0)):
                fsp = ffc.get("stepParams", {})
                ffis = fsp.get("filterFormItemSettings", {}).get("init", {})
                fn = ffis.get("filterField", {}).get("name", "")
                if fn:
                    field_names.append(fn)
        return field_names

    def _extract_form_dsl(self, action_node, cm):
        """Extract form structure as DSL string (mirrors nb_crud_page form_fields format)."""
        children = cm.get(action_node["uid"], [])
        for ch in children:
            if "ChildPage" in ch.get("use", ""):
                return self._walk_form_dsl(ch, cm)
        return "(no form found)"

    def _walk_form_dsl(self, node, cm):
        """Walk tree to find form and return DSL."""
        children = cm.get(node["uid"], [])
        for ch in children:
            use = ch.get("use", "")
            if "Form" in use and "Grid" not in use and "Item" not in use and "Filter" not in use:
                return self._form_to_dsl(ch, cm)
            result = self._walk_form_dsl(ch, cm)
            if result != "(no form found)":
                return result
        return "(no form found)"

    def _form_to_dsl(self, form_node, cm):
        """Convert a form's FormGrid items to DSL string."""
        children = cm.get(form_node["uid"], [])
        for ch in children:
            if "FormGrid" in ch.get("use", "") or "DetailsGrid" in ch.get("use", ""):
                return self._grid_to_dsl(ch, cm)
        return "(empty form)"

    def _grid_to_dsl(self, grid_node, cm):
        """Convert FormGridModel items to DSL lines."""
        items = sorted(cm.get(grid_node["uid"], []), key=lambda m: m.get("sortIndex", 0))
        gs = grid_node.get("stepParams", {}).get("gridSettings", {}).get("grid", {})
        grid_rows = gs.get("rows", {})
        grid_sizes = gs.get("sizes", {})
        # Build uid → item map
        uid_map = {i["uid"]: i for i in items}
        # Rebuild rows from gridSettings
        dsl_lines = []
        for row_id, cols in grid_rows.items():
            row_sizes = grid_sizes.get(row_id, [24] * len(cols))
            row_parts = []
            for ci, col_uids in enumerate(cols):
                col_size = row_sizes[ci] if ci < len(row_sizes) else 24
                for field_uid in col_uids:
                    item = uid_map.get(field_uid)
                    if not item:
                        continue
                    use = item.get("use", "")
                    sp = item.get("stepParams", {})
                    if "Divider" in use:
                        label = sp.get("dividerItemSettings", {}).get("init", {}).get("title", "")
                        dsl_lines.append(f"--- {label}" if label else "---")
                        continue
                    fp = sp.get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
                    if not fp:
                        continue
                    # Check required
                    eis = sp.get("editItemSettings", {})
                    req = eis.get("required", {}).get("required", False)
                    name = f"{fp}*" if req else fp
                    # Add size if not default
                    if len(cols) > 1 and col_size != 24 // len(cols):
                        name = f"{name}:{col_size}"
                    row_parts.append(name)
            if row_parts:
                dsl_lines.append(" | ".join(row_parts))
        if not dsl_lines:
            return "(empty form)"
        return "\n".join(dsl_lines)

    def _find_detail_popup(self, col_children, cm):
        """Find detail popup attached to click-to-open column."""
        for col in col_children:
            if "TableColumn" not in col.get("use", "") or "Actions" in col.get("use", ""):
                continue
            dfs = col.get("stepParams", {}).get("displayFieldSettings", {})
            if not dfs.get("clickToOpen", {}).get("clickToOpen"):
                continue
            for dch in cm.get(col["uid"], []):
                popup_sp = dch.get("stepParams", {}).get("popupSettings", {}).get("openView", {})
                popup_uid = popup_sp.get("uid")
                mode = popup_sp.get("mode", "drawer")
                size = popup_sp.get("size", "?")
                if popup_uid:
                    return self._describe_popup(popup_uid, cm, mode, size)
        return None

    def _describe_popup(self, popup_uid, cm, mode, size):
        """Describe a detail popup's tab structure as DSL."""
        children = cm.get(popup_uid, [])
        tabs = [c for c in children if "ChildPageTab" in c.get("use", "")]
        if not tabs:
            return f"({mode},{size}) empty"
        lines = [f"mode={mode}, size={size}"]
        for tab in sorted(tabs, key=lambda t: t.get("sortIndex", 0)):
            tab_title = tab.get("stepParams", {}).get("pageTabSettings", {}).get("tab", {}).get("title", "?")
            tab_children = cm.get(tab["uid"], [])
            tab_blocks = []
            for tc in tab_children:
                if "BlockGrid" in tc.get("use", ""):
                    for bc in cm.get(tc["uid"], []):
                        bu = bc.get("use", "")
                        if "Details" in bu:
                            dsl = self._form_to_dsl(bc, cm)
                            tab_blocks.append(f"Details:\n{dsl}")
                        elif "Table" in bu:
                            coll = bc.get("stepParams", {}).get("resourceSettings", {}).get("init", {}).get("collectionName", "?")
                            sub_cols = []
                            for sc in sorted(cm.get(bc["uid"], []), key=lambda m: m.get("sortIndex", 0)):
                                fp = sc.get("stepParams", {}).get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
                                if fp:
                                    sub_cols.append(fp)
                            tab_blocks.append(f"SubTable {coll}: {json.dumps(sub_cols)}")
                        elif "JS" in bu:
                            tab_blocks.append("JSBlock")
            content = "\n".join(tab_blocks) if tab_blocks else "(empty)"
            lines.append(f'Tab "{tab_title}":')
            for cl in content.split("\n"):
                lines.append(f"  {cl}")
        return "\n".join(lines)


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
