# CRM System Build Prompt

Use this prompt with Claude Code (with NocoBase MCP server + skills configured) to build a complete CRM system from scratch.

## Prerequisites

1. NocoBase running (see main README for Docker setup)
2. MCP server configured in `.mcp.json`
3. Skills installed (symlinked to `~/.claude/skills/nocobase/`)

## Launch Command

```bash
claude -p "$(cat <<'PROMPT'
# Build a CRM System in NocoBase

Use the NocoBase MCP tools to build a complete CRM (Customer Relationship Management) system.

## Business Requirements

### Data Model (7 tables, prefix: nb_crm_)

**1. nb_crm_customers — 客户**
- name (客户名称, required)
- code (客户编号)
- customer_type: 企业客户, 个人客户
- industry: 互联网, 金融, 制造, 教育, 医疗, 零售, 其他
- scale: 大型, 中型, 小型, 微型
- source: 官网, 转介绍, 展会, 电销, 广告, 其他
- status: 潜在, 跟进中, 已签约, 已流失 (colors: default, blue, green, red)
- level: A, B, C, D (colors: red, orange, blue, default)
- address, phone, email, website, remark

**2. nb_crm_contacts — 联系人**
- name (required), position, department
- phone, mobile, email, wechat
- is_primary: boolean (主要联系人)
- customer_id → nb_crm_customers (m2o)

**3. nb_crm_opportunities — 商机**
- title (商机名称, required)
- opportunity_no (商机编号, auto-generated)
- stage: 初步接触, 需求确认, 方案报价, 商务谈判, 赢单, 输单 (colors: default, blue, cyan, orange, green, red)
- amount: NUMERIC(12,2) (预计金额)
- probability: INTEGER (成交概率 %)
- expected_close_date: DATE
- source: same as customer source
- remark
- customer_id → nb_crm_customers (m2o)
- contact_id → nb_crm_contacts (m2o)

**4. nb_crm_activities — 跟进记录**
- activity_type: 电话, 拜访, 邮件, 会议, 微信, 其他
- subject (主题, required)
- content (详情, textarea)
- activity_date: DATE
- next_action (下次跟进计划)
- next_date: DATE
- customer_id → nb_crm_customers (m2o)
- opportunity_id → nb_crm_opportunities (m2o, optional)
- contact_id → nb_crm_contacts (m2o, optional)

**5. nb_crm_contracts — 合同**
- contract_no (合同编号)
- title (合同名称, required)
- amount: NUMERIC(12,2)
- status: 草稿, 审批中, 已签署, 执行中, 已完成, 已终止
- sign_date, start_date, end_date: DATE
- remark
- customer_id → nb_crm_customers (m2o)
- opportunity_id → nb_crm_opportunities (m2o, optional)

**6. nb_crm_products — 产品**
- name (required), code
- category: 软件, 硬件, 服务, 咨询, 其他
- price: NUMERIC(12,2) (标准价)
- unit: 套, 个, 年, 月, 次
- status: 在售, 停售 (colors: green, red)
- description

**7. nb_crm_order_items — 订单明细**
- quantity: INTEGER
- unit_price, discount, total: NUMERIC(12,2)
- remark
- contract_id → nb_crm_contracts (m2o)
- product_id → nb_crm_products (m2o)

### Relations Summary
- customers ← contacts (o2m)
- customers ← opportunities (o2m)
- customers ← activities (o2m)
- customers ← contracts (o2m)
- opportunities ← activities (o2m)
- contracts ← order_items (o2m)
- products ← order_items (o2m)

### Pages (6 pages in a "CRM" menu group)

**1. 客户管理**
- KPIs: 客户总数, 已签约, 跟进中, 已流失
- Table: name(clickable), code, customer_type, industry, level, status, phone, createdAt
- Filter: name, industry, level, status
- AddNew + Edit forms (field groups: 基本信息, 联系方式, 其他)
- Detail popup (drawer, large): 客户详情 tab + 联系人 sub-table + 商机 sub-table + 跟进记录 sub-table

**2. 联系人**
- Table: name, customer(关联客户), position, mobile, email, is_primary
- AddNew + Edit forms
- Detail popup (drawer, medium)

**3. 商机管理**
- KPIs: 商机总数, 预计总金额(sum), 赢单数, 平均成交率
- Table: opportunity_no(clickable), title, customer, stage, amount, probability, expected_close_date
- Filter: title, stage, customer
- Detail popup (drawer, large): 商机详情 + 跟进记录 sub-table

**4. 跟进记录**
- Table: activity_date, subject, activity_type, customer, opportunity, next_date
- AddNew form
- Filter: activity_type, customer

**5. 合同管理**
- KPIs: 合同总数, 合同总金额(sum), 执行中, 已完成
- Table: contract_no(clickable), title, customer, amount, status, sign_date, end_date
- Detail popup: 合同详情 + 订单明细 sub-table

**6. 产品目录**
- Table: name, code, category, price, unit, status
- AddNew + Edit
- Filter: name, category, status

### Workflows (4)
1. 商机编号自动生成: on create nb_crm_opportunities → SQL auto-number "OP-YYYY-NNN"
2. 赢单自动同步客户状态: on update opportunities (stage changed to "赢单") → update customer status to "已签约"
3. 合同编号自动生成: on create nb_crm_contracts → SQL auto-number "CT-YYYY-NNN"
4. 合同签署同步商机: on update contracts (status changed to "已签署") → update opportunity stage to "赢单"

### AI Employees (2)
1. crm-analyst (CRM分析师): 数据查询助手, can query all CRM tables, avatar nocobase-010-female
2. crm-assistant (客户助手): 帮助填写表单和查找客户信息, form filler + query, avatar nocobase-005-male

### Test Data
Insert 5-10 records per main table with realistic Chinese business data.

## Execution Order (Use Batch Tools for Speed!)

### Phase 1: Data Modeling (2 steps only!)
1. **One SQL call** — create ALL 7 tables in a single `nb_execute_sql()` call
2. **One `nb_setup_collection()` per table** (7 calls) — each call does register + sync + upgrade ALL fields + create ALL relations in ONE shot. Process parent tables first (customers, products), then child tables.

### Phase 2: Seed Data
- One `nb_execute_sql()` call with all INSERT statements

### Phase 3: Page Building (use nb_crud_page!)
1. `nb_create_menu()` — create CRM menu group + 6 pages (1 call)
2. **One `nb_crud_page()` per page** (6 calls) — each call creates layout + KPIs + filter + table + forms + detail popup in ONE shot

### Phase 4: Workflows
- `nb_create_workflow()` + `nb_add_node()` + `nb_enable_workflow()` for each workflow (4 workflows × 3 calls = 12 calls)

### Phase 5: AI Employees
- `nb_create_ai_employee()` × 2 + `nb_ai_shortcut()` for page integration

### Total: ~30 MCP tool calls (instead of 150+)

After each phase, verify results using nb_list_collections, nb_show_page, nb_list_workflows.
PROMPT
)"
```

## Expected Result

After ~3-5 minutes, Claude Code should produce:
- 7 tables with all fields properly typed (select enums with colors)
- 6 pages with KPIs, tables, filters, forms, detail popups with sub-tables
- 4 automated workflows
- 2 AI employees with page integration
- Test data across all tables

## Customization

Modify the prompt to build any business system:
- **HR System**: employees, departments, attendance, leave, payroll
- **Inventory**: warehouses, products, inbound, outbound, stock checks
- **Project Management**: projects, tasks, milestones, time tracking
- **Help Desk**: tickets, categories, SLA, knowledge base

The key structure is always:
1. Define tables with fields and relations
2. Define pages with blocks and interactions
3. Define automation workflows
4. Define AI assistants
