"""Collection management tools — register, list, sync, execute SQL.

Extracted from nb-setup.py.
"""

import json
import os
import subprocess
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import (
    NocoBaseClient, APIError, get_stdlib_client,
    SYSTEM_FIELD_PAYLOADS, SYSTEM_FIELD_MAP,
)
from ..utils import safe_json
from .fields import _build_field_update


def _ensure_system_columns(table_name: str) -> str:
    """Ensure system columns exist in DB via SQL ALTER TABLE.

    NocoBase requires createdAt/updatedAt/createdById/updatedById columns.
    This function guarantees they exist at the DB level, regardless of whether
    the original DDL included them.

    Returns summary string.
    """
    db_url = os.environ.get("NB_DB_URL", "postgresql://nocobase:nocobase@localhost:5435/nocobase")
    sql = f'''
        ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "createdAt" TIMESTAMPTZ DEFAULT NOW();
        ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "updatedAt" TIMESTAMPTZ DEFAULT NOW();
        ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "createdById" BIGINT;
        ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "updatedById" BIGINT;
    '''
    try:
        import psycopg2
        with psycopg2.connect(db_url) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql)
        return "OK"
    except ImportError:
        try:
            result = subprocess.run(
                ["psql", db_url, "-c", sql],
                capture_output=True, text=True, timeout=10,
            )
            return "OK" if result.returncode == 0 else f"ERROR: {result.stderr.strip()}"
        except Exception as e:
            return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR: {e}"


