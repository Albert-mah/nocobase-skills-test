"""NocoBase API client — login, session management, base request helpers.

Extracted from nb_page_builder.py NB class. Provides two client variants:

- NB: requests-based client with session management (for page building tools)
- NocoBaseClient: stdlib-only client (for data modeling tools)

Both auto-login on construction and provide the same base URL + auth token.
"""

import json
import os
import urllib.request
import urllib.error

import requests

from .utils import uid, deep_merge

# ── Interface -> Model mappings (used by page building tools) ──────────

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


# ── Interface -> uiSchema templates (for data modeling) ────────────────

INTERFACE_TEMPLATES = {
    "input": {
        "type": "string",
        "uiSchema": {"type": "string", "x-component": "Input"},
    },
    "textarea": {
        "type": "text",
        "uiSchema": {"type": "string", "x-component": "Input.TextArea"},
    },
    "email": {
        "type": "string",
        "uiSchema": {"type": "string", "x-component": "Input", "x-validator": "email"},
    },
    "phone": {
        "type": "string",
        "uiSchema": {"type": "string", "x-component": "Input", "x-component-props": {"type": "tel"}},
    },
    "url": {
        "type": "text",
        "uiSchema": {"type": "string", "x-component": "Input.URL"},
    },
    "password": {
        "type": "password",
        "hidden": True,
        "uiSchema": {"type": "string", "x-component": "Password"},
    },
    "color": {
        "type": "string",
        "uiSchema": {"type": "string", "x-component": "ColorPicker"},
    },
    "icon": {
        "type": "string",
        "uiSchema": {"type": "string", "x-component": "IconPicker"},
    },
    "markdown": {
        "type": "text",
        "uiSchema": {"type": "string", "x-component": "Markdown"},
    },
    "richText": {
        "type": "text",
        "uiSchema": {"type": "string", "x-component": "RichText"},
    },
    "select": {
        "type": "string",
        "uiSchema": {"type": "string", "x-component": "Select", "enum": []},
    },
    "multipleSelect": {
        "type": "array",
        "defaultValue": [],
        "uiSchema": {"type": "array", "x-component": "Select", "x-component-props": {"mode": "multiple"}, "enum": []},
    },
    "radioGroup": {
        "type": "string",
        "uiSchema": {"type": "string", "x-component": "Radio.Group"},
    },
    "checkboxGroup": {
        "type": "array",
        "defaultValue": [],
        "uiSchema": {"type": "string", "x-component": "Checkbox.Group"},
    },
    "checkbox": {
        "type": "boolean",
        "uiSchema": {"type": "boolean", "x-component": "Checkbox"},
    },
    "number": {
        "type": "double",
        "uiSchema": {"type": "number", "x-component": "InputNumber", "x-component-props": {"stringMode": True, "step": "1"}},
    },
    "integer": {
        "type": "bigInt",
        "uiSchema": {"type": "number", "x-component": "InputNumber", "x-component-props": {"stringMode": True, "step": "1"}, "x-validator": "integer"},
    },
    "percent": {
        "type": "float",
        "uiSchema": {"type": "string", "x-component": "Percent", "x-component-props": {"stringMode": True, "step": "1", "addonAfter": "%"}},
    },
    "sort": {
        "type": "sort",
        "uiSchema": {"type": "number", "x-component": "InputNumber", "x-component-props": {"stringMode": True, "step": "1"}, "x-validator": "integer"},
    },
    "datetime": {
        "type": "date",
        "uiSchema": {"type": "string", "x-component": "DatePicker", "x-component-props": {"showTime": False, "utc": True}},
    },
    "date": {
        "type": "dateOnly",
        "uiSchema": {"type": "string", "x-component": "DatePicker", "x-component-props": {"dateOnly": True, "showTime": False}},
    },
    "datetimeNoTz": {
        "type": "datetimeNoTz",
        "uiSchema": {"type": "string", "x-component": "DatePicker", "x-component-props": {"showTime": False, "utc": False}},
    },
    "time": {
        "type": "time",
        "uiSchema": {"type": "string", "x-component": "TimePicker"},
    },
    "id": {
        "type": "bigInt",
        "autoIncrement": True,
        "primaryKey": True,
        "allowNull": False,
        "uiSchema": {"type": "number", "x-component": "InputNumber", "x-read-pretty": True},
    },
    "createdAt": {
        "type": "date",
        "field": "createdAt",
        "uiSchema": {"type": "datetime", "x-component": "DatePicker", "x-component-props": {}, "x-read-pretty": True},
    },
    "updatedAt": {
        "type": "date",
        "field": "updatedAt",
        "uiSchema": {"type": "datetime", "x-component": "DatePicker", "x-component-props": {}, "x-read-pretty": True},
    },
    "createdBy": {
        "type": "belongsTo",
        "target": "users",
        "foreignKey": "createdById",
        "uiSchema": {"type": "object", "x-component": "AssociationField", "x-component-props": {"fieldNames": {"label": "nickname", "value": "id"}}, "x-read-pretty": True},
    },
    "updatedBy": {
        "type": "belongsTo",
        "target": "users",
        "foreignKey": "updatedById",
        "uiSchema": {"type": "object", "x-component": "AssociationField", "x-component-props": {"fieldNames": {"label": "nickname", "value": "id"}}, "x-read-pretty": True},
    },
    "json": {
        "type": "json",
        "default": None,
        "uiSchema": {"type": "object", "x-component": "Input.JSON", "x-component-props": {"autoSize": {"minRows": 5}}},
    },
}

