# NocoBase JS Sandbox Reference

NocoBase runs custom JavaScript in a sandboxed environment. All JS code for blocks, columns, and event flows execute inside this sandbox with a `ctx` object providing access to React, Ant Design, API, and form controls.

## ctx Object — Available in ALL JS contexts

| Property | Type | Description |
|----------|------|-------------|
| `ctx.React` | React library | Full React (createElement, useState, useEffect, etc.) |
| `ctx.antd` | Ant Design 5 | All components: Tag, Badge, Progress, Statistic, Card, Row, Col, Button, Space, Divider, Tooltip, etc. |
| `ctx.api` | API client | NocoBase API: `ctx.api.request({url, params, method, data})` |
| `ctx.render(element)` | Function | **Must call** to display content. Pass a React element. |
| `ctx.record` | Object | Current row data (in table columns and detail popups) |
| `ctx.themeToken` | Object | Ant Design theme tokens (colorPrimary, colorSuccess, etc.) |

## JS Column (nb_js_column)

Renders custom content for each table row. Code runs per-row.

### Pattern: Status Tag

```javascript
const s = (ctx.record || {}).status;
const colors = {
  '使用中': 'green', '闲置': 'blue',
  '维修中': 'orange', '已报废': 'red'
};
ctx.render(
  ctx.React.createElement(ctx.antd.Tag,
    { color: colors[s] || 'default' },
    s || '-'
  )
);
```

### Pattern: Priority Badge (P1 with pulse dot)

```javascript
const p = (ctx.record || {}).priority;
const map = { P1: 'red', P2: 'orange', P3: 'blue', P4: 'default' };
const h = ctx.React.createElement;
const els = [];
if (p === 'P1') {
  els.push(h('span', {
    key: 'dot',
    style: {
      display: 'inline-block', width: 8, height: 8,
      borderRadius: '50%', background: '#ff4d4f', marginRight: 6,
      animation: 'pulse 1.5s infinite',
      boxShadow: '0 0 0 0 rgba(255,77,79,0.6)'
    }
  }));
}
els.push(h(ctx.antd.Tag, { key: 'tag', color: map[p] || 'default' }, p || '-'));
ctx.render(h('span', null, ...els));
```

### Pattern: Money Formatting (¥)

```javascript
const val = (ctx.record || {}).purchase_price;
if (val == null) { ctx.render('-'); return; }
const formatted = Number(val).toLocaleString('zh-CN', {
  minimumFractionDigits: 2, maximumFractionDigits: 2
});
ctx.render(
  ctx.React.createElement('span',
    { style: { color: val > 10000 ? '#cf1322' : '#333', fontFamily: 'monospace' } },
    '¥' + formatted
  )
);
```

### Pattern: Date Countdown

```javascript
const d = (ctx.record || {}).warranty_date;
if (!d) { ctx.render('-'); return; }
const days = Math.ceil((new Date(d) - new Date()) / 86400000);
const color = days < 0 ? '#cf1322' : days < 30 ? '#fa8c16' : '#52c41a';
const text = days < 0
  ? '\u5df2\u8fc7\u671f' + (-days) + '\u5929'
  : '\u8fd8\u5269' + days + '\u5929';
ctx.render(
  ctx.React.createElement('span',
    { style: { color, fontWeight: days < 30 ? 600 : 400 } },
    text
  )
);
```

### Pattern: Progress Bar (Usage Rate)

```javascript
const used = (ctx.record || {}).used_licenses || 0;
const total = (ctx.record || {}).total_licenses || 1;
const pct = Math.round(used / total * 100);
const h = ctx.React.createElement;
ctx.render(
  h('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
    h(ctx.antd.Progress, {
      percent: pct, size: 'small', strokeColor: pct > 95 ? '#ff4d4f' : pct > 80 ? '#faad14' : '#52c41a',
      format: function() { return used + '/' + total; }
    })
  )
);
```

### Pattern: Relative Time

