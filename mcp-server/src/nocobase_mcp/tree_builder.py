"""Tree-based FlowModel page builder — build entire pages in memory, submit once.

Instead of 70-80 individual HTTP calls per CRUD page, TreeBuilder constructs the
complete FlowModel tree in memory, then submits it via a single flowModels:save
with nested subModels.

Key classes:
    TreeNode    — in-memory FlowModel node with recursive serialization
    TreeBuilder — pure-memory builder (0 HTTP during construction, only metadata queries)

Usage:
    tb = TreeBuilder(nb)
    root, meta = tb.crud_page(tab_uid, coll, table_fields, form_fields_dsl, ...)
    nb.save_tree(root, tab_uid)
"""

from __future__ import annotations

import json
import copy
from typing import Any, Optional, TYPE_CHECKING

from .utils import uid
from .models import DISPLAY_MAP, EDIT_MAP, STEP_PARAMS_TEMPLATES, MODEL_DEFS, validate_parent_child
from .client import (
    _normalize_fields, _parse_field_name,
)

if TYPE_CHECKING:
    from .client import NB


class TreeNode:
    """In-memory FlowModel node that serializes to nested subModels JSON."""

    def __init__(self, use: str, step_params: dict | None = None,
                 sort_index: int = 0, u: str | None = None, **extra):
        self.uid = u or uid()
        self.use = use
        self.step_params = dict(step_params) if step_params else {}
        self.sort_index = sort_index
        self.flow_registry = {}
        self._sub_models: dict[str, list[TreeNode] | TreeNode] = {}
        self._extra = extra  # filterManager, etc.

    def add_child(self, sub_key: str, sub_type: str, child: TreeNode,
                  validate: bool = False) -> TreeNode:
        """Attach a child node. sub_type='array' → list, 'object' → single.

        If validate=True, checks parent-child relationship against MODEL_DEFS.
        """
        if validate and not validate_parent_child(self.use, sub_key, child.use):
            raise ValueError(
                f"{self.use} does not accept sub_key '{sub_key}' "
                f"(child: {child.use})")
        if sub_type == "object":
            self._sub_models[sub_key] = child
        else:
            self._sub_models.setdefault(sub_key, [])
            lst = self._sub_models[sub_key]
            if not isinstance(lst, list):
                raise ValueError(f"sub_key '{sub_key}' already set as object, cannot add array child")
            lst.append(child)
        return child

    def to_dict(self, parent_id: str | None = None,
                sub_key: str | None = None,
                sub_type: str | None = None) -> dict:
        """Recursively serialize to flowModels:save API JSON format."""
        d: dict[str, Any] = {
            "uid": self.uid,
            "use": self.use,
            "stepParams": self.step_params,
            "sortIndex": self.sort_index,
            "flowRegistry": self.flow_registry,
        }
        if parent_id is not None:
            d["parentId"] = parent_id
        if sub_key is not None:
            d["subKey"] = sub_key
        if sub_type is not None:
            d["subType"] = sub_type
        d.update(self._extra)

        # Recursively serialize children
        if self._sub_models:
            sub = {}
            for key, val in self._sub_models.items():
                if isinstance(val, list):
                    sub[key] = {
                        "subType": "array",
                        "data": [
                            child.to_dict(parent_id=self.uid, sub_key=key, sub_type="array")
                            for child in val
                        ],
                    }
                else:
                    sub[key] = {
                        "subType": "object",
                        "data": val.to_dict(parent_id=self.uid, sub_key=key, sub_type="object"),
                    }
            d["subModels"] = sub

        return d

    def count_nodes(self) -> int:
        """DFS count of all nodes in this subtree (inclusive)."""
        total = 1
        for val in self._sub_models.values():
            if isinstance(val, list):
                for child in val:
                    total += child.count_nodes()
            else:
                total += val.count_nodes()
        return total

    def to_flat_list(self, parent_id: str | None = None,
                     sub_key: str | None = None,
                     sub_type: str | None = None) -> list[dict]:
        """Flatten tree to ordered list of individual save payloads (parent-first BFS).

        Each payload is a flat dict ready for flowModels:save — the format that
        correctly preserves subType on each record.
        """
        result = []
        d: dict[str, Any] = {
            "uid": self.uid,
            "use": self.use,
            "stepParams": self.step_params,
            "sortIndex": self.sort_index,
            "flowRegistry": self.flow_registry,
        }
        if parent_id is not None:
            d["parentId"] = parent_id
        if sub_key is not None:
            d["subKey"] = sub_key
        if sub_type is not None:
            d["subType"] = sub_type
        d.update(self._extra)
        result.append(d)

        # Recurse children in stable order
        for key, val in self._sub_models.items():
            if isinstance(val, list):
                for child in val:
                    result.extend(child.to_flat_list(
                        parent_id=self.uid, sub_key=key, sub_type="array"))
            else:
                result.extend(val.to_flat_list(
                    parent_id=self.uid, sub_key=key, sub_type="object"))

        return result


