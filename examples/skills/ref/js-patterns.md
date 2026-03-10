# JS Code Patterns

完整沙箱 API 文档见 `ref/js-sandbox.md`，官方 snippet 模板见 `ref/js-snippets.md`。

## Quick Reference

| 能力 | 用法 |
|------|------|
| 内置 React + antd | `ctx.libs.antd`、`ctx.libs.React`（或 `ctx.antd`、`ctx.React`） |
| JSX 直接写 | `ctx.render(<Button>Click</Button>)` — 自动编译 |
| ECharts 图表 | `await ctx.requireAsync('echarts@5/dist/echarts.min.js')` |
| Chart.js 图表 | `await ctx.requireAsync('chart.js@4.4.0/dist/chart.umd.min.js')` |
| Hooks (useState 等) | `const { useState } = ctx.libs.React;` 然后在组件里用 |
| 数据请求 | `await ctx.request({url:'COLL:list', method:'get', params:{...}})` |
| dayjs | `ctx.libs.dayjs()` |
| lodash | `ctx.libs.lodash.get(obj, path)` |
| DOM 创建（给图表库用） | `document.createElement('div')` + `ctx.render(container)` |

## Common Mistakes

| Wrong | Correct | Why |
|-------|---------|-----|
| `ctx.charts` / `ctx.echarts` / `ctx.g2` | `ctx.requireAsync('echarts@5/...')` | 不是内置的，需要 CDN 加载 |
| `ctx.dataSource` / `ctx.utils` | `ctx.request({url, params})` | 用 ctx.request |
| `api.collection('x').list()` | `ctx.request({url:'x:list'})` | 没有 ORM 风格 API |
| `filter[field]=value` 查询字符串 | `params:{filter:{field:{$op:'val'}}}` | NocoBase 用 JSON filter |
| `r.department`（M2O 字段） | `r.department?.name` | M2O 返回对象，不是字符串 |
| 硬编码数据 | `ctx.request()` 实时查询 | 数据必须从数据库读取 |

## 数据请求

```js
// 列表查询
const { data } = await ctx.request({
  url: 'COLLECTION:list',
  method: 'get',
  params: { pageSize: 200, sort: ['-createdAt'], filter: { status: 'active' } }
});
const items = data?.data || [];

// Filter 运算符
// 日期: $dateAfter, $dateBefore, $dateOn
// 数字: $gt, $gte, $lt, $lte
// 字符串: $includes, $notIncludes, $eq, $ne
```

## M2O 关系字段

```js
// M2O 字段返回对象 {id, name, ...}，不是字符串
const dept = r.department?.name || '-';

// 混合字段 helper
const v = f => { const x = r[f]; return typeof x === 'object' && x ? (x.name || x.title || '') : x; };
```

---

## Pattern: ECharts Pie（饼图）

```js
const container = document.createElement('div');
container.style.height = '300px';
container.style.width = '100%';
ctx.render(container);

const echarts = await ctx.requireAsync('echarts@5/dist/echarts.min.js');
if (!echarts) throw new Error('ECharts not loaded');

const { data } = await ctx.request({ url: 'COLLECTION:list', method: 'get', params: { pageSize: 500 } });
const items = data?.data || [];

// 按字段分组统计
const counts = {};
items.forEach(i => { const v = i.FIELD?.name || i.FIELD || '(空)'; counts[v] = (counts[v]||0) + 1; });
const pieData = Object.entries(counts).map(([name, value]) => ({ name, value }));

const chart = echarts.init(container);
chart.setOption({
  tooltip: { trigger: 'item' },
  series: [{ type: 'pie', radius: '60%', data: pieData, label: { formatter: '{b}: {c} ({d}%)' } }]
});
chart.resize();
```

## Pattern: ECharts Bar（柱状图）

```js
const container = document.createElement('div');
container.style.height = '300px';
container.style.width = '100%';
ctx.render(container);

const echarts = await ctx.requireAsync('echarts@5/dist/echarts.min.js');
const { data } = await ctx.request({ url: 'COLLECTION:list', method: 'get', params: { pageSize: 500 } });
const items = data?.data || [];

const counts = {};
items.forEach(i => { const v = i.FIELD?.name || i.FIELD || '(空)'; counts[v] = (counts[v]||0) + 1; });
const sorted = Object.entries(counts).sort((a,b) => b[1]-a[1]);

const chart = echarts.init(container);
chart.setOption({
  tooltip: {},
  xAxis: { type: 'category', data: sorted.map(s => s[0]), axisLabel: { rotate: 30 } },
  yAxis: { type: 'value' },
  series: [{ type: 'bar', data: sorted.map(s => s[1]), itemStyle: { color: '#1890ff' } }]
});
chart.resize();
```

## Pattern: ECharts Line（折线趋势）

```js
const container = document.createElement('div');
container.style.height = '300px';
container.style.width = '100%';
ctx.render(container);

const echarts = await ctx.requireAsync('echarts@5/dist/echarts.min.js');
const { data } = await ctx.request({ url: 'COLLECTION:list', method: 'get', params: { pageSize: 1000 } });
const items = data?.data || [];

// 按月统计
const now = new Date(); const months = [];
for (let i = 5; i >= 0; i--) {
  const d = new Date(now.getFullYear(), now.getMonth()-i, 1);
  months.push({ key: d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0'), label: (d.getMonth()+1)+'月' });
}
const counts = months.map(m => items.filter(i => (i.createdAt||'').startsWith(m.key)).length);

const chart = echarts.init(container);
chart.setOption({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: months.map(m => m.label) },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: counts, smooth: true, areaStyle: { opacity: 0.3 } }]
});
chart.resize();
```

