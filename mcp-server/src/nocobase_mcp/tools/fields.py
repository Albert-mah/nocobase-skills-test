"""Field management tools — upgrade interfaces, list fields, create relations.

Extracted from nb-setup.py.
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import (
    NocoBaseClient, APIError, get_stdlib_client,
    INTERFACE_TEMPLATES, SYSTEM_FIELD_MAP,
)
from ..utils import safe_json


def _build_field_update(field_name, target_interface, extra_config=None, existing_title=None):
    """Build the update payload for a field based on target interface."""
    tmpl = INTERFACE_TEMPLATES.get(target_interface)
    if not tmpl:
        return None

    payload = {
        "interface": target_interface,
        "uiSchema": json.loads(json.dumps(tmpl["uiSchema"])),
    }

    title_map = {
        "id": "ID", "created_at": "Created At", "updated_at": "Updated At",
        "created_by_id": "Created By", "updated_by_id": "Updated By",
    }
    auto_title = title_map.get(field_name, field_name.replace("_", " ").title())
    payload["uiSchema"]["title"] = existing_title or auto_title

    if extra_config:
        if "enum" in extra_config:
            payload["uiSchema"]["enum"] = extra_config["enum"]
        if "precision" in extra_config:
            props = payload["uiSchema"].setdefault("x-component-props", {})
            precision = extra_config["precision"]
            props["step"] = str(10 ** (-precision))
        if "title" in extra_config:
            payload["uiSchema"]["title"] = extra_config["title"]

    return payload


def register_tools(mcp: FastMCP):
    """Register field management tools on the MCP server."""

    @mcp.tool()
    def nb_upgrade_field(
        collection: str,
        field: str,
        interface: str,
        enum: Optional[list] = None,
        title: Optional[str] = None,
        precision: Optional[int] = None,
    ) -> str:
        """Upgrade a field's interface type in NocoBase.

        After syncing DB columns, fields default to 'input' interface. Use this
        to upgrade them to the correct type (select, date, number, etc.).

        IMPORTANT: The field must already exist (synced from DB). This only changes
        the interface/UI config, not the underlying column type.

        Args:
            collection: Collection name (e.g. "nb_pm_projects")
            field: Field name (e.g. "status")
            interface: Target interface. Common values:
                - input, textarea, email, phone, url, password, color, icon
                - select, multipleSelect, radioGroup, checkboxGroup, checkbox
                - number, integer, percent, sort
                - date, datetime, datetimeNoTz, time
                - markdown, richText, json
            enum: JSON array of enum options for select/multipleSelect/radioGroup.
                  Format: [{"value":"v1","label":"Label 1"},{"value":"v2","label":"Label 2"}]
            title: Display title override. If not provided, auto-generates from field name.
            precision: Decimal precision for number fields.

        Returns:
            Success or error message.

        Example:
            nb_upgrade_field("nb_pm_projects", "status", "select",
                enum='[{"value":"active","label":"Active"},{"value":"done","label":"Done"}]')
            nb_upgrade_field("nb_pm_projects", "start_date", "date")
            nb_upgrade_field("nb_pm_projects", "budget", "number", precision=2)
        """
        client = get_stdlib_client()

        # Fetch existing field
        try:
            resp = client.get(f"/api/collections/{collection}/fields:list?paginate=false")
            fields = resp.get("data", [])
        except APIError as e:
            return f"ERROR: Failed to fetch fields: {e}"

        existing = {f["name"]: f for f in fields}
        ef = existing.get(field)
        if not ef:
            return f"ERROR: Field '{field}' not found in collection '{collection}'. Run nb_sync_fields first."

        extra_config = {}
        if enum:
            try:
                extra_config["enum"] = safe_json(enum)
            except (json.JSONDecodeError, TypeError):
                return "ERROR: Invalid enum JSON. Expected format: [{\"value\":\"v\",\"label\":\"L\"}]"
        if title:
            extra_config["title"] = title
        if precision is not None:
            extra_config["precision"] = precision

        existing_title = (ef.get("uiSchema") or {}).get("title")
        payload = _build_field_update(field, interface, extra_config, existing_title)
        if not payload:
            return f"ERROR: Unknown interface '{interface}'"

        field_key = ef["key"]
        try:
            client.put(f"/api/fields:update?filterByTk={field_key}", payload)
            return f"Upgraded '{field}': {ef.get('interface', 'none')} -> {interface}"
        except APIError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def nb_list_fields(collection: str) -> str:
        """List all fields for a NocoBase collection.

        Shows field name, type, interface, and title for each field.

        Args:
            collection: Collection name (e.g. "nb_pm_projects")

        Returns:
            Formatted table of fields.
        """
        client = get_stdlib_client()
        try:
            resp = client.get(f"/api/collections/{collection}/fields:list?paginate=false")
            fields = resp.get("data", [])

            if not fields:
                return f"No fields found for '{collection}'"

            fields.sort(key=lambda f: (0 if f["name"] == "id" else 1, f["name"]))

            lines = [f"{'Field':<25} {'Type':<15} {'Interface':<15} {'Title'}"]
            lines.append(f"{'─'*25} {'─'*15} {'─'*15} {'─'*30}")
            for f in fields:
                ftitle = (f.get("uiSchema") or {}).get("title", "")
                lines.append(f"{f['name']:<25} {f.get('type',''):<15} {f.get('interface',''):<15} {ftitle}")
            lines.append(f"\nTotal: {len(fields)} fields")
            return "\n".join(lines)
        except APIError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def nb_create_relation(
        collection: str,
        field: str,
        type: str,
        target: str,
        foreign_key: str,
        label: str = "id",
        title: Optional[str] = None,
        other_key: Optional[str] = None,
        through: Optional[str] = None,
    ) -> str:
        """Create a relation field between two collections.

        Args:
            collection: Source collection name
            field: Relation field name (e.g. "project", "tasks")
            type: Relation type - one of: m2o, o2m, m2m, o2o
                - m2o (belongsTo): many records point to one target
                - o2m (hasMany): one record has many target records
                - m2m (belongsToMany): many-to-many through a join table
                - o2o (hasOne): one-to-one
            target: Target collection name
            foreign_key: Foreign key column name
            label: Target field to use as display label (default: "id")
            title: Display title for the relation field
            other_key: Other key for m2m relations
            through: Join table name for m2m relations

        Returns:
            Success or error message.

        Example:
            nb_create_relation("nb_pm_tasks", "project", "m2o", "nb_pm_projects", "project_id", label="name")
            nb_create_relation("nb_pm_projects", "tasks", "o2m", "nb_pm_tasks", "project_id")
        """
        client = get_stdlib_client()

        # Check if field already exists
        try:
            resp = client.get(f"/api/collections/{collection}/fields:list?paginate=false")
            existing_names = {f["name"] for f in resp.get("data", [])}
            if field in existing_names:
                return f"Relation '{field}' already exists in '{collection}' (skipped)"
        except APIError:
            pass

        type_map = {
            "m2o": "belongsTo", "o2m": "hasMany",
            "m2m": "belongsToMany", "o2o": "hasOne",
        }
        nb_type = type_map.get(type, type)
        display_title = title or field.replace("_", " ").title()

        payload = {
            "name": field,
            "type": nb_type,
            "interface": type,
            "target": target,
            "foreignKey": foreign_key,
            "uiSchema": {
                "x-component": "AssociationField",
                "x-component-props": {
                    "fieldNames": {"label": label, "value": "id"},
                },
                "title": display_title,
            },
        }

        if nb_type == "belongsToMany":
            if other_key:
                payload["otherKey"] = other_key
            if through:
                payload["through"] = through

        try:
            client.post(f"/api/collections/{collection}/fields:create", payload)
            return f"Created relation '{field}' ({type} -> {target}) on '{collection}'"
        except APIError as e:
            return f"ERROR: {e}"
