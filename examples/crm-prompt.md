# Full-Feature CRM System Build Prompt

Build a complete CRM system with 18 tables, 12 pages, 6 workflows, and 3 AI employees.

## Launch Command

```bash
mkdir -p /tmp/crm-build && cd /tmp/crm-build
# Ensure .mcp.json and skills are configured (see main README)
claude -p "$(cat crm-prompt.txt)" --dangerously-skip-permissions
```

## The Prompt

Save the content below as `crm-prompt.txt`:

---

# Build a Full-Feature CRM System in NocoBase

Use the NocoBase MCP tools to build a complete CRM. Use batch tools (`nb_setup_collection`, `nb_crud_page`) for speed.
Write progress to ./notes.md.

## Data Model (18 tables, prefix: nb_crm_)

### M1: 客户管理 (4 tables)

**nb_crm_customers — 客户**
- name* VARCHAR(255), code VARCHAR(50), short_name VARCHAR(100)
- customer_type: 企业客户, 个人客户 (select)
- industry: 互联网, 金融, 制造, 教育, 医疗, 零售, 房地产, 物流, 能源, 其他 (select)
- scale: 大型(500+), 中型(100-499), 小型(20-99), 微型(<20) (select)
- source: 官网, 转介绍, 展会, 电销, 广告, 社交媒体, 渠道合作, 其他 (select)
- status: 潜在, 跟进中, 已签约, 已流失, 黑名单 (select, colors: default/blue/green/red/grey)
- level: S, A, B, C, D (select, colors: red/orange/blue/cyan/default)
- address, city, province, postal_code, country VARCHAR
- phone, fax, email, website VARCHAR
- annual_revenue NUMERIC(14,2), employee_count INTEGER
- remark TEXT

**nb_crm_contacts — 联系人**
- name* VARCHAR(100), gender VARCHAR(10), position VARCHAR(100), department VARCHAR(100)
- phone, mobile, email, wechat, linkedin VARCHAR
- is_primary BOOLEAN DEFAULT false, is_decision_maker BOOLEAN DEFAULT false
- birthday DATE, remark TEXT
- customer_id BIGINT → nb_crm_customers (m2o)

**nb_crm_leads — 线索**
- name* VARCHAR(255), company VARCHAR(255), position VARCHAR(100)
- phone, mobile, email VARCHAR
- source: same as customer source (select)
- status: 新线索, 跟进中, 已转化, 已丢弃 (select, colors: blue/orange/green/red)
- score INTEGER DEFAULT 0 (线索评分)
- channel VARCHAR(100), campaign VARCHAR(200)
- remark TEXT

**nb_crm_lead_pool — 线索公海**
- lead_id BIGINT → nb_crm_leads (m2o)
- reason: 超时未跟进, 主动释放, 客户拒绝, 其他 (select)
- released_at TIMESTAMPTZ, claimed_at TIMESTAMPTZ
- status: 待认领, 已认领, 已过期 (select, colors: orange/green/grey)
- remark TEXT

### M2: 销售管理 (5 tables)

**nb_crm_opportunities — 商机**
- title* VARCHAR(255), opportunity_no VARCHAR(50)
- stage: 初步接触, 需求确认, 方案报价, 商务谈判, 合同审批, 赢单, 输单 (select, colors: default/blue/cyan/orange/purple/green/red)
- amount NUMERIC(14,2), probability INTEGER DEFAULT 50
- expected_close_date DATE, actual_close_date DATE
- source: same as customer source (select)
- loss_reason VARCHAR(200), competitor VARCHAR(200)
- remark TEXT
- customer_id BIGINT → nb_crm_customers (m2o)
- contact_id BIGINT → nb_crm_contacts (m2o)

**nb_crm_quotes — 方案报价**
- quote_no VARCHAR(50), title* VARCHAR(255)
- amount NUMERIC(14,2), discount_rate NUMERIC(5,2), final_amount NUMERIC(14,2)
- valid_until DATE
- status: 草稿, 已发送, 已接受, 已拒绝, 已过期 (select, colors: default/blue/green/red/grey)
- remark TEXT
- opportunity_id BIGINT → nb_crm_opportunities (m2o)
- customer_id BIGINT → nb_crm_customers (m2o)

**nb_crm_competitors — 竞争对手**
- name* VARCHAR(255), website VARCHAR(500)
- strength TEXT, weakness TEXT
- market_share VARCHAR(50), price_level: 高, 中, 低 (select)
- remark TEXT

