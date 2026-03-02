# NocoBase Builder Toolkit — 完整使用指南

> 让 AI Agent 用一段描述文字，自动搭建完整的 NocoBase 业务系统。

## 这是什么

一套工具链，把"手动在 NocoBase 界面上点点点搭建系统"变成"写一段描述，让 AI 自动搭建"。

**输入**：一份 prompt 文件（描述数据模型 + 页面 + 工作流 + AI 员工）
**输出**：一套完整可用的 NocoBase 业务系统（表 + 页面 + 工作流 + AI 助手 + 测试数据）

**已验证**：7 套系统、134 张表、74 页面、55 个 JS 增强，支持 Claude Code 和 Kimi Code 两种 Agent。

```
┌─────────────────┐     MCP 工具      ┌──────────────┐
│   AI Agent      │ ──── 55 个 ────→  │   NocoBase   │
│  (Claude/Kimi)  │     HTTP API      │  (Docker)    │
│                 │                    │              │
│  Skills(知识层)  │                    │  FlowModel   │
│  Prompt(需求)    │                    │  PostgreSQL  │
└─────────────────┘                    └──────────────┘
```

---

## 给谁看

| 读者 | 关心什么 | 推荐阅读 |
|------|---------|----------|
| **想试一下的同事** | 5 分钟跑通一个 Demo | [快速体验](#快速体验5-分钟) |
| **想用 Agent 搭系统的人** | 怎么写 prompt、怎么跑 | [搭建流程](#搭建流程) |
| **想二次开发的开发者** | 工具链架构、扩展方法 | [工具链架构](#工具链架构) |
| **想了解原理的人** | 为什么能工作、局限在哪 | [原理和局限](#原理和局限) |

---

## 快速体验（5 分钟）

### 前提

- 一台可以跑 Docker 的机器
- Python 3.10+
- 安装了 Claude Code 或 Kimi Code

### 第 1 步：启动 NocoBase

```bash
mkdir nocobase-app && cd nocobase-app

cat > docker-compose.yml << 'EOF'
version: '3'
services:
  app:
    image: nocobase/nocobase:latest
    ports:
      - "14000:80"
    environment:
      - APP_KEY=your-secret-key
      - DB_DIALECT=postgres
      - DB_HOST=db
      - DB_PORT=5432
      - DB_DATABASE=nocobase
      - DB_USER=nocobase
      - DB_PASSWORD=nocobase
    depends_on:
      - db
    volumes:
      - app-storage:/app/storage
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: nocobase
      POSTGRES_PASSWORD: nocobase
      POSTGRES_DB: nocobase
    ports:
      - "5435:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
volumes:
  app-storage:
  db-data:
EOF

docker compose up -d

# 等待启动（首次约 2 分钟）
until curl -s http://localhost:14000/api/app:getLang > /dev/null 2>&1; do
  sleep 5 && echo "等待中..."
done
echo "NocoBase 就绪：http://localhost:14000"
# 默认账号：admin@nocobase.com / admin123
```

### 第 2 步：安装 MCP Server

```bash
cd /path/to/nocobase-mcp-skills/mcp-server
pip install -e .
```

### 第 3 步：准备构建目录

```bash
mkdir /tmp/build-crm && cd /tmp/build-crm

# 1. MCP 配置
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "nocobase": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-server", "nocobase-mcp"],
      "env": {
        "NB_URL": "http://localhost:14000",
        "NB_USER": "admin@nocobase.com",
        "NB_PASSWORD": "admin123",
        "NB_DB_URL": "postgresql://nocobase:nocobase@localhost:5435/nocobase"
      }
    }
  }
}
EOF

# 2. 复制 Agent 指令和系统 Prompt
cp /path/to/nocobase-mcp-skills/examples/prompts/CLAUDE.md .
cp /path/to/nocobase-mcp-skills/examples/prompts/crm.txt ./prompt.txt
```

### 第 4 步：启动 Agent

```bash
# Claude Code（推荐）
claude -p "$(cat prompt.txt)" --model sonnet --max-turns 80

# 或 Kimi Code
kimi -w . --mcp-config-file .mcp.json -y --max-steps-per-turn 80 \
  -p "$(cat CLAUDE.md) $(cat prompt.txt)"
```

### 第 5 步：等待完成

Agent 会自动执行 5 个阶段（约 60-80 次工具调用，10-15 分钟）：

```
Phase 1  建表建模  ███████████████████████  ~16 调用  (~2 min)
Phase 2  测试数据  █████                    ~5 调用   (~1 min)
Phase 3  搭建页面  ████████████████████████  ~15 调用  (~5 min)
Phase 4  工作流    ██████████████████        ~12 调用  (~3 min)
Phase 5  AI 员工   ████████                  ~8 调用   (~2 min)
```

完成后打开 http://localhost:14000 看成果。

---

## 搭建流程

### 概览

```
需求文档 → prompt.txt → Agent 自动搭建 → 人工验收 → 微调
```

整个流程分 3 个角色：

| 角色 | 做什么 | 需要什么能力 |
|------|--------|------------|
| **需求方** | 提供业务需求（表/页面/流程） | 了解业务 |
| **Prompt 编写者** | 把需求翻译成 prompt.txt | 了解 NocoBase 概念（表/页面/工作流） |
| **Agent** | 自动执行 MCP 工具搭建系统 | 不需要人工干预 |

### 第一步：写 Prompt

Prompt 文件是整个搭建的唯一输入。它定义 5 个部分：

```
prompt.txt
├── 数据模型（表名、字段、类型、选项、关系）
├── 页面设计（菜单结构、KPI、表格列、表单字段、弹窗）
├── 工作流（触发条件、自动编号、状态联动）
├── AI 员工（角色、技能、页面入口）
└── 测试数据（每表数量）
```

**最简示例**（3 张表的项目管理）：

```
# Build Project Management System

Table prefix: nb_pm_

## Data Model (3 tables)

**nb_pm_projects** — name* VARCHAR(255), code VARCHAR(50),
  status(select:规划中/进行中/已完成/已归档, colors:blue/orange/green/grey),
  start_date DATE, end_date DATE, description TEXT

**nb_pm_tasks** — title* VARCHAR(255),
  status(select:待办/进行中/已完成, colors:default/blue/green),
  priority(select:高/中/低, colors:red/orange/blue),
  assignee VARCHAR(100), due_date DATE, description TEXT,
  project_id→nb_pm_projects(m2o)

**nb_pm_categories** — name* VARCHAR(100), code VARCHAR(50),
  description TEXT

### Relations
projects←tasks

## Pages (3 pages, "项目管理" group icon:projectoutlined)

1. 项目列表 — cols(name,code,status,start_date,end_date,createdAt),
   form(name*|code\nstatus\nstart_date|end_date\ndescription),
   detail:[项目详情, 任务列表 sub(title,status,priority,assignee,due_date)]

2. 任务列表 — cols(title,project,status,priority,assignee,due_date,createdAt),
   filter(title,status,priority),
   form(title*|project_id\nstatus|priority\nassignee|due_date\ndescription)

3. 分类管理 — cols(name,code,description,createdAt),
   form(name*|code\ndescription)

## Execution
Phase 1: SQL DDL → nb_setup_collection × 3
Phase 2: INSERT test data (5 projects, 15 tasks, 5 categories)
Phase 3: nb_create_menu + nb_crud_page × 3
```

**完整示例参考** `examples/prompts/` 目录：
- `crm.txt` — 客户关系管理（16 表 12 页面 6 工作流 3 AI 员工）
- `hrm.txt` — 人力资源管理（14 表 10 页面 5 工作流 2 AI 员工）
- `edu.txt` — 教务管理（13 表 12 页面 5 工作流 2 AI 员工）
- `itsm.txt` — IT 服务管理（13 表 10 页面 5 工作流 2 AI 员工）
- `wms.txt` — 仓储管理（14 表 12 页面 5 工作流 2 AI 员工）

### Prompt 编写规则

**数据模型部分**：

```
# 格式：表名 — 字段定义, 关系

nb_crm_customers — name* VARCHAR(255),       # * 表示必填
  status(select:潜在/跟进中/已签约),            # select 类型要列出选项
  colors:default/blue/green),                  # 选项颜色
  phone VARCHAR, amount NUMERIC(14,2),         # 常规字段
  department_id→nb_crm_departments(m2o)        # 关系
```

**页面部分**：

```
# 表格列：JSON 数组
cols(name, status, amount, createdAt)      # 始终包含 createdAt

# 表单字段：DSL 语法
form(
  --- 基本信息                               # 分隔线
  name* | code                              # 两列并排，name 必填
  status | priority                         # 两列并排
  --- 详情
  description                               # 全宽
)

# KPI：标题 + 筛选条件 + 颜色
KPIs(总数, 进行中/filter:status=进行中/color:#1890ff, 已完成/filter:status=已完成/color:#52c41a)

# 详情弹窗：多 Tab
detail:[主表详情, 子表1 sub(col1,col2,col3), 子表2 sub(col1,col2)]
```

**关键注意事项**：

1. SQL DDL 里 **不要写** `created_at, updated_at, created_by_id, updated_by_id` — 系统自动添加
2. `form_fields` 是 DSL 字符串（`"name* | code\nstatus"`），**不是** JSON 数组
3. `table_fields` 是 JSON 数组（`'["name","code","createdAt"]'`），**始终包含** `"createdAt"`
4. 父表在子表前面（外键顺序）
5. 表前缀统一（如 `nb_crm_`），不要跨前缀操作

### 第二步：启动 Agent

三个文件放在同一目录：

```
build-dir/
├── .mcp.json        # MCP server 配置
├── CLAUDE.md        # Agent 指令（工具使用规则）
└── prompt.txt       # 系统定义（你写的）
```

然后执行：

```bash
# Claude Code（推荐，最稳定）
claude -p "$(cat prompt.txt)" --model sonnet --max-turns 80

# 也可以用 --dangerously-skip-permissions 免确认（自担风险）
claude -p "$(cat prompt.txt)" --model sonnet --max-turns 80 --dangerously-skip-permissions
```

### 第三步：验收和微调

Agent 搭完后，打开 NocoBase 检查：

1. **菜单结构** — 侧边栏有没有正确的分组和页面
2. **表格** — 列是否正确、排序是否合理
3. **新增表单** — 字段是否齐全、必填是否正确、布局是否合理
4. **详情弹窗** — 能不能打开、子表是否正常
5. **工作流** — 新增一条记录，看自动编号、状态联动是否触发

发现问题怎么办？→ 看下一节[故障处理](#故障处理)

---

## 故障处理

### 常见问题和解决方法

#### 1. Agent 中途断了 / 没搭完

**症状**：Agent 达到 max-turns 限制退出，或网络断开。

**处理**：
```bash
# 查看 notes.md 看做到哪了
cat notes.md

# 继续（交互模式，告诉 Agent 从哪里继续）
claude
> 读 notes.md，从 Phase 3 继续搭建页面。
```

**预防**：用 `--max-turns 80`（不要太小），确保网络稳定。

#### 2. 表单里字段报错 "Field may have been deleted"

**症状**：打开新增表单，某个字段位置显示错误提示。

**原因**：prompt 里写的字段名和实际 collection 的字段名不一致（比如写了 `title` 但实际是 `asset_name`）。

**处理**：
```bash
# 让 Agent 检查并修复
claude
> 用 nb_fields("nb_am_purchase_requests") 查看可用字段，
> 然后用 nb_inspect_page("采购申请") 看当前页面结构，
> 修复引用了不存在字段的表单项。
```

**v2 版本改进**：`nb_page_builder` 现在会自动警告不存在的字段名并建议正确名称：
```
⚠️  'title' not in 采购申请(nb_am_purchase_requests).
    (26 fields — use nb.fields('nb_am_purchase_requests') to see all)
⚠️  'approval_note' not in 采购申请(nb_am_purchase_requests).
    maybe: ['applicant', 'approval_remark']
```

#### 3. nb_crud_page 失败

**症状**：Agent 调用 `nb_crud_page` 时报错。

**重要**：**不要让 Agent 改用单独的工具（nb_table_block + nb_addnew_form + ...）去拼凑**。这是最常见的错误恢复方式，但会导致页面结构不完整。

**正确处理**：
```bash
# 1. 看错误信息，通常是参数格式问题
#    - form_fields 传了 JSON 数组（应该是 DSL 字符串）
#    - table_fields 传了字符串（应该是 JSON 数组）
#    - 字段名不存在

# 2. 让 Agent 修正参数重试
> nb_crud_page 刚才失败了，错误是 XXX。
> 用 nb_fields("collection_name") 检查字段名，修正后重试 nb_crud_page。
```

#### 4. 表格渲染报错 "getColumnProps is not a function"

**症状**：页面上的表格区域显示红色错误。

**原因**：TableColumnModel 的 Display 子节点缺失或配置异常。

**处理**：
```bash
claude
> 用 nb_inspect_page("页面名") 查看表格结构。
> 用 nb_clean_tab 清除该页面内容，然后用 nb_crud_page 重建。
```

#### 5. 工作流没触发

**症状**：创建记录后，自动编号没生成或状态没联动。

**检查步骤**：
1. 在 NocoBase 后台 → 工作流管理 → 确认工作流是否已启用（绿色状态）
2. 检查触发条件：是 create 还是 update？collection 名对不对？
3. 查看执行历史中的错误信息

**处理**：
```bash
claude
> 用 nb_list_workflows 列出所有工作流。
> 检查 CRM 开头的工作流，确认它们都已启用。
> 如果没启用，用 nb_enable_workflow 启用。
```

#### 6. 想从零重建

**症状**：搭的系统问题太多，想全部删掉重来。

```bash
# 方法 1：用 Agent 清理
claude
> 用 nb_clean_prefix("nb_crm_") 删除所有 CRM 的表和 collection。
> 然后在 NocoBase 后台手动删除菜单组。
> 读 prompt.txt 重新搭建。

# 方法 2：Docker 全量重置（核弹选项）
docker compose down -v
docker compose up -d
# 等待重新初始化...
```

### 故障处理决策树

```
搭建出了问题
  │
  ├── Agent 没搭完 → 读 notes.md，交互模式继续
  │
  ├── 页面有错
  │    ├── 个别字段错 → nb_inspect_page → nb_patch_field / nb_remove_field
  │    ├── 表格整体坏 → nb_clean_tab → nb_crud_page 重建该页面
  │    └── 所有页面都有问题 → nb_clean_prefix → 全部重建
  │
  ├── 工作流不工作
  │    ├── 没启用 → nb_enable_workflow
  │    ├── 触发条件错 → 删除重建
  │    └── SQL 语法错 → 查看执行历史修正
  │
  └── 想全部重来 → nb_clean_prefix → 重跑 prompt
```

---

## 工具链架构

### 三层设计

```
  ┌──────────────────────────────────────────┐
  │  Knowledge Layer (Skills + Prompt)       │  告诉 Agent "做什么"和"怎么做"
  │  ┌───────────┐  ┌─────────────────────┐ │
  │  │  4 Skills  │  │  CLAUDE.md + prompt │ │
  │  │  (领域知识) │  │  (构建指令+系统定义) │ │
  │  └───────────┘  └─────────────────────┘ │
  ├──────────────────────────────────────────┤
  │  Capability Layer (MCP Server)           │  Agent 能"调用什么"
  │  55 个 MCP 工具                           │
  │  ┌─────────────────────────────────────┐ │
  │  │ 建模(10) 路由(5) 页面(15) 检查(12)  │ │
  │  │ AI员工(7) 工作流(7)                  │ │
  │  └─────────────────────────────────────┘ │
  ├──────────────────────────────────────────┤
  │  Target Layer (NocoBase)                 │  实际执行的系统
  │  FlowModel API + PostgreSQL              │
  └──────────────────────────────────────────┘
```

### 核心 MCP 工具（Agent 最常用的 6 个）

| 工具 | 一句话 | 调用次数/系统 |
|------|--------|-------------|
| `nb_execute_sql` | 执行 SQL（建表、插入数据） | 2-5 次 |
| `nb_setup_collection` | 注册+同步+升级+关系（一次搞定一张表） | N 次（每表一次） |
| `nb_create_menu` | 创建菜单组+页面路由 | 1-3 次 |
| `nb_crud_page` | 一次搞定整个 CRUD 页面 | N 次（每页一次） |
| `nb_create_workflow` | 创建工作流 | 每工作流 1 次 |
| `nb_create_ai_employee` | 创建 AI 员工 | 每员工 1 次 |

### 辅助工具（排错和增强）

| 工具 | 用途 |
|------|------|
| `nb_fields` | **查看 collection 可用字段**（搭建前检查） |
| `nb_inspect_page` | 查看页面结构（排错） |
| `nb_inspect_all` | 批量查看所有页面（排错） |
| `nb_read_node` | 读取节点详细配置 |
| `nb_patch_field` | 修改表单字段属性 |
| `nb_add_column` / `nb_remove_column` | 增删表格列 |
| `nb_clean_tab` | 清空页面内容（重建前） |
| `nb_clean_prefix` | 按前缀删除所有表（重来时用） |

### 字段校验机制

v2 版本新增了软校验——Agent 使用不存在的字段名时自动警告：

```python
# Agent 调用
nb_crud_page(tab, "nb_am_requests", '["title","status"]', "title* | urgency")

# 返回结果中包含 warnings：
{
  "grid_uid": "...",
  "warnings": [
    "field 'title' not in 采购申请(nb_am_requests). (26 fields — use nb.fields('nb_am_requests') to list)",
    "field 'urgency' not in 采购申请(nb_am_requests). maybe: ['approval_remark']"
  ]
}
```

Agent 看到 warnings 就知道字段名不对，可以调 `nb_fields` 查正确名称后重试。

---

## 原理和局限

### 为什么能工作

1. **NocoBase 是配置驱动**：所有页面/表单/工作流都是 JSON 配置（FlowModel），可以通过 API 精确控制
2. **MCP 抹平了 API 复杂度**：原始 API 需要 5-10 次调用才能建一个表单，`nb_crud_page` 一次搞定
3. **Prompt 结构化**：字段类型、表单布局、KPI 筛选条件都用约定格式描述，Agent 不需要猜
4. **Skills 提供领域知识**：Agent 知道"先建父表再建子表""表单用 DSL 不用 JSON"等规则

### 当前局限

| 局限 | 影响 | 缓解方式 |
|------|------|---------|
| JS 沙箱无外部库 | 不能用 ECharts，只能用 antd 组件做图表 | 用 antd Progress/Statistic 替代 |
| 无 GROUP BY API | 图表数据聚合只能客户端全量获取后 JS 处理 | `paginate: false` + forEach |
| Agent 偶尔猜字段名 | 页面引用不存在的字段导致渲染错误 | v2 字段校验 + `nb_fields` 工具 |
| 事件流较复杂 | Agent 做简单事件流（自动计算）可靠，复杂级联不稳定 | 提供代码模板减少自由发挥 |
| Kimi 稳定性 | Kimi 2.5 偶尔断连（peer closed connection） | 用 Claude Code 或断后重连 |
| max-turns 不够 | 大系统需要 60-80 次调用，默认值可能不够 | 设置 `--max-turns 80` |

### 路线图

```
✅ L1 数据建模     — SQL+API 自动建表、字段升级、关系
✅ L2 页面搭建     — CRUD 页面、KPI、筛选、弹窗
✅ L3 JS 列级增强  — 状态标签、金额格式化、日期倒计时
🔶 L4 页面级增强   — 图表区块、复杂事件流、详情弹窗 JS
⬜ L5 端到端自动化  — 需求→设计→搭建→验证 全自动
```

---

## 项目文件结构

```
nocobase-mcp-skills/
├── mcp-server/                  # MCP Server（核心）
│   ├── src/nocobase_mcp/
│   │   ├── server.py            # FastMCP 入口
│   │   ├── client.py            # NocoBase HTTP 客户端
│   │   └── tools/               # 7 个工具模块
│   │       ├── collections.py   # 建模工具 (10)
│   │       ├── fields.py        # 字段工具
│   │       ├── routes.py        # 路由/菜单工具 (5)
│   │       ├── pages.py         # 页面搭建工具 (15)
│   │       ├── page_tool.py     # 页面检查/维护工具 (12)
│   │       ├── workflows.py     # 工作流工具 (7)
│   │       └── ai_employee.py   # AI 员工工具 (7)
│   └── pyproject.toml
│
├── skills/                      # Skills 知识层（Claude Code 专用）
│   ├── nocobase-data-modeling/  # 数据建模知识
│   ├── nocobase-page-building/  # 页面搭建知识
│   ├── nocobase-workflow/       # 工作流知识
│   └── nocobase-ai-employee/    # AI 员工知识
│
├── examples/
│   ├── prompts/                 # Prompt 模板（5 套系统 + 辅助 prompt）
│   │   ├── CLAUDE.md            # Agent 通用指令
│   │   ├── crm.txt              # CRM 系统定义
│   │   ├── hrm.txt              # HRM 系统定义
│   │   ├── edu.txt              # 教务系统定义
│   │   ├── itsm.txt             # ITSM 系统定义
│   │   ├── wms.txt              # WMS 系统定义
│   │   ├── js-enhance-prompt.md # JS 增强 Agent prompt
│   │   └── js-sandbox-reference.md  # JS 沙箱代码参考
│   │
│   └── asset-management/        # 脚本化 Demo（23 表 20 页面）
│       ├── nb-am-setup.py       # 1. 数据建模
│       ├── nb-am-field-upgrade.py # 2. 字段升级
│       ├── nb-am-pages.py       # 3. 页面搭建
│       ├── nb-am-workflows.py   # 4. 工作流
│       ├── nb-am-events.py      # 5. 事件流
│       ├── nb-am-js-blocks.py   # 6. JS 增强
│       ├── nb-am-ai-employees.py # 7. AI 员工
│       ├── nb-am-seed-data.py   # 8. 测试数据
│       ├── nb_page_builder.py   # 页面构建库
│       ├── nb_workflow_builder.py # 工作流构建库
│       ├── nb-save-templates.py # 自动保存弹窗模板
│       └── nb-block-registry.py # 区块映射注册表
│
├── docs/
│   ├── guide.md                 # 本文档
│   └── api-patterns.md          # API 研究笔记
│
├── README.md                    # 项目 README
└── CLAUDE.md                    # 项目级 Agent 指令
```

---

## 附录 A：写 Prompt 的参考语法

### 字段类型

```
name VARCHAR(255)              → input 文本框
description TEXT               → textarea 多行文本
amount NUMERIC(14,2)           → number 数字（2位小数）
count INTEGER                  → integer 整数
start_date DATE                → date 日期选择
created_at TIMESTAMPTZ         → datetime 日期时间
is_active BOOLEAN              → checkbox 复选框
status(select:选项1/选项2)      → select 下拉选择
colors:red/blue)               → 选项颜色
customer_id→nb_crm_xxx(m2o)    → 多对一关系
```

### 表单 DSL 语法

```
name*                          单个字段，全宽，必填
name | code                    两列并排
name:16 | code:8               指定列宽（总和=24）
--- 标题                        分隔线（带标题）
---                            分隔线（无标题）
```

### KPI JSON 格式

```json
[
  {"title": "总数"},
  {"title": "进行中", "filter": {"status": "进行中"}, "color": "#1890ff"},
  {"title": "已完成", "filter": {"status": "已完成"}, "color": "#52c41a"}
]
```

### 详情弹窗 JSON 格式

```json
[
  {"title": "详情", "fields": "name | code\nstatus | priority\ndescription"},
  {"title": "任务", "assoc": "tasks", "coll": "nb_pm_tasks", "fields": ["title","status","due_date"]}
]
```

---

## 附录 B：已验证系统清单

| 系统 | 表数 | 页面 | 工作流 | AI 员工 | JS 增强 | 验证 Agent |
|------|------|------|--------|---------|---------|------------|
| AM（资产管理） | 23 | 20 | 13 | 4 | 21 列+2 卡片 | 脚本化 |
| CRM（客户管理） | 16 | 12 | 6 | 3 | 16 列+5 事件流 | Claude |
| HRM（人力资源） | 14 | 10 | 5 | 2 | 12 列 | Kimi |
| EDU（教务管理） | 13 | 12 | 5 | 2 | 18 列+4 事件流 | Claude |
| ITSM（IT服务） | 13 | 10 | 5 | 2 | — | Kimi |
| WMS（仓储管理） | 14 | 12 | 5 | 2 | — | Claude |
| PM（项目管理） | 21 | 5 | — | — | — | 脚本化 |
