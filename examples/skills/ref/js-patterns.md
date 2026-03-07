# JS Code Patterns

Read this when implementing JS in Phase 4. Do NOT read upfront.

## JS Sandbox

**Blocks/Columns/Items**: `ctx.React`, `ctx.antd` (Ant Design 5), `ctx.api`, `ctx.render(el)`, `ctx.record`
**Events**: `ctx.form.values`, `ctx.form.setFieldsValue({field: value})`

## Code Rules

1. Always: `const h = ctx.React.createElement;`
2. Async blocks: `(async () => { ... })();`
3. `ctx.render()` exactly once
4. No external imports, no Card wrapper, no backticks in code string
5. No JS for select/enum columns (NocoBase renders them natively)

## Pattern: Distribution (most common)
```javascript
(async()=>{const h=ctx.React.createElement;const{Progress}=ctx.antd;
const colors=['#1890ff','#52c41a','#faad14','#ff4d4f','#722ed1','#13c2c2'];
try{const r=await ctx.api.request({url:'COLLECTION:list',params:{paginate:false}});
const items=r?.data?.data||[];const counts={};
items.forEach(i=>{const v=i.FIELD||'(empty)';counts[v]=(counts[v]||0)+1;});
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
