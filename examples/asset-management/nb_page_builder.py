"""nb_page_builder.py — NocoBase FlowPage 2.0 页面构建通用库 v2

极简 API：只需字段名列表，自动从 collection 元数据推断 Model 类型。

v2 新增：
  - 多区块布局（multi_block, gridSettings 自动生成）
  - 表单/详情多列字段 + 分隔线/Markdown 分组
  - 弹窗模式可配（mode/size）+ 多区块标签页
  - JS 区块（js_block / js_column / js_item）+ 事件流（event_flow）

用法示例：
    from nb_page_builder import NB

    nb = NB()

    # 表格页面（极简）
    grid, tbl, addnew, actcol = nb.table(tab_uid, "my_coll",
        ["name", "code", "status"])

    # 多列表单
    nb.addnew_form(addnew, "my_coll", [
        [("name", 12), ("code", 12)],
        "---",
        "description",
    ], required=["name"])

    # 多区块详情弹窗
    nb.detail_popup(field_uid, "my_coll", [
        {"title": "Overview", "blocks": [
            {"type": "details", "fields": [
                [("name", 12), ("status", 12)], "description"]},
            {"type": "js", "title": "Stats", "code": "ctx.render(<h1>Hi</h1>)"},
        ], "sizes": [16, 8]},
        {"title": "Items", "assoc": "items", "coll": "my_items",
         "fields": ["name", "qty"]},
    ], mode="drawer", size="large")
"""

import requests
import random
import string

BASE = "http://localhost:14000"

# ── Interface → Model 映射 ─────────────────────────────────────
DISPLAY_MAP = {
    "input": "DisplayTextFieldModel", "textarea": "DisplayTextFieldModel",
    "email": "DisplayTextFieldModel", "phone": "DisplayTextFieldModel",
    "sequence": "DisplayTextFieldModel", "markdown": "DisplayTextFieldModel",
    "select": "DisplayEnumFieldModel", "radioGroup": "DisplayEnumFieldModel",
    "checkbox": "DisplayCheckboxFieldModel",
    "integer": "DisplayNumberFieldModel", "number": "DisplayNumberFieldModel",
    "percent": "DisplayNumberFieldModel", "sort": "DisplayNumberFieldModel",
    "date": "DisplayDateTimeFieldModel", "datetime": "DisplayDateTimeFieldModel",
    "createdAt": "DisplayDateTimeFieldModel", "updatedAt": "DisplayDateTimeFieldModel",
    "color": "DisplayColorFieldModel", "icon": "DisplayIconFieldModel",
    "m2o": "DisplayTextFieldModel",
    "o2m": "DisplayNumberFieldModel",
}

EDIT_MAP = {
    "input": "InputFieldModel", "textarea": "TextareaFieldModel",
    "email": "InputFieldModel", "phone": "InputFieldModel",
    "markdown": "TextareaFieldModel",
    "select": "SelectFieldModel", "radioGroup": "RadioGroupFieldModel",
    "checkbox": "CheckboxFieldModel",
    "integer": "NumberFieldModel", "number": "NumberFieldModel",
    "percent": "NumberFieldModel",
    "date": "DateOnlyFieldModel", "datetime": "DateTimeTzFieldModel",
    "color": "InputFieldModel", "icon": "InputFieldModel",
    "m2o": "RecordSelectFieldModel",
}


def uid():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))


def _deep_merge(base, patch):
    """Deep merge patch into base dict (in-place)."""
    for k, v in patch.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


# ── Fields 格式解析（多列+分组）──────────────────────────────────

def _parse_field_name(name):
    """Parse 'name*' or 'name:16' or 'name*:16' → (clean_name, width_or_None, is_required)."""
    required = False
    width = None
    if ":" in name:
        name, w = name.rsplit(":", 1)
        width = int(w.strip())
    name = name.strip()
    if name.endswith("*"):
        name = name[:-1].strip()
        required = True
    return name, width, required


def _normalize_fields(fields):
    """统一 fields 参数为内部表示。返回 (items, auto_required)。

    支持三种格式：
        1. 多行字符串（pipe 语法）：
            '''
            --- Basic Info
            name* | code
            status | priority | category
            description
            '''
        2. 列表（旧格式兼容）：
            ["name", "code", [("name",12),("code",12)], "---"]
        3. 混合：列表中的字符串项也支持 pipe
    """
    # 多行字符串 → 拆行变列表
    if isinstance(fields, str):
        fields = [l.strip() for l in fields.strip().split("\n") if l.strip()]

    result = []
    auto_required = set()

    for item in fields:
        if isinstance(item, str) and item.strip().startswith("---"):
            title = item.strip()[3:].strip()
            result.append({"type": "divider", "label": title or ""})
        elif isinstance(item, str) and item.strip().startswith("#"):
            result.append({"type": "markdown", "content": item.strip()})
        elif isinstance(item, str) and "|" in item:
            # pipe 语法: "name* | code" or "name:16 | code:8"
            parts = [p.strip() for p in item.split("|")]
            auto_width = 24 // len(parts)
            cols = []
            for part in parts:
                name, width, req = _parse_field_name(part)
                if req:
                    auto_required.add(name)
                cols.append((name, width or auto_width))
            result.append({"type": "row", "cols": cols})
        elif isinstance(item, str):
            name, width, req = _parse_field_name(item)
            if req:
                auto_required.add(name)
            result.append({"type": "row", "cols": [(name, width or 24)]})
        elif isinstance(item, list):
            cols = []
            for col in item:
                if isinstance(col, tuple):
                    name, _, req = _parse_field_name(col[0]) if isinstance(col[0], str) else (col[0], None, False)
                    if req:
                        auto_required.add(name)
                    cols.append((name, col[1]))
                else:
                    name, width, req = _parse_field_name(col) if isinstance(col, str) else (col, None, False)
                    if req:
                        auto_required.add(name)
                    cols.append((name, width or 24))
            result.append({"type": "row", "cols": cols})
        elif isinstance(item, tuple):
            name, _, req = _parse_field_name(item[0]) if isinstance(item[0], str) else (item[0], None, False)
            if req:
                auto_required.add(name)
            result.append({"type": "row", "cols": [(name, item[1] if len(item) > 1 else 24)]})

    return result, auto_required


