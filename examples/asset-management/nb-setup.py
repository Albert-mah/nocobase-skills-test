#!/usr/bin/env python3
"""
nb-setup.py -- NocoBase Collection Setup Tool (JSON-driven)

One script to register collections, create system fields, sync DB fields,
upgrade interfaces, create relations, and insert seed data.

Flow (7 steps per collection):
  1. Check collection exists
  2. Register collection (autoCreate=false)
  3. Create system fields via API (createdAt/updatedAt/createdBy/updatedBy)
  4. Sync DB columns as NocoBase fields
  5. Upgrade field interfaces (input → select, etc.)
  6. Create relation fields (m2o/o2m/m2m)
  7. Insert seed data

Usage:
    python nb-setup.py --url http://localhost:14000 tables.json
    python nb-setup.py --url http://localhost:14000 --collection nb_pm_categories --list
    python nb-setup.py --url http://localhost:14000 tables.json --dry-run
    python nb-setup.py --url http://localhost:14000 --collection nb_pm_categories --sync

Environment:
    NB_URL       -- NocoBase base URL (default: http://localhost:14000)
    NB_USER      -- Login email  (default: admin@nocobase.com)
    NB_PASSWORD  -- Login password (default: admin123)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

# ---------------------------------------------------------------------------
# Interface -> uiSchema templates
# ---------------------------------------------------------------------------

INTERFACE_TEMPLATES = {
    # ── Text ──────────────────────────────────────────────────────────────
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
    # ── Selection ─────────────────────────────────────────────────────────
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
    # ── Numbers ── type 不强制覆盖，保留 DB 原始类型 ─────────────────────
    # 新建字段时建议在 JSON 配置中显式指定 type (double/bigInt/float 等)
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
    # ── Date/Time ─────────────────────────────────────────────────────────
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
    # ── System ────────────────────────────────────────────────────────────
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
    # ── JSON ──────────────────────────────────────────────────────────────
    "json": {
        "type": "json",
        "default": None,
        "uiSchema": {"type": "object", "x-component": "Input.JSON", "x-component-props": {"autoSize": {"minRows": 5}}},
    },
}

# System fields that must be created via API (not SQL).
# createdBy/updatedBy auto-generate their FK columns (createdById/updatedById).
# If created via SQL first, the config can only be fixed via DB — API won't work.
SYSTEM_FIELD_PAYLOADS = [
    {
        "name": "createdAt",
        "interface": "createdAt",
        "type": "date",
        "field": "createdAt",
        "uiSchema": {
            "type": "datetime",
            "title": "Created at",
            "x-component": "DatePicker",
            "x-component-props": {},
            "x-read-pretty": True,
        },
    },
    {
        "name": "updatedAt",
        "interface": "updatedAt",
        "type": "date",
        "field": "updatedAt",
        "uiSchema": {
            "type": "datetime",
            "title": "Updated at",
            "x-component": "DatePicker",
            "x-component-props": {},
            "x-read-pretty": True,
        },
    },
    {
        "name": "createdBy",
        "interface": "createdBy",
        "type": "belongsTo",
        "target": "users",
        "foreignKey": "createdById",
        "uiSchema": {
            "type": "object",
            "title": "Created by",
            "x-component": "AssociationField",
            "x-component-props": {"fieldNames": {"label": "nickname", "value": "id"}},
            "x-read-pretty": True,
        },
    },
    {
        "name": "updatedBy",
        "interface": "updatedBy",
        "type": "belongsTo",
        "target": "users",
        "foreignKey": "updatedById",
        "uiSchema": {
            "type": "object",
            "title": "Updated by",
            "x-component": "AssociationField",
            "x-component-props": {"fieldNames": {"label": "nickname", "value": "id"}},
            "x-read-pretty": True,
        },
    },
]

# Synced DB columns that should auto-detect their interface (upgrade step)
SYSTEM_FIELD_MAP = {
    "id": "id",
    "sort": "sort",
    # createdAt/updatedAt/createdBy/updatedBy are created via API, not mapped from DB columns
}


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------

class NocoBaseClient:
    """Thin HTTP client for NocoBase API, using only urllib."""

    def __init__(self, base_url, user="admin@nocobase.com", password="admin123"):
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


class APIError(Exception):
    def __init__(self, code, body, url):
        self.code = code
        self.body = body
        self.url = url
        super().__init__(f"HTTP {code}: {url}\n{body[:500]}")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def list_fields(client, collection_name):
    """List all fields for a collection, print as table."""
    resp = client.get(f"/api/collections/{collection_name}/fields:list?paginate=false")
    fields = resp.get("data", [])
    if not fields:
        print(f"  (no fields found for {collection_name})")
        return

    # Sort: id first, then alphabetical
    fields.sort(key=lambda f: (0 if f["name"] == "id" else 1, f["name"]))

    print(f"\n  {'Field':<25} {'Type':<15} {'Interface':<15} {'Title'}")
    print(f"  {'─'*25} {'─'*15} {'─'*15} {'─'*30}")
    for f in fields:
        title = (f.get("uiSchema") or {}).get("title", "")
        print(f"  {f['name']:<25} {f.get('type',''):<15} {f.get('interface',''):<15} {title}")
    print(f"\n  Total: {len(fields)} fields")


def check_collection_exists(client, name):
    """Check if a collection is registered in NocoBase.
    Uses collections:get (not fields:list) because fields:list returns 200+[]
    even for non-existent collections."""
    try:
        resp = client.get(f"/api/collections:get?filterByTk={name}")
        if resp.get("data") is None:
            return False, []
        # Collection exists, now fetch its fields
        fresp = client.get(f"/api/collections/{name}/fields:list?paginate=false")
        fields = fresp.get("data", [])
        return True, fields
    except APIError as e:
        if e.code == 404 or "not found" in e.body.lower():
            return False, []
        raise


def register_collection(client, name, title, dry_run=False):
    """Register a collection with autoCreate=false, timestamps=false."""
    if dry_run:
        print(f"  🔵 DRY-RUN: Would register collection '{name}' (title: {title})")
        return True
    try:
        client.post("/api/collections:create", {
            "name": name,
            "title": title,
            "autoCreate": False,
            "timestamps": False,
        })
        print(f"  ✅ Registered collection '{name}'")
        return True
    except APIError as e:
        if "duplicate" in e.body.lower() or e.code == 400:
            print(f"  ⏭️  Collection '{name}' already registered (skip)")
            return True
        print(f"  ❌ Failed to register '{name}': {e}")
        return False


def sync_fields(client, dry_run=False):
    """Sync all fields from data source."""
    if dry_run:
        print(f"  🔵 DRY-RUN: Would sync fields")
        return True
    try:
        client.post("/api/mainDataSource:syncFields", expect_empty=True)
        print(f"  ✅ Synced fields")
        return True
    except APIError as e:
        print(f"  ❌ Sync failed: {e}")
        return False


def create_system_fields(client, collection_name, existing_fields, dry_run=False):
    """Create system fields (createdAt/updatedAt/createdBy/updatedBy) via API.

    These must be created via API because:
    - createdBy/updatedBy auto-create their FK columns (createdById/updatedById)
    - Field keys and config are managed by NocoBase internals
    - SQL-created columns cannot be properly managed via API later
    """
    existing_names = {f["name"] for f in existing_fields}
    # Also check by interface — SQL-created fields use snake_case (created_at)
    # but API-created ones use camelCase (createdAt). Match by interface to catch both.
    existing_interfaces = {f.get("interface", "") for f in existing_fields}
    ok, skip = 0, 0

    for payload in SYSTEM_FIELD_PAYLOADS:
        fname = payload["name"]
        iface = payload["interface"]
        if fname in existing_names or iface in existing_interfaces:
            skip += 1
            continue

        if dry_run:
            print(f"    🔵 DRY-RUN: Would create system field '{fname}'")
            ok += 1
            continue

        try:
            client.post(f"/api/collections/{collection_name}/fields:create", payload)
            print(f"    ✅ System field '{fname}'")
            ok += 1
        except APIError as e:
            if "duplicate" in str(e).lower():
                print(f"    ⏭️  System field '{fname}' already exists")
                skip += 1
            else:
                print(f"    ❌ System field '{fname}': {e}")

    return ok, skip


def build_field_update(field_name, target_interface, extra_config=None, existing_title=None):
    """Build the update payload for a field based on target interface."""
    tmpl = INTERFACE_TEMPLATES.get(target_interface)
    if not tmpl:
        return None

    payload = {
        "interface": target_interface,
        "uiSchema": json.loads(json.dumps(tmpl["uiSchema"])),
    }
    # upgrade 场景不覆盖 DB type —— 只更新 interface + uiSchema
    # 模板中的 type 仅供新建字段参考

    # Title 优先级: extra_config > existing_title > auto-generate
    title_map = {
        "id": "ID", "created_at": "Created At", "updated_at": "Updated At",
        "created_by_id": "Created By", "updated_by_id": "Updated By",
    }
    auto_title = title_map.get(field_name, field_name.replace("_", " ").title())
    payload["uiSchema"]["title"] = existing_title or auto_title

    # Handle extra config
    if extra_config:
        # enum for select/multipleSelect/radioGroup
        if "enum" in extra_config:
            payload["uiSchema"]["enum"] = extra_config["enum"]
        # precision for number
        if "precision" in extra_config:
            props = payload["uiSchema"].setdefault("x-component-props", {})
            precision = extra_config["precision"]
            props["step"] = str(10 ** (-precision))
        # title override
        if "title" in extra_config:
            payload["uiSchema"]["title"] = extra_config["title"]

    return payload


def upgrade_fields(client, collection_name, field_configs, existing_fields, dry_run=False):
    """Upgrade field interfaces to match config. Returns (ok_count, skip_count, fail_count).

    Only upgrades EXISTING fields (synced from DB). Fields not found in DB are skipped.
    The correct flow: SQL CREATE TABLE → syncFields → upgrade_fields.
    """
    ok, skip, fail = 0, 0, 0

    # Build lookup: field name -> existing field data
    existing = {f["name"]: f for f in existing_fields}

    for field_name, config in field_configs.items():
        # Parse shorthand: string = interface name, dict = full config
        if isinstance(config, str):
            target_interface = config
            extra_config = {}
        else:
            target_interface = config.get("interface", "input")
            extra_config = {k: v for k, v in config.items() if k != "interface"}

        ef = existing.get(field_name)
        if not ef:
            # Field not in DB -- can't upgrade what doesn't exist
            print(f"    ⚠️  Field '{field_name}' not found in synced fields (skip)")
            skip += 1
            continue

        current_interface = ef.get("interface", "")
        needs_update = False

        if current_interface != target_interface:
            needs_update = True
        else:
            # Interface matches -- check if sub-properties need update
            current_ui = ef.get("uiSchema") or {}
            # Check enum
            if target_interface in ("select", "multipleSelect", "radioGroup") and "enum" in extra_config:
                if current_ui.get("enum", []) != extra_config["enum"]:
                    needs_update = True
            # Check title
            if "title" in extra_config and current_ui.get("title") != extra_config["title"]:
                needs_update = True

        if not needs_update:
            skip += 1
            continue

        field_key = ef["key"]
        existing_title = (ef.get("uiSchema") or {}).get("title")
        payload = build_field_update(field_name, target_interface, extra_config, existing_title)
        if not payload:
            print(f"    ⚠️  Unknown interface '{target_interface}' for field '{field_name}'")
            skip += 1
            continue

        if dry_run:
            print(f"    🔵 DRY-RUN: Would upgrade '{field_name}': {current_interface} → {target_interface}")
            ok += 1
            continue

        try:
            client.put(f"/api/fields:update?filterByTk={field_key}", payload)
            print(f"    ✅ {field_name}: {current_interface} → {target_interface}")
            ok += 1
        except APIError as e:
            print(f"    ❌ {field_name}: {e}")
            fail += 1

    return ok, skip, fail


def create_relation(client, collection_name, rel_name, rel_config, existing_fields, dry_run=False):
    """Create a relation field if it doesn't exist."""
    existing_names = {f["name"] for f in existing_fields}
    if rel_name in existing_names:
        return "skip"

    rel_type = rel_config.get("type", "m2o")
    target = rel_config.get("target")
    foreign_key = rel_config.get("foreignKey")
    title = rel_config.get("title", rel_name.replace("_", " ").title())
    label_field = rel_config.get("label", "id")

    # Map shorthand type to NocoBase type
    type_map = {
        "m2o": "belongsTo",
        "o2m": "hasMany",
        "m2m": "belongsToMany",
        "o2o": "hasOne",
    }
    nb_type = type_map.get(rel_type, rel_type)

    payload = {
        "name": rel_name,
        "type": nb_type,
        "interface": rel_type,
        "target": target,
        "uiSchema": {
            "x-component": "AssociationField",
            "x-component-props": {
                "fieldNames": {"label": label_field, "value": "id"},
            },
            "title": title,
        },
    }

    if nb_type == "belongsTo":
        payload["foreignKey"] = foreign_key
    elif nb_type == "hasMany":
        payload["foreignKey"] = foreign_key
    elif nb_type == "belongsToMany":
        payload["foreignKey"] = foreign_key
        payload["otherKey"] = rel_config.get("otherKey")
        payload["through"] = rel_config.get("through")
    elif nb_type == "hasOne":
        payload["foreignKey"] = foreign_key

    if dry_run:
        print(f"    🔵 DRY-RUN: Would create relation '{rel_name}' ({rel_type} → {target})")
        return "ok"

    try:
        client.post(f"/api/collections/{collection_name}/fields:create", payload)
        print(f"    ✅ Relation '{rel_name}' ({rel_type} → {target})")
        return "ok"
    except APIError as e:
        print(f"    ❌ Relation '{rel_name}': {e}")
        return "fail"