```javascript
const t = (ctx.record || {}).createdAt;
if (!t) { ctx.render('-'); return; }
const diff = (Date.now() - new Date(t).getTime()) / 1000;
var text, warn = false;
if (diff < 60) text = '\u521a\u521a';
else if (diff < 3600) text = Math.floor(diff/60) + '\u5206\u949f\u524d';
else if (diff < 86400) text = Math.floor(diff/3600) + '\u5c0f\u65f6\u524d';
else { text = Math.floor(diff/86400) + '\u5929\u524d'; warn = true; }
ctx.render(
  ctx.React.createElement('span',
    { style: { color: warn ? '#fa8c16' : '#666', fontSize: 13 } },
    text
  )
);
```

### Pattern: Boolean Check/Cross Icon

```javascript
const val = (ctx.record || {}).sla_breach;
ctx.render(
  ctx.React.createElement('span',
    { style: { color: val ? '#ff4d4f' : '#52c41a', fontSize: 16 } },
    val ? '\u26a0\ufe0f' : '\u2705'
  )
);
```

## JS Block (nb_js_block)

Renders a custom block on the page (charts, dashboards, KPI groups).

### Pattern: KPI Statistic Card (with API query)

```javascript
(async () => {
  try {
    const r = await ctx.api.request({
      url: 'nb_itsm_assets:list',
      params: { paginate: false, filter: { status: '使用中' } }
    });
    const count = Array.isArray(r?.data?.data) ? r.data.data.length : 0;
    ctx.render(ctx.React.createElement(ctx.antd.Statistic, {
      title: '使用中资产', value: count,
      valueStyle: { fontSize: 28, color: '#52c41a' }
    }));
  } catch(e) {
    ctx.render(ctx.React.createElement(ctx.antd.Statistic, {
      title: '使用中资产', value: '?', valueStyle: { fontSize: 28 }
    }));
  }
})();
```

### Pattern: Multi-KPI Row

```javascript
(async () => {
  const h = ctx.React.createElement;
  const { Row, Col, Card, Statistic } = ctx.antd;
  const queries = [
    { title: '总数', url: 'nb_itsm_assets:list', filter: {} },
    { title: '使用中', url: 'nb_itsm_assets:list', filter: {status: '使用中'}, color: '#52c41a' },
    { title: '闲置', url: 'nb_itsm_assets:list', filter: {status: '闲置'}, color: '#1890ff' },
  ];
  const counts = await Promise.all(queries.map(async (q) => {
    try {
      const r = await ctx.api.request({ url: q.url, params: { paginate: false, filter: q.filter } });
      return Array.isArray(r?.data?.data) ? r.data.data.length : 0;
    } catch(e) { return '?'; }
  }));
  ctx.render(h(Row, { gutter: 16 },
    queries.map((q, i) => h(Col, { span: 8, key: i },
      h(Card, { size: 'small' },
        h(Statistic, { title: q.title, value: counts[i], valueStyle: { color: q.color || '#333' } })
      )
    ))
  ));
})();
```

## Event Flow (nb_event_flow)

Attaches JS logic to form events.

### Available Events

| Event | When | Common Use |
|-------|------|------------|
| `formValuesChange` | Any form field changes | Auto-calculate, cross-field logic |
| `beforeRender` | Form opens (before display) | Auto-fill defaults (current user, today) |
| `afterSubmit` | After form submit succeeds | Show message, redirect |

### ctx in Event Flows

| Property | Type | Description |
|----------|------|-------------|
| `ctx.form` | Formily Form | `ctx.form.values` = all field values |
| `ctx.form.query('fieldName').take()` | Field | Get a specific field instance |
| `ctx.form.setValuesIn('field', value)` | Function | Set a field value |
| `ctx.model` | Model | `ctx.model.currentUser` = logged-in user info |
| `ctx.model.currentUser.nickname` | String | Current user's display name |
| `ctx.api` | API client | Same as block/column ctx.api |

### Pattern: Auto-fill Current User (beforeRender)

```javascript
(async () => {
  const field = ctx.form.query('reporter').take();
  if (field && !field.value) {
    const nick = ctx.model?.currentUser?.nickname || '';
    ctx.form.setValuesIn('reporter', nick);
  }
})();
```

### Pattern: Auto-calculate Total (formValuesChange)

```javascript
(async () => {
  const vals = ctx.form?.values || {};
  const qty = Number(vals.quantity) || 0;
  const price = Number(vals.unit_price) || 0;
  if (qty > 0 && price > 0) {
    ctx.form.setValuesIn('total_price', qty * price);
  }
})();
```

