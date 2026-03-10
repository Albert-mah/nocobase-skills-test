# JS Code Patterns

## Quick Reference — Common Mistakes and Fixes

| Wrong | Correct | Why |
|-------|---------|-----|
| `ctx.charts` / `ctx.echarts` / `ctx.g2` | `ctx.antd.Progress` + `div` | 沙箱里没有图表库 |
| `ctx.dataSource` / `ctx.utils` | `ctx.api.request({url, params})` | 沙箱里只有 ctx.api |
| `useState` / `useEffect` | `(async()=>{...})();` | eval 上下文，不是 React 组件 |
| `api.collection('x').list()` | `ctx.api.request({url:'x:list', params:{paginate:false}})` | 没有 ORM 风格 API |
| `document.createElement` / `innerHTML` | `ctx.render(h('div', ...))` | 必须用 ctx.render 输出 |
| `filter[field]=value` 查询字符串 | `params:{filter:{field:{$op:'val'}}}` | NocoBase 用 JSON filter |
| `{Pie, Bar, Line}` 图表组件 | `Progress` 条形 + `div` 柱状 | 没有 AntV/ECharts |
| `r.department` (M2O 字段) | `r.department?.name` | M2O 返回对象，不是字符串 |

## JS Sandbox

**Blocks/Columns/Items**: `ctx.React`, `ctx.antd` (Ant Design 5), `ctx.api`, `ctx.render(el)`, `ctx.record`
**Events**: `ctx.form.values`, `ctx.form.setFieldsValue({field: value})`

## Code Rules

1. Always: `const h = ctx.React.createElement;`
2. Async blocks: `(async () => { ... })();`
3. `ctx.render()` exactly once
4. No external imports, no Card wrapper, no backticks in code string
5. No JS for select/enum columns (NocoBase renders them natively)
6. **NO chart library** — ctx.charts, ctx.echarts, ctx.g2 do NOT exist. Use `ctx.antd.Progress` for bars, plain `div` for trends.
7. **NO React hooks** — useState, useEffect, useCallback etc are NOT available. Blocks run in eval(), not component lifecycle. Use async IIFE: `(async()=>{...})();`
8. **NO ctx.dataSource, ctx.utils** — these APIs do NOT exist.
9. **NO api.collection().list()** — this ORM-style API does NOT exist in JS sandbox.
10. Data fetching (ONLY correct way): `const r = await ctx.api.request({url:'COLLECTION:list', params:{paginate:false}}); const items = r?.data?.data || [];`

## M2O / Relation Field Handling (CRITICAL)

M2O fields (department, position, employee, etc.) return **objects** like `{id, name, ...}`, NOT strings.

```javascript
// ❌ WRONG — renders [object Object]
const dept = r.department;
// ❌ WRONG — same problem in .map()
["department","position"].map(f => r[f])

// ✅ CORRECT — extract .name from relation objects
const dept = r.department?.name || '-';
// ✅ CORRECT — helper function for mixed fields
const v = f => { const x = r[f]; return typeof x === 'object' && x !== null ? (x.name || x.title || x.label || '') : x; };
["department","position"].map(f => v(f)).filter(Boolean).join(' · ')
```

## NocoBase Filter API Syntax (CRITICAL)

```javascript
// ❌ WRONG — query string bracket notation
params: { filter: { "date>=": "2025-03-01" } }
// ❌ WRONG — filter[field>]=value is NOT NocoBase syntax
url: 'collection:list?filter[date>]=2025-03-01'

// ✅ CORRECT — NocoBase JSON filter with operators
params: { filter: { date: { $dateAfter: "2025-03-01" } } }
params: { filter: { status: "active" } }  // exact match
params: { filter: { amount: { $gt: 1000 } } }  // greater than
params: { filter: { name: { $includes: "keyword" } } }  // contains

// Common date operators: $dateAfter, $dateBefore, $dateOn
// Common number operators: $gt, $gte, $lt, $lte
// Common string operators: $includes, $notIncludes, $eq, $ne
```