## Pattern: ECharts Funnel（漏斗图）

```js
const container = document.createElement('div');
container.style.height = '300px';
container.style.width = '100%';
ctx.render(container);

const echarts = await ctx.requireAsync('echarts@5/dist/echarts.min.js');
const { data } = await ctx.request({ url: 'COLLECTION:list', method: 'get', params: { pageSize: 500 } });
const items = data?.data || [];

const stages = ['STAGE1','STAGE2','STAGE3','STAGE4','STAGE5'];
const funnelData = stages.map(s => ({ name: s, value: items.filter(i => i.STAGE_FIELD === s).length }));

const chart = echarts.init(container);
chart.setOption({
  tooltip: { trigger: 'item' },
  series: [{ type: 'funnel', left: '10%', width: '80%', data: funnelData, label: { formatter: '{b}: {c}' } }]
});
chart.resize();
```

## Pattern: Statistics Cards（统计卡片 — JSX）

```jsx
const { Card, Statistic, Row, Col } = ctx.libs.antd;

const { data } = await ctx.request({ url: 'COLLECTION:list', method: 'get', params: { pageSize: 500 } });
const items = data?.data || [];

const total = items.length;
const activeCount = items.filter(i => i.status === 'active').length;
const amount = items.reduce((s, i) => s + (Number(i.AMOUNT_FIELD) || 0), 0);

ctx.render(
  <Row gutter={16}>
    <Col span={8}><Card><Statistic title="总数" value={total} valueStyle={{ color: '#1890ff' }} /></Card></Col>
    <Col span={8}><Card><Statistic title="活跃" value={activeCount} valueStyle={{ color: '#52c41a' }} /></Card></Col>
    <Col span={8}><Card><Statistic title="金额" value={'¥' + amount.toLocaleString()} valueStyle={{ color: '#faad14' }} /></Card></Col>
  </Row>
);
```

## Pattern: Distribution（antd Progress 条形 — 无需 ECharts）

```js
(async()=>{const h=ctx.React.createElement;const{Progress}=ctx.antd;
const colors=['#1890ff','#52c41a','#faad14','#ff4d4f','#722ed1','#13c2c2'];
try{const r=await ctx.api.request({url:'COLLECTION:list',params:{paginate:false}});
const items=r?.data?.data||[];const counts={};
items.forEach(i=>{const v=i.FIELD?.name||i.FIELD||'(empty)';counts[v]=(counts[v]||0)+1;});
const total=items.length||1;
const sorted=Object.entries(counts).sort((a,b)=>b[1]-a[1]);
ctx.render(h('div',{style:{padding:'4px 0'}},
  sorted.map(([label,count],i)=>h('div',{key:i,style:{display:'flex',alignItems:'center',marginBottom:6,gap:8}},
    h('div',{style:{width:64,fontSize:12,color:'#666',textAlign:'right',flexShrink:0}},label),
    h('div',{style:{flex:1}},h(Progress,{percent:Math.round(count/total*100),strokeColor:colors[i%colors.length],size:'small',format:()=>count}))
  ))));
}catch(e){ctx.render(h('div',null,'...'));}})();
```

## Pattern: Alert List

```js
(async()=>{const h=ctx.React.createElement;const{List,Tag}=ctx.antd;
try{const r=await ctx.api.request({url:'COLLECTION:list',params:{paginate:false,filter:{FILTER_FIELD:'FILTER_VALUE'}}});
const items=(r?.data?.data||[]).slice(0,5);
ctx.render(h(List,{size:'small',dataSource:items,renderItem:item=>
  h(List.Item,null,h('div',{style:{display:'flex',justifyContent:'space-between',width:'100%'}},
    h('span',{style:{fontSize:12}},item.NAME_FIELD),
    h(Tag,{color:'red',style:{fontSize:11}},item.TAG_FIELD)))
}));}catch(e){ctx.render(h('div',null,'...'));}})();
```

## Pattern: Profile Card (detail item)

```js
const h=ctx.React.createElement;const{Tag,Statistic,Row,Col}=ctx.antd;
const r=ctx.record||{};
const days=Math.floor((Date.now()-new Date(r.createdAt))/86400000);
ctx.render(h('div',{style:{padding:8}},
  h(Row,{gutter:12},
    h(Col,{span:6},h(Tag,{color:'blue'},r.FIELD1||'-')),
    h(Col,{span:6},h(Tag,{color:'green'},r.FIELD2||'-')),
    h(Col,{span:6},h(Tag,null,r.FIELD3||'-')),
    h(Col,{span:6},h(Statistic,{title:'Days',value:days,valueStyle:{fontSize:14}}))
  )
));
```

## Pattern: Event (stage → field mapping)

```js
const vals=ctx.form?.values||{};
const map={STAGE1:10,STAGE2:30,STAGE3:50,STAGE4:70,STAGE5:90,STAGE6:100};
if(vals.stage&&map[vals.stage]!==undefined){ctx.form.setFieldsValue({probability:map[vals.stage]});}
```

Replace COLLECTION, FIELD, AMOUNT_FIELD, STATUS_FIELD, STAGE_FIELD, etc. with actual values.
