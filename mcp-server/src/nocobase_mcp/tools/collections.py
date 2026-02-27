"""Collection management tools — register, list, sync, execute SQL.

Extracted from nb-setup.py.
"""

import json
import subprocess
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import (
    NocoBaseClient, APIError, get_stdlib_client,
    SYSTEM_FIELD_PAYLOADS, SYSTEM_FIELD_MAP,
)


def register_tools(mcp: FastMCP):
    """Register collection management tools on the MCP server."""

    @mcp.tool()
    def nb_execute_sql(sql: str, db_url: Optional[str] = None) -> str:
        """Execute SQL against the NocoBase PostgreSQL database.

        Uses psql command-line tool. For bulk DDL (CREATE TABLE, ALTER TABLE),
        this is faster and more reliable than API calls.

        Args:
            sql: SQL statement(s) to execute. Multiple statements separated by semicolons.
            db_url: PostgreSQL connection URL. Default: postgresql://nocobase:nocobase@localhost:5435/nocobase

        Returns:
            psql output or error message.

        Example:
            nb_execute_sql("CREATE TABLE IF NOT EXISTS nb_pm_projects (id BIGSERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL)")
        """
        db_url = db_url or "postgresql://nocobase:nocobase@localhost:5435/nocobase"
        try:
            result = subprocess.run(
                ["psql", db_url, "-c", sql],
                capture_output=True, text=True, timeout=30,
            )
            output = result.stdout.strip()
            if result.returncode != 0:
                return f"ERROR: {result.stderr.strip()}\n{output}"
            return output or "OK (no output)"
        except FileNotFoundError:
            return "ERROR: psql not found. Install postgresql-client."
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

        # Create system fields for specific collection if requested
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

        # Global sync
        try:
            client.post("/api/mainDataSource:syncFields", expect_empty=True)
            results.append("Fields synced successfully")
        except APIError as e:
            results.append(f"Sync error: {e}")

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
