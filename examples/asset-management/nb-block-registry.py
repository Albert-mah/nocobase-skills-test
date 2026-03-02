#!/usr/bin/env python3
"""nb-block-registry.py — 生成区块映射表供 AI 读取

输出一个结构化的区块注册表（JSON + 人类可读文本），
记录每个页面的所有区块位置、UID、类型和上下文。

AI Agent 可以通过读取 block-registry.json 快速定位：
  - 某个 collection 的表格在哪个页面
  - 某个表单的 UID 是什么（用于添加事件流）
  - 详情弹窗在哪（用于添加 JS Item）
  - JS 区块的位置（用于更新图表代码）

用法：
    python3 nb-block-registry.py                    # 生成 registry
    python3 nb-block-registry.py --output=path.json # 指定输出路径
    python3 nb-block-registry.py --text              # 输出人类可读文本（适合 AI context）
    python3 nb-block-registry.py --prefix=nb_am     # 只导出特定前缀的 collection

输出文件：block-registry.json（默认）
"""

import sys
import json
from collections import defaultdict

sys.path.insert(0, ".")
from nb_page_builder import NB


# ═══════════════════════════════════════════════════════════════
# 区块类型描述
# ═══════════════════════════════════════════════════════════════

BLOCK_TYPES = {
    "TableBlockModel": "table",
    "CreateFormModel": "form_create",
    "EditFormModel": "form_edit",
    "DetailModel": "detail",
    "JSBlockModel": "js_block",
    "JSColumnModel": "js_column",
    "JSItemModel": "js_item",
    "FilterFormModel": "filter",
}

ACTION_TYPES = {
    "AddNewActionModel": "addnew",
    "EditActionModel": "edit",
    "ViewActionModel": "view",
    "DeleteActionModel": "delete",
    "PopupActionModel": "popup",
    "FilterActionModel": "filter",
    "RefreshActionModel": "refresh",
    "FormSubmitActionModel": "submit",
}


def build_tree(all_models):
    """Build parent→children mapping."""
    children = defaultdict(list)
    by_uid = {}
    for m in all_models:
        by_uid[m["uid"]] = m
        pid = m.get("parentId")
        if pid:
            children[pid].append(m)
    return by_uid, children


def get_routes(nb):
    """Get all routes with page/tab model UIDs.

    NocoBase route structure:
      group → flowPage → tabs (actual content)
    The flowPage's RootPageModel is usually empty.
    Real content lives under tabs routes via schemaUid.
    """
    r = nb.s.get(f"{nb.base}/api/desktopRoutes:list?paginate=false")
    routes = r.json().get("data", [])
    route_by_id = {rt["id"]: rt for rt in routes}

    route_map = {}  # schemaUid → route info
    for rt in routes:
        rtype = rt.get("type") or ""
        page_uid = rt.get("schemaUid", "") or (rt.get("options") or {}).get("pageModelUid", "")
        if not page_uid:
            continue

        if rtype == "tabs":
            # Tab route: resolve title from parent flowPage, then grandparent group
            parent = route_by_id.get(rt.get("parentId"))
            page_title = parent.get("title", "") if parent else ""
            tab_title = rt.get("title") or ""
            # Resolve group from grandparent
            group = ""
            if parent:
                grandparent = route_by_id.get(parent.get("parentId"))
                if grandparent:
                    group = grandparent.get("title", "")
            route_map[page_uid] = {
                "route_id": rt["id"],
                "title": page_title or tab_title,
                "tab_title": tab_title,
                "parent_id": rt.get("parentId"),
                "group": group,
            }
        elif rtype == "flowPage":
            # flowPage: include but content may be in child tabs
            title = rt.get("title") or ""
            parent = route_by_id.get(rt.get("parentId"))
            group = parent.get("title", "") if parent else ""
            route_map[page_uid] = {
                "route_id": rt["id"],
                "title": title,
                "parent_id": rt.get("parentId"),
                "group": group,
            }

    return route_map


def get_coll_titles(nb):
    """Get collection name → title mapping."""
    r = nb.s.get(f"{nb.base}/api/collections:list?paginate=false")
    colls = r.json().get("data", [])
    return {c["name"]: c.get("title", c["name"]) for c in colls}


