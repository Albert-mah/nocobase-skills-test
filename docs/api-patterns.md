# NocoBase FlowModel API Patterns

Key patterns discovered while building the page builder tools.

## FlowModel CRUD

### Save (Create)
```
POST /api/flowModels:save
{
    "uid": "random11chr",
    "use": "TableBlockModel",
    "parentId": "parent_uid",
    "subKey": "items",
    "subType": "array",
    "stepParams": {...},
    "sortIndex": 0,
    "flowRegistry": {}
}
```

### Update (Full Replace!)
```
GET /api/flowModels:get?filterByTk=<uid>   → get current data
POST /api/flowModels:update?filterByTk=<uid>
{
    "options": {
        "use": "...",
        "parentId": "...",
        "stepParams": {...merged...},
        "flowRegistry": {...},
        ...
    }
}
```

**CRITICAL**: The `options` wrapper is required. The update does a full replace of
all fields inside `options`. Always GET first, deep merge your changes, then PUT.

### Destroy
```
POST /api/flowModels:destroy?filterByTk=<uid>
```

## gridSettings Structure

Controls block/field layout. Used on BlockGridModel and FormGridModel.

```json
{
    "gridSettings": {
        "grid": {
            "rows": {
                "random_row_id_1": [["block_uid_1"], ["block_uid_2"]],
                "random_row_id_2": [["block_uid_3"]]
            },
            "sizes": {
                "random_row_id_1": [16, 8],
                "random_row_id_2": [24]
            }
        }
    }
}
```

- `rows`: Dict of row_id → 2D array. Each inner array is a column containing block UIDs.
- `sizes`: Dict of row_id → array of Ant Design grid spans (total per row = 24).
- Row IDs are random 11-char strings.

## filterManager

Written on BlockGridModel to connect filter forms to tables.

```
POST /api/flowModels:save
{
    "uid": "<grid_uid>",
    "filterManager": [
        {
            "filterId": "<filter_item_uid>",
            "targetId": "<table_uid>",
            "filterPaths": ["name", "code", "description"]
        }
    ]
}
```

Note: filterManager uses `flowModels:save` (flat format), not `flowModels:update` (options wrapper).

## Route API

### Create Group
```
POST /api/desktopRoutes:create
{"type": "group", "title": "...", "parentId": ..., "icon": "..."}
```

### Create Page
```
POST /api/desktopRoutes:create
{
    "type": "flowPage",
    "title": "...",
    "parentId": ...,
    "schemaUid": "<random>",
    "menuSchemaUid": "<random>",
    "icon": "...",
    "enableTabs": false,
    "children": [{"type": "tabs", "schemaUid": "<tab_uid>", "tabSchemaName": "<random>", "hidden": true}]
}
```

Also needs:
```
POST /api/uiSchemas:insert
{"type": "void", "x-component": "FlowRoute", "x-uid": "<schemaUid>"}
```

## Collection/Field API

### Register Collection
```
POST /api/collections:create
{"name": "...", "title": "...", "autoCreate": false, "timestamps": false}
```

### Sync Fields
```
POST /api/mainDataSource:syncFields
```

### Upgrade Field
```
PUT /api/fields:update?filterByTk=<field_key>
{"interface": "select", "uiSchema": {...}}
```

### Create Relation
```
POST /api/collections/<name>/fields:create
{"name": "...", "type": "belongsTo", "interface": "m2o", "target": "...", "foreignKey": "...", "uiSchema": {...}}
```
