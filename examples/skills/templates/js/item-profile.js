// Item: Profile Tags — shows select/enum fields as colored tags + date stat
// Tool: nb_inject_js(uid, code)
// Placeholders: {TAG_FIELDS}, {DATE_FIELD}, {LABEL}
// {TAG_FIELDS} = JSON array of field configs: [{"field":"grade","colors":{"A":"red","B":"orange","C":"blue"}},{"field":"status","colors":{"已签约":"green","跟进中":"blue"}},{"field":"industry"},{"field":"source"}]
// {DATE_FIELD} = date field for "N天" calc, e.g. "createdAt"
// {LABEL} = stat label, e.g. "建档天数"
(()=>{const h=ctx.React.createElement;const{Tag,Row,Col,Statistic}=ctx.antd;const r=ctx.record||{};const tagFields={TAG_FIELDS};const dateField='{DATE_FIELD}';const label='{LABEL}';const palette=['blue','green','orange','red','purple','cyan','magenta','geekblue','lime','gold'];let pi=0;const tags=[];tagFields.forEach(tf=>{const v=r[tf.field];if(!v)return;const c=(tf.colors&&tf.colors[v])||palette[pi++%palette.length];tags.push(h(Tag,{key:tf.field,color:c,style:{fontSize:13,padding:'2px 10px',borderRadius:10,marginBottom:4}},v));});const dv=r[dateField];const days=dv?Math.floor((Date.now()-new Date(dv))/86400000):0;ctx.render(h('div',{style:{padding:'8px 4px'}},h('div',{style:{display:'flex',flexWrap:'wrap',gap:6,alignItems:'center'}},...tags,days>0?h('div',{style:{marginLeft:8,display:'inline-block'}},h(Statistic,{title:label,value:days,suffix:'天',valueStyle:{fontSize:16}})):null)));})();
