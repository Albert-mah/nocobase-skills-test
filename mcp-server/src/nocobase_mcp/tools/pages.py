"""Page building tools — FlowModel page construction.

Extracted from nb_page_builder.py. These tools create page content:
tables, forms, filters, KPI blocks, JS blocks, popups, etc.
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..client import get_nb_client, NB
from ..utils import uid, safe_json


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
        field_list = safe_json(fields)
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
        props: Optional[dict] = None,
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
        field_props = safe_json(props) if props else None
        cp = nb.addnew_form(addnew_uid, collection, fields_dsl, props=field_props)
        return json.dumps({"childpage_uid": cp})

    @mcp.tool()
    def nb_edit_action(
        actcol_uid: str,
        collection: str,
        fields_dsl: str,
        props: Optional[dict] = None,
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
        field_props = safe_json(props) if props else None
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
        tabs = safe_json(tabs_config)
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
        fields = safe_json(search_fields)
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
        filter_: Optional[dict] = None,
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
        filter_dict = safe_json(filter_) if filter_ else None
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
        rows = safe_json(rows_spec)

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
        info = safe_json(ctx_info)
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
            model_uid: UID of the form FlowModel to attach to.
                       Must be CreateFormModel or EditFormModel UID — NOT action UIDs.
                       Get this from nb_crud_page result "create_form" or "edit_form" field.
            event_name: Event name to listen for. Common events:
                        - "formValuesChange" — form field value changes
                        - "beforeRender" — block initialization
                        - "afterSubmit" — after form submission
            code: JavaScript code. Has access to ctx.form, ctx.model, ctx.api.
                  Read values:  ctx.form?.values || {}
                  Set values:   ctx.form.setFieldsValue({field: value})
                  Query field:  ctx.form.query('field').take()
                  Current user: ctx.model?.currentUser?.nickname (NOT ctx.currentUser)
                  Always wrap in: (async () => { ... })();

        Returns:
            JSON with flow_key.

        Example:
            nb_event_flow("createFormUid", "formValuesChange",
                "(async()=>{const v=ctx.form?.values||{};if(v.qty&&v.price)ctx.form.setFieldsValue({total:v.qty*v.price});})();")
        """
        nb = get_nb_client()
        flow_key = nb.event_flow(model_uid, event_name, code)
        if flow_key:
            return json.dumps({"flow_key": flow_key})
        return "Failed to add event flow"

    @mcp.tool()
    def nb_crud_page(
        tab_uid: str,
        collection: str,
        table_fields: str,
        form_fields: str,
        filter_fields: Optional[list] = None,
        kpis_json: Optional[list] = None,
        detail_json: Optional[list] = None,
        table_title: Optional[str] = None,
        sidebar_outlines: Optional[list] = None,
    ) -> str:
        """Build a complete CRUD page in one call — layout + KPIs + filter + table + forms + popup.

        Uses tree-based builder: constructs entire page in memory, then submits
        via a single flowModels:save call (4-5 HTTP calls instead of 70-80).

        Args:
            tab_uid: Tab UID from nb_create_page or nb_create_menu
            collection: Collection name for the main table
            table_fields: JSON array of field names for table columns.
                Example: '["name","code","status","createdAt"]'
                The first field will be clickable (opens detail popup if configured).
            form_fields: Fields DSL string for AddNew and Edit forms.
                Syntax:
                  - "name" — single field, full width
                  - "name*" — required field
                  - "name | code" — two fields side by side
                  - "name:16 | code:8" — explicit column widths (total=24)
                  - "--- Section Title" — divider with label
                  - "---" — plain divider
                Example: "--- Basic Info\\nname* | code\\nstatus | priority\\n--- Details\\ndescription"
            filter_fields: Optional JSON array of field names for the filter/search bar.
                Example: '["name","status","category"]'
                If omitted, no filter bar is created.
            kpis_json: Optional JSON array of KPI card definitions.
                Each item: {"title": "Label", "filter": {"field": "value"}, "color": "#hex"}
                The "filter" and "color" keys are optional.
                Example: '[{"title":"Total"},{"title":"Active","filter":{"status":"active"},"color":"#52c41a"}]'
            detail_json: Optional JSON for detail popup (drawer/dialog on row click).
                Same format as nb_detail_popup's tabs parameter:
                  [{"title":"Tab Name", "fields":"field DSL or blocks array"},
                   {"title":"Sub Items", "assoc":"items", "coll":"child_collection", "fields":["f1","f2"]}]
                Example: '[{"title":"Details","fields":"name | code\\nstatus"},{"title":"Tasks","assoc":"tasks","coll":"nb_pm_tasks","fields":["name","status"]}]'
                **Default behavior (omitted)**: auto-generates a "详情" tab using the
                same field layout as the Edit form (form_fields DSL minus required markers).
                This gives every page a meaningful detail popup with zero extra work.
                Only specify detail_json when you need sub-table tabs, custom blocks,
                or a different layout from the edit form.
                Set to "none" to explicitly skip detail popup creation.
            table_title: Optional title text displayed above the table card.
            sidebar_outlines: Optional list of outline definitions to place in a
                sidebar column next to the table (Dashboard-style layout).
                Each item: {"title": "Name", "ctx_info": {"type": "...", ...}}
                When provided, layout changes from:
                  [Table span=24]
                to:
                  [Table span=15] [Outline blocks span=9]
                This creates a rich Dashboard-style layout. Outlines are vertically
                stacked in the sidebar. Their UIDs are returned in the result.
                Example: [{"title":"客户分布","ctx_info":{"type":"distribution","collection":"nb_crm_customers","group_by":"industry"}}]

        Returns:
            JSON with grid_uid, table_uid, create_form, edit_form, node_count.

        Example:
            nb_crud_page("tab123", "nb_crm_customers",
                '["name","code","status","industry","phone","createdAt"]',
                '--- 基本信息\\nname* | code\\ncustomer_type | industry\\nstatus | level\\n--- 联系方式\\nphone | email\\naddress',
                filter_fields='["name","status","industry"]',
                kpis_json='[{"title":"客户总数"},{"title":"已签约","filter":{"status":"已签约"},"color":"#52c41a"}]',
                sidebar_outlines=[{"title":"客户行业分布","ctx_info":{"type":"distribution","collection":"nb_crm_customers","group_by":"industry","display":"pie"}}])
        """
        from ..tree_builder import TreeBuilder

        nb = get_nb_client()

        # Parse inputs
        cols = safe_json(table_fields)
        kpis = safe_json(kpis_json) if kpis_json else None
        ff = safe_json(filter_fields) if filter_fields else None
        detail = safe_json(detail_json) if detail_json and detail_json != "none" else detail_json
        outlines = safe_json(sidebar_outlines) if sidebar_outlines else None

        # Clean existing content
        nb.clean_tab(tab_uid)

        # Build tree in memory (0 HTTP for construction, only metadata queries)
        tb = TreeBuilder(nb)
        root, meta = tb.crud_page(
            tab_uid=tab_uid,
            coll=collection,
            table_fields=cols,
            form_fields_dsl=form_fields,
            filter_fields=ff,
            kpis=kpis,
            detail_tabs=detail,
            table_title=table_title,
            sidebar_outlines=outlines,
        )

        # Save all nodes (flat individual saves to preserve subType)
        filter_manager = meta.pop("_filter_manager", None)
        nb.save_tree(root, tab_uid, filter_manager=filter_manager)

        # Build result (same format as before for backward compatibility)
        result = {
            "grid_uid": meta.get("grid_uid"),
            "table_uid": meta.get("table_uid"),
            "create_form": meta.get("create_form"),
            "edit_form": meta.get("edit_form"),
            "node_count": meta.get("node_count", 0),
        }
        if meta.get("detail_popup"):
            result["detail_popup"] = True
        if meta.get("sidebar_outline_uids"):
            result["sidebar_outline_uids"] = meta["sidebar_outline_uids"]
        if nb.warnings:
            result["warnings"] = nb.warnings

        return json.dumps(result)

    @mcp.tool()
    def nb_crud_page_file(file_path: str) -> str:
        """Build multiple CRUD pages from a JSON file — avoids tool-call parameter limits.

        Write a JSON file with an array of page definitions, then call this tool
        with the file path. Each page definition has the same parameters as
        nb_crud_page.

        Args:
            file_path: Path to a JSON file containing an array of page definitions.
                Each item: {
                    "tab_uid": "...",
                    "collection": "...",
                    "table_fields": ["name","code","status","createdAt"],
                    "form_fields": "--- Basic\\nname* | code\\nstatus",
                    "filter_fields": ["name","status"],       // optional
                    "kpis_json": [{"title":"Total"}],         // optional
                    "detail_json": [...],                     // optional
                    "table_title": "...",                     // optional
                    "sidebar_outlines": [                     // optional — Dashboard-style
                      {"title":"Status Distribution",
                       "ctx_info":{"type":"distribution","collection":"xxx","group_by":"status"}}
                    ]
                }
                Note: table_fields can be a JSON array (not a string).
                form_fields is a DSL string (use \\n for newlines).
                sidebar_outlines creates outline blocks in a sidebar column (span=9)
                next to the table (span=15), giving a Dashboard-style layout.

        Returns:
            JSON with results for each page (grid_uid, table_uid, create_form, edit_form,
            sidebar_outline_uids if sidebar_outlines was provided).

        Example file content:
            [
              {
                "tab_uid": "abc123",
                "collection": "nb_crm_customers",
                "table_fields": ["name","phone","status","industry","createdAt"],
                "form_fields": "--- 基本信息\\nname* | phone\\nindustry | status\\n--- 备注\\nremark",
                "filter_fields": ["name","status"],
                "kpis_json": [{"title":"客户总数"},{"title":"已签约","filter":{"status":"已签约"},"color":"#52c41a"}],
                "sidebar_outlines": [
                  {"title":"客户行业分布","ctx_info":{"type":"distribution","collection":"nb_crm_customers","group_by":"industry","display":"pie"}},
                  {"title":"客户等级分析","ctx_info":{"type":"distribution","collection":"nb_crm_customers","group_by":"level"}}
                ]
              },
              {
                "tab_uid": "def456",
                "collection": "nb_crm_contacts",
                "table_fields": ["name","phone","email","position","createdAt"],
                "form_fields": "name* | phone\\nemail | position\\ncustomer"
              }
            ]
        """
        import os
        if not os.path.isfile(file_path):
            return json.dumps({"error": f"File not found: {file_path}"})

        with open(file_path, "r", encoding="utf-8") as f:
            pages = json.load(f)

        if not isinstance(pages, list):
            return json.dumps({"error": "File must contain a JSON array of page definitions"})

        results = []
        for i, page in enumerate(pages):
            try:
                tab = page.get("tab_uid", "")
                coll = page.get("collection", "")
                tf = page.get("table_fields", [])
                ff = page.get("form_fields", "")
                if not tab or not coll or not tf or not ff:
                    results.append({"index": i, "error": "Missing required fields (tab_uid, collection, table_fields, form_fields)"})
                    continue

                # Normalize table_fields: accept both list and JSON string
                if isinstance(tf, list):
                    tf = json.dumps(tf)

                r = nb_crud_page(
                    tab_uid=tab,
                    collection=coll,
                    table_fields=tf,
                    form_fields=ff,
                    filter_fields=page.get("filter_fields"),
                    kpis_json=page.get("kpis_json"),
                    detail_json=page.get("detail_json"),
                    table_title=page.get("table_title"),
                    sidebar_outlines=page.get("sidebar_outlines"),
                )
                parsed = json.loads(r)
                parsed["index"] = i
                parsed["collection"] = coll
                results.append(parsed)
            except Exception as e:
                results.append({"index": i, "collection": coll, "error": str(e)})

        return json.dumps({"pages_built": len([r for r in results if "error" not in r]),
                          "pages_failed": len([r for r in results if "error" in r]),
                          "results": results})