**nb_crm_activities — 跟进记录**
- activity_type: 电话, 拜访, 邮件, 会议, 微信, 演示, 提案, 其他 (select)
- subject* VARCHAR(255), content TEXT (textarea)
- activity_date DATE, duration INTEGER (分钟)
- result: 成功, 待跟进, 无效, 拒绝 (select, colors: green/orange/grey/red)
- next_action VARCHAR(500), next_date DATE
- customer_id BIGINT → nb_crm_customers (m2o)
- opportunity_id BIGINT → nb_crm_opportunities (m2o)
- contact_id BIGINT → nb_crm_contacts (m2o)

**nb_crm_targets — 销售目标**
- period VARCHAR(20) (如 "2026-Q1", "2026-03")
- target_type: 月度, 季度, 年度 (select)
- target_amount NUMERIC(14,2), achieved_amount NUMERIC(14,2) DEFAULT 0
- target_count INTEGER, achieved_count INTEGER DEFAULT 0
- status: 进行中, 已完成, 未达标 (select, colors: blue/green/red)
- remark TEXT

### M3: 合同与回款 (4 tables)

**nb_crm_contracts — 合同**
- contract_no VARCHAR(50), title* VARCHAR(255)
- contract_type: 标准合同, 框架协议, 补充协议, 续约合同 (select)
- amount NUMERIC(14,2), paid_amount NUMERIC(14,2) DEFAULT 0
- status: 草稿, 审批中, 已签署, 执行中, 已完成, 已终止, 已作废 (select, colors: default/blue/cyan/green/grey/red/grey)
- sign_date DATE, start_date DATE, end_date DATE
- payment_terms VARCHAR(200), remark TEXT
- customer_id BIGINT → nb_crm_customers (m2o)
- opportunity_id BIGINT → nb_crm_opportunities (m2o)

**nb_crm_contract_items — 合同明细**
- product_name VARCHAR(255), specification VARCHAR(200)
- quantity INTEGER, unit VARCHAR(20), unit_price NUMERIC(12,2)
- discount NUMERIC(5,2) DEFAULT 0, total NUMERIC(14,2)
- remark TEXT
- contract_id BIGINT → nb_crm_contracts (m2o)
- product_id BIGINT → nb_crm_products (m2o)

**nb_crm_payments — 回款记录**
- payment_no VARCHAR(50), amount NUMERIC(14,2)
- payment_date DATE, payment_method: 银行转账, 支票, 现金, 在线支付 (select)
- status: 待确认, 已到账, 已退款 (select, colors: orange/green/red)
- remark TEXT
- contract_id BIGINT → nb_crm_contracts (m2o)
- customer_id BIGINT → nb_crm_customers (m2o)

**nb_crm_products — 产品**
- name* VARCHAR(255), code VARCHAR(50)
- category: 软件, 硬件, 服务, 咨询, 培训, 实施, 其他 (select)
- price NUMERIC(12,2), cost NUMERIC(12,2)
- unit: 套, 个, 年, 月, 次, 人天 (select)
- status: 在售, 停售, 预售 (select, colors: green/red/blue)
- description TEXT

### M4: 服务与支持 (3 tables)

**nb_crm_tickets — 服务工单**
- ticket_no VARCHAR(50), subject* VARCHAR(255), description TEXT (textarea)
- ticket_type: 咨询, 报障, 投诉, 建议, 需求 (select)
- priority: 紧急, 高, 中, 低 (select, colors: red/orange/blue/default)
- status: 待处理, 处理中, 待确认, 已解决, 已关闭 (select, colors: orange/blue/cyan/green/grey)
- response_at TIMESTAMPTZ, resolved_at TIMESTAMPTZ
- satisfaction: 非常满意, 满意, 一般, 不满意 (select)
- remark TEXT
- customer_id BIGINT → nb_crm_customers (m2o)
- contact_id BIGINT → nb_crm_contacts (m2o)

**nb_crm_knowledge — 知识库**
- title* VARCHAR(500), content TEXT (textarea/markdown)
- category: 产品FAQ, 技术文档, 操作指南, 故障排除, 最佳实践 (select)
- tags VARCHAR(500)
- view_count INTEGER DEFAULT 0
- status: 草稿, 已发布, 已归档 (select, colors: default/green/grey)

**nb_crm_approvals — 审批记录**
- approval_type: 合同审批, 报价审批, 折扣审批, 退款审批 (select)
- subject* VARCHAR(255), content TEXT
- status: 待审批, 已通过, 已驳回, 已撤回 (select, colors: orange/green/red/grey)
- submitted_at TIMESTAMPTZ, decided_at TIMESTAMPTZ
- decision_remark TEXT
- related_id BIGINT, related_type VARCHAR(100)
- customer_id BIGINT → nb_crm_customers (m2o)