# System fields that must be created via API (not SQL)
SYSTEM_FIELD_PAYLOADS = [
    {
        "name": "createdAt", "interface": "createdAt", "type": "date", "field": "createdAt",
        "uiSchema": {
            "type": "datetime", "title": "Created at", "x-component": "DatePicker",
            "x-component-props": {}, "x-read-pretty": True,
        },
    },
    {
        "name": "updatedAt", "interface": "updatedAt", "type": "date", "field": "updatedAt",
        "uiSchema": {
            "type": "datetime", "title": "Updated at", "x-component": "DatePicker",
            "x-component-props": {}, "x-read-pretty": True,
        },
    },
    {
        "name": "createdBy", "interface": "createdBy", "type": "belongsTo", "target": "users",
        "foreignKey": "createdById",
        "uiSchema": {
            "type": "object", "title": "Created by", "x-component": "AssociationField",
            "x-component-props": {"fieldNames": {"label": "nickname", "value": "id"}},
            "x-read-pretty": True,
        },
    },
    {
        "name": "updatedBy", "interface": "updatedBy", "type": "belongsTo", "target": "users",
        "foreignKey": "updatedById",
        "uiSchema": {
            "type": "object", "title": "Updated by", "x-component": "AssociationField",
            "x-component-props": {"fieldNames": {"label": "nickname", "value": "id"}},
            "x-read-pretty": True,
        },
    },
]

SYSTEM_FIELD_MAP = {"id": "id", "sort": "sort"}


# ── Fields format parsing (multi-column + sections) ─────────────────────

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
    """Normalize fields parameter to internal representation. Returns (items, auto_required).

    Supports:
        1. Multi-line string (pipe syntax): "name* | code\\nstatus"
        2. List (legacy): ["name", "code", [("name",12),("code",12)], "---"]
        3. Mixed: list items also support pipe syntax
    """
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


class APIError(Exception):
    """Raised on HTTP errors from NocoBase API."""
    def __init__(self, code: int, body: str, url: str):
        self.code = code
        self.body = body
        self.url = url
        super().__init__(f"HTTP {code}: {url}\n{body[:500]}")


class NocoBaseClient:
    """Thin HTTP client for NocoBase API using only urllib (no requests dependency).

    Used by data modeling tools (collections, fields, SQL).
    """

    def __init__(self, base_url: str, user: str = "admin@nocobase.com",
                 password: str = "admin123"):
        self.base = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.token = None

    def login(self):
        data = self._request("POST", "/api/auth:signIn", {
            "account": self.user, "password": self.password
        })
        self.token = data["data"]["token"]
        return self.token

    def _request(self, method, path, body=None, expect_empty=False):
        url = self.base + path
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if not raw or expect_empty:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode()
            except Exception:
                pass
            raise APIError(e.code, body_text, url)

    def get(self, path):
        return self._request("GET", path)

    def post(self, path, body=None, expect_empty=False):
        return self._request("POST", path, body, expect_empty=expect_empty)

    def put(self, path, body=None):
        return self._request("PUT", path, body)

    def delete(self, path):
        return self._request("DELETE", path)