## Pattern: Distribution (most common)
```javascript
(async()=>{const h=ctx.React.createElement;const{Progress}=ctx.antd;
const colors=['#1890ff','#52c41a','#faad14','#ff4d4f','#722ed1','#13c2c2'];
try{const r=await ctx.api.request({url:'COLLECTION:list',params:{paginate:false}});
const items=r?.data?.data||[];const counts={};
// NOTE: For m2o fields use i.FIELD?.name, for plain fields use i.FIELD
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

## Pattern: Amount Summary (financial)
```javascript
(async()=>{const h=ctx.React.createElement;const{Statistic,Row,Col}=ctx.antd;
try{const r=await ctx.api.request({url:'COLLECTION:list',params:{paginate:false}});
const items=r?.data?.data||[];
const total=items.reduce((s,i)=>s+(Number(i.AMOUNT_FIELD)||0),0);
const done=items.filter(i=>i.STATUS_FIELD==='DONE_VALUE').reduce((s,i)=>s+(Number(i.AMOUNT_FIELD)||0),0);
const fmt=v=>'¥'+v.toLocaleString('zh-CN',{minimumFractionDigits:0});
ctx.render(h(Row,{gutter:8},
  h(Col,{span:8},h(Statistic,{title:'Total',value:fmt(total),valueStyle:{fontSize:14,color:'#1890ff'}})),
  h(Col,{span:8},h(Statistic,{title:'Done',value:fmt(done),valueStyle:{fontSize:14,color:'#52c41a'}})),
  h(Col,{span:8},h(Statistic,{title:'Pending',value:fmt(total-done),valueStyle:{fontSize:14,color:'#faad14'}}))
));}catch(e){ctx.render(h('div',null,'...'));}})();
```

## Pattern: Alert List
```javascript
(async()=>{const h=ctx.React.createElement;const{List,Tag}=ctx.antd;
try{const r=await ctx.api.request({url:'COLLECTION:list',params:{paginate:false,filter:{FILTER_FIELD:'FILTER_VALUE'}}});
const items=(r?.data?.data||[]).slice(0,5);
ctx.render(h(List,{size:'small',dataSource:items,renderItem:item=>
  h(List.Item,null,h('div',{style:{display:'flex',justifyContent:'space-between',width:'100%'}},
    h('span',{style:{fontSize:12}},item.NAME_FIELD),
    h(Tag,{color:'red',style:{fontSize:11}},item.TAG_FIELD)))
}));}catch(e){ctx.render(h('div',null,'...'));}})();
```

## Pattern: Funnel/Pipeline
```javascript
(async()=>{const h=ctx.React.createElement;const{Progress}=ctx.antd;
const stages=['STAGE1','STAGE2','STAGE3','STAGE4','STAGE5'];
const colors=['#1890ff','#52c41a','#faad14','#ff4d4f','#722ed1'];
try{const r=await ctx.api.request({url:'COLLECTION:list',params:{paginate:false}});
const items=r?.data?.data||[];
const counts=stages.map(s=>items.filter(i=>i.STAGE_FIELD===s).length);
const max=Math.max(...counts,1);
ctx.render(h('div',{style:{padding:'4px 0'}},
  stages.map((s,i)=>h('div',{key:i,style:{display:'flex',alignItems:'center',marginBottom:6,gap:8}},
    h('div',{style:{width:56,fontSize:11,color:'#666',textAlign:'right'}},s),
    h('div',{style:{flex:1}},h(Progress,{percent:Math.round(counts[i]/max*100),strokeColor:colors[i%colors.length],size:'small',format:()=>counts[i]}))
  ))));
}catch(e){ctx.render(h('div',null,'...'));}})();
```

## Pattern: Monthly Trend
```javascript
// NOTE: For date filtering, use NocoBase operators like $dateAfter/$dateBefore
// Do NOT use filter[field>]=value bracket syntax
(async()=>{const h=ctx.React.createElement;
const colors=['#e6f7ff','#bae7ff','#91d5ff','#69c0ff','#40a9ff','#1890ff'];
try{const r=await ctx.api.request({url:'COLLECTION:list',params:{paginate:false}});
const items=r?.data?.data||[];const now=new Date();const months=[];
for(let i=5;i>=0;i--){const d=new Date(now.getFullYear(),now.getMonth()-i,1);months.push({key:d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0'),label:(d.getMonth()+1)+'月'});}
const counts=months.map(m=>items.filter(i=>(i.createdAt||'').startsWith(m.key)).length);
const max=Math.max(...counts,1);
ctx.render(h('div',{style:{display:'flex',alignItems:'flex-end',gap:4,height:100,padding:'4px 0'}},
  months.map((m,i)=>h('div',{key:i,style:{flex:1,textAlign:'center'}},
    h('div',{style:{height:Math.max(counts[i]/max*80,4),background:colors[i],borderRadius:3,marginBottom:4}}),
    h('div',{style:{fontSize:10,color:'#999'}},m.label),
    h('div',{style:{fontSize:11,fontWeight:500}},counts[i])
  ))));
}catch(e){ctx.render(h('div',null,'...'));}})();
```

## Pattern: Profile Card (detail item)
```javascript
const h=ctx.React.createElement;const{Tag,Statistic,Row,Col}=ctx.antd;
const r=ctx.record||{};
// Helper for m2o fields: r.department?.name instead of r.department
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

## Pattern: Event (stage → probability mapping)
```javascript
const vals=ctx.form?.values||{};
const map={STAGE1:10,STAGE2:30,STAGE3:50,STAGE4:70,STAGE5:90,STAGE6:100};
if(vals.stage&&map[vals.stage]!==undefined){ctx.form.setFieldsValue({probability:map[vals.stage]});}
```

Replace COLLECTION, FIELD, AMOUNT_FIELD, STATUS_FIELD, STAGE_FIELD, etc. with actual values.