def insert_data(client, collection_name, records, dry_run=False):
    """Insert data records one by one."""
    ok, fail = 0, 0
    for i, record in enumerate(records):
        if dry_run:
            print(f"    🔵 DRY-RUN: Would insert record #{i+1}: {json.dumps(record, ensure_ascii=False)[:80]}")
            ok += 1
            continue
        try:
            client.post(f"/api/{collection_name}:create", record)
            print(f"    ✅ Record #{i+1}")
            ok += 1
        except APIError as e:
            print(f"    ❌ Record #{i+1}: {e}")
            fail += 1
    return ok, fail


def process_collection(client, coll_config, dry_run=False, skip_data=False):
    """Process a single collection definition: register, sync, upgrade, relations, data."""
    name = coll_config["name"]
    title = coll_config.get("title", name)
    fields = coll_config.get("fields", {})
    relations = coll_config.get("relations", {})
    data = coll_config.get("data", []) if not skip_data else []

    print(f"\n{'='*60}")
    print(f"  Collection: {name} ({title})")
    print(f"{'='*60}")

    # Step 1: Check
    print(f"\n  [1/7] Check collection...")
    exists, existing_fields = check_collection_exists(client, name)
    if exists and len(existing_fields) == 0:
        # Dirty state: collection registered but no fields synced
        print(f"  ⚠️  Dirty state: collection exists but 0 fields — destroy and re-register")
        if not dry_run:
            try:
                client.delete(f"/api/collections:destroy?filterByTk={name}")
                print(f"  ✅ Destroyed dirty collection")
                exists = False
            except APIError as e:
                print(f"  ❌ Failed to destroy: {e}")
        else:
            print(f"  🔵 DRY-RUN: Would destroy and re-register")
            exists = False
    elif exists:
        print(f"  ⏭️  Collection exists ({len(existing_fields)} fields)")
    else:
        print(f"  ℹ️  Collection not registered")

    # Step 2: Register
    print(f"\n  [2/7] Register collection...")
    if not exists:
        if not register_collection(client, name, title, dry_run):
            print(f"  ❌ Aborting collection '{name}'")
            return
    else:
        print(f"  ⏭️  Already registered")

    # Step 3: Create system fields via API (createdAt/updatedAt/createdBy/updatedBy)
    # Must happen BEFORE syncFields — these fields need API creation because:
    # - createdBy/updatedBy auto-generate FK columns (createdById/updatedById)
    # - SQL-created columns can't be properly managed via API later
    print(f"\n  [3/7] Create system fields...")
    sys_ok, sys_skip = create_system_fields(client, name, existing_fields, dry_run)
    if sys_ok + sys_skip > 0:
        print(f"  Summary: ✅{sys_ok} ⏭️{sys_skip}")

    # Step 4: Sync DB fields
    print(f"\n  [4/7] Sync fields...")
    sync_fields(client, dry_run)
    # Re-fetch fields after sync
    if not dry_run:
        _, existing_fields = check_collection_exists(client, name)
        print(f"  ℹ️  Now {len(existing_fields)} fields")

    # Step 5: Upgrade field interfaces
    if fields:
        # Auto-add system fields that aren't explicitly configured
        all_fields = dict(fields)
        for ef in existing_fields:
            fname = ef["name"]
            if fname not in all_fields and fname in SYSTEM_FIELD_MAP:
                all_fields[fname] = SYSTEM_FIELD_MAP[fname]

        print(f"\n  [5/7] Upgrade field interfaces ({len(all_fields)} fields)...")
        ok, sk, fa = upgrade_fields(client, name, all_fields, existing_fields, dry_run)
        print(f"  Summary: ✅{ok} ⏭️{sk} ❌{fa}")
    else:
        print(f"\n  [5/7] No field config (skip)")

    # Step 6: Relations
    if relations:
        print(f"\n  [6/7] Create relations ({len(relations)})...")
        if not dry_run:
            _, existing_fields = check_collection_exists(client, name)
        rok, rsk, rfa = 0, 0, 0
        for rel_name, rel_config in relations.items():
            result = create_relation(client, name, rel_name, rel_config, existing_fields, dry_run)
            if result == "ok": rok += 1
            elif result == "skip":
                rsk += 1
                print(f"    ⏭️  Relation '{rel_name}' already exists")
            else: rfa += 1
        print(f"  Summary: ✅{rok} ⏭️{rsk} ❌{rfa}")
    else:
        print(f"\n  [6/7] No relations (skip)")

    # Step 7: Data
    if data:
        print(f"\n  [7/7] Insert data ({len(data)} records)...")
        dok, dfa = insert_data(client, name, data, dry_run)
        print(f"  Summary: ✅{dok} ❌{dfa}")
    else:
        print(f"\n  [7/7] No data (skip)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NocoBase Collection Setup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("config_file", nargs="?", help="JSON config file")
    parser.add_argument("--url", default=os.environ.get("NB_URL", "http://localhost:14000"),
                        help="NocoBase URL (default: $NB_URL or http://localhost:14000)")
    parser.add_argument("--user", default=os.environ.get("NB_USER", "admin@nocobase.com"),
                        help="Login email")
    parser.add_argument("--password", default=os.environ.get("NB_PASSWORD", "admin123"),
                        help="Login password")
    parser.add_argument("--collection", "-c", help="Collection name (for --list or --sync)")
    parser.add_argument("--list", "-l", action="store_true", help="List fields of a collection")
    parser.add_argument("--sync", "-s", action="store_true", help="Just sync fields, no upgrade")
    parser.add_argument("--clean", action="store_true", help="Destroy collection registration (keeps DB table)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be done, don't execute")
    parser.add_argument("--skip-data", action="store_true", help="Skip data insertion (useful for re-runs)")

    args = parser.parse_args()

    # Validate args
    if not args.config_file and not args.collection:
        parser.error("Need a config file or --collection")

    # Connect
    client = NocoBaseClient(args.url, args.user, args.password)
    print(f"🔑 Logging in to {args.url}...")
    try:
        client.login()
        print(f"✅ Authenticated")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        sys.exit(1)

    # Mode: list fields
    if args.list:
        if not args.collection:
            parser.error("--list requires --collection")
        print(f"\n📋 Fields for '{args.collection}':")
        list_fields(client, args.collection)
        return

    # Mode: clean (destroy collection registration)
    # WARNING: collections:destroy also drops DB columns asynchronously!
    # Only use this when you intend to fully recreate the table via SQL afterwards.
    if args.clean:
        if not args.collection:
            parser.error("--clean requires --collection")
        print(f"\n⚠️  WARNING: collections:destroy will DROP DB columns!")
        print(f"   You must recreate the table via SQL after this operation.")
        print(f"\n🗑️  Destroying collection '{args.collection}'...")
        try:
            client.post(f"/api/collections:destroy?filterByTk={args.collection}", expect_empty=True)
            print(f"  ✅ Collection '{args.collection}' destroyed")
            print(f"  ℹ️  Next steps: DROP TABLE + CREATE TABLE via SQL, then re-run setup")
        except APIError as e:
            print(f"  ❌ Failed: {e}")
        return

    # Mode: quick sync
    if args.sync and args.collection and not args.config_file:
        print(f"\n🔄 Syncing '{args.collection}'...")
        exists, _ = check_collection_exists(client, args.collection)
        if not exists:
            print(f"  ℹ️  Registering collection first...")
            register_collection(client, args.collection, args.collection)
        sync_fields(client)
        print(f"\n📋 Fields after sync:")
        list_fields(client, args.collection)
        return

    # Mode: JSON config
    if args.config_file:
        try:
            with open(args.config_file) as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"❌ File not found: {args.config_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {args.config_file}: {e}")
            sys.exit(1)

        collections = config.get("collections", [])
        if not collections:
            print("⚠️  No collections in config file")
            return

        if args.dry_run:
            print(f"\n🔵 DRY-RUN MODE — nothing will be modified\n")

        print(f"📦 Processing {len(collections)} collection(s)...")

        for coll in collections:
            process_collection(client, coll, args.dry_run, args.skip_data)

        print(f"\n{'='*60}")
        print(f"  Done! Processed {len(collections)} collection(s)")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