def extract_block_info(model, by_uid, children_map):
    """Extract block metadata from a FlowModel node."""
    use = model.get("use", "")
    sp = model.get("stepParams") or {}

    info = {
        "uid": model["uid"],
        "type": BLOCK_TYPES.get(use, use),
    }

    # Collection info
    rs = sp.get("resourceSettings", {}).get("init", {})
    if rs.get("collectionName"):
        info["collection"] = rs["collectionName"]
    if rs.get("associationName"):
        info["association"] = rs["associationName"]

    # Title (from card settings)
    card_title = sp.get("cardSettings", {}).get("titleDescription", {}).get("title")
    if card_title:
        info["title"] = card_title

    # JS block code info
    js_code = sp.get("jsSettings", {}).get("runJs", {}).get("code", "")
    if js_code:
        info["js_code_length"] = len(js_code)
        # Extract key patterns
        if "ctx.api.request" in js_code:
            info["has_api_query"] = True
        if "ctx.record" in js_code:
            info["has_record_access"] = True
        if "ctx.form" in js_code:
            info["has_form_access"] = True

    # Column title
    col_title = sp.get("tableColumnSettings", {}).get("title", {}).get("title")
    if col_title:
        info["column_title"] = col_title

    # Column width
    col_width = sp.get("tableColumnSettings", {}).get("width", {}).get("width")
    if col_width:
        info["width"] = col_width

    # Event flows
    registry = model.get("flowRegistry") or {}
    if registry:
        events = []
        for fk, flow in registry.items():
            event_name = flow.get("on", {}).get("eventName", "")
            steps = flow.get("steps", {})
            events.append({
                "flow_key": fk,
                "event": event_name,
                "steps": len(steps),
            })
        info["event_flows"] = events

    # Children: actions, columns, items
    kids = children_map.get(model["uid"], [])
    sub_blocks = []
    for kid in kids:
        kid_use = kid.get("use", "")
        if kid_use in ACTION_TYPES:
            action_info = {"uid": kid["uid"], "type": ACTION_TYPES[kid_use]}
            # Check popup settings
            popup = (kid.get("stepParams") or {}).get("popupSettings", {}).get("openView", {})
            if popup.get("collectionName"):
                action_info["popup_collection"] = popup["collectionName"]
                action_info["popup_mode"] = popup.get("mode", "drawer")

            # Find ChildPageModel under this action
            action_kids = children_map.get(kid["uid"], [])
            for ak in action_kids:
                if ak.get("use") == "ChildPageModel":
                    action_info["child_page_uid"] = ak["uid"]
                    # Dig into tabs
                    tabs = children_map.get(ak["uid"], [])
                    tab_infos = []
                    for tab in tabs:
                        if tab.get("use") == "ChildPageTabModel":
                            tab_title = (tab.get("stepParams") or {}).get(
                                "pageTabSettings", {}).get("tab", {}).get("title", "")
                            tab_infos.append({"uid": tab["uid"], "title": tab_title})
                    if tab_infos:
                        action_info["tabs"] = tab_infos

            sub_blocks.append(action_info)

        elif kid_use in ("JSColumnModel", "JSItemModel"):
            kid_info = extract_block_info(kid, by_uid, children_map)
            sub_blocks.append(kid_info)

        elif kid_use == "TableColumnModel":
            fp = (kid.get("stepParams") or {}).get(
                "fieldSettings", {}).get("init", {}).get("fieldPath", "")
            if fp:
                sub_blocks.append({"uid": kid["uid"], "type": "column", "field": fp})

        elif kid_use == "FormItemModel":
            fp = (kid.get("stepParams") or {}).get(
                "fieldSettings", {}).get("init", {}).get("fieldPath", "")
            if fp:
                sub_blocks.append({"uid": kid["uid"], "type": "form_field", "field": fp})

    if sub_blocks:
        info["children"] = sub_blocks

    return info


def build_registry(nb, prefix=None):
    """Build the complete block registry."""
    print("  Loading FlowModels...")
    r = nb.s.get(f"{nb.base}/api/flowModels:list?paginate=false")
    all_models = r.json().get("data", [])
    print(f"  Total nodes: {len(all_models)}")

    by_uid, children_map = build_tree(all_models)
    route_map = get_routes(nb)
    coll_titles = get_coll_titles(nb)

    # Find all FlowPageModels
    pages = [m for m in all_models if m.get("use") == "FlowPageModel"]

    # Also find top-level tabs (ChildPageTabModel under FlowPageModel via route)
    registry = {
        "generated": "auto",
        "total_nodes": len(all_models),
        "pages": [],
        "orphan_blocks": [],  # blocks not under any page
        "templates": [],
    }

    # Process each route/page
    page_uids_processed = set()

    for page_uid, route_info in route_map.items():
        page_model = by_uid.get(page_uid)
        if not page_model:
            continue

        # Filter by prefix if specified
        page_data = {
            "page_uid": page_uid,
            "title": route_info["title"],
            "group": route_info.get("group", ""),
            "route_id": route_info["route_id"],
            "blocks": [],
        }

        # Walk the tree under this page
        def walk(uid, depth=0):
            model = by_uid.get(uid)
            if not model:
                return
            use = model.get("use", "")

            if use in BLOCK_TYPES:
                sp = (model.get("stepParams") or {}).get("resourceSettings", {}).get("init", {})
                coll = sp.get("collectionName", "")

                # Filter by prefix
                if prefix and coll and not coll.startswith(prefix):
                    return

                block_info = extract_block_info(model, by_uid, children_map)
                page_data["blocks"].append(block_info)

            # Recurse into children
            for child in children_map.get(uid, []):
                walk(child["uid"], depth + 1)

        walk(page_uid)
        page_uids_processed.add(page_uid)

        if page_data["blocks"] or not prefix:
            registry["pages"].append(page_data)

    # Get templates
    r = nb.s.get(f"{nb.base}/api/flowModelTemplates:list?paginate=false")
    templates = r.json().get("data", [])
    for t in templates:
        registry["templates"].append({
            "uid": t["uid"],
            "name": t.get("name", ""),
            "type": t.get("type", ""),
            "use_model": t.get("useModel", ""),
            "collection": t.get("collectionName", ""),
            "target_uid": t.get("targetUid", ""),
        })

    # Add collection titles
    registry["collections"] = {}
    for page in registry["pages"]:
        for block in page.get("blocks", []):
            coll = block.get("collection", "")
            if coll and coll not in registry["collections"]:
                registry["collections"][coll] = coll_titles.get(coll, coll)

    return registry