### Relations Summary (define on BOTH sides)
- customers ← contacts (o2m), customers ← opportunities (o2m), customers ← activities (o2m)
- customers ← contracts (o2m), customers ← payments (o2m), customers ← tickets (o2m), customers ← approvals (o2m)
- opportunities ← activities (o2m), opportunities ← quotes (o2m), opportunities → contracts (o2m via customer)
- contracts ← contract_items (o2m), contracts ← payments (o2m)
- products ← contract_items (o2m)
- leads ← lead_pool (o2m)
- contacts ← activities (o2m)

## Pages (12 pages, "CRM系统" menu group with sub-groups)

Menu structure:
- CRM系统 (group, icon: teamoutlined)
  - 客户管理 (sub-group, icon: idcardoutlined)
    - 客户列表, 联系人, 线索管理, 公海池
  - 销售管理 (sub-group, icon: barchartoutlined)
    - 商机管理, 方案报价, 跟进记录, 销售目标
  - 合同回款 (sub-group, icon: containeroutlined)
    - 合同管理, 回款记录, 产品目录
  - 服务支持 (sub-group, icon: tooloutlined)
    - 服务工单

### Page 1: 客户列表
- KPIs: 客户总数, 已签约, 跟进中, 本月新增(filter: createdAt this month)
- Table: name(click), code, customer_type, industry, level, status, city, phone, annual_revenue, createdAt
- Filter: name, industry, level, status
- Form fields: --- 基本信息\nname* | code\ncustomer_type | industry\nscale | level\nstatus | source\n--- 联系方式\nphone | email\nwebsite | fax\n--- 地址\nprovince | city\naddress\n--- 其他\nannual_revenue | employee_count\nremark
- Detail popup (drawer, large): 客户详情 tab + 联系人 sub-table(name,position,mobile,email,is_primary) + 商机 sub-table(title,stage,amount) + 合同 sub-table(title,amount,status)

### Page 2: 联系人
- Table: name(click), customer, position, mobile, email, is_primary, is_decision_maker
- Filter: name, customer
- Form: name* | gender\nposition | department\nphone | mobile\nemail | wechat\nis_primary | is_decision_maker\nbirthday\nremark
- Detail popup (drawer, medium)

### Page 3: 线索管理
- KPIs: 线索总数, 新线索, 跟进中, 已转化
- Table: name(click), company, phone, source, status, score, createdAt
- Filter: name, status, source
- Form: name* | company\nposition | source\nphone | mobile\nemail\nchannel | campaign\nremark
- Detail popup (drawer, medium)

### Page 4: 公海池
- Table: lead_id, reason, status, released_at, claimed_at
- Filter: status

### Page 5: 商机管理
- KPIs: 商机总数, 赢单数(filter: stage=赢单), 总金额(sum hint), 平均概率
- Table: opportunity_no(click), title, customer, stage, amount, probability, expected_close_date
- Filter: title, stage, customer
- Form: title* | opportunity_no\ncustomer_id | contact_id\nstage | source\namount | probability\nexpected_close_date | actual_close_date\ncompetitor | loss_reason\nremark
- Detail popup (drawer, large): 商机详情 + 跟进记录 sub-table(activity_date,subject,activity_type,result) + 报价 sub-table(quote_no,amount,status)

### Page 6: 方案报价
- Table: quote_no(click), title, customer, amount, final_amount, status, valid_until
- Filter: title, status
- Form: quote_no | title*\nopportunity_id | customer_id\namount | discount_rate\nfinal_amount | valid_until\nstatus\nremark
- Detail popup (drawer, medium)

### Page 7: 跟进记录
- Table: activity_date, subject(click), activity_type, customer, opportunity, result, next_date
- Filter: activity_type, customer, result
- Form: subject* | activity_type\ncustomer_id | opportunity_id\ncontact_id | activity_date\nduration | result\ncontent\nnext_action | next_date

### Page 8: 销售目标
- Table: period(click), target_type, target_amount, achieved_amount, target_count, achieved_count, status
- Form: period* | target_type\ntarget_amount | achieved_amount\ntarget_count | achieved_count\nstatus\nremark

