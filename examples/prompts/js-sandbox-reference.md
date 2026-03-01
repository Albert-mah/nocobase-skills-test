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

## Important Notes

1. **All code must be a single string** — no ES6 template literals (backticks) inside the code string
2. **Always wrap in `(async () => { ... })();`** for event flows to avoid issues
3. **Always null-check `ctx.record`** in columns: use `(ctx.record || {}).fieldName`
4. **ctx.render() must be called exactly once** in blocks and columns
5. **Chinese characters**: Use unicode escapes in string literals if needed (e.g., `'\u5929'` for 天)
6. **No external imports** — only ctx.React, ctx.antd, and ctx.api are available
7. **ctx.antd** is Ant Design 5 — use component names like `Tag`, `Badge`, `Progress`, `Statistic`, `Card`, `Row`, `Col`, `Space`, `Divider`, `Tooltip`, `Alert`
