#!/usr/bin/env python3
"""nb-save-templates.py — 自动将所有弹窗保存为模板

扫描所有 ChildPageModel（弹窗表单）和 TableBlockModel/DetailModel 等区块，
自动注册为 flowModelTemplates，便于其他页面复用。

命名规则：
  popup 类型: "{collection_title}_{action}"
    例: "采购申请_新增", "资产台账_编辑", "资产台账_详情"
  block 类型: "{collection_title}_{block_type}"
    例: "采购申请_新增表单", "资产台账_编辑表单", "资产台账_表格"

用法：
    python3 nb-save-templates.py              # 扫描并保存所有弹窗模板
    python3 nb-save-templates.py --dry-run    # 只显示，不写入
    python3 nb-save-templates.py --clean      # 删除所有自动生成的模板
    python3 nb-save-templates.py --list       # 列出已有模板

集成到构建流程：
    在 nb-am-pages.py / nb-pm-pages.py 等脚本末尾加一行：
        os.system("python3 nb-save-templates.py")
    或者在 nb_page_builder.py 的 summary() 里自动调用。
"""

import sys
import json

sys.path.insert(0, ".")
from nb_page_builder import NB


# ═══════════════════════════════════════════════════════════════
# Action type → 中文描述
# ═══════════════════════════════════════════════════════════════

ACTION_LABELS = {
    "AddNewActionModel": "新增",
    "EditActionModel": "编辑",
    "ViewActionModel": "详情",
    "PopupActionModel": "弹窗",
    "DeleteActionModel": "删除",
}

BLOCK_LABELS = {
    "CreateFormModel": "新增表单",
    "EditFormModel": "编辑表单",
    "DetailModel": "详情区块",
    "TableBlockModel": "表格",
    "JSBlockModel": "JS区块",
}

AUTO_PREFIX = "[Auto] "  # 自动模板的标记前缀


def get_collection_title(nb, coll_name):
    """获取 collection 的中文 title。"""
    try:
        r = nb.s.get(f"{nb.base}/api/collections:get?filterByTk={coll_name}")
        if r.ok:
            data = r.json().get("data")
            if data:
                return data.get("title", coll_name)
    except Exception:
        pass
    return coll_name


def get_existing_templates(nb):
    """获取已有模板，返回 {targetUid: template} 映射。"""
    r = nb.s.get(f"{nb.base}/api/flowModelTemplates:list?paginate=false")
    templates = r.json().get("data", [])
    return {t["targetUid"]: t for t in templates}


def discover_popup_actions(all_models):
    """找到所有弹窗动作（AddNew/Edit/View）及其 ChildPageModel。"""
    actions = []
    model_map = {m["uid"]: m for m in all_models}

    for m in all_models:
        use = m.get("use", "")
        if use not in ACTION_LABELS:
            continue

        # 找 ChildPageModel 子节点
        child_pages = [c for c in all_models
                       if c.get("parentId") == m["uid"]
                       and c.get("use") == "ChildPageModel"]
        if not child_pages:
            continue

        # 获取 collection
        popup_settings = (m.get("stepParams") or {}).get("popupSettings", {}).get("openView", {})
        coll = popup_settings.get("collectionName", "")
        if not coll:
            continue

        actions.append({
            "action_uid": m["uid"],
            "action_use": use,
            "child_page_uid": child_pages[0]["uid"],
            "collection": coll,
            "popup_mode": popup_settings.get("mode", "drawer"),
            "popup_size": popup_settings.get("size", "large"),
        })

    return actions


def discover_form_blocks(all_models):
    """找到所有独立的表单/表格区块。"""
    blocks = []

    for m in all_models:
        use = m.get("use", "")
        if use not in BLOCK_LABELS:
            continue

        sp = m.get("stepParams") or {}
        rs = sp.get("resourceSettings", {}).get("init", {})
        coll = rs.get("collectionName", "")
        if not coll:
            continue

        blocks.append({
            "block_uid": m["uid"],
            "block_use": use,
            "collection": coll,
            "parent_id": m.get("parentId", ""),
        })

    return blocks


def save_popup_templates(nb, dry_run=False):
    """保存所有弹窗为 popup 模板。"""
    print("\n" + "=" * 60)
    print("  Scanning popup actions...")
    print("=" * 60)

    r = nb.s.get(f"{nb.base}/api/flowModels:list?paginate=false")
    all_models = r.json().get("data", [])
    print(f"  Total FlowModel nodes: {len(all_models)}")

    existing = get_existing_templates(nb)
    actions = discover_popup_actions(all_models)
    print(f"  Popup actions found: {len(actions)}")

    # Collection title cache
    coll_titles = {}

    created = 0
    skipped = 0
    for act in actions:
        coll = act["collection"]
        if coll not in coll_titles:
            coll_titles[coll] = get_collection_title(nb, coll)
        title = coll_titles[coll]
        label = ACTION_LABELS.get(act["action_use"], act["action_use"])
        name = f"{AUTO_PREFIX}{title}_{label}"

        # 用 action_uid 作为 targetUid（popup 模板指向 action）
        target_uid = act["action_uid"]

        if target_uid in existing:
            skipped += 1
            continue

        print(f"  + {name:40s}  target={target_uid}  coll={coll}")

        if not dry_run:
            r = nb.s.post(f"{nb.base}/api/flowModelTemplates:create", json={
                "name": name,
                "description": f"Auto-saved popup: {title} {label}",
                "targetUid": target_uid,
                "useModel": act["action_use"],
                "type": "popup",
                "dataSourceKey": "main",
                "collectionName": coll,
            })
            if not r.ok:
                print(f"    ERROR: {r.text[:100]}")
            else:
                created += 1

    print(f"\n  Popup templates: {created} created, {skipped} skipped (already exist)")
    return created