### Page 9: 合同管理
- KPIs: 合同总数, 执行中, 合同总额(sum hint), 已回款(sum hint)
- Table: contract_no(click), title, customer, contract_type, amount, paid_amount, status, end_date
- Filter: title, status, customer
- Form: contract_no | title*\ncontract_type | status\ncustomer_id | opportunity_id\namount | paid_amount\nsign_date | start_date\nend_date\npayment_terms\nremark
- Detail popup (drawer, large): 合同详情 + 合同明细 sub-table(product_name,quantity,unit_price,total) + 回款 sub-table(payment_no,amount,payment_date,status)

### Page 10: 回款记录
- Table: payment_no(click), customer, contract, amount, payment_date, payment_method, status
- Form: payment_no | amount*\npayment_date | payment_method\ncontract_id | customer_id\nstatus\nremark

### Page 11: 产品目录
- Table: name(click), code, category, price, cost, unit, status
- Filter: name, category, status
- Form: name* | code\ncategory | status\nprice | cost\nunit\ndescription

### Page 12: 服务工单
- KPIs: 工单总数, 待处理, 处理中, 已解决
- Table: ticket_no(click), subject, customer, ticket_type, priority, status, response_at
- Filter: subject, status, priority, customer
- Form: ticket_no | subject*\nticket_type | priority\ncustomer_id | contact_id\nstatus | satisfaction\ndescription\nremark
- Detail popup (drawer, large)

## Workflows (6)
1. CRM-商机编号: on create opportunities → SQL auto-number "OP-YYYY-NNN"
2. CRM-赢单同步: on update opportunities (stage changed to "赢单") → update customer status to "已签约"
3. CRM-合同编号: on create contracts → SQL auto-number "CT-YYYY-NNN"
4. CRM-回款编号: on create payments → SQL auto-number "PM-YYYY-NNN"
5. CRM-工单编号: on create tickets → SQL auto-number "TK-YYYY-NNN"
6. CRM-报价编号: on create quotes → SQL auto-number "QT-YYYY-NNN"

## AI Employees (3)
1. crm-analyst (CRM数据分析师): query all CRM tables, avatar nocobase-010-female, temperature 0.3
   - Skills: dataModeling-getCollectionNames, dataModeling-getCollectionMetadata, dataSource-dataSourceQuery, dataSource-dataSourceCounting
   - System prompt: 你是CRM数据分析师,可以查询客户/商机/合同/回款等18张数据表,用数据回答业务问题
   - Shortcuts on 客户列表 page: "客户分析", "商机漏斗", "回款统计"

2. crm-assistant (客户助手): form filler + query, avatar nocobase-005-male
   - Skills: frontend-formFiller, dataSource-dataSourceQuery, dataModeling-getCollectionMetadata
   - System prompt: 你是客户助手,帮助填写客户/商机/合同表单,自动补全信息
   - Button on 客户列表 table: "智能填写"

3. crm-service (服务支持): query tickets + knowledge base, avatar nocobase-020-female, temperature 0.5
   - Skills: dataSource-dataSourceQuery, dataModeling-getCollectionMetadata, dataModeling-getCollectionNames
   - System prompt: 你是服务支持助手,可以查询工单和知识库,帮助快速解决客户问题
   - Shortcuts on 服务工单 page: "搜索知识库", "工单统计"

## Test Data (via nb_execute_sql)
Insert realistic Chinese business data:
- 15 customers (mix of industries, levels, statuses)
- 25 contacts across customers
- 10 leads (various stages)
- 5 lead pool entries
- 12 opportunities (various stages with amounts)
- 8 quotes
- 5 competitors
- 20 activities
- 3 targets (monthly)
- 8 contracts (various types and statuses)
- 15 contract items
- 10 payments
- 6 products
- 8 tickets
- 5 knowledge articles
- 3 approvals

## Execution Order (Use Batch Tools!)

### Phase 1: Data Modeling
1. ONE `nb_execute_sql()` — all 18 CREATE TABLE statements
2. ONE `nb_setup_collection()` per table (18 calls) — parent tables first: products, customers, competitors, knowledge → then children in dependency order

### Phase 2: Seed Data
- ONE `nb_execute_sql()` — all INSERT statements (parent tables first for FK integrity)

### Phase 3: Page Building
1. `nb_create_group("CRM系统")` → create sub-groups and pages manually since we have nested groups
2. ONE `nb_crud_page()` per page (12 calls)

### Phase 4: Workflows (6 × 3 calls each)
### Phase 5: AI Employees (3 employees + shortcuts/buttons)

Total: ~50 MCP calls for a full 18-table CRM system.