def register_tools(mcp: FastMCP):
    """Register collection management tools on the MCP server."""

    @mcp.tool()
    def nb_execute_sql(sql: str, db_url: Optional[str] = None) -> str:
        """Execute SQL against the NocoBase PostgreSQL database.

        Uses psql command-line tool. For bulk DDL (CREATE TABLE, ALTER TABLE),
        this is faster and more reliable than API calls.

        **Auto system columns**: When CREATE TABLE statements are detected,
        automatically adds createdAt/updatedAt/createdById/updatedById columns
        to each created table. You do NOT need to include these in your DDL.

        Args:
            sql: SQL statement(s) to execute. Multiple statements separated by semicolons.
            db_url: PostgreSQL connection URL. Default: postgresql://nocobase:nocobase@localhost:5435/nocobase

        Returns:
            psql output or error message.

        Example:
            nb_execute_sql("CREATE TABLE IF NOT EXISTS nb_pm_projects (id BIGSERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL)")
        """
        import os
        import re
        db_url = db_url or os.environ.get("NB_DB_URL", "postgresql://nocobase:nocobase@localhost:5435/nocobase")
        # Try psycopg2 first (no external binary needed)
        try:
            import psycopg2
            with psycopg2.connect(db_url) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(sql)
                    # Try to fetch results if it was a SELECT
                    try:
                        rows = cur.fetchall()
                        if rows:
                            cols = [d[0] for d in cur.description] if cur.description else []
                            lines = ["\t".join(cols)] if cols else []
                            for row in rows:
                                lines.append("\t".join(str(v) for v in row))
                            result = "\n".join(lines)
                        else:
                            result = "OK (0 rows)"
                    except psycopg2.ProgrammingError:
                        result = f"OK ({cur.rowcount} rows affected)" if cur.rowcount >= 0 else "OK"
            # Auto-add system columns for any CREATE TABLE statements
            tables = re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', sql, re.IGNORECASE)
            if tables:
                sys_results = []
                for tbl in tables:
                    sr = _ensure_system_columns(tbl)
                    if sr != "OK":
                        sys_results.append(f"{tbl}: {sr}")
                if sys_results:
                    result += "\n[system-cols] " + "; ".join(sys_results)
                else:
                    result += f"\n[system-cols] added to {len(tables)} tables"
            return result
        except ImportError:
            pass  # Fall through to psql
        except Exception as e:
            return f"ERROR: {e}"

        # Fallback: psql CLI
        try:
            proc = subprocess.run(
                ["psql", db_url, "-c", sql],
                capture_output=True, text=True, timeout=30,
            )
            output = proc.stdout.strip()
            if proc.returncode != 0:
                return f"ERROR: {proc.stderr.strip()}\n{output}"
            result = output or "OK (no output)"
            # Auto-add system columns for any CREATE TABLE statements
            tables = re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', sql, re.IGNORECASE)
            if tables:
                sys_results = []
                for tbl in tables:
                    sr = _ensure_system_columns(tbl)
                    if sr != "OK":
                        sys_results.append(f"{tbl}: {sr}")
                if sys_results:
                    result += "\n[system-cols] " + "; ".join(sys_results)
                else:
                    result += f"\n[system-cols] added to {len(tables)} tables"
            return result
        except FileNotFoundError:
            return "ERROR: Neither psycopg2 nor psql available. Install: pip install psycopg2-binary"
        except subprocess.TimeoutExpired:
            return "ERROR: SQL execution timed out (30s limit)"

    @mcp.tool()
    def nb_register_collection(name: str, title: str, tree: Optional[str] = None) -> str:
        """Register an existing database table as a NocoBase collection.

        The table must already exist in the database (created via SQL).
        This call registers it in NocoBase's metadata with autoCreate=false.

        Args:
            name: Collection name (must match the DB table name exactly)
            title: Display title in NocoBase UI
            tree: Tree type if this is a hierarchical collection. Use "adjacency-list" for parent-child trees.

        Returns:
            Success or error message.

        Example:
            nb_register_collection("nb_pm_projects", "Projects")
            nb_register_collection("nb_pm_categories", "Categories", tree="adjacency-list")
        """
        client = get_stdlib_client()
        payload = {
            "name": name,
            "title": title,
            "autoCreate": False,
            "timestamps": False,
        }
        if tree:
            payload["tree"] = tree
        try:
            client.post("/api/collections:create", payload)
            return f"Registered collection '{name}' (title: {title})"
        except APIError as e:
            if "duplicate" in e.body.lower() or e.code == 400:
                return f"Collection '{name}' already registered (skipped)"
            return f"ERROR: {e}"

    @mcp.tool()
    def nb_sync_fields(collection: Optional[str] = None) -> str:
        """Sync database columns into NocoBase field metadata.

        After creating columns via SQL, call this to make NocoBase aware of them.
        Also creates system fields (createdAt, updatedAt, createdBy, updatedBy) via API
        if they don't exist yet.

        Args:
            collection: If provided, also creates system fields for this specific collection
                        before syncing. If None, just triggers a global sync.

        Returns:
            Summary of sync results.
        """
        client = get_stdlib_client()
        results = []

        # Ensure system columns in DB + create field metadata
        if collection:
            # Guarantee DB columns exist first
            col_result = _ensure_system_columns(collection)
            if col_result != "OK":
                results.append(f"System columns: {col_result}")

        # Global sync (DB → NocoBase metadata)
        try:
            client.post("/api/mainDataSource:syncFields", expect_empty=True)
            results.append("Fields synced successfully")
        except APIError as e:
            results.append(f"Sync error: {e}")

        # Create system field metadata via API
        if collection:
            try:
                resp = client.get(f"/api/collections/{collection}/fields:list?paginate=false")
                existing_fields = resp.get("data", [])
                existing_names = {f["name"] for f in existing_fields}
                existing_interfaces = {f.get("interface", "") for f in existing_fields}

                created, skipped = 0, 0
                for payload in SYSTEM_FIELD_PAYLOADS:
                    fname = payload["name"]
                    iface = payload["interface"]
                    if fname in existing_names or iface in existing_interfaces:
                        skipped += 1
                        continue
                    try:
                        client.post(f"/api/collections/{collection}/fields:create", payload)
                        created += 1
                    except APIError:
                        skipped += 1

                results.append(f"System fields: {created} created, {skipped} skipped")
            except APIError as e:
                results.append(f"System fields error: {e}")

        # Report field count if collection specified
        if collection:
            try:
                resp = client.get(f"/api/collections/{collection}/fields:list?paginate=false")
                count = len(resp.get("data", []))
                results.append(f"Collection '{collection}' now has {count} fields")
            except APIError:
                pass

        return "\n".join(results)

    @mcp.tool()
    def nb_setup_collection(
        name: str,
        title: str,
        fields_json: Optional[dict] = None,
        relations_json: Optional[list] = None,
        tree: Optional[str] = None,
    ) -> str:
        """Register a collection, sync fields, upgrade interfaces, and create relations — all in one call.

        Combines nb_register_collection + nb_sync_fields + nb_upgrade_field (batch) + nb_create_relation (batch).
        Use this instead of calling those tools individually for each table.

        Args:
            name: Collection name (must match DB table name)
            title: Display title in NocoBase UI
            fields_json: Optional JSON object mapping field names to upgrade configs.
                Keys are field names, values are objects with:
                  - "interface": target interface (required)
                  - "enum": array of enum options for select/multipleSelect
                  - "title": display title override
                  - "precision": decimal precision for number fields

                Example:
                    {"status": {"interface": "select", "enum": [{"value":"active","label":"Active","color":"green"}]},
                     "start_date": {"interface": "date"},
                     "budget": {"interface": "number", "precision": 2},
                     "description": {"interface": "textarea"},
                     "email": {"interface": "email"}}

                Fields not listed here keep their default interface (input).

            relations_json: Optional JSON array of relation definitions.
                Each item: {"field": "name", "type": "m2o|o2m|m2m", "target": "collection", "foreign_key": "fk_col", "label": "display_field"}

                Example:
                    [{"field": "project", "type": "m2o", "target": "nb_pm_projects", "foreign_key": "project_id", "label": "name"},
                     {"field": "tasks", "type": "o2m", "target": "nb_pm_tasks", "foreign_key": "project_id"}]

            tree: Tree type for hierarchical collections ("adjacency-list")

        Returns:
            Summary of all operations performed.

        Example:
            nb_setup_collection("nb_crm_customers", "客户",
                '{"status":{"interface":"select","enum":[{"value":"active","label":"Active","color":"green"}]},"phone":{"interface":"phone"}}',
                '[{"field":"contacts","type":"o2m","target":"nb_crm_contacts","foreign_key":"customer_id"}]')
        """
        client = get_stdlib_client()
        results = []

        # Step 1: Register collection
        payload = {"name": name, "title": title, "autoCreate": False, "timestamps": False}
        if tree:
            payload["tree"] = tree
        try:
            client.post("/api/collections:create", payload)
            results.append(f"[register] OK")
        except APIError as e:
            if "duplicate" in e.body.lower() or e.code == 400:
                results.append(f"[register] already exists")
            else:
                results.append(f"[register] ERROR: {e}")
                return "\n".join(results)

        # Step 2: Ensure system columns in DB + sync + create system field metadata
        # 2a: Guarantee DB columns exist (defensive — works regardless of DDL)
        col_result = _ensure_system_columns(name)
        if col_result != "OK":
            results.append(f"[system-cols] {col_result}")

        # 2b: Sync DB → NocoBase metadata
        try:
            client.post("/api/mainDataSource:syncFields", expect_empty=True)
        except APIError:
            pass

        # 2c: Create system field metadata via API (for proper ORM mapping)
        try:
            resp = client.get(f"/api/collections/{name}/fields:list?paginate=false")
            existing_names = {f["name"] for f in resp.get("data", [])}
        except APIError:
            existing_names = set()

        sys_created = 0
        for spay in SYSTEM_FIELD_PAYLOADS:
            if spay["name"] not in existing_names and spay["interface"] not in existing_names:
                try:
                    client.post(f"/api/collections/{name}/fields:create", spay)
                    sys_created += 1
                except APIError:
                    pass

        # Re-fetch fields after system field creation
        try:
            resp = client.get(f"/api/collections/{name}/fields:list?paginate=false")
            fields = resp.get("data", [])
            results.append(f"[sync] {len(fields)} fields ({sys_created} system fields created)")
        except APIError as e:
            results.append(f"[sync] ERROR: {e}")
            fields = []

        # Step 3: Batch upgrade field interfaces
        if fields_json:
            try:
                field_configs = safe_json(fields_json)
            except (json.JSONDecodeError, TypeError):
                results.append("[upgrade] ERROR: invalid fields_json")
                field_configs = {}

            existing_map = {f["name"]: f for f in fields}
            upgraded, skipped, failed = 0, 0, 0

            for fname, fconfig in field_configs.items():
                ef = existing_map.get(fname)
                if not ef:
                    results.append(f"[upgrade] {fname}: not found (skipped)")
                    skipped += 1
                    continue

                target_iface = fconfig.get("interface", "input")
                if ef.get("interface") == target_iface:
                    skipped += 1
                    continue

                extra = {}
                if "enum" in fconfig:
                    extra["enum"] = fconfig["enum"]
                if "title" in fconfig:
                    extra["title"] = fconfig["title"]
                if "precision" in fconfig:
                    extra["precision"] = fconfig["precision"]

                existing_title = (ef.get("uiSchema") or {}).get("title")
                upd = _build_field_update(fname, target_iface, extra, existing_title)
                if not upd:
                    skipped += 1
                    continue

                try:
                    client.put(f"/api/fields:update?filterByTk={ef['key']}", upd)
                    upgraded += 1
                except APIError:
                    failed += 1

            results.append(f"[upgrade] {upgraded} upgraded, {skipped} skipped, {failed} failed")

        # Step 4: Batch create relations
        if relations_json:
            try:
                relations = safe_json(relations_json)
            except (json.JSONDecodeError, TypeError):
                results.append("[relations] ERROR: invalid relations_json")
                relations = []

            # Re-fetch fields for relation check
            try:
                resp = client.get(f"/api/collections/{name}/fields:list?paginate=false")
                existing_names = {f["name"] for f in resp.get("data", [])}
            except APIError:
                existing_names = set()

            rel_ok, rel_skip = 0, 0
            type_map = {"m2o": "belongsTo", "o2m": "hasMany", "m2m": "belongsToMany", "o2o": "hasOne"}

            for rel in relations:
                rfield = rel["field"]
                if rfield in existing_names:
                    rel_skip += 1
                    continue

                nb_type = type_map.get(rel["type"], rel["type"])
                rlabel = rel.get("label", "id")
                rtitle = rel.get("title", rfield.replace("_", " ").title())

                rpayload = {
                    "name": rfield, "type": nb_type, "interface": rel["type"],
                    "target": rel["target"], "foreignKey": rel["foreign_key"],
                    "uiSchema": {
                        "x-component": "AssociationField",
                        "x-component-props": {"fieldNames": {"label": rlabel, "value": "id"}},
                        "title": rtitle,
                    },
                }
                if nb_type == "belongsToMany":
                    if "other_key" in rel:
                        rpayload["otherKey"] = rel["other_key"]
                    if "through" in rel:
                        rpayload["through"] = rel["through"]

                try:
                    client.post(f"/api/collections/{name}/fields:create", rpayload)
                    rel_ok += 1
                except APIError:
                    rel_skip += 1

            results.append(f"[relations] {rel_ok} created, {rel_skip} skipped")

        return f"{name}: " + " | ".join(results)

    @mcp.tool()
    def nb_list_collections(filter: Optional[str] = None) -> str:
        """List all registered NocoBase collections.

        Args:
            filter: Optional name prefix to filter collections (e.g. "nb_pm_" to list only PM tables)

        Returns:
            List of collections with name, title, and field count.
        """
        client = get_stdlib_client()
        try:
            resp = client.get("/api/collections:list?paginate=false")
            collections = resp.get("data", [])

            if filter:
                collections = [c for c in collections if c["name"].startswith(filter)]

            collections.sort(key=lambda c: c["name"])

            if not collections:
                return "No collections found" + (f" matching '{filter}'" if filter else "")

            lines = [f"{'Name':<35} {'Title':<25} {'Category'}"]
            lines.append(f"{'─'*35} {'─'*25} {'─'*15}")
            for c in collections:
                name = c.get("name", "")
                title = c.get("title", "")
                cat = c.get("category", "")
                lines.append(f"{name:<35} {title:<25} {cat}")
            lines.append(f"\nTotal: {len(collections)} collections")
            return "\n".join(lines)
        except APIError as e:
            return f"ERROR: {e}"