### Pattern: Priority Matrix (formValuesChange)

```javascript
(async () => {
  const vals = ctx.form?.values || {};
  const impact = vals.impact;
  const urgency = vals.urgency;
  if (!impact || !urgency) return;
  const high = ['紧急', '高'];
  var priority;
  if (high.includes(impact) && high.includes(urgency)) priority = 'P1';
  else if (high.includes(impact) || high.includes(urgency)) priority = 'P2';
  else if (impact === '中' || urgency === '中') priority = 'P3';
  else priority = 'P4';
  ctx.form.setValuesIn('priority', priority);
})();
```

### Pattern: Auto-fill Today's Date (beforeRender)

```javascript
(async () => {
  const field = ctx.form.query('apply_date').take();
  if (field && !field.value) {
    ctx.form.setValuesIn('apply_date', new Date().toISOString().slice(0, 10));
  }
})();
```

## L4 Patterns — Charts, Complex Events, Detail Enhancements

### Pattern: Status Distribution Chart (antd Progress bars)

No ECharts available in sandbox. Use antd Progress + API aggregation for chart-like visualization.

```javascript
(async () => {
  const h = ctx.React.createElement;
  const { Statistic, Progress } = ctx.antd;

  try {
    const r = await ctx.api.request({
      url: 'nb_am_assets:list',
      params: { paginate: false, fields: ['status'] }
    });
    const items = Array.isArray(r?.data?.data) ? r.data.data : [];

    // Count by field
    const counts = {};
    items.forEach(item => {
      const s = item.status || '未知';
      counts[s] = (counts[s] || 0) + 1;
    });
    const total = items.length;

    const cfg = {
      '在用':   { color: '#52c41a', icon: '✅' },
      '闲置':   { color: '#1890ff', icon: '📦' },
      '维修中': { color: '#faad14', icon: '🔧' },
      '已报废': { color: '#ff4d4f', icon: '🗑️' },
    };

    const entries = Object.entries(counts).sort((a,b) => b[1] - a[1]);

    ctx.render(
      h('div', null,
        h(Statistic, { title: '资产总数', value: total, valueStyle: { fontSize: 32, fontWeight: 700 } }),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 } },
          ...entries.map(([status, count], i) => {
            const pct = total > 0 ? Math.round(count / total * 100) : 0;
            const c = cfg[status] || { color: '#999', icon: '📋' };
            return h('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 8 } },
              h('span', { style: { width: 24, textAlign: 'center' } }, c.icon),
              h('span', { style: { width: 60, fontSize: 13, color: '#666' } }, status),
              h(Progress, {
                percent: pct, strokeColor: c.color, size: 'small', style: { flex: 1 },
                format: function() { return count + ' (' + pct + '%)'; }
              })
            );
          })
        )
      )
    );
  } catch(e) {
    ctx.render(h('div', { style: { color: '#ff4d4f' } }, '加载失败: ' + (e.message || e)));
  }
})();
```

### Pattern: Department Value Bar Chart (antd, with relation appends)

Aggregates numeric field by a related entity using `appends` parameter.