def format_text(registry):
    """Format registry as human/AI readable text."""
    lines = []
    lines.append("# Block Registry")
    lines.append(f"# Total nodes: {registry['total_nodes']}")
    lines.append(f"# Pages: {len(registry['pages'])}")
    lines.append(f"# Templates: {len(registry['templates'])}")
    lines.append("")

    # Collection legend
    if registry.get("collections"):
        lines.append("## Collections")
        for name, title in sorted(registry["collections"].items()):
            lines.append(f"  {name:40s}  {title}")
        lines.append("")

    for page in registry["pages"]:
        title = page["title"]
        group = page.get("group", "")
        prefix = f"{group} > " if group else ""
        lines.append(f"## {prefix}{title}")
        lines.append(f"   page_uid: {page['page_uid']}  route: {page['route_id']}")

        for block in page.get("blocks", []):
            btype = block.get("type", "?")
            uid = block.get("uid", "?")
            coll = block.get("collection", "")
            title_str = block.get("title") or block.get("column_title") or ""

            indent = "  "
            line = f"{indent}[{btype}] uid={uid}"
            if coll:
                line += f"  coll={coll}"
            if title_str:
                line += f"  title=\"{title_str}\""

            # Event flows
            if block.get("event_flows"):
                events = ", ".join(e["event"] for e in block["event_flows"])
                line += f"  events=[{events}]"

            # JS info
            if block.get("js_code_length"):
                line += f"  js={block['js_code_length']}chars"

            lines.append(line)

            # Children (actions, columns)
            for child in block.get("children", []):
                ctype = child.get("type", "?")
                cuid = child.get("uid", "?")
                if ctype in ("addnew", "edit", "view", "popup"):
                    cpopup = child.get("popup_collection", "")
                    cmode = child.get("popup_mode", "")
                    cline = f"{indent}  [{ctype}] uid={cuid}"
                    if cpopup:
                        cline += f"  popup={cpopup}"
                    if cmode:
                        cline += f"  mode={cmode}"
                    if child.get("child_page_uid"):
                        cline += f"  child_page={child['child_page_uid']}"
                    lines.append(cline)
                    # Tabs
                    for tab in child.get("tabs", []):
                        lines.append(f"{indent}    tab: {tab['title']} uid={tab['uid']}")
                elif ctype == "column":
                    lines.append(f"{indent}  [col] {child.get('field','?')}")
                elif ctype == "form_field":
                    lines.append(f"{indent}  [field] {child.get('field','?')}")
                elif ctype in ("js_column", "js_item"):
                    ctitle = child.get("column_title") or child.get("title") or ""
                    cjs = child.get("js_code_length", 0)
                    lines.append(f"{indent}  [{ctype}] uid={cuid} title=\"{ctitle}\" js={cjs}chars")

        lines.append("")

    # Templates
    if registry.get("templates"):
        lines.append("## Templates")
        for t in registry["templates"]:
            lines.append(f"  [{t['type']}] {t['name']:40s}  model={t['use_model']}  coll={t['collection']}  target={t['target_uid']}")
        lines.append("")

    return "\n".join(lines)


def main():
    args = sys.argv[1:]

    output_path = "block-registry.json"
    text_mode = "--text" in args
    prefix = None

    for a in args:
        if a.startswith("--output="):
            output_path = a.split("=", 1)[1]
        if a.startswith("--prefix="):
            prefix = a.split("=", 1)[1]

    nb = NB()

    print(f"\n{'=' * 60}")
    print(f"  Block Registry Generator")
    if prefix:
        print(f"  Prefix filter: {prefix}")
    print(f"{'=' * 60}")

    registry = build_registry(nb, prefix)

    if text_mode:
        text = format_text(registry)
        text_path = output_path.replace(".json", ".txt")
        with open(text_path, "w") as f:
            f.write(text)
        print(f"\n  Written: {text_path}")
        print(f"  Pages: {len(registry['pages'])}")
        print(f"  Templates: {len(registry['templates'])}")
        # Also print to stdout
        print("\n" + text)
    else:
        with open(output_path, "w") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
        print(f"\n  Written: {output_path}")
        print(f"  Pages: {len(registry['pages'])}")
        total_blocks = sum(len(p.get("blocks", [])) for p in registry["pages"])
        print(f"  Blocks: {total_blocks}")
        print(f"  Templates: {len(registry['templates'])}")
        print(f"  Collections: {len(registry.get('collections', {}))}")


if __name__ == "__main__":
    main()
