"""nb_page_tool.py — NocoBase FlowModel 局部 CRUD 工具

对已创建的页面进行增删改查，无需全量重建。
设计为 Python 方法优先（后续可封装为 MCP tool）。

用法（CLI）：
    python3 nb_page_tool.py show "资产台账"                              # 查看页面结构树
    python3 nb_page_tool.py locate "资产台账" --block table --field name  # 定位字段节点
    python3 nb_page_tool.py patch <uid> --prop description="帮助文本"     # 修改节点属性
    python3 nb_page_tool.py add-field <form_grid_uid> --coll x --field y --after z
    python3 nb_page_tool.py rm-field <field_uid>                         # 删除字段
    python3 nb_page_tool.py add-column <table_uid> --coll x --field y    # 追加列
    python3 nb_page_tool.py rm-column <column_uid>                       # 删除列

用法（Python）：
    from nb_page_tool import PageTool
    pt = PageTool()
    pt.show("资产台账")
    uid = pt.locate("资产台账", block="table", field="name")
    pt.patch_field(uid, description="帮助文本", defaultValue="默认值")
"""

import sys, json, argparse
from nb_page_builder import NB, _deep_merge, uid, EDIT_MAP, DISPLAY_MAP


class PageTool:
    """FlowModel 局部 CRUD 工具。"""

    def __init__(self, base_url=None):
        self.nb = NB(base_url)
        self._models = None
        self._routes = None

    # ── 数据获取 ──────────────────────────────────────────────

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
        """Build parentId → [model] map."""
        models = self._load_models()
        cm = {}
        for m in models:
            pid = m.get("parentId")
            if pid:
                cm.setdefault(pid, []).append(m)
        return cm

    def _model_by_uid(self, uid_):
        """Find model by uid."""
        for m in self._load_models():
            if m["uid"] == uid_:
                return m
        return None

    # ── 路由 → Tab UID 解析 ───────────────────────────────────

    def _find_tab_uid(self, page_title):
        """从路由树中找到页面对应的 tab UID。"""
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
            # Single tab (hidden) — title may be None
            for c in children:
                if c.get("schemaUid"):
                    return c["schemaUid"]
        for child in route.get("children", []):
            found = self._search_route(child, title)
            if found:
                return found
        return None

    # ── 树构建 & 显示 ─────────────────────────────────────────

    def _build_tree(self, root_uid, cm=None):
        """从 parentId 关系构建子树。"""
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

    def show(self, page_title):
        """显示页面结构树。"""
        tab_uid = self._find_tab_uid(page_title)
        if not tab_uid:
            print(f"Page '{page_title}' not found")
            return None
        cm = self._children_map()
        tree = self._build_tree(tab_uid, cm)
        self._print_tree(tree, 0)
        return tree

    def _print_tree(self, node, depth):
        indent = "  " * depth
        use = node["use"]
        u = node["uid"]
        sp = node.get("stepParams", {})

        # Extract useful info
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
        print(f"{indent}{use} [{u}]{detail}")

        for child in node.get("children", []):
            self._print_tree(child, depth + 1)

    # ── 定位 ─────────────────────────────────────────────────

    def locate(self, page_title, block=None, field=None):
        """定位页面中的节点 UID。

        block: "table" | "addnew" | "edit" | "filter" | "details"
        field: 字段名（可选，进一步定位到具体字段）

        Returns: uid string or None
        """
        tab_uid = self._find_tab_uid(page_title)
        if not tab_uid:
            return None
        cm = self._children_map()
        tree = self._build_tree(tab_uid, cm)
        return self._find_in_tree(tree, block, field)

    def _find_in_tree(self, node, block, field):
        use = node["use"]
        sp = node.get("stepParams", {})

        # Block-level matching
        if block and not field:
            block_map = {
                "table": "TableBlockModel",
                "addnew": "AddNewActionModel",
                "edit": "EditActionModel",
                "filter": "FilterFormModel",
                "details": "DetailsBlockModel",
                "form_create": "CreateFormModel",
                "form_edit": "EditFormModel",
            }
            target_use = block_map.get(block, block)
            if use == target_use:
                return node["uid"]

        # Field-level matching
        if field:
            fp = sp.get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
            if fp == field:
                return node["uid"]

        # Recurse
        for child in node.get("children", []):
            found = self._find_in_tree(child, block, field)
            if found:
                return found
        return None

    def locate_all(self, page_title, use_filter=None, field_filter=None):
        """定位页面中所有匹配的节点。返回 [(uid, use, field_path)] 列表。"""
        tab_uid = self._find_tab_uid(page_title)
        if not tab_uid:
            return []
        cm = self._children_map()
        tree = self._build_tree(tab_uid, cm)
        results = []
        self._collect_matches(tree, use_filter, field_filter, results)
        return results

    def _collect_matches(self, node, use_filter, field_filter, results):
        use = node["use"]
        sp = node.get("stepParams", {})
        fp = sp.get("fieldSettings", {}).get("init", {}).get("fieldPath", "")

        match = True
        if use_filter and use != use_filter:
            match = False
        if field_filter and fp != field_filter:
            match = False
        if match and (use_filter or field_filter):
            results.append((node["uid"], use, fp))

        for child in node.get("children", []):
            self._collect_matches(child, use_filter, field_filter, results)

    # ── 修改 ─────────────────────────────────────────────────

    def patch_field(self, uid_, **kwargs):
        """修改字段属性（description, defaultValue, placeholder, hidden, disabled, tooltip）。

        用法：
            pt.patch_field("abc123", description="帮助文本", defaultValue="默认值")
        """
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
            print(f"No valid properties to patch")
            return False
        ok = self.nb.update(uid_, patch)
        if ok:
            print(f"  Patched {uid_}: {list(kwargs.keys())}")
        else:
            print(f"  Failed to patch {uid_}")
        return ok

    def patch_column(self, uid_, **kwargs):
        """修改表格列属性（width, title, hidden）。

        用法：
            pt.patch_column("abc123", width=120, title="新标题")
        """
        patch = {}
        tcs = {}
        if "width" in kwargs:
            tcs["width"] = {"width": kwargs["width"]}
        if "title" in kwargs:
            tcs["title"] = {"title": kwargs["title"]}
        if tcs:
            patch["stepParams"] = {"tableColumnSettings": tcs}
        ok = self.nb.update(uid_, patch)
        if ok:
            print(f"  Patched column {uid_}: {list(kwargs.keys())}")
        return ok

    # ── 增删字段 ─────────────────────────────────────────────

    def add_field(self, form_grid_uid, coll, field, after=None, required=False, props=None):
        """向现有表单追加字段。

        form_grid_uid: FormGridModel 的 UID（通过 locate 获取）
        after: 插入到哪个字段之后（field name）；None = 末尾
        """
        # 获取当前 grid 结构
        model = self._model_by_uid(form_grid_uid)
        if not model:
            print(f"FormGridModel {form_grid_uid} not found")
            return None

        # 确定 sort index
        cm = self._children_map()
        children = cm.get(form_grid_uid, [])
        max_sort = max((c.get("sortIndex", 0) for c in children), default=-1) + 1

        if after:
            # 找到 after 字段的 sort index，插入其后
            for c in children:
                fp = c.get("stepParams", {}).get("fieldSettings", {}).get("init", {}).get("fieldPath", "")
                if fp == after:
                    max_sort = c.get("sortIndex", 0) + 1
                    break

        fi = self.nb.form_field(form_grid_uid, coll, field, max_sort,
                                required=required, props=props)

        # 更新 gridSettings：追加新行
        gs = model.get("stepParams", {}).get("gridSettings", {}).get("grid", {})
        rows = gs.get("rows", {})
        sizes = gs.get("sizes", {})
        new_row_id = uid()
        rows[new_row_id] = [[fi]]
        sizes[new_row_id] = [24]
        self.nb.update(form_grid_uid, {"stepParams": {"gridSettings": {"grid": {"rows": rows, "sizes": sizes}}}})
        self._models = None  # invalidate cache
        print(f"  Added field '{field}' to form {form_grid_uid} (uid={fi})")
        return fi

    def remove_field(self, field_uid):
        """删除表单字段（FormItemModel 及其子节点）。

        注意：不会自动更新父 FormGridModel 的 gridSettings。
        如果需要完美清理，建议 clean_tab + 重建。
        """
        self.nb.destroy_tree(field_uid)
        self._models = None
        print(f"  Removed field {field_uid}")

    def add_column(self, table_uid, coll, field, click=False, width=None, sort=None):
        """向现有表格追加列。"""
        cm = self._children_map()
        children = [c for c in cm.get(table_uid, []) if c.get("subKey") == "columns"]
        if sort is None:
            sort = max((c.get("sortIndex", 0) for c in children), default=-1) + 1
        cu, fu = self.nb.col(table_uid, coll, field, sort, click=click, width=width)
        self._models = None
        print(f"  Added column '{field}' to table {table_uid} (uid={cu})")
        return cu

    def remove_column(self, column_uid):
        """删除表格列。"""
        self.nb.destroy_tree(column_uid)
        self._models = None
        print(f"  Removed column {column_uid}")

    # ── 批量操作 ─────────────────────────────────────────────

    def batch_patch(self, page_title, patches):
        """批量修改多个字段。

        patches: dict mapping field_name → props dict
            {"name": {"description": "帮助文本"},
             "status": {"defaultValue": "在用"}}

        自动定位字段 UID 并逐个 patch。
        """
        results = {}
        for field_name, props in patches.items():
            matches = self.locate_all(page_title, use_filter="FormItemModel", field_filter=field_name)
            if not matches:
                print(f"  Field '{field_name}' not found in '{page_title}'")
                results[field_name] = False
                continue
            for uid_, use, fp in matches:
                ok = self.patch_field(uid_, **props)
                results[field_name] = ok
        return results

    # ── 信息查询 ─────────────────────────────────────────────

    def info(self, uid_):
        """获取节点完整信息。"""
        r = self.nb.s.get(f"{self.nb.base}/api/flowModels:get?filterByTk={uid_}")
        if r.ok:
            return r.json().get("data", {})
        return None

    def pages(self):
        """列出所有页面（flowPage 路由）。"""
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


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="NocoBase FlowModel CRUD tool")
    sub = parser.add_subparsers(dest="cmd")

    # show
    p_show = sub.add_parser("show", help="Show page structure tree")
    p_show.add_argument("page", help="Page title")

    # pages
    sub.add_parser("pages", help="List all pages")

    # locate
    p_loc = sub.add_parser("locate", help="Locate node UID")
    p_loc.add_argument("page", help="Page title")
    p_loc.add_argument("--block", help="Block type: table/addnew/edit/filter/details")
    p_loc.add_argument("--field", help="Field name")

    # info
    p_info = sub.add_parser("info", help="Get node full info")
    p_info.add_argument("uid", help="Node UID")

    # patch
    p_patch = sub.add_parser("patch", help="Patch field properties")
    p_patch.add_argument("uid", help="Node UID")
    p_patch.add_argument("--prop", action="append", help="key=value property", required=True)

    # add-field
    p_af = sub.add_parser("add-field", help="Add field to form")
    p_af.add_argument("form_grid_uid", help="FormGridModel UID")
    p_af.add_argument("--coll", required=True, help="Collection name")
    p_af.add_argument("--field", required=True, help="Field name")
    p_af.add_argument("--after", help="Insert after field")
    p_af.add_argument("--required", action="store_true")

    # rm-field
    p_rf = sub.add_parser("rm-field", help="Remove field from form")
    p_rf.add_argument("uid", help="FormItemModel UID")

    # add-column
    p_ac = sub.add_parser("add-column", help="Add column to table")
    p_ac.add_argument("table_uid", help="TableBlockModel UID")
    p_ac.add_argument("--coll", required=True, help="Collection name")
    p_ac.add_argument("--field", required=True, help="Field name")
    p_ac.add_argument("--width", type=int, help="Column width")

    # rm-column
    p_rc = sub.add_parser("rm-column", help="Remove column from table")
    p_rc.add_argument("uid", help="TableColumnModel UID")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    pt = PageTool()

    if args.cmd == "show":
        pt.show(args.page)

    elif args.cmd == "pages":
        for p in pt.pages():
            print(f"  {p['path']}  tab={p['tab_uid']}")

    elif args.cmd == "locate":
        uid_ = pt.locate(args.page, block=args.block, field=args.field)
        if uid_:
            print(f"  Found: {uid_}")
        else:
            print(f"  Not found")

    elif args.cmd == "info":
        data = pt.info(args.uid)
        if data:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("  Not found")

    elif args.cmd == "patch":
        props = {}
        for p in args.prop:
            k, v = p.split("=", 1)
            # Try to parse as JSON value, fallback to string
            try:
                v = json.loads(v)
            except (json.JSONDecodeError, ValueError):
                pass
            props[k] = v
        pt.patch_field(args.uid, **props)

    elif args.cmd == "add-field":
        pt.add_field(args.form_grid_uid, args.coll, args.field,
                     after=args.after, required=args.required)

    elif args.cmd == "rm-field":
        pt.remove_field(args.uid)

    elif args.cmd == "add-column":
        pt.add_column(args.table_uid, args.coll, args.field, width=args.width)

    elif args.cmd == "rm-column":
        pt.remove_column(args.uid)


if __name__ == "__main__":
    main()