```javascript
(async () => {
  const h = ctx.React.createElement;
  const { Typography } = ctx.antd;

  try {
    const r = await ctx.api.request({
      url: 'nb_am_assets:list',
      params: { paginate: false, appends: ['department'], fields: ['purchase_price', 'department_id'] }
    });
    const items = Array.isArray(r?.data?.data) ? r.data.data : [];

    // Aggregate by department
    const deptValues = {};
    const deptCounts = {};
    items.forEach(item => {
      const dept = (item.department && item.department.name) || '未分配';
      const price = Number(item.purchase_price) || 0;
      deptValues[dept] = (deptValues[dept] || 0) + price;
      deptCounts[dept] = (deptCounts[dept] || 0) + 1;
    });

    const entries = Object.entries(deptValues).sort((a,b) => b[1] - a[1]);
    const maxVal = Math.max(...entries.map(e => e[1]), 1);
    const fmt = (v) => v >= 10000 ? (v / 10000).toFixed(1) + '万' : Number(v).toLocaleString('zh-CN');
    const colors = ['#1890ff', '#13c2c2', '#52c41a', '#faad14', '#f5222d', '#722ed1'];

    ctx.render(
      h('div', null,
        h(Typography.Text, { type: 'secondary', style: { fontSize: 12, marginBottom: 12, display: 'block' } },
          '按部门汇总资产价值 (¥)'),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 10 } },
          ...entries.map(([dept, val], i) => {
            const pct = Math.round(val / maxVal * 100);
            return h('div', { key: i },
              h('div', { style: { display: 'flex', justifyContent: 'space-between', marginBottom: 2 } },
                h('span', { style: { fontSize: 13, fontWeight: 500 } }, dept),
                h('span', { style: { fontSize: 13, color: '#666' } },
                  '¥' + fmt(val) + ' (' + (deptCounts[dept] || 0) + '件)')
              ),
              h('div', { style: { height: 16, background: '#f0f0f0', borderRadius: 4, overflow: 'hidden' } },
                h('div', { style: {
                  width: pct + '%', height: '100%',
                  background: colors[i % colors.length], borderRadius: 4
                } })
              )
            );
          })
        )
      )
    );
  } catch(e) {
    ctx.render(h('div', { style: { color: '#ff4d4f' } }, '加载失败: ' + (e.message || e)));
  }
})();
```

### Pattern: Cascade Field Exploration (formValuesChange)

When a select field changes, query related data and log available field methods.
Use this to discover whether `setDataSource()` or `setComponentProps()` is available.

```javascript
(async () => {
  const vals = ctx.form?.values || {};
  const catId = vals.category_id;
  if (!catId) return;

  const supplierField = ctx.form.query('supplier_id').take();
  if (!supplierField) return;

  // Query related data via API
  try {
    const r = await ctx.api.request({
      url: 'nb_am_suppliers:list',
      params: { paginate: false }
    });
    const suppliers = Array.isArray(r?.data?.data) ? r.data.data : [];
    console.log('[Cascade] suppliers found:', suppliers.length);

    // Check available field methods for dataSource manipulation
    console.log('[Cascade] setDataSource:', typeof supplierField.setDataSource);
    console.log('[Cascade] componentProps:', !!supplierField.componentProps);
    console.log('[Cascade] methods:',
      Object.keys(supplierField).filter(k => typeof supplierField[k] === 'function').join(', '));
  } catch(e) {
    console.log('[Cascade] error:', e.message);
  }
})();
```

### Pattern: Conditional Required Field (formValuesChange)

Make a field required/optional based on another field's value.

```javascript
(async () => {
  const vals = ctx.form?.values || {};
  const urgency = vals.urgency;

  const noteField = ctx.form.query('approval_note').take();
  if (!noteField) return;

  const isUrgent = urgency === '紧急';

  // Formily field — try setRequired first, fallback to direct property
  if (typeof noteField.setRequired === 'function') {
    noteField.setRequired(isUrgent);
  } else {
    try { noteField.required = isUrgent; } catch(e) {}
  }
})();
```

### Pattern: Cross-field Date Validation (formValuesChange)

Validate that end date is after start date.

```javascript
(async () => {
  const vals = ctx.form?.values || {};
  const start = vals.start_date;
  const end = vals.end_date;

  if (start && end) {
    const s = new Date(start);
    const e = new Date(end);
    if (e < s) {
      ctx.message?.warning('结束日期不能早于开始日期');
      // Optionally clear the invalid field:
      // ctx.form.setValuesIn('end_date', null);
    }
  }
})();
```

### Pattern: Status Lifecycle Progress (JSItemModel in Detail Popup)

Shows the current position in a lifecycle using a progress bar.
Uses `ctx.record` which is available in detail popup JSItem.