class NB:
    """NocoBase FlowPage builder — requests-based client with session management.

    Used by page building and route tools. Handles auto-login, metadata caching,
    FlowModel CRUD (save/update/destroy), and all high-level page building methods.
    """

    def __init__(self, base_url: str = None, auto_login: bool = True,
                 account: str = None, password: str = None):
        self.base = base_url or os.environ.get("NB_URL", "http://localhost:14000")
        self.account = account or os.environ.get("NB_USER", "admin@nocobase.com")
        self.password = password or os.environ.get("NB_PASSWORD", "admin123")
        self.s = requests.Session()
        self.s.trust_env = False
        self.created = 0
        self.errors = []
        self._field_cache = {}
        self._title_cache = {}
        self._sort_counters = {}
        if auto_login:
            self.login()

    def login(self, account: str = None, password: str = None):
        account = account or self.account
        password = password or self.password
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
                        "target": f.get("target", "")}
            for f in r.json().get("data", [])
        }
        if not self._title_cache:
            r2 = self.s.get(f"{self.base}/api/collections:list?paginate=false")
            for c in r2.json().get("data", []):
                self._title_cache[c["name"]] = c.get("titleField") or "name"

    def _iface(self, coll, field):
        self._load_meta(coll)
        return self._field_cache.get(coll, {}).get(field, {}).get("interface", "input")

    def _target(self, coll, field):
        self._load_meta(coll)
        return self._field_cache.get(coll, {}).get(field, {}).get("target", "")

    def _label(self, target_coll):
        self._load_meta(target_coll)
        return self._title_cache.get(target_coll, "name")

    def _next_sort(self, parent):
        self._sort_counters.setdefault(parent, 0)
        s = self._sort_counters[parent]
        self._sort_counters[parent] += 1
        return s

    # ── Low-level FlowModel API ───────────────────────────────────

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
        """Update existing FlowModel via flowModels:update (GET -> merge -> PUT).

        CRITICAL: flowModels:update is FULL REPLACE. Always GET first, deep merge,
        then PUT. Never send partial options.
        """
        r = self.s.get(f"{self.base}/api/flowModels:get?filterByTk={u}")
        if not r.ok:
            return False
        data = r.json().get("data", {})
        opts = {k: v for k, v in data.items() if k not in ("uid", "name")}
        deep_merge(opts, patch)
        r2 = self.s.post(f"{self.base}/api/flowModels:update?filterByTk={u}",
                         json={"options": opts})
        return r2.ok

    def destroy(self, u):
        self.s.post(f"{self.base}/api/flowModels:destroy?filterByTk={u}")

    def destroy_tree(self, u):
        descendants = self._collect_descendants(u)
        to_delete = descendants + [u]
        for uid_ in reversed(to_delete):
            self.s.post(f"{self.base}/api/flowModels:destroy?filterByTk={uid_}")
        self._invalidate_cache()
        return len(to_delete)

    def _list_all(self):
        if not hasattr(self, '_all_models_cache'):
            r = self.s.get(f"{self.base}/api/flowModels:list?paginate=false")
            self._all_models_cache = r.json().get("data", [])
        return self._all_models_cache

    def _invalidate_cache(self):
        if hasattr(self, '_all_models_cache'):
            del self._all_models_cache

    def _collect_descendants(self, root_uid):
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
        to_delete = self._collect_descendants(tab_uid)
        for uid_ in reversed(to_delete):
            self.s.post(f"{self.base}/api/flowModels:destroy?filterByTk={uid_}")
        self._sort_counters.pop(tab_uid, None)
        self._invalidate_cache()
        return len(to_delete)

    # ── Auto-infer primitives ───────────────────────────────────

    def col(self, tbl, coll, field, idx, click=False, width=None):
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

    # ── Internal builders ──────────────────────────────────────

    def _build_form_grid(self, fg, coll, fields, required, props=None):
        """Build form fields with gridSettings (multi-column + sections)."""
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
                rows[row_id] = [[fi] for fi in col_uids]
                sizes[row_id] = col_sizes

        gs = {"gridSettings": {"grid": {"rows": rows, "sizes": sizes}}}
        self.update(fg, {"stepParams": gs})

    def _build_detail_grid(self, dg, coll, fields):
        """Build detail fields with gridSettings (multi-column + sections)."""
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
                rows[row_id] = [[di] for di in col_uids]
                sizes[row_id] = col_sizes

        gs = {"gridSettings": {"grid": {"rows": rows, "sizes": sizes}}}
        self.update(dg, {"stepParams": gs})

    def _build_block_grid(self, rows_spec):
        """Convert declarative row specs to gridSettings JSON.

        Each element is a row:
            (block_uid,)                          → full width
            [(uid1, 16), (uid2, 8)]               → multi-column
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

    def _build_tab_blocks(self, bg, coll, tab):
        """Build multiple blocks inside a BlockGridModel (details/js/sub_table)."""
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

        # Multi-block layout
        tab_sizes = tab.get("sizes")
        if len(block_uids) > 1 or tab_sizes:
            row_id = uid()
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
        """Create menu group (folder in sidebar). Returns group route id."""
        data = {"type": "group", "title": title, "icon": icon}
        if parent_id is not None:
            data["parentId"] = parent_id
        r = self.s.post(f"{self.base}/api/desktopRoutes:create", json=data)
        return r.json().get("data", {}).get("id")

    def route(self, title, parent_id, icon="appstoreoutlined", tabs=None):
        """Create a page (flowPage) route. Returns (route_id, page_uid, tab_uid_or_dict)."""
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
            return rid, pu, tu

    def menu(self, group_title, parent_id, pages, *, group_icon="appstoreoutlined"):
        """Create a menu group with child pages. Returns dict {title: tab_uid}."""
        gid = self.group(group_title, parent_id, icon=group_icon)
        tabs = {}
        for title, icon in pages:
            _, _, tu = self.route(title, gid, icon=icon)
            tabs[title] = tu
        return tabs

    def table_block(self, parent, coll, fields, first_click=True, title=None, sort=None,
                    link_actions=None):
        """Create standalone TableBlockModel. Returns (tbl, addnew, actcol)."""
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
        """Create FilterFormBlock with single search input. Returns (filter_block_uid, filter_item_uid)."""
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

        if target_uid:
            paths = search_fields or [field]
            self._filter_mappings = getattr(self, '_filter_mappings', {})
            self._filter_mappings.setdefault(parent, []).append({
                "filterId": fi, "targetId": target_uid, "filterPaths": paths})

        return fb, fi

    def page_layout(self, tab_uid):
        """Create BlockGridModel for multi-block page. Returns grid UID."""
        self.clean_tab(tab_uid)
        return self.save("BlockGridModel", tab_uid, "grid", "object")

    def set_layout(self, grid_uid, rows_spec):
        """Set gridSettings on an existing BlockGridModel. Also writes filterManager."""
        gs = self._build_block_grid(rows_spec)
        self.update(grid_uid, {"stepParams": {"gridSettings": gs}})

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
        """Create form under AddNew popup. Returns childpage UID."""
        req = set(required or [])
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
        """Create Edit action + form. Returns edit action UID."""
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
        """Multi-tab detail popup. Returns childpage UID."""
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

    # ── JS blocks ──────────────────────────────────────────────

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

    # ── KPI ────────────────────────────────────────────────────

    def kpi(self, parent, title, coll, filter_=None, color=None, sort=None):
        """Create a KPI card that queries API and shows count."""
        filter_js = ""
        if filter_:
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

    # ── Event flows ────────────────────────────────────────────

    def event_flow(self, model_uid, event_name, code):
        """Add event flow (runjs step) to an existing FlowModel node."""
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

    def form_logic(self, form_uid, description, code=None):
        """Add formValuesChange event flow."""
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
        """Add beforeRender event flow."""
        if code is None:
            code = "// beforeRender\n"
            for line in description.strip().splitlines():
                code += f"// {line.strip()}\n"
            code += "\nctx.model.setFieldsValue(ctx.defaultValues);"
        return self.event_flow(model_uid, "beforeRender", code)

    # ── Outline (planning placeholders) ────────────────────────

    def outline(self, parent, title, ctx_info, sort=None, kind="block"):
        """Create JS block/column/item that displays a planning outline on the page.

        The outline shows all context needed for later implementation by AI/human.
        The block's own UID is auto-injected into the rendered output.

        Args:
            parent:   parent UID (grid for block, table for column, form grid for item)
            title:    display title
            ctx_info: dict of context info to render
            sort:     sort index (auto-increment if None)
            kind:     "block" (JSBlockModel) | "column" (JSColumnModel) | "item" (JSItemModel)

        Returns: UID of created block
        """
        u = uid()
        ctx_info_with_uid = {"uid": u, **ctx_info}
        info_json = json.dumps(ctx_info_with_uid, ensure_ascii=False, indent=2)

        icon = "\U0001f4cb"  # clipboard emoji
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
        """Create multiple outline blocks. Returns list of UIDs.
        specs: (title, ctx_info_dict) tuples.
        """
        return [self.outline(parent, t, c) for t, c in specs]

    def outline_columns(self, table_uid, *specs):
        """Plan multiple JS columns for a table. Returns list of UIDs.
        specs: (title, ctx_info_dict) tuples.
        """
        return [self.outline(table_uid, t, c, kind="column") for t, c in specs]

    # ── Find helpers ───────────────────────────────────────────

    def find_click_field(self, tbl_uid, field_name="name"):
        """Find the DisplayFieldModel UID of a click-to-open column."""
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

    # ── AI Employee ────────────────────────────────────────────

    def ai_employee_create(self, username, nickname, position, avatar, bio,
                           about, greeting, skills, model_settings=None):
        """Create an AI employee. Returns username."""
        values = {
            "username": username,
            "nickname": nickname,
            "position": position,
            "avatar": avatar,
            "bio": bio,
            "about": about,
            "greeting": greeting,
            "enabled": True,
            "builtIn": False,
            "skillSettings": {"skills": skills},
            "modelSettings": model_settings or {
                "llmService": "gemini",
                "model": "models/gemini-2.5-flash",
                "temperature": 0.7, "topP": 1,
                "frequencyPenalty": 0, "presencePenalty": 0,
                "timeout": 60000, "maxRetries": 1,
                "responseFormat": "text",
            },
            "enableKnowledgeBase": False,
            "knowledgeBase": {"topK": 3, "score": "0.6", "knowledgeBaseIds": []},
            "knowledgeBasePrompt": "From knowledge base:\n{knowledgeBaseData}\nanswer user's question using this information.",
        }
        r = self.s.post(f"{self.base}/api/aiEmployees:create", json=values)
        return r.json().get("data", {}).get("username", username)

    def ai_employee_list(self):
        """List all AI employees."""
        r = self.s.get(f"{self.base}/api/aiEmployees:list?paginate=false")
        return r.json().get("data", [])

    def ai_employee_get(self, username):
        """Get AI employee by username."""
        r = self.s.get(f"{self.base}/api/aiEmployees:get?filterByTk={username}")
        return r.json().get("data", {})

    def ai_employee_update(self, username, values):
        """Update AI employee fields."""
        r = self.s.post(f"{self.base}/api/aiEmployees:update?filterByTk={username}",
                        json=values)
        return r.ok

    def ai_employee_delete(self, username):
        """Delete AI employee by username."""
        r = self.s.post(f"{self.base}/api/aiEmployees:destroy?filterByTk={username}")
        return r.ok

    def ai_shortcut_list(self, page_schema_uid, employees):
        """Create floating avatar shortcuts on a page.

        Args:
            page_schema_uid: Tab schemaUid of the page
            employees: list of dicts [{username, tasks: [{title, system, user}]}]
        Returns: container UID
        """
        container_uid = f"ai-shortcuts-{page_schema_uid}"
        self.save("AIEmployeeShortcutListModel", page_schema_uid,
                  "ai-shortcuts", "object", sp={}, u=container_uid)
        for i, emp in enumerate(employees):
            tasks = emp.get("tasks", [])
            sp = {"shortcutSettings": {"editTasks": {"tasks": tasks}}} if tasks else {}
            self.save("AIEmployeeShortcutModel", container_uid,
                      "shortcuts", "array",
                      sp=sp, sort=i,
                      props={"aiEmployee": {"username": emp["username"]}})
        return container_uid

    def ai_button(self, block_uid, username, tasks=None):
        """Create AI employee button in a block's action bar.

        Args:
            block_uid: TableBlockModel or CreateFormModel UID
            username: AI employee username
            tasks: list of task dicts [{title, message: {system, user}, autoSend}]
        Returns: button UID
        """
        sp = {}
        if tasks:
            sp = {"shortcutSettings": {"editTasks": {"tasks": tasks}}}
        return self.save("AIEmployeeButtonModel", block_uid, "actions", "array",
                         sp=sp, sort=98,
                         props={
                             "aiEmployee": {"username": username},
                             "context": {"workContext": [
                                 {"type": "flow-model", "uid": block_uid}
                             ]},
                             "auto": False,
                         })

    # ── Summary ────────────────────────────────────────────────

    def summary(self):
        return {"created": self.created, "errors": self.errors[:10]}


def get_nb_client() -> NB:
    """Get a configured NB client from environment variables."""
    return NB(
        base_url=os.environ.get("NB_URL", "http://localhost:14000"),
        account=os.environ.get("NB_USER", "admin@nocobase.com"),
        password=os.environ.get("NB_PASSWORD", "admin123"),
    )


def get_stdlib_client() -> NocoBaseClient:
    """Get a configured NocoBaseClient (stdlib) from environment variables."""
    client = NocoBaseClient(
        base_url=os.environ.get("NB_URL", "http://localhost:14000"),
        user=os.environ.get("NB_USER", "admin@nocobase.com"),
        password=os.environ.get("NB_PASSWORD", "admin123"),
    )
    client.login()
    return client