class TreeBuilder:
    """Pure-memory FlowModel page builder.

    Construction methods build TreeNode trees with 0 HTTP calls.
    Only metadata queries (_iface, _target, _label) go to the network.
    """

    def __init__(self, nb: NB):
        self.nb = nb

    # ── Metadata helpers (delegate to NB) ──────────────────────

    def _iface(self, coll: str, field: str) -> str:
        return self.nb._iface(coll, field)

    def _target(self, coll: str, field: str) -> str:
        return self.nb._target(coll, field)

    def _label(self, target_coll: str) -> str:
        return self.nb._label(target_coll)

    def _load_meta(self, coll: str):
        self.nb._load_meta(coll)

    # ── Atomic node builders ───────────────────────────────────

    def column_node(self, coll: str, field: str, idx: int,
                    click: bool = False, width: int | None = None) -> TreeNode:
        """TableColumnModel + nested DisplayFieldModel."""
        iface = self._iface(coll, field)
        display = DISPLAY_MAP.get(iface, "DisplayTextFieldModel")

        col_sp: dict[str, Any] = {
            **STEP_PARAMS_TEMPLATES["field_init"](coll, field),
            "tableColumnSettings": {"model": {"use": display}},
        }
        if width:
            col_sp["tableColumnSettings"]["width"] = {"width": width}

        col_node = TreeNode("TableColumnModel", col_sp, idx)

        # Display field child
        fsp: dict[str, Any] = {
            "popupSettings": {"openView": {
                "collectionName": coll, "dataSourceKey": "main"}},
        }
        if iface == "m2o":
            t = self._target(coll, field)
            if t:
                fsp["displayFieldSettings"] = {"fieldNames": {"label": self._label(t)}}

        field_node = TreeNode(display, fsp, 0)

        if click:
            # Modify field_node.step_params directly (not fsp) because
            # TreeNode.__init__ shallow-copies — new keys on fsp won't propagate
            field_node.step_params["popupSettings"]["openView"].update({
                "mode": "drawer", "size": "large",
                "pageModelClass": "ChildPageModel", "uid": field_node.uid,
            })
            field_node.step_params.setdefault("displayFieldSettings", {})["clickToOpen"] = {"clickToOpen": True}

        col_node.add_child("field", "object", field_node)
        return col_node

    def form_item_node(self, coll: str, field: str, idx: int,
                       required: bool = False, props: dict | None = None) -> TreeNode:
        """FormItemModel + nested EditFieldModel."""
        iface = self._iface(coll, field)
        edit = EDIT_MAP.get(iface, "InputFieldModel")
        props = props or {}

        sp: dict[str, Any] = STEP_PARAMS_TEMPLATES["field_init"](coll, field)
        eis: dict[str, Any] = {}
        if required:
            eis["required"] = {"required": True}
        dv = props.get("defaultValue")
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

        item_node = TreeNode("FormItemModel", sp, idx)
        field_node = TreeNode(edit, {}, 0)
        item_node.add_child("field", "object", field_node)
        return item_node

    def detail_item_node(self, coll: str, field: str, idx: int) -> TreeNode:
        """DetailsItemModel + nested DisplayFieldModel."""
        iface = self._iface(coll, field)
        display = DISPLAY_MAP.get(iface, "DisplayTextFieldModel")

        sp: dict[str, Any] = {
            **STEP_PARAMS_TEMPLATES["field_init"](coll, field),
            "detailItemSettings": {"model": {"use": display}},
        }
        if iface == "m2o":
            t = self._target(coll, field)
            if t:
                sp["detailItemSettings"]["fieldNames"] = {"label": self._label(t)}

        item_node = TreeNode("DetailsItemModel", sp, idx)
        field_node = TreeNode(display, {}, 0)
        item_node.add_child("field", "object", field_node)
        return item_node

    def divider_node(self, label: str, idx: int) -> TreeNode:
        """DividerItemModel for form/detail section headers."""
        sp = STEP_PARAMS_TEMPLATES["divider_label"](label) if label else {}
        return TreeNode("DividerItemModel", sp, idx)

    def markdown_item_node(self, content: str, idx: int) -> TreeNode:
        """MarkdownItemModel for inline markdown content."""
        sp = {"markdownBlockSettings": {"editMarkdown": {"content": content}}}
        return TreeNode("MarkdownItemModel", sp, idx)

    # ── Composite builders ─────────────────────────────────────

    def form_grid(self, coll: str, fields_dsl: str | list,
                  required: set | None = None, props: dict | None = None) -> TreeNode:
        """FormGridModel with form items, gridSettings computed in memory.

        Returns a FormGridModel TreeNode with all FormItemModel children attached.
        """
        items, auto_req = _normalize_fields(fields_dsl)
        all_req = (required or set()) | auto_req
        props = props or {}
        rows, sizes, sort_idx = {}, {}, 0

        grid_node = TreeNode("FormGridModel", {}, 0)

        for item in items:
            row_id = uid()
            if item["type"] == "divider":
                child = self.divider_node(item.get("label", ""), sort_idx)
                grid_node.add_child("items", "array", child)
                rows[row_id] = [[child.uid]]
                sizes[row_id] = [24]
                sort_idx += 1
            elif item["type"] == "markdown":
                child = self.markdown_item_node(item["content"], sort_idx)
                grid_node.add_child("items", "array", child)
                rows[row_id] = [[child.uid]]
                sizes[row_id] = [24]
                sort_idx += 1
            elif item["type"] == "row":
                col_uids, col_sizes = [], []
                for field_name, span in item["cols"]:
                    fi = self.form_item_node(
                        coll, field_name, sort_idx,
                        required=(field_name in all_req),
                        props=props.get(field_name),
                    )
                    grid_node.add_child("items", "array", fi)
                    col_uids.append(fi.uid)
                    col_sizes.append(span)
                    sort_idx += 1
                rows[row_id] = [[fi_uid] for fi_uid in col_uids]
                sizes[row_id] = col_sizes

        grid_node.step_params = {
            "gridSettings": {"grid": {"rows": rows, "sizes": sizes}}
        }
        return grid_node

    def detail_grid(self, coll: str, fields_dsl: str | list) -> TreeNode:
        """DetailsGridModel with detail items, gridSettings computed in memory."""
        items, _ = _normalize_fields(fields_dsl)
        rows, sizes, sort_idx = {}, {}, 0

        grid_node = TreeNode("DetailsGridModel", {}, 0)

        for item in items:
            row_id = uid()
            if item["type"] == "divider":
                child = self.divider_node(item.get("label", ""), sort_idx)
                grid_node.add_child("items", "array", child)
                rows[row_id] = [[child.uid]]
                sizes[row_id] = [24]
                sort_idx += 1
            elif item["type"] == "markdown":
                child = self.markdown_item_node(item["content"], sort_idx)
                grid_node.add_child("items", "array", child)
                rows[row_id] = [[child.uid]]
                sizes[row_id] = [24]
                sort_idx += 1
            elif item["type"] == "row":
                col_uids, col_sizes = [], []
                for field_name, span in item["cols"]:
                    di = self.detail_item_node(coll, field_name, sort_idx)
                    grid_node.add_child("items", "array", di)
                    col_uids.append(di.uid)
                    col_sizes.append(span)
                    sort_idx += 1
                rows[row_id] = [[di_uid] for di_uid in col_uids]
                sizes[row_id] = col_sizes

        grid_node.step_params = {
            "gridSettings": {"grid": {"rows": rows, "sizes": sizes}}
        }
        return grid_node

    def table_block(self, coll: str, fields: list, first_click: bool = True,
                    title: str | None = None, sort: int = 0,
                    link_actions: list | None = None) -> TreeNode:
        """TableBlockModel with columns, actions. Returns root TreeNode.

        The addnew and actcol UIDs are accessible via node._sub_models["actions"]
        and node._sub_models["columns"] respectively.
        """
        sp: dict[str, Any] = {
            **STEP_PARAMS_TEMPLATES["resource_init"](coll),
            **STEP_PARAMS_TEMPLATES["table_default_sort"],
        }
        if title:
            sp.update(STEP_PARAMS_TEMPLATES["card_title"](title))

        tbl = TreeNode("TableBlockModel", sp, sort)

        # Standard actions
        tbl.add_child("actions", "array", TreeNode("FilterActionModel", {}, 1))
        tbl.add_child("actions", "array", TreeNode("RefreshActionModel", {}, 2))

        addnew = TreeNode("AddNewActionModel",
                          STEP_PARAMS_TEMPLATES["popup_drawer"](coll), 3)
        tbl.add_child("actions", "array", addnew)

        if link_actions:
            for li, la in enumerate(link_actions):
                la_sp = {"buttonSettings": {"general": {
                    "title": la["title"], "type": "default",
                    **({"icon": la.get("icon")} if la.get("icon") else {})}}}
                tbl.add_child("actions", "array", TreeNode("LinkActionModel", la_sp, 4 + li))

        # Columns
        for i, f in enumerate(fields):
            col = self.column_node(coll, f, i + 1, click=(first_click and i == 0))
            tbl.add_child("columns", "array", col)

        # Actions column
        actcol = TreeNode("TableActionsColumnModel",
                          STEP_PARAMS_TEMPLATES["actions_column_title"], 99)
        tbl.add_child("columns", "array", actcol)

        # Stash references for callers
        tbl._addnew = addnew
        tbl._actcol = actcol
        # Stash first click field node for detail popup attachment
        if first_click and fields:
            first_col = tbl._sub_models["columns"][0]  # first TableColumnModel
            first_field = first_col._sub_models.get("field")  # DisplayFieldModel (object)
            tbl._click_field = first_field
        else:
            tbl._click_field = None

        return tbl

    def filter_form(self, coll: str, field: str, search_fields: list | None = None,
                    target_uid: str | None = None, label: str = "Search",
                    sort: int = 0) -> TreeNode:
        """FilterFormBlockModel with single search input. Returns root TreeNode."""
        self._load_meta(coll)
        field_meta = self.nb._field_cache.get(coll, {}).get(field, {})

        fb = TreeNode("FilterFormBlockModel",
                      STEP_PARAMS_TEMPLATES["filter_layout_horizontal"], sort)

        fg = TreeNode("FilterFormGridModel", {}, 0)
        fb.add_child("grid", "object", fg)

        fi_sp: dict[str, Any] = {
            "fieldSettings": {"init": {
                "dataSourceKey": "main", "collectionName": coll, "fieldPath": field}},
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
        fi = TreeNode("FilterFormItemModel", fi_sp, 10)
        fi.add_child("field", "object", TreeNode("InputFieldModel", {}, 0))
        fg.add_child("items", "array", fi)

        # Stash filter info for filterManager
        fb._filter_item_uid = fi.uid
        fb._filter_paths = search_fields or [field]

        return fb

    def kpi_block(self, title: str, coll: str, filter_: dict | None = None,
                  color: str | None = None, sort: int = 0) -> TreeNode:
        """JSBlockModel KPI card. Uses _generate_kpi_code from NB."""
        code = self.nb._generate_kpi_code(title, coll, filter_, color)
        sp = {
            **STEP_PARAMS_TEMPLATES["js_code"](code),
            **STEP_PARAMS_TEMPLATES["card_title"](title),
        }
        return TreeNode("JSBlockModel", sp, sort)

    def js_block_node(self, title: str, code: str, sort: int = 0) -> TreeNode:
        """Generic JSBlockModel."""
        sp = {
            **STEP_PARAMS_TEMPLATES["js_code"](code),
            **STEP_PARAMS_TEMPLATES["card_title"](title),
        }
        return TreeNode("JSBlockModel", sp, sort)

    def outline_node(self, title: str, ctx_info: dict, sort: int = 0) -> TreeNode:
        """Outline placeholder JSBlockModel."""
        code = self.nb._outline_code(title, ctx_info)
        return self.js_block_node(title, code, sort)

    # ── AddNew / Edit / Detail popup ───────────────────────────

    def addnew_form(self, coll: str, fields_dsl: str | list,
                    required: set | None = None, props: dict | None = None) -> TreeNode:
        """ChildPageModel tree for AddNew popup: ChildPage → Tab → Grid → CreateForm → FormGrid.

        Returns the ChildPageModel node. Caller attaches it to AddNewActionModel via
        add_child("page", "object", ...).
        """
        cp = TreeNode("ChildPageModel", STEP_PARAMS_TEMPLATES["page_no_title"])
        ct = TreeNode("ChildPageTabModel", {
            "pageTabSettings": {"tab": {"title": "New"}}}, 0)
        cp.add_child("tabs", "array", ct)

        bg = TreeNode("BlockGridModel", {}, 0)
        ct.add_child("grid", "object", bg)

        fm = TreeNode("CreateFormModel",
                      STEP_PARAMS_TEMPLATES["resource_init"](coll), 0)
        bg.add_child("items", "array", fm)

        fm.add_child("actions", "array", TreeNode("FormSubmitActionModel", {}, 0))

        fg = self.form_grid(coll, fields_dsl, required, props)
        fm.add_child("grid", "object", fg)

        # Stash create form UID
        cp._create_form_uid = fm.uid
        return cp

    def edit_action(self, coll: str, fields_dsl: str | list,
                    required: set | None = None, props: dict | None = None) -> TreeNode:
        """EditActionModel tree: EditAction → ChildPage → Tab → Grid → EditForm → FormGrid.

        Returns the EditActionModel node.
        """
        ea_sp = STEP_PARAMS_TEMPLATES["popup_drawer"](coll)
        ea_sp["popupSettings"]["openView"]["filterByTk"] = "{{ ctx.record.id }}"
        ea = TreeNode("EditActionModel", ea_sp, 0)

        cp = TreeNode("ChildPageModel", STEP_PARAMS_TEMPLATES["page_no_title"])
        ea.add_child("page", "object", cp)

        ct = TreeNode("ChildPageTabModel", {
            "pageTabSettings": {"tab": {"title": "Edit"}}}, 0)
        cp.add_child("tabs", "array", ct)

        bg = TreeNode("BlockGridModel", {}, 0)
        ct.add_child("grid", "object", bg)

        fm = TreeNode("EditFormModel",
                      STEP_PARAMS_TEMPLATES["resource_init_with_tk"](coll), 0)
        bg.add_child("items", "array", fm)

        fm.add_child("actions", "array", TreeNode("FormSubmitActionModel", {}, 0))

        fg = self.form_grid(coll, fields_dsl, required, props)
        fm.add_child("grid", "object", fg)

        # Stash edit form UID
        ea._edit_form_uid = fm.uid
        return ea

    def _build_tab_blocks(self, bg: TreeNode, coll: str, tab: dict) -> list[TreeNode]:
        """Build blocks inside a BlockGridModel for detail popup tab."""
        blocks = tab.get("blocks")
        if blocks is None:
            if "assoc" in tab:
                blocks = [{"type": "sub_table", "assoc": tab["assoc"],
                           "coll": tab["coll"], "fields": tab["fields"],
                           "title": tab.get("title")}]
            else:
                blocks = [{"type": "details", "fields": tab["fields"]}]

        block_nodes = []
        for bi, blk in enumerate(blocks):
            btype = blk.get("type", "details")

            if btype == "details":
                det_sp: dict[str, Any] = STEP_PARAMS_TEMPLATES["resource_init_with_tk"](coll)
                if blk.get("title"):
                    det_sp.update(STEP_PARAMS_TEMPLATES["card_title"](blk["title"]))
                det = TreeNode("DetailsBlockModel", det_sp, bi)
                bg.add_child("items", "array", det)

                dg = self.detail_grid(coll, blk["fields"])
                det.add_child("grid", "object", dg)
                block_nodes.append(det)

            elif btype == "js":
                js_sp: dict[str, Any] = STEP_PARAMS_TEMPLATES["js_code"](blk.get("code", ""))
                if blk.get("title"):
                    js_sp.update(STEP_PARAMS_TEMPLATES["card_title"](blk["title"]))
                js_node = TreeNode("JSBlockModel", js_sp, bi)
                bg.add_child("items", "array", js_node)
                block_nodes.append(js_node)

            elif btype == "sub_table":
                sub_tbl = self._sub_table_node(
                    coll, blk["assoc"], blk["coll"], blk["fields"],
                    blk.get("title"), bi)
                bg.add_child("items", "array", sub_tbl)

                # AddNew form for sub-table
                af = blk.get("addnew_fields") or blk["fields"]
                if af:
                    sub_addnew = sub_tbl._addnew
                    addnew_cp = self.addnew_form(blk["coll"], af,
                                                  required={af[0]} if af else set())
                    sub_addnew.add_child("page", "object", addnew_cp)

                block_nodes.append(sub_tbl)

            elif btype == "form":
                fm = TreeNode("EditFormModel",
                              STEP_PARAMS_TEMPLATES["resource_init_with_tk"](coll), bi)
                bg.add_child("items", "array", fm)
                fm.add_child("actions", "array", TreeNode("FormSubmitActionModel", {}, 0))
                req = set(blk.get("required", []))
                fg = self.form_grid(coll, blk["fields"], req, props=blk.get("props"))
                fm.add_child("grid", "object", fg)
                block_nodes.append(fm)

        # Multi-block layout
        tab_sizes = tab.get("sizes")
        if len(block_nodes) > 1 or tab_sizes:
            row_id = uid()
            row_cols = [[bn.uid] for bn in block_nodes]
            if tab_sizes:
                gs = {"gridSettings": {"grid": {
                    "rows": {row_id: row_cols},
                    "sizes": {row_id: tab_sizes}}}}
            else:
                n = len(block_nodes)
                auto = [24 // n] * n
                auto[-1] = 24 - sum(auto[:-1])
                gs = {"gridSettings": {"grid": {
                    "rows": {row_id: row_cols},
                    "sizes": {row_id: auto}}}}
            bg.step_params = gs

        return block_nodes

    def _sub_table_node(self, parent_coll: str, assoc: str, target_coll: str,
                        fields: list, title: str | None = None,
                        sort: int = 0) -> TreeNode:
        """Association sub-table TreeNode."""
        sp: dict[str, Any] = STEP_PARAMS_TEMPLATES["resource_init"](target_coll)
        sp["resourceSettings"]["init"].update({
            "associationName": f"{parent_coll}.{assoc}",
            "sourceId": "{{ctx.view.inputArgs.filterByTk}}"})
        if title:
            sp.update(STEP_PARAMS_TEMPLATES["card_title"](title))

        tbl = TreeNode("TableBlockModel", sp, sort)
        tbl.add_child("actions", "array", TreeNode("RefreshActionModel", {}, 2))

        addnew = TreeNode("AddNewActionModel",
                          STEP_PARAMS_TEMPLATES["popup_dialog"](target_coll), 3)
        tbl.add_child("actions", "array", addnew)
        tbl._addnew = addnew

        for i, f in enumerate(fields):
            col = self.column_node(target_coll, f, i + 1)
            tbl.add_child("columns", "array", col)

        actcol = TreeNode("TableActionsColumnModel",
                          STEP_PARAMS_TEMPLATES["actions_column_title"], 99)
        tbl.add_child("columns", "array", actcol)
        tbl._actcol = actcol

        return tbl

    def detail_popup(self, coll: str, tabs: list) -> TreeNode:
        """ChildPageModel for detail popup with tabs.

        Returns ChildPageModel TreeNode. Caller attaches to click field via
        add_child("page", "object", ...).
        """
        enable_tabs = len(tabs) > 1
        page_sp = STEP_PARAMS_TEMPLATES["page_with_tabs"] if enable_tabs else STEP_PARAMS_TEMPLATES["page_no_title"]
        cp = TreeNode("ChildPageModel", page_sp)

        for ti, tab in enumerate(tabs):
            ct = TreeNode("ChildPageTabModel", {
                "pageTabSettings": {"tab": {"title": tab["title"]}}}, ti)
            cp.add_child("tabs", "array", ct)

            bg = TreeNode("BlockGridModel", {}, 0)
            ct.add_child("grid", "object", bg)
            self._build_tab_blocks(bg, coll, tab)

        return cp

    # ── Main entry point ───────────────────────────────────────

    def crud_page(self, tab_uid: str, coll: str, table_fields: list,
                  form_fields_dsl: str | list,
                  filter_fields: list | None = None,
                  kpis: list | None = None,
                  detail_tabs: list | str | None = None,
                  table_title: str | None = None,
                  sidebar_outlines: list | None = None,
                  ) -> tuple[TreeNode, dict]:
        """Build a complete CRUD page tree in memory.

        Returns:
            (root_node, meta_dict) where meta_dict contains UIDs for
            create_form, edit_form, table_uid, etc.
        """
        meta: dict[str, Any] = {}

        # Root: BlockGridModel
        root = TreeNode("BlockGridModel", {}, 0)
        meta["grid_uid"] = root.uid

        # Track all blocks for layout
        kpi_nodes = []
        sort_idx = 0

        # ── KPIs ──
        if kpis:
            for kpi in kpis:
                ktitle = kpi.get("title", "Count")
                kfilter = kpi.get("filter")
                kcolor = kpi.get("color")
                kpi_node = self.kpi_block(ktitle, coll, filter_=kfilter,
                                          color=kcolor, sort=sort_idx)
                root.add_child("items", "array", kpi_node)
                kpi_nodes.append(kpi_node)
                sort_idx += 1

        # ── Table ──
        tbl = self.table_block(coll, table_fields, first_click=True,
                               title=table_title, sort=sort_idx)
        root.add_child("items", "array", tbl)
        meta["table_uid"] = tbl.uid
        sort_idx += 1

        # ── Filter ──
        filter_node = None
        if filter_fields:
            first_field = filter_fields[0] if filter_fields else "name"
            filter_node = self.filter_form(
                coll, first_field, search_fields=filter_fields,
                target_uid=tbl.uid, sort=sort_idx)
            root.add_child("items", "array", filter_node)
            sort_idx += 1

        # ── AddNew form ──
        addnew_cp = self.addnew_form(coll, form_fields_dsl)
        # Update AddNew action's popupSettings with UID
        tbl._addnew.add_child("page", "object", addnew_cp)
        meta["create_form"] = addnew_cp._create_form_uid

        # ── Edit action ──
        edit_node = self.edit_action(coll, form_fields_dsl)
        tbl._actcol.add_child("actions", "array", edit_node)
        meta["edit_form"] = edit_node._edit_form_uid

        # ── Sidebar outlines ──
        sidebar_nodes = []
        if sidebar_outlines:
            for ol in sidebar_outlines:
                ol_title = ol.get("title", "Outline")
                ol_info = ol.get("ctx_info", {})
                ol_node = self.outline_node(ol_title, ol_info, sort=sort_idx)
                root.add_child("items", "array", ol_node)
                sidebar_nodes.append(ol_node)
                sort_idx += 1
            meta["sidebar_outline_uids"] = [n.uid for n in sidebar_nodes]

        # ── Layout (gridSettings on root) ──
        rows, sizes = {}, {}

        # KPI row
        if kpi_nodes:
            row_id = uid()
            span = 24 // len(kpi_nodes)
            rows[row_id] = [[kn.uid] for kn in kpi_nodes]
            sizes[row_id] = [span] * len(kpi_nodes)

        # Filter row
        if filter_node:
            row_id = uid()
            rows[row_id] = [[filter_node.uid]]
            sizes[row_id] = [24]

        # Table row (with optional sidebar)
        row_id = uid()
        if sidebar_nodes:
            rows[row_id] = [[tbl.uid], [sidebar_nodes[0].uid] +
                            ([sn.uid for sn in sidebar_nodes[1:]] if len(sidebar_nodes) > 1 else [])]
            sizes[row_id] = [15, 9]
        else:
            rows[row_id] = [[tbl.uid]]
            sizes[row_id] = [24]

        root.step_params = {"gridSettings": {"grid": {"rows": rows, "sizes": sizes}}}

        # ── Detail popup ──
        if detail_tabs != "none":
            click_field = tbl._click_field
            if click_field:
                if detail_tabs:
                    tabs = detail_tabs
                else:
                    # Auto-generate detail tab from form fields
                    detail_fields = form_fields_dsl
                    if isinstance(detail_fields, str):
                        detail_fields = detail_fields.replace("*", "")
                    tabs = [{"title": "详情", "fields": detail_fields}]

                # Update click field popup settings
                click_field.step_params["popupSettings"]["openView"].update({
                    "collectionName": coll, "dataSourceKey": "main",
                    "mode": "drawer", "size": "large",
                    "pageModelClass": "ChildPageModel", "uid": click_field.uid,
                })

                popup_cp = self.detail_popup(coll, tabs)
                click_field.add_child("page", "object", popup_cp)
                meta["detail_popup"] = True

        # ── FilterManager ──
        if filter_node:
            meta["_filter_manager"] = [{
                "filterId": filter_node._filter_item_uid,
                "targetId": tbl.uid,
                "filterPaths": filter_node._filter_paths,
            }]

        meta["node_count"] = root.count_nodes()
        return root, meta

    # ── Template support ───────────────────────────────────────

    @staticmethod
    def extract_template(tree_dict: dict, collection: str, name: str) -> dict:
        """Extract a reusable template from a page tree JSON.

        Replaces all UIDs with placeholders and collection references with markers.
        """
        raw = json.dumps(tree_dict)
        # Replace collection name with placeholder
        raw = raw.replace(f'"{collection}"', '"__COLLECTION__"')
        template = json.loads(raw)
        template["_template_name"] = name
        template["_source_collection"] = collection
        return template

    @staticmethod
    def apply_template(template: dict, target_collection: str,
                       field_map: dict | None = None) -> dict:
        """Apply a template to create a new page tree.

        Generates fresh UIDs and replaces collection/field references.
        """
        raw = json.dumps(template)
        # Replace collection placeholder
        raw = raw.replace('"__COLLECTION__"', f'"{target_collection}"')

        # Replace field references
        if field_map:
            for old_field, new_field in field_map.items():
                raw = raw.replace(f'"{old_field}"', f'"{new_field}"')

        result = json.loads(raw)

        # Generate fresh UIDs for all nodes
        uid_map = {}

        def _regen_uids(node):
            if isinstance(node, dict):
                if "uid" in node:
                    old = node["uid"]
                    if old not in uid_map:
                        uid_map[old] = uid()
                    node["uid"] = uid_map[old]
                if "parentId" in node and node["parentId"] in uid_map:
                    node["parentId"] = uid_map[node["parentId"]]
                for v in node.values():
                    _regen_uids(v)
            elif isinstance(node, list):
                for item in node:
                    _regen_uids(item)

        _regen_uids(result)

        # Clean template metadata
        result.pop("_template_name", None)
        result.pop("_source_collection", None)

        return result
