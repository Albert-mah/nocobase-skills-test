"""Route/menu management tools — create groups, pages, menus, list/delete routes.

Extracted from nb_page_builder.py (group, route, menu methods).
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import get_nb_client, NB, APIError
from ..utils import uid, safe_json


def register_tools(mcp: FastMCP):
    """Register route management tools on the MCP server."""

    @mcp.tool()
    def nb_create_group(title: str, icon: str = "appstoreoutlined",
                        parent_id: Optional[int] = None) -> str:
        """Create a menu group (folder) in the NocoBase sidebar.

        Groups are purely structural — they hold child pages or sub-groups,
        but have NO page content themselves. Created at top level by default.

        Args:
            title: Display name for the menu group
            icon: Ant Design icon name (e.g. "homeoutlined", "settingoutlined")
            parent_id: Parent group route ID. Default None = top-level.
                       Only set this to create a sub-group under an existing group.

        Returns:
            JSON with group route ID.

        Example:
            nb_create_group("Asset Management", "bankoutlined")
        """
        nb = get_nb_client()
        gid = nb.group(title, parent_id, icon=icon)
        return json.dumps({"group_id": gid, "title": title})

    @mcp.tool()
    def nb_create_page(title: str, parent_id: int,
                       icon: str = "appstoreoutlined",
                       tabs: Optional[list] = None) -> str:
        """Create a page (flowPage) route in the NocoBase sidebar.

        Pages hold actual content (tables, forms, charts, etc.).
        Must be created under a group (from nb_create_group).

        Args:
            title: Page display name
            parent_id: Parent group/page route ID
            icon: Ant Design icon name
            tabs: JSON array of tab names for multi-tab pages.
                  Example: '["Overview", "Details"]'
                  If not provided, creates a single-tab page (tab is hidden).

        Returns:
            JSON with route_id, page_uid, and tab UIDs.

        Example:
            nb_create_page("Asset Ledger", 123, icon="databaseoutlined")
            nb_create_page("Settings", 123, tabs='["Categories", "Types"]')
        """
        nb = get_nb_client()
        tab_list = safe_json(tabs) if tabs else None
        rid, pu, tu = nb.route(title, parent_id, icon=icon, tabs=tab_list)
        return json.dumps({"route_id": rid, "page_uid": pu, "tab_uids": tu})

    @mcp.tool()
    def nb_create_menu(group_title: str,
                       pages: str,
                       group_icon: str = "appstoreoutlined",
                       parent_id: Optional[int] = None) -> str:
        """Create a top-level menu group with child pages in one call.

        Creates a top-level sidebar group with pages directly under it.
        Each page gets a tab UID for adding content via nb_crud_page.

        Args:
            group_title: Display name for the menu group
            pages: JSON array of [title, icon] pairs.
                   Example: '[["Asset Ledger","databaseoutlined"],["Purchases","shoppingcartoutlined"]]'
            group_icon: Icon for the group folder
            parent_id: Parent group route ID. Default None = top-level menu.
                       Only set this when creating a sub-group under an existing group.

        Returns:
            JSON mapping page titles to their tab UIDs.

        Example:
            nb_create_menu("CRM", '[["Customers","idcardoutlined"],["Contacts","useroutlined"]]', "teamoutlined")
        """
        nb = get_nb_client()
        page_list = safe_json(pages)
        pid = parent_id if parent_id else None
        tabs = nb.menu(group_title, pid, page_list, group_icon=group_icon)
        return json.dumps(tabs)

    @mcp.tool()
    def nb_list_routes() -> str:
        """List all desktop routes (menu structure) in NocoBase.

        Returns a tree of groups, pages, and tabs showing the sidebar structure.
        """
        nb = get_nb_client()
        routes = nb._get_json("api/desktopRoutes:list?paginate=false&tree=true") or []

        lines = []
        _format_route_tree(routes, lines, 0)
        if not lines:
            return "No routes found"
        return "\n".join(lines)

    @mcp.tool()
    def nb_delete_route(route_id: int) -> str:
        """Delete a desktop route (menu item or page) and its children.

        Args:
            route_id: Route ID to delete (from nb_list_routes or nb_create_page)

        Returns:
            Success or error message.
        """
        nb = get_nb_client()
        try:
            nb._post_json(f"api/desktopRoutes:destroy?filterByTk={route_id}")
            return f"Deleted route {route_id}"
        except APIError as e:
            return f"ERROR: {e}"


def _format_route_tree(routes, lines, depth):
    """Recursively format route tree for display."""
    for rt in routes:
        indent = "  " * depth
        rtype = rt.get("type", "?")
        title = rt.get("title") or "(untitled)"
        rid = rt.get("id", "?")
        schema_uid = rt.get("schemaUid", "")

        type_icon = {"group": "📁", "flowPage": "📄", "tabs": "📑"}.get(rtype, "  ")
        uid_info = f" uid={schema_uid}" if schema_uid else ""
        lines.append(f"{indent}{type_icon} [{rid}] {title} ({rtype}){uid_info}")

        children = rt.get("children", [])
        if children:
            _format_route_tree(children, lines, depth + 1)
