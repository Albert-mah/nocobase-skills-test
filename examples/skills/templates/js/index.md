# JS Templates Index

## Rendering API

All JS blocks run in a sandbox with these globals:

| Global | Description |
|--------|-------------|
| `ctx.api.request({url, params})` | NocoBase REST API. `url` = `"collection:list"`, `params` = `{paginate:false, filter:{...}, sort:["-field"], appends:["relation"]}` |
| `ctx.React.createElement(type, props, ...children)` | React 19. Alias as `const h = ctx.React.createElement` |
| `ctx.antd` | **Full Ant Design 5.x** — see component list below |
| `ctx.render(element)` | Output to the block container |
| `ctx.record` | Current row data (available in **columns** and **detail items** only, NOT in page blocks) |

**⚠️ NOT available** (will be rejected by tool validation):
- `ctx.charts`, `ctx.echarts`, `ctx.g2`, `ctx.dataSource` — NO chart library, NO dataSource API
- `useState`, `useEffect`, `useCallback` — NO React hooks (blocks run in eval, not component lifecycle)
- Use `ctx.api.request({url, params})` for data, async IIFE `(async()=>{...})()` for async code
- Use `ctx.antd.Progress` for bar charts, SVG/div for custom visuals

## Phase 2 Workflow

After `nb_auto_js("PREFIX")`, columns are auto-filled. Blocks/items/events are `[todo]` stubs.
Implement each `[todo]`:

```
1. Read the stub description — it tells you WHAT to show
2. Choose a visualization that fits the data + context
3. Write the JS code — fetch data, compute, render with antd
4. nb_inject_js(uid, code)
5. nb_inject_js_dir("js/")  — or inject all at once
```

## Column Templates — `nb_inject_js(uid, code)`

Render custom content per table row. `ctx.record` available.

**Rules:**
- Do NOT use JS columns for select/enum fields (等级/状态/类型/优先级) — NocoBase renders colored tags natively
- DO use JS columns to make tables look **rich and informative**, matching the HTML prototype column designs

### ★ col-composite.js — THE primary column template (use on every main entity)

Every business entity's **primary name/title column** should be composite: bold blue title + gray subtitle info.

| Business entity | TITLE field | SUBS fields | Width |
|----------------|-------------|-------------|-------|
| 客户 | `name` | `"city","source"` | 200 |
| 商机 | `title` | `"customer_id"` (or use createdAt) | 200 |
| 合同 | `title` | `"start_date","end_date"` | 200 |
| 线索 | `contact_name` | `"company","position"` | 180 |
| 工单 | `subject` | `"description"` | 220 |
| 员工 | `name` | `"department_id","position"` | 180 |
| 产品 | `name` | `"category","spec"` | 200 |

Placeholders: `{TITLE}` = main field name, `{SUBS}` = JS string: `"field1","field2"` (supports 1-3 sub-fields)

### Other column templates

| File | Renders | Use when | Placeholders |
|------|---------|----------|-------------|
| `col-currency.js` | ¥12,345.00 monospace | decimal/金额 fields | `{FIELD}`, `{THRESHOLD}` |
| `col-countdown.js` | "⏱ 还剩12天" / "⚠ 已逾期3天" | date fields + 到期/截止 concept | `{FIELD}` |
| `col-progress.js` | Colored bar + percentage | percentage/达成率/完成率 | `{FIELD}` |
| `col-stars.js` | ★★★★☆ | integer rating/评分/满意度 | `{FIELD}` |
| `col-relative-time.js` | "3小时前" / "2天前" | date + 最近/创建时间 | `{FIELD}` |
| `col-comparison.js` | Target vs actual bar | 目标 vs 实际 comparison | `{TARGET}`, `{ACTUAL}` |

### How to map HTML prototype → JS columns

Read the HTML prototype `<table>` section. For each column:
1. `<td>` with **two nested divs** (bold name + gray info) → `col-composite.js`
2. `<td>` with **¥ + monospace number** → `col-currency.js`
3. `<td>` with **"还剩X天"/"已逾期"** → `col-countdown.js`
4. `<td>` with **progress bar** → `col-progress.js`
5. `<td>` with **"N小时前"/"N天前"** → `col-relative-time.js`
6. `<td>` with **stars** → `col-stars.js`
7. `<td>` with **just a tag/badge** → skip (NocoBase native select rendering)

## Block JS — 自由编写，视觉多样化

Page-level blocks. Async context, `ctx.api` + `ctx.antd` available. **No templates — write original code for each block.**

### 基本结构

```js
(async () => {
  const h = ctx.React.createElement;
  const { /* pick components */ } = ctx.antd;
  const r = await ctx.api.request({ url: 'collection:list', params: { paginate: false } });
  const data = r?.data?.data || [];
  // ... compute ...
  ctx.render(h('div', null, /* your visualization */));
})();
```

### Ant Design 组件速查