def save_block_templates(nb, dry_run=False):
    """保存所有独立表单/表格区块为 block 模板。"""
    print("\n" + "=" * 60)
    print("  Scanning form/table blocks...")
    print("=" * 60)

    r = nb.s.get(f"{nb.base}/api/flowModels:list?paginate=false")
    all_models = r.json().get("data", [])

    existing = get_existing_templates(nb)
    blocks = discover_form_blocks(all_models)
    print(f"  Form/table blocks found: {len(blocks)}")

    # Deduplicate: for each (collection, use), keep only one (the first)
    seen = set()
    unique_blocks = []
    for b in blocks:
        key = (b["collection"], b["block_use"])
        if key not in seen:
            seen.add(key)
            unique_blocks.append(b)

    print(f"  Unique (collection, type) pairs: {len(unique_blocks)}")

    coll_titles = {}
    created = 0
    skipped = 0

    for b in unique_blocks:
        coll = b["collection"]
        if coll not in coll_titles:
            coll_titles[coll] = get_collection_title(nb, coll)
        title = coll_titles[coll]
        label = BLOCK_LABELS.get(b["block_use"], b["block_use"])
        name = f"{AUTO_PREFIX}{title}_{label}"

        target_uid = b["block_uid"]

        if target_uid in existing:
            skipped += 1
            continue

        print(f"  + {name:40s}  target={target_uid}  coll={coll}")

        if not dry_run:
            r = nb.s.post(f"{nb.base}/api/flowModelTemplates:create", json={
                "name": name,
                "description": f"Auto-saved block: {title} {label}",
                "targetUid": target_uid,
                "useModel": b["block_use"],
                "type": "block",
                "dataSourceKey": "main",
                "collectionName": coll,
            })
            if not r.ok:
                print(f"    ERROR: {r.text[:100]}")
            else:
                created += 1

    print(f"\n  Block templates: {created} created, {skipped} skipped")
    return created


def list_templates(nb):
    """列出所有已有模板。"""
    r = nb.s.get(f"{nb.base}/api/flowModelTemplates:list?paginate=false")
    templates = r.json().get("data", [])
    print(f"\n{'=' * 70}")
    print(f"  All Templates ({len(templates)})")
    print(f"{'=' * 70}")

    auto = [t for t in templates if t.get("name", "").startswith(AUTO_PREFIX)]
    manual = [t for t in templates if not t.get("name", "").startswith(AUTO_PREFIX)]

    if manual:
        print(f"\n  --- Manual ({len(manual)}) ---")
        for t in manual:
            print(f"  {t['type']:6s}  {t.get('useModel',''):25s}  {t['name']:40s}  coll={t.get('collectionName','')}")

    if auto:
        print(f"\n  --- Auto ({len(auto)}) ---")
        for t in auto:
            print(f"  {t['type']:6s}  {t.get('useModel',''):25s}  {t['name']:40s}  coll={t.get('collectionName','')}")


def clean_auto_templates(nb):
    """删除所有自动生成的模板。"""
    r = nb.s.get(f"{nb.base}/api/flowModelTemplates:list?paginate=false")
    templates = r.json().get("data", [])
    auto = [t for t in templates if t.get("name", "").startswith(AUTO_PREFIX)]

    if not auto:
        print("  No auto-generated templates to clean.")
        return

    print(f"  Cleaning {len(auto)} auto-generated templates...")
    for t in auto:
        r = nb.s.post(f"{nb.base}/api/flowModelTemplates:destroy?filterByTk={t['uid']}")
        status = "OK" if r.ok else f"ERR({r.status_code})"
        print(f"    - {t['name']:40s}  [{status}]")


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return

    nb = NB()
    dry_run = "--dry-run" in sys.argv

    if "--list" in sys.argv:
        list_templates(nb)
        return

    if "--clean" in sys.argv:
        clean_auto_templates(nb)
        return

    print(f"\n{'=' * 60}")
    print(f"  Auto-Save Templates")
    print(f"  {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'=' * 60}")

    p = save_popup_templates(nb, dry_run)
    b = save_block_templates(nb, dry_run)

    print(f"\n{'=' * 60}")
    print(f"  Done! {p + b} templates saved")
    if dry_run:
        print(f"  (dry-run mode — nothing was written)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
