"""Page building tools — FlowModel page construction.

Extracted from nb_page_builder.py. These tools create page content:
tables, forms, filters, KPI blocks, JS blocks, popups, etc.
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import get_nb_client, NB
from ..utils import uid


def register_tools(mcp: FastMCP):
    """Register page building tools on the MCP server."""

    @mcp.tool()
    def nb_page_layout(tab_uid: str) -> str:
        """Create a BlockGridModel for a page tab, preparing it for content.

        Automatically cleans any existing content under the tab first (idempotent).
        Returns the grid UID that you pass to other page building tools.

        Args:
            tab_uid: Tab UID from nb_create_page or nb_create_menu

        Returns:
            JSON with grid_uid.

        Example:
            nb_page_layout("abc123def45")
        """
        nb = get_nb_client()
        grid = nb.page_layout(tab_uid)
        return json.dumps({"grid_uid": grid})

    @mcp.tool()
    def nb_table_block(
        parent: str,
        collection: str,
        fields: str,
        first_click: bool = True,
        title: Optional[str] = None,
    ) -> str:
        """Create a table block on a page.

        Creates a TableBlockModel with columns, AddNew button, Edit action,
        Filter action, and Refresh action.

        Args:
            parent: Parent grid UID (from nb_page_layout)
            collection: Collection name to display
            fields: JSON array of field names for table columns.
                    Example: '["name","code","status","createdAt"]'
            first_click: If true, first column is click-to-open (opens detail popup)
            title: Optional card title above the table

        Returns:
            JSON with table_uid, addnew_uid, actcol_uid.

        Example:
            nb_table_block("grid123", "nb_pm_projects", '["name","status","createdAt"]', title="Projects")
        """
        nb = get_nb_client()
        field_list = json.loads(fields)
        tbl, addnew, actcol = nb.table_block(parent, collection, field_list,
                                              first_click=first_click, title=title)
        return json.dumps({
            "table_uid": tbl,
            "addnew_uid": addnew,
            "actcol_uid": actcol,
        })

    @mcp.tool()
    def nb_addnew_form(
        addnew_uid: str,
        collection: str,
        fields_dsl: str,
        props: Optional[str] = None,
    ) -> str:
        """Create a form for the AddNew popup of a table.

        Supports pipe DSL for multi-column layout and field options.

        Args:
            addnew_uid: AddNew action UID (from nb_table_block)
            collection: Collection name
            fields_dsl: Field layout DSL (multi-line string). Supports:
                - Simple field: "name"
                - Required field: "name*"
                - Multi-column row (pipe syntax): "name* | code"
                - Divider with label: "--- Basic Info"
                - Width control: "name:16 | code:8"
                Example:
                    "--- Basic Info\\nname* | code\\nstatus | priority\\n--- Details\\ndescription"
            props: Optional JSON object mapping field names to property overrides.
                   Example: '{"name":{"description":"Full name"},"status":{"defaultValue":"active"}}'

        Returns:
            JSON with childpage_uid.

        Example:
            nb_addnew_form("addnew123", "nb_pm_projects", "--- Info\\nname* | code\\nstatus\\n--- Notes\\ndescription")
        """
        nb = get_nb_client()
        field_props = json.loads(props) if props else None
        cp = nb.addnew_form(addnew_uid, collection, fields_dsl, props=field_props)
        return json.dumps({"childpage_uid": cp})

    @mcp.tool()
    def nb_edit_action(
        actcol_uid: str,
        collection: str,
        fields_dsl: str,
        props: Optional[str] = None,
    ) -> str:
        """Create an Edit action with form in the table actions column.

        Args:
            actcol_uid: Actions column UID (from nb_table_block)
            collection: Collection name
            fields_dsl: Field layout DSL (same format as nb_addnew_form)
            props: Optional JSON field property overrides

        Returns:
            JSON with edit_action_uid.

        Example:
            nb_edit_action("actcol123", "nb_pm_projects", "name* | code\\nstatus\\ndescription")
        """
        nb = get_nb_client()
        field_props = json.loads(props) if props else None
        ea = nb.edit_action(actcol_uid, collection, fields_dsl, props=field_props)
        return json.dumps({"edit_action_uid": ea})

    @mcp.tool()
    def nb_detail_popup(
        parent_uid: str,
        collection: str,
        tabs_config: str,
        mode: str = "drawer",
        size: str = "large",
    ) -> str:
        """Create a multi-tab detail popup for a table row.

        Typically attached to the first click-to-open column of a table.
        Supports details blocks, JS blocks, sub-tables, and forms per tab.

        Args:
            parent_uid: Display field UID of the click-to-open column.
                        Get this from nb_find_click_field or from table creation.
            collection: Main collection name
            tabs_config: JSON array of tab configurations. Each tab:
                - Details tab: {"title":"Info", "fields":"name | code\\nstatus"}
                - Multi-block tab: {"title":"Overview", "blocks":[
                    {"type":"details", "fields":"name | code"},
                    {"type":"js", "title":"Stats", "code":"ctx.render(...)"}
                  ], "sizes":[16,8]}
                - Sub-table tab: {"title":"Tasks", "assoc":"tasks", "coll":"nb_pm_tasks",
                    "fields":["name","status"]}
            mode: Popup mode - "drawer" (side panel) or "dialog" (modal)
            size: Popup size - "small", "medium", "large"

        Returns:
            JSON with childpage_uid.

        Example:
            nb_detail_popup("field123", "nb_pm_projects",
                '[{"title":"Info","fields":"name | code\\nstatus"},{"title":"Tasks","assoc":"tasks","coll":"nb_pm_tasks","fields":["name","status"]}]')
        """
        nb = get_nb_client()
        tabs = json.loads(tabs_config)
        cp = nb.detail_popup(parent_uid, collection, tabs, mode=mode, size=size)
        return json.dumps({"childpage_uid": cp})

    @mcp.tool()
    def nb_filter_form(
        parent: str,
        collection: str,
        search_fields: str,
        target_uid: Optional[str] = None,
        label: str = "Search",
    ) -> str:
        """Create a search/filter form block for a table.

        Creates a single search input that filters the target table across
        multiple fields.

        Args:
            parent: Parent grid UID
            collection: Collection name
            search_fields: JSON array of field paths to search.
                           Example: '["name","code","description"]'
            target_uid: UID of the TableBlockModel to filter.
                        If provided, the filter is automatically connected.
            label: Label text for the search input (default: "Search")

        Returns:
            JSON with filter_block_uid, filter_item_uid.

        Example:
            nb_filter_form("grid123", "nb_pm_projects", '["name","code"]', target_uid="tbl123")
        """
        nb = get_nb_client()
        fields = json.loads(search_fields)
        field = fields[0] if fields else "name"
        fb, fi = nb.filter_form(parent, collection, field,
                                target_uid=target_uid, label=label,
                                search_fields=fields)
        return json.dumps({"filter_block_uid": fb, "filter_item_uid": fi})

    @mcp.tool()
    def nb_kpi_block(
        parent: str,
        title: str,
        collection: str,
        filter_: Optional[str] = None,
        color: Optional[str] = None,
    ) -> str:
        """Create a KPI card that shows a count from a collection.

        Uses a JS block that queries the API and renders an Ant Design Statistic.

        Args:
            parent: Parent grid UID
            title: KPI card title (e.g. "Total", "Active", "Overdue")
            collection: Collection name to count
            filter_: Optional JSON filter object (e.g. '{"status":"active"}')
            color: Optional value color (e.g. "#1890ff", "#52c41a")

        Returns:
            JSON with kpi_uid.

        Example:
            nb_kpi_block("grid123", "Active", "nb_pm_projects", filter_='{"status":"active"}', color="#52c41a")
        """
        nb = get_nb_client()
        filter_dict = json.loads(filter_) if filter_ else None
        kpi_uid = nb.kpi(parent, title, collection, filter_=filter_dict, color=color)
        return json.dumps({"kpi_uid": kpi_uid})

    @mcp.tool()
    def nb_js_block(parent: str, title: str, code: str) -> str:
        """Create a JavaScript block on a page.

        JS blocks run custom React code with access to ctx.React, ctx.antd,
        ctx.api, ctx.record, and ctx.render().

        Args:
            parent: Parent grid UID
            title: Block card title
            code: JavaScript code. Must call ctx.render() to display content.
                  Available context:
                  - ctx.React — React library
                  - ctx.antd — Ant Design components
                  - ctx.api — NocoBase API client
                  - ctx.record — Current record (in popups)
                  - ctx.render(element) — Render a React element

        Returns:
            JSON with js_block_uid.

        Example:
            nb_js_block("grid123", "Welcome", "ctx.render(ctx.React.createElement('h1', null, 'Hello!'))")
        """
        nb = get_nb_client()
        js_uid = nb.js_block(parent, title, code)
        return json.dumps({"js_block_uid": js_uid})

    @mcp.tool()
    def nb_js_column(
        table_uid: str,
        title: str,
        code: str,
        width: Optional[int] = None,
    ) -> str:
        """Create a custom JavaScript column in a table.

        JS columns render custom content per row using ctx.record.

        Args:
            table_uid: Table block UID
            title: Column header title
            code: JavaScript code. Available context:
                  - ctx.record — Current row data
                  - ctx.React, ctx.antd — React and Ant Design
                  - ctx.render(element) — Render the cell content
            width: Optional fixed column width in pixels

        Returns:
            JSON with column_uid.

        Example:
            nb_js_column("tbl123", "Status", "const s=(ctx.record||{}).status;ctx.render(ctx.React.createElement(ctx.antd.Tag,{color:s==='active'?'green':'red'},s||'-'))", width=100)
        """
        nb = get_nb_client()
        col_uid = nb.js_column(table_uid, title, code, width=width)
        return json.dumps({"column_uid": col_uid})

    @mcp.tool()
    def nb_set_layout(grid_uid: str, rows_spec: str) -> str:
        """Set the grid layout for a BlockGridModel (arrange blocks on the page).

        Controls how blocks are arranged in rows and columns.

        Args:
            grid_uid: BlockGridModel UID (from nb_page_layout)
            rows_spec: JSON array of row specifications. Each row is:
                - Full width: ["block_uid"]  or [["block_uid"]]
                - Multi-column: [["uid1", 16], ["uid2", 8]]
                  (sizes are Ant Design grid spans, total = 24)
                Example: '[["kpi1",6],["kpi2",6],["kpi3",6],["kpi4",6]]'
                         would create one row with 4 equal KPI cards.

                Full example:
                '[
                  [["kpi1",6],["kpi2",6],["kpi3",6],["kpi4",6]],
                  [["filter1"]],
                  [["table1"]]
                ]'

        Returns:
            Success message.

        Example:
            nb_set_layout("grid123", '[[["kpi1",6],["kpi2",6]],[["filter1"]],[["table1"]]]')
        """
        nb = get_nb_client()
        rows = json.loads(rows_spec)

        # Convert JSON rows_spec to the format expected by set_layout:
        # Each row is either (uid,) for full-width or [(uid, size), ...] for multi-col
        converted = []
        for row in rows:
            if not row:
                continue
            # Check if this is a simple full-width row: ["uid"] or [["uid"]]
            if len(row) == 1:
                item = row[0]
                if isinstance(item, list):
                    converted.append((item[0],))
                else:
                    converted.append((item,))
            else:
                # Multi-column row: [["uid1", 16], ["uid2", 8]]
                cols = []
                for item in row:
                    if isinstance(item, list):
                        cols.append((item[0], item[1] if len(item) > 1 else 24))
                    else:
                        cols.append((item, 24))
                converted.append(cols)

        nb.set_layout(grid_uid, converted)
        return "Layout updated successfully"

    @mcp.tool()
    def nb_clean_tab(tab_uid: str) -> str:
        """Delete all FlowModel content under a tab (idempotent cleanup).

        Removes all blocks, fields, and actions under the tab while keeping
        the tab route itself. Use before rebuilding a page.

        Args:
            tab_uid: Tab UID to clean

        Returns:
            Number of nodes deleted.
        """
        nb = get_nb_client()
        count = nb.clean_tab(tab_uid)
        return f"Cleaned {count} nodes under tab {tab_uid}"

    @mcp.tool()
    def nb_outline(
        parent: str,
        title: str,
        ctx_info: str,
        kind: str = "block",
    ) -> str:
        """Create a planning outline block/column/item on a page.

        Outlines are styled context cards that show planning information
        (type, collection, fields, description, etc.) for later implementation
        by a dedicated JS agent. The block's own UID is auto-injected.

        Use this during page building to plan JS capabilities without
        implementing the actual code.

        Args:
            parent: Parent UID (grid for block, table for column, form grid for item)
            title: Display title for the outline
            ctx_info: JSON object with context info. Common keys:
                      type, collection, filter, target_uid, description,
                      fields, api, event, formula — any key/value works.
                      Example: '{"type":"kpi","collection":"assets","filter":{"status":"active"}}'
            kind: "block" (JSBlockModel, default) | "column" (JSColumnModel) | "item" (JSItemModel)

        Returns:
            JSON with outline_uid.

        Examples:
            # KPI outline
            nb_outline("grid123", "Active Assets",
                '{"type":"kpi","collection":"nb_am_assets","filter":{"status":"active"},"render":"antd.Statistic"}')

            # Table JS column outline
            nb_outline("tbl123", "Status",
                '{"type":"status-tag","field":"status","colors":{"active":"green","inactive":"red"}}',
                kind="column")

            # Event flow outline in form
            nb_outline("formgrid123", "Auto Calculate Total",
                '{"type":"event-flow","event":"formValuesChange","trigger_fields":["qty","price"],"formula":"qty*price"}',
                kind="item")
        """
        nb = get_nb_client()
        info = json.loads(ctx_info)
        outline_uid = nb.outline(parent, title, info, kind=kind)
        return json.dumps({"outline_uid": outline_uid})

    @mcp.tool()
    def nb_event_flow(
        model_uid: str,
        event_name: str,
        code: str,
    ) -> str:
        """Add an event flow (runjs step) to an existing FlowModel node.

        Event flows run JavaScript code in response to UI events on a block.

        Args:
            model_uid: UID of the FlowModel to attach the event flow to
                       (e.g., CreateFormModel, EditFormModel, TableBlockModel)
            event_name: Event name to listen for. Common events:
                        - "formValuesChange" — form field value changes
                        - "beforeRender" — block initialization
                        - "afterSubmit" — after form submission
            code: JavaScript code to execute. Has access to ctx.form, ctx.model,
                  ctx.api, ctx.record, etc.

        Returns:
            JSON with flow_key.

        Example:
            nb_event_flow("form123", "formValuesChange",
                "const v = ctx.form?.values || {}; if (v.qty && v.price) ctx.form.setFieldsValue({total: v.qty * v.price});")
        """
        nb = get_nb_client()
        flow_key = nb.event_flow(model_uid, event_name, code)
        if flow_key:
            return json.dumps({"flow_key": flow_key})
        return "Failed to add event flow"