| 组件 | 用法 | 适合场景 |
|------|------|---------|
| `Statistic` | 大数字 + 标题 | 核心指标（但不要所有 block 都用这个！） |
| `Progress` | `type="circle"` 环形 / `type="line"` 条形 | 达成率、完成度、占比 |
| `Tag` | 彩色标签 | 状态标记、分类标识 |
| `List` + `List.Item` | 列表渲染 | 排行榜、最近记录、预警列表 |
| `Card` | 卡片容器 | 包裹统计信息 |
| `Row` + `Col` | 24栅格布局 | 多卡片并排 |
| `Alert` | 提示条 | 预警、空状态 |
| `Badge` | 角标/状态点 | 数量提示 |
| `Timeline` | 时间线 | 事件序列、操作历史 |
| `Steps` | 步骤条 | 流程阶段 |
| `Rate` | 星级 | 评分、满意度 |
| `Descriptions` | 描述列表 | 键值对详情 |
| `Typography.Text` | 富文本 | 标题、说明文字 |
| `Tooltip` | 悬浮提示 | 数据详情 |
| `Space` + `Divider` | 间距/分割 | 布局辅助 |
| `Empty` | 空状态 | 无数据时 |

### 自绘可视化（用 div + inline style）

| 模式 | 实现方式 | 适合场景 |
|------|---------|---------|
| 水平条形图 | div 宽度按比例 + 颜色映射 | 分布对比 |
| 环形图/甜甜圈 | SVG circle + stroke-dasharray | 占比可视化 |
| 迷你面积图 | SVG path + linearGradient | 趋势对比 |
| 漏斗图 | 居中递减宽度条 | 转化流程 |
| 热力网格 | CSS grid + 背景色深浅 | 活跃度分布 |
| 迷你柱状图 | flex 容器 + 垂直 div | 周/月对比 |

### ★ 多样化原则（必须遵守）

1. **同一页面的多个 block 必须使用不同的可视化模式** — 不能全用 Statistic，不能全用横向条形图
2. **颜色语义化**：`#52c41a` 绿=正常/增长，`#1890ff` 蓝=信息，`#faad14` 橙=警告，`#f5222d` 红=危险/下降
3. **信息密度**：不要只显示一个数字 — 加上趋势箭头 ↑↓、环比对比、或上下文说明
4. **Ant Design 企业级风格**：简洁专业，适当留白，字号层次分明（标题14px, 数值24-32px, 辅助文字12px）
5. **数据驱动**：根据数据特征选择可视化 — 分类→条形图/环形图，时间序列→趋势图，占比→Progress，排名→列表

## Item Templates — `nb_inject_js(uid, code)`

Custom content inside detail views or forms. `ctx.record` available in detail context.

| File | Type | Placeholders |
|------|------|-------------|
| `item-lifecycle.js` | Status pipeline + progress bar | `{STATUS_FIELD}`, `{STAGES}`, `{STATUS_COLORS}` |
| `item-stats.js` | 2-4 computed statistics | `{STATS}` |
| `item-gauge.js` | Progress circle with label | `{VALUE_FIELD}`, `{TOTAL_FIELD}`, `{LABEL}` |

## Event Templates — `nb_inject_js(uid, code, event_name="...")`

Form event handlers. Three event types:
- `formValuesChange` — when any field changes (auto-calc, validation, cascading)
- `beforeRender` — when form opens (auto-fill defaults)
- `afterSubmit` — after successful submit (notifications, redirects)

| File | Event | Type | Placeholders |
|------|-------|------|-------------|
| `event-calc.js` | formValuesChange | Auto-calculate A*B→Result | `{FIELD_A}`, `{FIELD_B}`, `{RESULT}` |
| `event-mapping.js` | formValuesChange | Value→value lookup | `{TRIGGER}`, `{TARGET}`, `{MAP}` |
| `event-autofill.js` | beforeRender | Fill current user/date | `{FILLS}` |
| `event-validate.js` | formValuesChange | Cross-field validation | `{FIELD_A}`, `{FIELD_B}`, `{RULE}`, `{MESSAGE}` |
| `event-conditional.js` | formValuesChange | Conditional required fields | `{TRIGGER}`, `{TRIGGER_VALUES}`, `{TARGET_FIELDS}` |

## Column/Item/Event Placeholder Reference

| Placeholder | Format | Example |
|-------------|--------|---------|
| `{FIELD}` | field name string | `amount`, `status` |
| `{COLLECTION}` | table name | `nb_crm_customers` |
| `{COLOR_MAP}` | JS object literal | `{"高":"#ff4d4f","中":"#faad14","低":"#52c41a"}` |
| `{STAGE_ORDER}` | JS array literal | `["线索","商机","报价","成交"]` |
| `{STATS}` | JSON array | `[{"title":"原值","field":"price","prefix":"¥"}]` |
| `{MAP}` | JS object literal | `{"VIP":"A级","普通":"B级"}` |
| `{FILLS}` | JSON array | `[{"field":"reporter","source":"currentUser"},{"field":"date","source":"today"}]` |

> Note: Block JS does NOT use placeholder templates. Write original code for each block.