```javascript
(async () => {
  const h = ctx.React.createElement;
  const { Card, Tag, Typography, Statistic, Progress } = ctx.antd;
  const r = ctx.record || {};

  const currentStatus = r.status || '';

  // Lifecycle stages and their colors
  const statusColors = {
    '在用': '#52c41a', '在库': '#1890ff', '闲置': '#faad14',
    '维修中': '#ff7a45', '报废中': '#ff4d4f', '已报废': '#999'
  };

  // Progress bar segments
  const stages = ['采购', '入库', '在用', '报废'];
  const statusOrder = { '采购中': 0, '在库': 1, '在用': 2, '闲置': 2, '维修中': 2, '报废中': 3, '已报废': 3 };
  const currentStep = statusOrder[currentStatus] !== undefined ? statusOrder[currentStatus] : -1;

  // Depreciation calculation
  const pp = Number(r.purchase_price) || 0;
  const uy = Number(r.useful_years) || 5;
  const sv = Number(r.salvage_value) || 0;
  const pd = r.purchase_date ? new Date(r.purchase_date) : null;

  let yearsUsed = 0, netValue = pp, depPct = 0;
  if (pd && pp > 0) {
    yearsUsed = Math.max(0, (Date.now() - pd.getTime()) / (365.25 * 86400000));
    const dep = Math.min((pp - sv) / uy * yearsUsed, pp - sv);
    netValue = Math.max(pp - dep, sv);
    depPct = uy > 0 ? Math.min(100, (yearsUsed / uy) * 100) : 0;
  }

  const fmt = (v) => '¥' + Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2 });

  ctx.render(
    h('div', null,
      // Status badge + lifecycle bar
      h(Card, { size: 'small', title: '资产状态', style: { marginBottom: 12 } },
        h(Tag, { color: statusColors[currentStatus] || '#999',
          style: { fontSize: 14, padding: '4px 16px', borderRadius: 12, marginBottom: 12 } },
          currentStatus || '未知'),
        h('div', { style: { display: 'flex', gap: 4 } },
          ...stages.map((stage, i) => {
            const isActive = i <= currentStep;
            return h('div', { key: i, style: { flex: 1 } },
              h('div', { style: {
                height: 6, borderRadius: 3,
                background: isActive ? (statusColors[currentStatus] || '#1890ff') : '#f0f0f0'
              } }),
              h('div', { style: { textAlign: 'center', fontSize: 11, marginTop: 4,
                color: isActive ? '#333' : '#999' } }, stage)
            );
          })
        )
      ),
      // Depreciation card
      pp > 0 ? h(Card, { size: 'small', title: '折旧信息' },
        h(Progress, {
          percent: Math.round(depPct),
          strokeColor: depPct > 80 ? '#ff4d4f' : depPct > 50 ? '#faad14' : '#52c41a'
        }),
        h('div', { style: { display: 'flex', justifyContent: 'space-between', marginTop: 8 } },
          h(Statistic, { title: '原值', value: fmt(pp), valueStyle: { fontSize: 14 } }),
          h(Statistic, { title: '净值', value: fmt(netValue), valueStyle: { fontSize: 14, color: '#52c41a' } }),
          h(Statistic, { title: '已用', value: yearsUsed.toFixed(1) + '年', valueStyle: { fontSize: 14 } })
        )
      ) : null
    )
  );
})();
```

## Important Notes

1. **All code must be a single string** — no ES6 template literals (backticks) inside the code string
2. **Always wrap in `(async () => { ... })();`** for event flows to avoid issues
3. **Always null-check `ctx.record`** in columns: use `(ctx.record || {}).fieldName`
4. **ctx.render() must be called exactly once** in blocks and columns
5. **Chinese characters**: Use unicode escapes in string literals if needed (e.g., `'\u5929'` for 天)
6. **No external imports** — only ctx.React, ctx.antd, and ctx.api are available. **No ECharts, no CDN scripts.**
7. **ctx.antd** is Ant Design 5 — use component names like `Tag`, `Badge`, `Progress`, `Statistic`, `Card`, `Row`, `Col`, `Space`, `Divider`, `Tooltip`, `Alert`
8. **Charts**: Use antd `Progress` bars + API aggregation for chart-like visualizations (no ECharts in sandbox)
9. **Aggregation**: NocoBase list API has no GROUP BY. Fetch all records with `paginate: false` then aggregate in JS
10. **Relation data**: Use `appends: ['relation_name']` in API params to include related entity fields
11. **Formily field methods**: Use `ctx.form.query('fieldName').take()` → returns Formily Field with `.required`, `.setRequired()`, `.value`, `.componentType`
12. **JSItemModel in detail popups**: `ctx.record` is available and contains the parent record's data
