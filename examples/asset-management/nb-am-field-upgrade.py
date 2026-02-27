#!/usr/bin/env python3
"""nb-am-field-upgrade.py — 字段字典升级脚本（44 个 select/enum 字段）

将 nb-am-setup.py 中定义的 select/multipleSelect 字段从纯文本 input 升级为下拉选项。
只做接口升级（Step 5），不重建表、不创建关系。

Usage:
    python3 nb-am-field-upgrade.py              # 全量升级
    python3 nb-am-field-upgrade.py --module M1  # 只升级 M1 基础数据
    python3 nb-am-field-upgrade.py --dry-run    # 预览模式
    python3 nb-am-field-upgrade.py --check      # 只检查当前状态

Environment:
    NB_URL       http://localhost:14000
    NB_USER      admin@nocobase.com
    NB_PASSWORD  admin123
"""

import argparse
import json
import os
import sys

# Import from nb-setup.py and nb-am-setup.py (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module

nb_setup = import_module("nb-setup")
NocoBaseClient = nb_setup.NocoBaseClient
check_collection_exists = nb_setup.check_collection_exists
upgrade_fields = nb_setup.upgrade_fields

am_setup = import_module("nb-am-setup")
ALL_COLLECTIONS = am_setup.ALL_COLLECTIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UPGRADEABLE_INTERFACES = {"select", "multipleSelect", "radioGroup", "checkbox",
                          "number", "integer", "percent", "date", "datetime",
                          "time", "textarea", "sort", "email", "phone", "markdown"}


def get_upgrade_fields(coll_config):
    """Extract only the fields that need interface upgrade (not plain input)."""
    fields = coll_config.get("fields", {})
    upgrade = {}
    for fname, fconfig in fields.items():
        if isinstance(fconfig, str):
            iface = fconfig
        else:
            iface = fconfig.get("interface", "input")

        if iface != "input":
            upgrade[fname] = fconfig
    return upgrade


def check_field_status(client, coll_name, upgrade_fields_config):
    """Check current field interfaces vs target. Returns (correct, wrong, missing) lists."""
    _, existing = check_collection_exists(client, coll_name)
    existing_map = {f["name"]: f for f in existing}

    correct, wrong, missing = [], [], []
    for fname, fconfig in upgrade_fields_config.items():
        target_iface = fconfig if isinstance(fconfig, str) else fconfig.get("interface", "input")
        ef = existing_map.get(fname)
        if not ef:
            missing.append(fname)
        elif ef.get("interface") == target_iface:
            # Also check enum for select fields
            if target_iface in ("select", "multipleSelect", "radioGroup"):
                target_enum = fconfig.get("enum", []) if isinstance(fconfig, dict) else []
                current_enum = (ef.get("uiSchema") or {}).get("enum", [])
                if target_enum and current_enum != target_enum:
                    wrong.append((fname, ef.get("interface"), target_iface, "enum mismatch"))
                    continue
            correct.append(fname)
        else:
            wrong.append((fname, ef.get("interface"), target_iface, "interface"))
    return correct, wrong, missing


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AM 字段字典升级（44 个 select/enum 字段）")
    parser.add_argument("--url", default=os.environ.get("NB_URL", "http://localhost:14000"))
    parser.add_argument("--user", default=os.environ.get("NB_USER", "admin@nocobase.com"))
    parser.add_argument("--password", default=os.environ.get("NB_PASSWORD", "admin123"))
    parser.add_argument("--module", "-m", choices=["M1", "M2", "M3", "M4"],
                        help="Only upgrade one module")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Preview mode")
    parser.add_argument("--check", "-c", action="store_true", help="Only check current status")
    args = parser.parse_args()

    modules = [args.module] if args.module else ["M1", "M2", "M3", "M4"]

    print(f"\n{'═' * 60}")
    print(f"  AM Field Upgrade — select/enum 字段字典升级")
    print(f"  Modules: {', '.join(modules)}")
    print(f"  Mode: {'CHECK' if args.check else 'DRY-RUN' if args.dry_run else 'UPGRADE'}")
    print(f"{'═' * 60}")

    # Login
    client = NocoBaseClient(args.url, args.user, args.password)
    print(f"\n  🔑 Logging in to {args.url}...")
    try:
        client.login()
        print(f"  ✅ Authenticated")
    except Exception as e:
        print(f"  ❌ Login failed: {e}")
        sys.exit(1)

    # Process each collection
    total_ok, total_skip, total_fail = 0, 0, 0
    total_fields = 0

    for m in modules:
        print(f"\n{'─' * 60}")
        print(f"  Module {m}")
        print(f"{'─' * 60}")

        for coll in ALL_COLLECTIONS[m]:
            coll_name = coll["name"]
            upgrade = get_upgrade_fields(coll)

            if not upgrade:
                continue

            total_fields += len(upgrade)

            if args.check:
                # Check mode: only report status
                correct, wrong, missing = check_field_status(client, coll_name, upgrade)
                status_parts = []
                if correct:
                    status_parts.append(f"✅{len(correct)}")
                if wrong:
                    status_parts.append(f"❌{len(wrong)}")
                if missing:
                    status_parts.append(f"⚠️{len(missing)}")
                print(f"\n  {coll_name}: {' '.join(status_parts)}")
                for fname, cur, tgt, reason in wrong:
                    print(f"    ❌ {fname}: {cur} → {tgt} ({reason})")
                for fname in missing:
                    print(f"    ⚠️  {fname}: not found in DB")
            else:
                # Upgrade mode
                print(f"\n  {coll_name} ({len(upgrade)} fields)...")
                _, existing_fields = check_collection_exists(client, coll_name)
                ok, sk, fa = upgrade_fields(client, coll_name, upgrade, existing_fields, args.dry_run)
                total_ok += ok
                total_skip += sk
                total_fail += fa

    # Summary
    print(f"\n{'═' * 60}")
    if args.check:
        print(f"  Check complete: {total_fields} upgrade-target fields across {', '.join(modules)}")
    else:
        print(f"  Upgrade complete: ✅{total_ok} ⏭️{total_skip} ❌{total_fail}")
        print(f"  Total fields: {total_fields}")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()