class NB:
    """NocoBase FlowPage builder v2 — 极简 API，自动推断一切。"""

    def __init__(self, base_url=None, auto_login=True):
        self.base = base_url or BASE
        self.s = requests.Session()
        self.s.trust_env = False
        self.created = 0
        self.errors = []
        self.warnings = []
        self._field_cache = {}
        self._title_cache = {}
        self._coll_title_cache = {}
        self._sort_counters = {}  # parent_uid → next sort index
        if auto_login:
            self.login()

    def login(self, account="admin@nocobase.com", password="admin123"):
        r = self.s.post(f"{self.base}/api/auth:signIn",
                        json={"account": account, "password": password})
        self.s.headers.update({"Authorization": f"Bearer {r.json()['data']['token']}"})
        return self

    # ── Metadata ────────────────────────────────────────────────

    def _load_meta(self, coll):
        if coll in self._field_cache:
            return
        r = self.s.get(f"{self.base}/api/collections/{coll}/fields:list?pageSize=200")
        self._field_cache[coll] = {
            f["name"]: {"interface": f.get("interface", "input"),
                        "type": f.get("type", "string"),
                        "target": f.get("target", ""),
                        "title": f.get("uiSchema", {}).get("title", f["name"])}
            for f in r.json().get("data", [])
        }
        if not self._title_cache:
            r2 = self.s.get(f"{self.base}/api/collections:list?paginate=false")
            for c in r2.json().get("data", []):
                self._title_cache[c["name"]] = c.get("titleField") or "name"
                self._coll_title_cache[c["name"]] = c.get("title", c["name"])

    def _visible_fields(self, coll):
        """Return user-visible field names (skip internal f_xxx, *Id, sort, id)."""
        schema = self._field_cache.get(coll, {})
        skip = {"id", "sort", "createdById", "updatedById"}
        return [f for f in schema
                if f not in skip
                and not f.startswith("f_")
                and not f.endswith("Id")
                and schema[f].get("interface") not in ("createdBy", "updatedBy")]

    def _check_field(self, coll, field):
        """Soft-validate field exists. Warns if not found, suggests similar names."""
        self._load_meta(coll)
        schema = self._field_cache.get(coll, {})
        if not schema or field in schema:
            return True
        visible = self._visible_fields(coll)
        # Find similar: substring match or shared prefix/suffix
        similar = [f for f in visible if field in f or f in field]
        if not similar and len(field) >= 3:
            similar = [f for f in visible
                       if f[:3] == field[:3] or f[-4:] == field[-4:]]
        coll_label = self._coll_title_cache.get(coll, coll)
        if similar:
            hint = f" maybe: {similar}"
        else:
            hint = f" ({len(visible)} fields — use nb.fields('{coll}') to see all)"
        msg = f"⚠️  '{field}' not in {coll_label}({coll}).{hint}"
        print(msg)
        self.warnings.append(msg)
        return False

    def _iface(self, coll, field):
        self._load_meta(coll)
        self._check_field(coll, field)
        return self._field_cache.get(coll, {}).get(field, {}).get("interface", "input")

    def _target(self, coll, field):
        self._load_meta(coll)
        return self._field_cache.get(coll, {}).get(field, {}).get("target", "")

    def _label(self, target_coll):
        self._load_meta(target_coll)
        tf = self._title_cache.get(target_coll)
        if tf and tf != "id":
            schema = self._field_cache.get(target_coll, {})
            if not schema or tf in schema:
                return tf
        schema = self._field_cache.get(target_coll, {})
        for candidate in ("name", "title", "label", "subject", "code"):
            if candidate in schema and schema[candidate].get("interface") in ("input", "sequence"):
                return candidate
        for fname, fmeta in schema.items():
            if (fmeta.get("interface") in ("input", "sequence")
                    and fname not in ("id",) and not fname.endswith("Id")):
                return fname
        return "id"

    def fields(self, coll, all=False):
        """Print collection schema — handy for agents to check available fields.

        Usage:
            nb.fields("nb_am_purchase_requests")       # user-visible fields only
            nb.fields("nb_am_purchase_requests", all=True)  # include internal fields
        """
        self._load_meta(coll)
        schema = self._field_cache.get(coll, {})
        visible = sorted(schema.keys()) if all else self._visible_fields(coll)
        coll_label = self._coll_title_cache.get(coll, coll)
        print(f"\n  {coll_label} ({coll}) — {len(visible)} fields")
        for name in sorted(visible):
            meta = schema[name]
            iface = meta.get("interface", "?")
            title = meta.get("title", "")
            target = meta.get("target", "")
            line = f"    {name:30s}  {iface:12s}  {title}"
            if target:
                line += f"  → {target}"
            print(line)
        return sorted(visible)

    def _next_sort(self, parent):
        """Auto-increment sort index per parent. Resets on new page_layout()."""
        self._sort_counters.setdefault(parent, 0)
        s = self._sort_counters[parent]
        self._sort_counters[parent] += 1
        return s

    # ── Low-level API ───────────────────────────────────────────

    def save(self, use, parent, sub_key, sub_type, sp=None, sort=0, u=None, **kw):
        u = u or uid()
        data = {"uid": u, "use": use, "parentId": parent,
                "subKey": sub_key, "subType": sub_type,
                "stepParams": sp or {}, "sortIndex": sort, "flowRegistry": {}, **kw}
        r = self.s.post(f"{self.base}/api/flowModels:save", json=data)
        if r.ok and r.json().get("data"):
            self.created += 1
        else:
            self.errors.append(f"{use}({u}): {r.text[:100]}")
        return u

    def update(self, u, patch):
        """Update existing FlowModel via flowModels:update (merge, not replace).

        patch: dict to deep-merge into existing options (top-level keys like
        stepParams, flowRegistry, use, parentId, etc.).
        """
        r = self.s.get(f"{self.base}/api/flowModels:get?filterByTk={u}")
        if not r.ok:
            return False
        data = r.json().get("data", {})
        # GET returns flat: {uid, name, use, parentId, stepParams, flowRegistry, ...}
        # We need to send back as {"options": {use, parentId, stepParams, ...}}
        opts = {k: v for k, v in data.items() if k not in ("uid", "name")}
        _deep_merge(opts, patch)
        r2 = self.s.post(f"{self.base}/api/flowModels:update?filterByTk={u}",
                         json={"options": opts})
        return r2.ok

    def destroy(self, u):
        """Delete a single FlowModel node."""
        self.s.post(f"{self.base}/api/flowModels:destroy?filterByTk={u}")

    def destroy_tree(self, u):
        """Delete a node and all its descendants (leaf-first)."""
        descendants = self._collect_descendants(u)
        to_delete = descendants + [u]  # descendants first, root last
        for uid_ in reversed(to_delete):
            self.s.post(f"{self.base}/api/flowModels:destroy?filterByTk={uid_}")
        print(f"  🗑️  Destroyed {len(to_delete)} nodes (root: {u})")
        self._invalidate_cache()

    def _list_all(self):
        """Fetch all FlowModels (cached per session)."""
        if not hasattr(self, '_all_models_cache'):
            r = self.s.get(f"{self.base}/api/flowModels:list?paginate=false")
            self._all_models_cache = r.json().get("data", [])
        return self._all_models_cache

    def _invalidate_cache(self):
        """Clear the FlowModel list cache (call after bulk deletes)."""
        if hasattr(self, '_all_models_cache'):
            del self._all_models_cache

    def _collect_descendants(self, root_uid):
        """BFS collect all descendant UIDs of a node."""
        all_models = self._list_all()
        children_map = {}
        for m in all_models:
            pid = m.get("parentId")
            if pid:
                children_map.setdefault(pid, []).append(m["uid"])
        result = []
        queue = list(children_map.get(root_uid, []))
        while queue:
            uid_ = queue.pop(0)
            result.append(uid_)
            queue.extend(children_map.get(uid_, []))
        return result

    def clean_tab(self, tab_uid):
        """Delete all FlowModel descendants under a tab (keep the RouteModel stub)."""
        to_delete = self._collect_descendants(tab_uid)
        for uid_ in reversed(to_delete):
            self.s.post(f"{self.base}/api/flowModels:destroy?filterByTk={uid_}")
        if to_delete:
            print(f"  🗑️  Cleaned {len(to_delete)} nodes under {tab_uid}")
        self._sort_counters.pop(tab_uid, None)
        self._invalidate_cache()

    # ── Auto-infer primitives ───────────────────────────────────

    def col(self, tbl, coll, field, idx, click=False, width=None):
        """Add table column (auto-infer display model)."""
        iface = self._iface(coll, field)
        display = DISPLAY_MAP.get(iface, "DisplayTextFieldModel")
        cu, fu = uid(), uid()

        col_sp = {"fieldSettings": {"init": {"dataSourceKey": "main", "collectionName": coll, "fieldPath": field}},
                  "tableColumnSettings": {"model": {"use": display}}}
        if width:
            col_sp["tableColumnSettings"]["width"] = {"width": width}
        self.save("TableColumnModel", tbl, "columns", "array", col_sp, idx, cu)

        fsp = {"popupSettings": {"openView": {"collectionName": coll, "dataSourceKey": "main"}}}
        if iface == "m2o":
            t = self._target(coll, field)
            if t:
                fsp["displayFieldSettings"] = {"fieldNames": {"label": self._label(t)}}
        if click:
            fsp["popupSettings"]["openView"].update(
                {"mode": "drawer", "size": "large", "pageModelClass": "ChildPageModel", "uid": fu})
            fsp.setdefault("displayFieldSettings", {})["clickToOpen"] = {"clickToOpen": True}
        self.save(display, cu, "field", "object", fsp, 0, fu)
        return cu, fu

    def form_field(self, grid, coll, field, idx, required=False, default=None, props=None):
        """Add form field (auto-infer edit model). Returns FormItemModel uid.

        props: optional dict with extra field properties:
            description  — help text below the field
            placeholder  — input placeholder
            hidden       — hide field (bool)
            disabled     — disable field (bool)
            defaultValue — default value (alias for default param)
            tooltip      — tooltip text
            pattern      — validation regex pattern
        """
        iface = self._iface(coll, field)
        edit = EDIT_MAP.get(iface, "InputFieldModel")
        fi, ff = uid(), uid()
        props = props or {}

        sp = {"fieldSettings": {"init": {"dataSourceKey": "main", "collectionName": coll, "fieldPath": field}}}
        eis = {}
        if required:
            eis["required"] = {"required": True}
        dv = default if default is not None else props.get("defaultValue")
        if dv is not None:
            eis["initialValue"] = {"defaultValue": dv}
        if props.get("description"):
            eis["description"] = {"description": props["description"]}
        if props.get("tooltip"):
            eis["tooltip"] = {"tooltip": props["tooltip"]}
        if props.get("placeholder"):
            eis["placeholder"] = {"placeholder": props["placeholder"]}
        if props.get("hidden"):
            eis["hidden"] = {"hidden": True}
        if props.get("disabled"):
            eis["disabled"] = {"disabled": True}
        if props.get("pattern"):
            eis["pattern"] = {"pattern": props["pattern"]}
        if eis:
            sp["editItemSettings"] = eis
        self.save("FormItemModel", grid, "items", "array", sp, idx, fi)
        self.save(edit, fi, "field", "object", {}, 0, ff)
        return fi

    def detail_field(self, grid, coll, field, idx):
        """Add detail field (auto-infer display model). Returns DetailsItemModel uid."""
        iface = self._iface(coll, field)
        display = DISPLAY_MAP.get(iface, "DisplayTextFieldModel")
        di, df = uid(), uid()

        sp = {"fieldSettings": {"init": {"dataSourceKey": "main", "collectionName": coll, "fieldPath": field}},
              "detailItemSettings": {"model": {"use": display}}}
        if iface == "m2o":
            t = self._target(coll, field)
            if t:
                sp["detailItemSettings"]["fieldNames"] = {"label": self._label(t)}
        self.save("DetailsItemModel", grid, "items", "array", sp, idx, di)
        self.save(display, di, "field", "object", {}, 0, df)
        return di

    # ── Grid 布局构建 ───────────────────────────────────────────

    def _build_form_grid(self, fg, coll, fields, required, props=None):
        """创建表单字段并设置 FormGridModel 的 gridSettings（支持多列+分组）。

        props: dict mapping field_name → per-field properties, e.g.
            {"name": {"description": "请输入全称", "placeholder": "例：XX"},
             "status": {"defaultValue": "在用", "hidden": True}}
        """
        items, auto_req = _normalize_fields(fields)
        required = required | auto_req
        props = props or {}
        rows, sizes, sort_idx = {}, {}, 0

        for item in items:
            row_id = uid()
            if item["type"] == "divider":
                div_sp = {}
                if item.get("label"):
                    div_sp = {"markdownItemSetting": {"title": {
                        "label": item["label"], "orientation": "left",
                        "color": "rgba(0, 0, 0, 0.88)",
                        "borderColor": "rgba(5, 5, 5, 0.06)"}}}
                du = self.save("DividerItemModel", fg, "items", "array", div_sp, sort_idx)
                rows[row_id] = [[du]]
                sizes[row_id] = [24]
                sort_idx += 1
            elif item["type"] == "markdown":
                mu = self.save("MarkdownItemModel", fg, "items", "array", {
                    "markdownBlockSettings": {"editMarkdown": {"content": item["content"]}}
                }, sort_idx)
                rows[row_id] = [[mu]]
                sizes[row_id] = [24]
                sort_idx += 1
            elif item["type"] == "row":
                col_uids, col_sizes = [], []
                for field_name, span in item["cols"]:
                    fi = self.form_field(fg, coll, field_name, sort_idx,
                                         required=(field_name in required),
                                         props=props.get(field_name))
                    col_uids.append(fi)
                    col_sizes.append(span)
                    sort_idx += 1
                # 每个字段独立一列：[[uid1],[uid2]] = 并排
                rows[row_id] = [[fi] for fi in col_uids]
                sizes[row_id] = col_sizes

        gs = {"gridSettings": {"grid": {"rows": rows, "sizes": sizes}}}
        self.update(fg, {"stepParams": gs})

    def _build_detail_grid(self, dg, coll, fields):
        """创建详情字段并设置 DetailsGridModel 的 gridSettings（支持多列+分组）。"""
        items, _ = _normalize_fields(fields)
        rows, sizes, sort_idx = {}, {}, 0

        for item in items:
            row_id = uid()
            if item["type"] == "divider":
                div_sp = {}
                if item.get("label"):
                    div_sp = {"markdownItemSetting": {"title": {
                        "label": item["label"], "orientation": "left",
                        "color": "rgba(0, 0, 0, 0.88)",
                        "borderColor": "rgba(5, 5, 5, 0.06)"}}}
                du = self.save("DividerItemModel", dg, "items", "array", div_sp, sort_idx)
                rows[row_id] = [[du]]
                sizes[row_id] = [24]
                sort_idx += 1
            elif item["type"] == "markdown":
                mu = self.save("MarkdownItemModel", dg, "items", "array", {
                    "markdownBlockSettings": {"editMarkdown": {"content": item["content"]}}
                }, sort_idx)
                rows[row_id] = [[mu]]
                sizes[row_id] = [24]
                sort_idx += 1
            elif item["type"] == "row":
                col_uids, col_sizes = [], []
                for field_name, span in item["cols"]:
                    di = self.detail_field(dg, coll, field_name, sort_idx)
                    col_uids.append(di)
                    col_sizes.append(span)
                    sort_idx += 1
                # 每个字段独立一列：[[uid1],[uid2]] = 并排
                rows[row_id] = [[di] for di in col_uids]
                sizes[row_id] = col_sizes

        gs = {"gridSettings": {"grid": {"rows": rows, "sizes": sizes}}}
        self.update(dg, {"stepParams": gs})

    def _build_block_grid(self, rows_spec):
        """声明式多区块行定义 → gridSettings JSON。

        rows_spec 每个元素是一行：
            (block_uid,)                          → 全宽
            [(uid1, 16), (uid2, 8)]               → 多列
            [(uid1, 16, ["extra"]), (uid2, 8)]    → 列内纵向堆叠
        """
        rows, sizes = {}, {}
        for row_spec in rows_spec:
            row_id = uid()
            if isinstance(row_spec, (str, tuple)):
                bu = row_spec[0] if isinstance(row_spec, tuple) else row_spec
                rows[row_id] = [[bu]]
                sizes[row_id] = [24]
            else:
                row_cols, row_sizes = [], []
                for col_def in row_spec:
                    col_blocks = [col_def[0]]
                    if len(col_def) > 2 and col_def[2]:
                        col_blocks.extend(col_def[2])
                    row_cols.append(col_blocks)
                    row_sizes.append(col_def[1] if len(col_def) > 1 else 24)
                rows[row_id] = row_cols
                sizes[row_id] = row_sizes
        return {"grid": {"rows": rows, "sizes": sizes}}

    # ── 弹窗内多区块构建 ───────────────────────────────────────

    def _build_tab_blocks(self, bg, coll, tab):
        """在一个 BlockGridModel 内构建多个区块（details/js/sub_table）。"""
        blocks = tab.get("blocks")
        if blocks is None:
            if "assoc" in tab:
                blocks = [{"type": "sub_table", "assoc": tab["assoc"],
                           "coll": tab["coll"], "fields": tab["fields"],
                           "title": tab.get("title")}]
            else:
                blocks = [{"type": "details", "fields": tab["fields"]}]

        block_uids = []
        for bi, blk in enumerate(blocks):
            btype = blk.get("type", "details")

            if btype == "details":
                det = self.save("DetailsBlockModel", bg, "items", "array", {
                    "resourceSettings": {"init": {"dataSourceKey": "main",
                                                  "collectionName": coll,
                                                  "filterByTk": "{{ctx.view.inputArgs.filterByTk}}"}},
                    **({"cardSettings": {"titleDescription": {"title": blk["title"]}}}
                       if blk.get("title") else {})
                }, bi)
                dg = self.save("DetailsGridModel", det, "grid", "object")
                self._build_detail_grid(dg, coll, blk["fields"])
                block_uids.append(det)

            elif btype == "js":
                sp = {"jsSettings": {"runJs": {"version": "v1", "code": blk.get("code", "")}}}
                if blk.get("title"):
                    sp["cardSettings"] = {"titleDescription": {"title": blk["title"]}}
                js_uid = self.save("JSBlockModel", bg, "items", "array", sp, bi)
                block_uids.append(js_uid)

            elif btype == "sub_table":
                tbl, an = self.sub_table(bg, coll, blk["assoc"], blk["coll"],
                                         blk["fields"], blk.get("title"))
                af = blk.get("addnew_fields") or blk["fields"]
                if af:
                    self.addnew_form(an, blk["coll"], af,
                                     required=[af[0]] if af else [])
                block_uids.append(tbl)

            elif btype == "form":
                fm = self.save("EditFormModel", bg, "items", "array", {
                    "resourceSettings": {"init": {"dataSourceKey": "main",
                                                  "collectionName": coll,
                                                  "filterByTk": "{{ctx.view.inputArgs.filterByTk}}"}}}, bi)
                self.save("FormSubmitActionModel", fm, "actions", "array", {}, 0)
                fg = self.save("FormGridModel", fm, "grid", "object")
                req = set(blk.get("required", []))
                self._build_form_grid(fg, coll, blk["fields"], req, props=blk.get("props"))
                block_uids.append(fm)

        # 多区块时设置 gridSettings
        tab_sizes = tab.get("sizes")
        if len(block_uids) > 1 or tab_sizes:
            row_id = uid()
            # rows 格式: [[col1_blocks], [col2_blocks]] — 每个内层数组是一列
            row_cols = [[bu] for bu in block_uids]
            if tab_sizes:
                gs = {"gridSettings": {"grid": {
                    "rows": {row_id: row_cols},
                    "sizes": {row_id: tab_sizes}}}}
            else:
                n = len(block_uids)
                auto = [24 // n] * n
                auto[-1] = 24 - sum(auto[:-1])
                gs = {"gridSettings": {"grid": {
                    "rows": {row_id: row_cols},
                    "sizes": {row_id: auto}}}}
            self.update(bg, {"stepParams": gs})

        return block_uids

    # ── High-level builders ────────────────────────────────────

    def group(self, title, parent_id=None, icon="appstoreoutlined"):
        """Create menu group (folder in sidebar, NO page content).

        Groups are purely structural — they only hold child pages or sub-groups.
        A group has NO tab UID and NO FlowModel content.

        Usage:
            gid = nb.group("资产管理", parent_gid)     # sub-group
            gid = nb.group("顶级菜单", None)            # top-level group

        Returns: group route id (int)
        """
        data = {"type": "group", "title": title, "icon": icon}
        if parent_id is not None:
            data["parentId"] = parent_id
        r = self.s.post(f"{self.base}/api/desktopRoutes:create", json=data)
        gid = r.json().get("data", {}).get("id")
        print(f"  📁 {title} (group id={gid})")
        return gid

    def route(self, title, parent_id, icon="appstoreoutlined", tabs=None):
        """Create a page (flowPage) route — this is where actual content lives.

        Pages hold FlowModel content (tables, forms, charts, etc.).
        parent_id should be a group id (from nb.group()) or another page id.

        Returns: (route_id, page_uid, tab_uid_or_dict)
          - Single tab: tab_uid is a string
          - Multi-tab:  tab_uid is a dict {tab_name: uid}

        Usage:
            rid, pu, tu = nb.route("资产台账", group_id)           # single tab
            rid, pu, tu = nb.route("设置", gid, tabs=["A","B"])    # multi-tab
        """
        pu, mu = uid(), uid()
        if tabs:
            children, tu = [], {}
            for i, t in enumerate(tabs):
                u = uid()
                tu[t] = u
                children.append({"type": "tabs", "title": t, "schemaUid": u,
                                 "tabSchemaName": uid(), "hidden": i == 0})
            data = {"type": "flowPage", "title": title, "parentId": parent_id,
                    "schemaUid": pu, "menuSchemaUid": mu, "icon": icon,
                    "enableTabs": True, "children": children}
            r = self.s.post(f"{self.base}/api/desktopRoutes:create", json=data)
            self.s.post(f"{self.base}/api/uiSchemas:insert",
                        json={"type": "void", "x-component": "FlowRoute", "x-uid": pu})
            rid = r.json().get("data", {}).get("id")
            print(f"  📄 {title} (id={rid}, tabs={list(tu.keys())})")
            return rid, pu, tu
        else:
            tu = uid()
            data = {"type": "flowPage", "title": title, "parentId": parent_id,
                    "schemaUid": pu, "menuSchemaUid": mu, "icon": icon,
                    "enableTabs": False,
                    "children": [{"type": "tabs", "schemaUid": tu, "tabSchemaName": uid(), "hidden": True}]}
            r = self.s.post(f"{self.base}/api/desktopRoutes:create", json=data)
            self.s.post(f"{self.base}/api/uiSchemas:insert",
                        json={"type": "void", "x-component": "FlowRoute", "x-uid": pu})
            rid = r.json().get("data", {}).get("id")
            print(f"  📄 {title} (id={rid}, tab={tu})")
            return rid, pu, tu

    def menu(self, group_title, parent_id, pages, *, group_icon="appstoreoutlined"):
        """Create a menu group with child pages in one call.

        This is the preferred way to build sidebar structure. It creates:
        1. A group (folder) for the section
        2. Individual pages under it (each with a tab UID for content)

        Args:
            group_title: Display name for the menu group
            parent_id:   Parent group id (None for top-level)
            pages:       List of (title, icon) tuples for child pages
            group_icon:  Icon for the group folder

        Returns: dict mapping page titles to tab UIDs

        Usage:
            tabs = nb.menu("资产管理", top_gid, [
                ("资产台账", "databaseoutlined"),
                ("采购申请", "shoppingcartoutlined"),
            ], group_icon="bankoutlined")
            # tabs = {"资产台账": "abc123", "采购申请": "def456"}
        """
        gid = self.group(group_title, parent_id, icon=group_icon)
        tabs = {}
        for title, icon in pages:
            _, _, tu = self.route(title, gid, icon=icon)
            tabs[title] = tu
        return tabs

    def table(self, parent, coll, fields, first_click=True):
        """Create table block with gridSettings. Returns (grid, tbl, addnew, actcol).

        Creates BlockGridModel → TableBlockModel with single-block layout.
        For multi-block pages, use table_block() + page_layout() instead.
        """
        grid = self.save("BlockGridModel", parent, "grid", "object")
        tbl = self.save("TableBlockModel", grid, "items", "array", {
            "resourceSettings": {"init": {"dataSourceKey": "main", "collectionName": coll}},
            "tableSettings": {"defaultSorting": {"sort": [{"field": "createdAt", "direction": "desc"}]}}})
        self.save("FilterActionModel", tbl, "actions", "array", {}, 1)
        self.save("RefreshActionModel", tbl, "actions", "array", {}, 2)
        addnew = self.save("AddNewActionModel", tbl, "actions", "array", {
            "popupSettings": {"openView": {"collectionName": coll, "dataSourceKey": "main",
                                           "mode": "drawer", "size": "large", "pageModelClass": "ChildPageModel"}}}, 3)
        for i, f in enumerate(fields):
            self.col(tbl, coll, f, i + 1, click=(first_click and i == 0))
        actcol = self.save("TableActionsColumnModel", tbl, "columns", "array", {
            "tableColumnSettings": {"title": {"title": '{{t("Actions")}}'}}}, 99)
        # Set gridSettings for the table block
        gs = self._build_block_grid([(tbl,)])
        self.update(grid, {"stepParams": {"gridSettings": gs}})
        return grid, tbl, addnew, actcol

    def table_block(self, parent, coll, fields, first_click=True, title=None, sort=None,
                    link_actions=None):
        """Create standalone TableBlockModel (no grid wrapper). Returns (tbl, addnew, actcol).

        Use with page_layout() for multi-block pages.
        link_actions: [{"title": "Reports", "icon": "barChartOutlined"}]
        """
        if sort is None:
            sort = self._next_sort(parent)
        sp = {"resourceSettings": {"init": {"dataSourceKey": "main", "collectionName": coll}},
              "tableSettings": {"defaultSorting": {"sort": [{"field": "createdAt", "direction": "desc"}]}}}
        if title:
            sp["cardSettings"] = {"titleDescription": {"title": title}}
        tbl = self.save("TableBlockModel", parent, "items", "array", sp, sort)
        self.save("FilterActionModel", tbl, "actions", "array", {}, 1)
        self.save("RefreshActionModel", tbl, "actions", "array", {}, 2)
        addnew = self.save("AddNewActionModel", tbl, "actions", "array", {
            "popupSettings": {"openView": {"collectionName": coll, "dataSourceKey": "main",
                                           "mode": "drawer", "size": "large", "pageModelClass": "ChildPageModel"}}}, 3)
        if link_actions:
            for li, la in enumerate(link_actions):
                self.save("LinkActionModel", tbl, "actions", "array", {
                    "buttonSettings": {"general": {"title": la["title"], "type": "default",
                                                    **({"icon": la.get("icon")} if la.get("icon") else {})}}
                }, 4 + li)
        for i, f in enumerate(fields):
            self.col(tbl, coll, f, i + 1, click=(first_click and i == 0))
        actcol = self.save("TableActionsColumnModel", tbl, "columns", "array", {
            "tableColumnSettings": {"title": {"title": '{{t("Actions")}}'}}}, 99)
        return tbl, addnew, actcol

    def filter_form(self, parent, coll, field="name", target_uid=None, sort=None,
                    label="Search", search_fields=None):
        """Create FilterFormBlock with single search input.

        One input field that filters the target table. Use search_fields to
        specify which columns to search (one input searches multiple columns).

        Args:
            field: which field to bind the input to (default "name")
            target_uid: UID of the TableBlockModel to filter
            search_fields: list of field paths to search, e.g. ["name","code","description"]
                           If None, defaults to [field]

        Usage:
            fb, fi = nb.filter_form(grid, C, "name", target_uid=tbl,
                search_fields=["name", "code", "description"])

        Returns (filter_block_uid, filter_item_uid).
        The filter_item_uid is used internally by set_layout() to write filterManager.
        """
        if sort is None:
            sort = self._next_sort(parent)
        fb = self.save("FilterFormBlockModel", parent, "items", "array", {
            "formFilterBlockModelSettings": {"layout": {
                "layout": "horizontal", "labelAlign": "left",
                "labelWidth": 50, "labelWrap": False, "colon": True}},
        }, sort)
        fg = self.save("FilterFormGridModel", fb, "grid", "object")
        self._load_meta(coll)
        field_meta = self._field_cache.get(coll, {}).get(field, {})
        fi_sp = {
            "fieldSettings": {"init": {"dataSourceKey": "main",
                                       "collectionName": coll, "fieldPath": field}},
            "filterFormItemSettings": {
                "init": {
                    "filterField": {
                        "name": field,
                        "title": field.replace("_", " ").title(),
                        "interface": field_meta.get("interface", "input"),
                        "type": field_meta.get("type", "string"),
                    },
                    **({"defaultTargetUid": target_uid} if target_uid else {}),
                },
                "showLabel": {"showLabel": True},
                "label": {"label": label},
            },
        }
        fi = self.save("FilterFormItemModel", fg, "items", "array", fi_sp, 10)
        self.save("InputFieldModel", fi, "field", "object", {}, 0)

        # Store filter mapping for set_layout() to write filterManager
        if target_uid:
            paths = search_fields or [field]
            self._filter_mappings = getattr(self, '_filter_mappings', {})
            self._filter_mappings.setdefault(parent, []).append({
                "filterId": fi, "targetId": target_uid, "filterPaths": paths})

        return fb, fi

    def action_panel(self, parent, actions, sort=0):
        """Create ActionPanelBlock with buttons.

        actions: [
            {"type": "popup", "title": "New Ticket", "mode": "drawer", "size": "large",
             "coll": "...", "tabs": [...]},
            {"type": "link", "title": "Reports", "icon": "barChartOutlined"},
        ]
        Returns panel_uid.
        """
        panel = self.save("ActionPanelBlockModel", parent, "items", "array", {}, sort)
        for i, act in enumerate(actions):
            if act["type"] == "link":
                self.save("LinkActionModel", panel, "actions", "array", {
                    "buttonSettings": {"general": {"title": act["title"], "type": "default",
                                                    **({"icon": act.get("icon")} if act.get("icon") else {})}}
                }, i)
            elif act["type"] == "popup":
                pu = uid()
                self.save("PopupActionModel", panel, "actions", "array", {
                    "popupSettings": {"openView": {
                        "collectionName": act.get("coll", ""),
                        "dataSourceKey": "main",
                        "mode": act.get("mode", "drawer"),
                        "size": act.get("size", "large"),
                        "pageModelClass": "ChildPageModel", "uid": pu}},
                    "buttonSettings": {"general": {"title": act["title"],
                                                    "type": act.get("btn_type", "primary"),
                                                    **({"icon": act.get("icon")} if act.get("icon") else {})}}
                }, i, pu)
                if act.get("tabs"):
                    tabs = act["tabs"]
                    enable = len(tabs) > 1
                    cp = self.save("ChildPageModel", pu, "page", "object",
                                   {"pageSettings": {"general": {"displayTitle": False, "enableTabs": enable}}})
                    for ti, tab in enumerate(tabs):
                        ct = self.save("ChildPageTabModel", cp, "tabs", "array",
                                       {"pageTabSettings": {"tab": {"title": tab["title"]}}}, ti)
                        bg = self.save("BlockGridModel", ct, "grid", "object")
                        self._build_tab_blocks(bg, act.get("coll", ""), tab)
        return panel

    def page_layout(self, tab_uid):
        """Create BlockGridModel for multi-block page. Returns grid UID.

        Automatically cleans existing content under the tab first.

        Usage:
            grid = nb.page_layout(tab_uid)
            kpis = nb.kpi_row(grid, coll, ("Total",), ("Active", ...))
            tbl, an, ac = nb.table_block(grid, coll, fields)
            nb.set_layout(grid, [
                [(k, 6) for k in kpis],
                (tbl,),
            ])
        """
        self.clean_tab(tab_uid)
        return self.save("BlockGridModel", tab_uid, "grid", "object")

    def set_layout(self, grid_uid, rows_spec):
        """Set gridSettings on an existing BlockGridModel.

        rows_spec: list of rows, each row is:
            (block_uid,)                    → full width (24)
            [(uid1, 16), (uid2, 8)]         → multi-column with sizes

        Also writes filterManager if filter_form() was called with target_uid.
        """
        gs = self._build_block_grid(rows_spec)
        self.update(grid_uid, {"stepParams": {"gridSettings": gs}})

        # Write filterManager — it's a top-level field on BlockGridModel,
        # needs flowModels:save (flat format) not flowModels:update (options wrapper)
        fm = getattr(self, '_filter_mappings', {}).get(grid_uid, [])
        if fm:
            self.s.post(f"{self.base}/api/flowModels:save",
                        json={"uid": grid_uid, "filterManager": fm})

    def sub_table(self, parent_grid, parent_coll, assoc, target_coll, fields, title=None):
        """Create association sub-table. Returns (tbl, addnew)."""
        tbl = self.save("TableBlockModel", parent_grid, "items", "array", {
            "resourceSettings": {"init": {"dataSourceKey": "main", "collectionName": target_coll,
                                          "associationName": f"{parent_coll}.{assoc}",
                                          "sourceId": "{{ctx.view.inputArgs.filterByTk}}"}},
            **({"cardSettings": {"titleDescription": {"title": title}}} if title else {})})
        self.save("RefreshActionModel", tbl, "actions", "array", {}, 2)
        addnew = self.save("AddNewActionModel", tbl, "actions", "array", {
            "popupSettings": {"openView": {"collectionName": target_coll, "dataSourceKey": "main",
                                           "mode": "dialog", "size": "small", "pageModelClass": "ChildPageModel"}}}, 3)
        for i, f in enumerate(fields):
            self.col(tbl, target_coll, f, i + 1)
        self.save("TableActionsColumnModel", tbl, "columns", "array", {
            "tableColumnSettings": {"title": {"title": '{{t("Actions")}}'}}}, 99)
        return tbl, addnew

    def addnew_form(self, addnew_uid, coll, fields, required=None, props=None,
                    mode="drawer", size="large"):
        """Create form under AddNew. Supports multi-column fields.

        props: dict mapping field_name → per-field properties (overlay).
            Example: {"name": {"description": "请输入全称"},
                      "status": {"defaultValue": "在用"}}
        """
        req = set(required or [])
        # Update popup settings on AddNew action
        self.update(addnew_uid, {"stepParams": {"popupSettings": {"openView": {
            "collectionName": coll, "dataSourceKey": "main",
            "mode": mode, "size": size, "pageModelClass": "ChildPageModel"}}}})
        cp = self.save("ChildPageModel", addnew_uid, "page", "object",
                       {"pageSettings": {"general": {"displayTitle": False, "enableTabs": False}}})
        ct = self.save("ChildPageTabModel", cp, "tabs", "array",
                       {"pageTabSettings": {"tab": {"title": "New"}}})
        bg = self.save("BlockGridModel", ct, "grid", "object")
        fm = self.save("CreateFormModel", bg, "items", "array",
                       {"resourceSettings": {"init": {"dataSourceKey": "main", "collectionName": coll}}})
        self.save("FormSubmitActionModel", fm, "actions", "array", {}, 0)
        fg = self.save("FormGridModel", fm, "grid", "object")
        self._build_form_grid(fg, coll, fields, req, props=props)
        return cp

    def edit_action(self, actcol, coll, fields, required=None, props=None,
                    mode="drawer", size="large"):
        """Create Edit action + form. Supports multi-column fields.

        props: dict mapping field_name → per-field properties (overlay).
        """
        req = set(required or [])
        ea = self.save("EditActionModel", actcol, "actions", "array", {
            "popupSettings": {"openView": {"collectionName": coll, "dataSourceKey": "main",
                                           "mode": mode, "size": size, "pageModelClass": "ChildPageModel",
                                           "filterByTk": "{{ ctx.record.id }}"}}}, 0)
        cp = self.save("ChildPageModel", ea, "page", "object",
                       {"pageSettings": {"general": {"displayTitle": False, "enableTabs": False}}})
        ct = self.save("ChildPageTabModel", cp, "tabs", "array",
                       {"pageTabSettings": {"tab": {"title": "Edit"}}})
        bg = self.save("BlockGridModel", ct, "grid", "object")
        fm = self.save("EditFormModel", bg, "items", "array", {
            "resourceSettings": {"init": {"dataSourceKey": "main", "collectionName": coll,
                                          "filterByTk": "{{ctx.view.inputArgs.filterByTk}}"}}})
        self.save("FormSubmitActionModel", fm, "actions", "array", {}, 0)
        fg = self.save("FormGridModel", fm, "grid", "object")
        self._build_form_grid(fg, coll, fields, req, props=props)
        return ea

    def detail_popup(self, parent_uid, coll, tabs, mode="drawer", size="large"):
        """Multi-tab detail popup with multi-block support per tab.

        tabs = [
            # 详情（支持多列字段）
            {"title": "Info", "fields": [
                [("name", 12), ("code", 12)], "description"]},
            # 多区块标签页
            {"title": "Overview", "blocks": [
                {"type": "details", "fields": [...]},
                {"type": "js", "title": "Stats", "code": "..."},
                {"type": "sub_table", "assoc": "items", "coll": "x", "fields": [...]},
                {"type": "form", "fields": [...], "required": [...]},
            ], "sizes": [16, 8]},
            # 子表格（旧格式兼容）
            {"title": "Tasks", "assoc": "tasks", "coll": "x", "fields": [...]},
        ]
        """
        # Update parent's popup settings (mode/size)
        self.update(parent_uid, {"stepParams": {"popupSettings": {"openView": {
            "collectionName": coll, "dataSourceKey": "main",
            "mode": mode, "size": size,
            "pageModelClass": "ChildPageModel", "uid": parent_uid}}}})
        enable_tabs = len(tabs) > 1
        cp = self.save("ChildPageModel", parent_uid, "page", "object",
                       {"pageSettings": {"general": {"displayTitle": False, "enableTabs": enable_tabs}}})
        for ti, tab in enumerate(tabs):
            ct = self.save("ChildPageTabModel", cp, "tabs", "array",
                           {"pageTabSettings": {"tab": {"title": tab["title"]}}}, ti)
            bg = self.save("BlockGridModel", ct, "grid", "object")
            self._build_tab_blocks(bg, coll, tab)
        return cp

    def popup_action(self, actcol, coll, title, tabs, mode="dialog", size="small",
                     icon=None, btn_type="link", sort=1):
        """Create PopupCollectionActionModel with custom content."""
        au = uid()
        sp = {
            "popupSettings": {"openView": {
                "collectionName": coll, "dataSourceKey": "main",
                "mode": mode, "size": size, "pageModelClass": "ChildPageModel",
                "uid": au, "filterByTk": "{{ ctx.record.id }}"}},
            "buttonSettings": {"general": {"type": btn_type, "title": title,
                                           **({"icon": icon} if icon else {})}},
        }
        self.save("PopupCollectionActionModel", actcol, "actions", "array", sp, sort, au)
        enable_tabs = len(tabs) > 1
        cp = self.save("ChildPageModel", au, "page", "object",
                       {"pageSettings": {"general": {"displayTitle": False, "enableTabs": enable_tabs}}})
        for ti, tab in enumerate(tabs):
            ct = self.save("ChildPageTabModel", cp, "tabs", "array",
                           {"pageTabSettings": {"tab": {"title": tab["title"]}}}, ti)
            bg = self.save("BlockGridModel", ct, "grid", "object")
            if tab.get("form"):
                fm = self.save("EditFormModel", bg, "items", "array", {
                    "resourceSettings": {"init": {"dataSourceKey": "main", "collectionName": coll,
                                                  "filterByTk": "{{ctx.view.inputArgs.filterByTk}}"}}})
                self.save("FormSubmitActionModel", fm, "actions", "array", {}, 0)
                fg = self.save("FormGridModel", fm, "grid", "object")
                req = set(tab.get("required", []))
                self._build_form_grid(fg, coll, tab["form"], req)
            else:
                self._build_tab_blocks(bg, coll, tab)
        return au, cp

    def config_table(self, tab_uid, coll, fields, title):
        """Create a config table in a Settings tab (table + inline AddNew)."""
        bg = self.save("BlockGridModel", tab_uid, "grid", "object")
        tbl = self.save("TableBlockModel", bg, "items", "array", {
            "resourceSettings": {"init": {"dataSourceKey": "main", "collectionName": coll}},
            "cardSettings": {"titleDescription": {"title": title}}})
        self.save("FilterActionModel", tbl, "actions", "array", {}, 1)
        self.save("RefreshActionModel", tbl, "actions", "array", {}, 2)
        an = self.save("AddNewActionModel", tbl, "actions", "array", {
            "popupSettings": {"openView": {"collectionName": coll, "dataSourceKey": "main",
                                           "mode": "dialog", "size": "small", "pageModelClass": "ChildPageModel"}}}, 3)
        for i, f in enumerate(fields):
            self.col(tbl, coll, f, i + 1)
        self.addnew_form(an, coll, fields, required=[fields[0]] if fields else [])
        return tbl

    # ── JS 区块 ─────────────────────────────────────────────────

    def js_block(self, parent_grid, title, code, sort=None):
        """Create page-level JSBlockModel."""
        if sort is None:
            sort = self._next_sort(parent_grid)
        sp = {"jsSettings": {"runJs": {"version": "v1", "code": code}},
              "cardSettings": {"titleDescription": {"title": title}}}
        return self.save("JSBlockModel", parent_grid, "items", "array", sp, sort)

    def js_column(self, table_uid, title, code, sort=50, width=None):
        """Create JSColumnModel in table."""
        sp = {"jsSettings": {"runJs": {"version": "v1", "code": code}},
              "tableColumnSettings": {"title": {"title": title}}}
        if width:
            sp["tableColumnSettings"]["width"] = {"width": width}
        return self.save("JSColumnModel", table_uid, "columns", "array", sp, sort)

    def js_item(self, form_grid, title, code, sort=0):
        """Create JSItemModel in form/details."""
        sp = {"jsSettings": {"runJs": {"version": "v1", "code": code}},
              "editItemSettings": {"showLabel": {"showLabel": True, "title": title}}}
        return self.save("JSItemModel", form_grid, "items", "array", sp, sort)

    # ── JS 模板 — 常用组件自动生成 ────────────────────────────

    def kpi(self, parent, title, coll, filter_=None, color=None, sort=None):
        """Create a working KPI card that queries API and shows count.

        Usage:
            kpi1 = nb.kpi(grid, "Total", "nb_pm_projects")
            kpi2 = nb.kpi(grid, "Active", "nb_pm_projects",
                          filter_={"status": "active"}, color="#1890ff")
        """
        filter_js = ""
        if filter_:
            import json
            filter_js = f", filter: {json.dumps(filter_)}"
        color_js = f", color:'{color}'" if color else ""
        code = f"""(async () => {{
  try {{
    const r = await ctx.api.request({{
      url: '{coll}:list',
      params: {{ paginate: false{filter_js} }}
    }});
    const count = Array.isArray(r?.data?.data) ? r.data.data.length
                : Array.isArray(r?.data) ? r.data.length : 0;
    ctx.render(ctx.React.createElement(ctx.antd.Statistic, {{
      title: '{title}', value: count,
      valueStyle: {{ fontSize: 28{color_js} }}
    }}));
  }} catch(e) {{
    ctx.render(ctx.React.createElement(ctx.antd.Statistic, {{
      title: '{title}', value: '?', valueStyle: {{ fontSize: 28 }}
    }}));
  }}
}})();"""
        return self.js_block(parent, title, code, sort)

    def kpi_row(self, parent, coll, *specs):
        """Create multiple KPI cards in one call. Returns list of UIDs.

        specs: ("Title", filter_dict_or_None, color_or_None)
            or just "Title" for a simple count

        Usage:
            kpis = nb.kpi_row(grid, "nb_pm_projects",
                ("Total",),
                ("Active",   {"status": "active"},  "#1890ff"),
                ("Completed",{"status": "done"},    "#52c41a"),
                ("At Risk",  {"status": "blocked"}, "#ff4d4f"))
        """
        uids = []
        for spec in specs:
            if isinstance(spec, str):
                spec = (spec,)
            title = spec[0]
            filter_ = spec[1] if len(spec) > 1 else None
            color = spec[2] if len(spec) > 2 else None
            uids.append(self.kpi(parent, title, coll, filter_, color))
        return uids

    def chart_placeholder(self, parent, title, desc="", icon="📊", sort=None):
        """Styled chart placeholder (nicer than plain TODO)."""
        code = f"""ctx.render(ctx.React.createElement('div', {{
  style: {{ padding: 32, textAlign: 'center', background: 'linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%)',
    borderRadius: 8, minHeight: 200, display: 'flex', alignItems: 'center',
    justifyContent: 'center', flexDirection: 'column' }}
}}, [
  ctx.React.createElement('div', {{key:'i', style:{{fontSize:48, marginBottom:12}}}}, '{icon}'),
  ctx.React.createElement('div', {{key:'t', style:{{fontSize:16, fontWeight:500, color:'#333'}}}}, '{title}'),
  ctx.React.createElement('div', {{key:'d', style:{{fontSize:12, marginTop:6, color:'#999'}}}}, '{desc}'),
]));"""
        return self.js_block(parent, title, code, sort)

    def quick_filter(self, parent, coll, field, labels, target_uid, sort=None):
        """Create JS quick-filter tags that filter a target table.

        Usage:
            nb.quick_filter(grid, "nb_pm_projects", "status",
                ["All", "Active", "Completed", "Blocked"], tbl)
        """
        import json
        labels_js = json.dumps(labels)
        code = f"""const targetUid = '{target_uid}';
const field = '{field}';
const labels = {labels_js};
const {{ Tag, Space }} = ctx.antd;
const [active, setActive] = ctx.React.useState('All');

const handleClick = (label) => {{
  setActive(label);
  // TODO: 联动筛选 targetUid 表格
  // ctx.model.getModelByUid(targetUid)?.setFilter(...)
}};

ctx.render(ctx.React.createElement(Space, {{ wrap: true }},
  labels.map(s => ctx.React.createElement(Tag, {{
    key: s,
    color: s === active ? 'blue' : undefined,
    style: {{ cursor: 'pointer', padding: '4px 12px', userSelect: 'none' }},
    onClick: () => handleClick(s)
  }}, s))
));"""
        return self.js_block(parent, f"{field} Filter", code, sort)

    def event_flow(self, model_uid, event_name, code):
        """Add flowRegistry event flow (runjs) to existing model. Returns flow_key."""
        r = self.s.get(f"{self.base}/api/flowModels:get?filterByTk={model_uid}")
        if not r.ok:
            self.errors.append(f"event_flow GET {model_uid}: {r.text[:100]}")
            return None
        data = r.json().get("data", {})
        registry = data.get("flowRegistry", {}) or {}

        flow_key, step_key = uid(), uid()
        registry[flow_key] = {
            "key": flow_key, "title": "Event flow",
            "on": {"eventName": event_name,
                   "defaultParams": {"condition": {"items": [], "logic": "$and"}}},
            "steps": {step_key: {
                "key": step_key, "use": "runjs", "sort": 1,
                "flowKey": flow_key, "defaultParams": {"code": code}}},
        }
        self.update(model_uid, {"flowRegistry": registry})
        return flow_key

    # ── 查找辅助 ────────────────────────────────────────────────

    def find_click_field(self, tbl_uid, field_name="name"):
        """Find the DisplayFieldModel UID of a click-to-open column in a table.
        Returns UID or None."""
        r = self.s.get(f"{self.base}/api/flowModels:list?paginate=false")
        items = r.json().get("data", [])
        for it in items:
            if it.get("parentId") == tbl_uid and it.get("use") == "TableColumnModel":
                fp = it.get("stepParams", {}).get("fieldSettings", {}).get("init", {}).get("fieldPath")
                if fp == field_name:
                    for ch in items:
                        if ch.get("parentId") == it["uid"] and "Display" in (ch.get("use") or ""):
                            return ch["uid"]
        return None

    # ── 高级封装：需求占位 + 表单逻辑 ─────────────────────────

    def outline(self, parent, title, ctx_info, sort=None, kind="block"):
        """Create JS block/column/item that displays a planning outline on the page.

        The outline shows all context needed for later implementation by AI/human.
        The block's own UID is auto-injected into the rendered output.

        Args:
            parent:   parent UID (grid for block, table for column, form grid for item)
            title:    display title
            ctx_info: dict of context info to render. Common keys:
                      type, collection, filter, target_uid, description, fields,
                      api, event, formula — any key/value works.
            sort:     sort index (auto-increment if None)
            kind:     "block" (JSBlockModel) | "column" (JSColumnModel) |
                      "item" (JSItemModel)

        Returns: UID of created block

        Usage:
            # KPI 大纲
            nb.outline(grid, "在用资产统计", {
                "type": "kpi",
                "collection": "nb_am_assets",
                "filter": {"status": "在用"},
                "render": "antd.Statistic, count query",
            })

            # 筛选按钮大纲
            nb.outline(grid, "状态筛选", {
                "type": "quick-filter",
                "target_uid": table_uid,
                "field": "status",
                "options": ["全部", "在用", "借用中", "报修中", "已报废"],
            })

            # 图表大纲
            nb.outline(grid, "资产分类分布", {
                "type": "chart",
                "chart_type": "pie",
                "collection": "nb_am_assets",
                "group_by": "category_id",
            })

            # 表格 JS 列大纲
            nb.outline(table, "状态", {
                "type": "status-tag",
                "field": "status",
                "colors": {"在用":"green", "借用中":"blue", "报修中":"orange"},
            }, kind="column")

            # 事件流大纲（显示在表单区域）
            nb.outline(form_grid, "自动计算总价", {
                "type": "event-flow",
                "event": "formValuesChange",
                "trigger_fields": ["quantity", "unit_price"],
                "target_field": "total_amount",
                "formula": "quantity * unit_price",
            }, kind="item")
        """
        import json as _json
        u = uid()
        ctx_info_with_uid = {"uid": u, **ctx_info}
        info_json = _json.dumps(ctx_info_with_uid, ensure_ascii=False, indent=2)

        icon = "\U0001f4cb"  # 📋
        code = (
            "const h = ctx.React.createElement;\n"
            f"const info = {info_json};\n"
            "const entries = Object.entries(info);\n"
            "const tk = ctx.themeToken || {};\n"
            "ctx.render(h('div', {style: {"
            "padding: 10, borderRadius: 6, fontSize: 12, lineHeight: '20px', "
            "background: tk.colorBgLayout || '#f5f5f5', "
            "border: '1px dashed ' + (tk.colorBorder || '#d9d9d9')"
            "}},\n"
            "  h('div', {style: {fontWeight: 600, fontSize: 13, marginBottom: 4, "
            "color: tk.colorPrimary || '#1890ff'}}, "
            f"'{icon} {title}'),\n"
            "  ...entries.map(([k,v]) => h('div', {key: k, style: {"
            "color: tk.colorTextSecondary || '#888'}},\n"
            "    h('span', {style: {fontWeight: 500, color: tk.colorText || '#333', "
            "marginRight: 4}}, k + ':'),\n"
            "    h('span', null, typeof v === 'object' ? JSON.stringify(v) : String(v))\n"
            "  ))\n"
            "));"
        )

        if kind == "column":
            return self.js_column(parent, title, code, sort or 50, width=120)
        elif kind == "item":
            return self.js_item(parent, title, code, sort or 0)
        else:
            return self.js_block(parent, title, code, sort)

    def outline_row(self, parent, *specs):
        """Create multiple outline blocks in one call. Returns list of UIDs.

        specs: (title, ctx_info_dict) tuples.

        Usage:
            nb.outline_row(grid,
                ("在用资产", {"type": "kpi", "collection": "nb_am_assets", "filter": {"status": "在用"}}),
                ("借用中",   {"type": "kpi", "collection": "nb_am_assets", "filter": {"status": "借用中"}}),
                ("已报废",   {"type": "kpi", "collection": "nb_am_assets", "filter": {"status": "已报废"}}),
            )
        """
        return [self.outline(parent, t, c) for t, c in specs]

    def outline_columns(self, table_uid, *specs):
        """Plan multiple JS columns for a table. Returns list of UIDs.

        Each spec is (title, ctx_info_dict). Common ctx_info keys:
            type:    "status-tag" | "badge" | "amount" | "countdown" | "composite"
                     | "computed" | "progress" | "relation-count"
            field:   source field name (for single-field columns)
            fields:  source field names (for multi-field columns)
            colors:  color mapping dict
            formula: calculation description
            render:  rendering description
            api:     API endpoint for async columns

        Usage:
            nb.outline_columns(table_uid,
                ("状态", {"type": "status-tag", "field": "status",
                          "colors": {"在用":"green", "借用中":"blue"}}),
                ("净值", {"type": "computed", "fields": ["purchase_price", "useful_years"],
                          "formula": "直线折旧法", "render": "金额, 低于30%标红"}),
                ("维修次数", {"type": "relation-count", "api": "nb_am_repairs:list",
                              "filter_field": "asset_id", "render": ">3次标红"}),
            )
        """
        return [self.outline(table_uid, t, c, kind="column") for t, c in specs]

    def js_todo(self, parent, title, requirement, sort=0, block_type="block"):
        """Create JS block/item with requirement description (legacy, prefer outline()).

        block_type: "block" (page-level JSBlockModel) or "item" (form JSItemModel)
        """
        code = f"// TODO: {title}\n"
        code += f"// {'=' * 50}\n"
        for line in requirement.strip().splitlines():
            code += f"// {line.strip()}\n"
        code += f"// {'=' * 50}\n\n"
        code += ("ctx.render(ctx.React.createElement('div', "
                 "{style:{padding:16,textAlign:'center',color:'#999',background:'#fafafa',"
                 "borderRadius:8,border:'1px dashed #d9d9d9'}},"
                 f"'🚧 {title} (待实现)'))")

        if block_type == "item":
            return self.js_item(parent, title, code, sort)
        else:
            return self.js_block(parent, title, code, sort)

    def form_logic(self, form_uid, description, code=None):
        """Add formValuesChange event flow with requirement description.

        If code is None, creates a placeholder with the description.
        Otherwise uses the provided JS code.

        Usage:
            nb.form_logic(form_uid, '''
            自动计算：
            - story_points 变化时更新 estimated_hours = story_points * 4
            - status 变为 done 时自动填充 completed_date
            ''')
        """
        if code is None:
            code = "// Form Logic — formValuesChange\n"
            code += f"// {'=' * 50}\n"
            for line in description.strip().splitlines():
                code += f"// {line.strip()}\n"
            code += f"// {'=' * 50}\n\n"
            code += ("(async () => {\n"
                     "  const values = ctx.form?.values || {};\n"
                     "  // TODO: Implement form logic\n"
                     "  console.log('Form values changed:', Object.keys(values));\n"
                     "})();")
        return self.event_flow(form_uid, "formValuesChange", code)

    def before_render(self, model_uid, description, code=None):
        """Add beforeRender event flow (initialization logic).

        Usage:
            nb.before_render(details_uid, '''
            初始化：加载项目统计数据
            ''')
        """
        if code is None:
            code = "// beforeRender\n"
            for line in description.strip().splitlines():
                code += f"// {line.strip()}\n"
            code += "\nctx.model.setFieldsValue(ctx.defaultValues);"
        return self.event_flow(model_uid, "beforeRender", code)

    # ── Summary ─────────────────────────────────────────────────

    def summary(self):
        print(f"\n✅ Created {self.created} nodes", end="")
        if self.errors:
            print(f", {len(self.errors)} errors", end="")
        if self.warnings:
            print(f", {len(self.warnings)} warnings", end="")
        print()
        for e in self.errors[:10]:
            print(f"  ❌ {e}")
        for w in self.warnings[:10]:
            print(f"  {w}")
