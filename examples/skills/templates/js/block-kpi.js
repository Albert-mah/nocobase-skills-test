// Block: Multi-KPI Row — shows 3-4 statistic cards in a row
// Tool: nb_inject_js(uid, code)
// Placeholders: {COLLECTION}, {QUERIES}
// {QUERIES} = JSON array: [{"title":"总数","filter":{}},{"title":"使用中","filter":{"status":"使用中"},"color":"#52c41a"}]
(async()=>{const h=ctx.React.createElement;const{Row,Col,Card,Statistic}=ctx.antd;const queries={QUERIES};const counts=await Promise.all(queries.map(async(q)=>{try{const r=await ctx.api.request({url:'{COLLECTION}:list',params:{paginate:false,filter:q.filter||{}}});return Array.isArray(r?.data?.data)?r.data.data.length:0;}catch(e){return '?';}}));ctx.render(h(Row,{gutter:16},...queries.map((q,i)=>h(Col,{span:Math.floor(24/queries.length),key:i},h(Card,{size:'small'},h(Statistic,{title:q.title,value:counts[i],valueStyle:{color:q.color||'#333'}}))))));})();
