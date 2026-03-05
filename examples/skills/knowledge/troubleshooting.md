---
name: nocobase-troubleshooting
description: Debug common page building issues — detail popups, subtables, associations, JS items
triggers:
  - error
  - Cannot read
  - 报错
  - debug
  - 排查
  - subtable
  - association
  - detail
tools:
  - nb_inspect_page
  - nb_inspect_all
  - nb_read_node
  - nb_find_placeholders
  - nb_list_fields
---

# NocoBase Page Troubleshooting Guide

## Quick Diagnostic Flow

```
页面报错？
  ├── "Cannot read properties of undefined (reading 'collection')"
  │   → 子表 association 缺失 → 见 §1
  ├── 详情弹窗空白
  │   → ChildPageModel 结构问题 → 见 §2
  ├── JS 占位符没生效
  │   → inject_js 注入问题 → 见 §3
  ├── 表单事件不触发
  │   → flowRegistry 结构问题 → 见 §4
  └── 字段不显示 / 多余字段
      → 字段名不匹配 → 见 §5
```

---

## §1 子表 Association 错误

### 症状
```
Cannot read properties of undefined (reading 'collection')
```
常见于：详情弹窗中的关联子表标签页（如"联系人"、"关联商机"）

### 根因
子表 TableBlockModel 的 `resourceSettings.init` 缺少 `association` 字段。

### 排查步骤

1. **定位子表节点 UID**
```
nb_inspect_page(tab_uid)
→ 找到详情弹窗下的 TableBlockModel
→ 记录 UID
```

2. **读取节点确认**
```
nb_read_node(uid, "resource")
→ 检查 resourceSettings.init:
   ✓ collectionName = "nb_crm_contacts"      (有)
   ✗ association = "nb_crm_customers.contacts" (缺失！)
```

3. **检查 o2m 关系是否存在**
```
nb_list_fields("nb_crm_customers")
→ 搜索 interface=o2m 的字段
→ 应有 contacts / opportunities / contracts
```

### 修复

**情况 A：o2m 关系不存在**
```
nb_setup_collection("nb_crm_customers", "客户",
  relations_json='[{"field":"contacts","type":"o2m","target":"nb_crm_contacts","foreign_key":"customer_id"}]')
```

**情况 B：association 字段缺失**

用 nb_read_node 读取完整节点 → 补充 association → nb_update_node 保存。

或者重建该 detail popup 页面，确保 XML markup 中 `<subtable>` 有 `assoc` 属性：
```xml
<subtable collection="nb_crm_contacts" assoc="contacts" fields="name,phone,position" />
```

### 预防

XML markup 中的 `<subtable>` **必须同时提供**：
- `collection` — 子表 collection 名
- `assoc` — 父表上的 o2m 关系字段名
- `fields` — 子表要显示的字段列表

---

## §2 详情弹窗结构

### 正确的节点层级

```
TableBlockModel (主表)
  └─ TableColumnModel (首列，带 popupSettings)
       └─ ChildPageModel (详情弹窗根节点)
            ├─ ChildPageTabModel (标签页 1)
            │    └─ BlockGridModel
            │         ├─ DetailsBlockModel (字段详情)
            │         │    └─ DetailGridModel → DisplayFieldModel...
            │         ├─ JSBlockModel (JS 可视化块)
            │         ├─ JSItemModel (JS 表单项)
            │         └─ TableBlockModel (关联子表)
            │              ↑ 必须有 association!
            └─ ChildPageTabModel (标签页 2)
                 └─ ...
```

### 关键属性

| 节点 | 关键 stepParams | 说明 |
|------|----------------|------|
| ChildPageModel | `enableTabs: true` | 多标签页必须开启 |
| TableColumnModel (首列) | `popupSettings.openView` | 控制弹窗打开方式 |
| DetailsBlockModel | `resourceSettings.init.collectionName` | 读哪个 collection |
| DetailsBlockModel | `resourceSettings.init.filterByTk` | `{{ ctx.view.inputArgs.filterByTk }}` |
| TableBlockModel (子表) | `resourceSettings.init.association` | `{parentColl}.{assocField}` |
| TableBlockModel (子表) | `resourceSettings.init.sourceId` | `{{ ctx.view.inputArgs.filterByTk }}` |

### XML Markup 详情弹窗示例

```xml
<detail>
  <!-- Tab 1: 字段详情 + JS 可视化 -->
  <tab title="基本信息" fields="name|code\nstatus|industry">
    <js-item title="状态时间线">
      显示记录从创建到当前的状态变化历史
    </js-item>
  </tab>

  <!-- Tab 2: 关联子表 -->
  <tab title="联系人">
    <subtable collection="nb_crm_contacts" assoc="contacts" fields="name,phone,position" />
  </tab>

  <!-- Tab 3: JS 可视化仪表板 -->
  <tab title="统计">
    <js-block title="回款进度">
      环形进度条显示已回款/合同总额比例
    </js-block>
    <js-block title="跟进时间线">
      按时间倒序展示跟进记录的时间线
    </js-block>
  </tab>
</detail>
```

---

## §3 JS 占位符问题

### 占位符没被替换

```
nb_find_placeholders("CRM")
→ 检查还有哪些 __placeholder__ 没实现
→ 对每个: nb_inject_js(uid, code)
```

### inject_js 返回成功但页面仍显示占位符

可能原因：
- 浏览器缓存 → 强制刷新 (Ctrl+Shift+R)
- 注入了错误的 UID → `nb_read_node(uid, "js")` 确认代码已更新

### JS 代码执行报错

```
nb_read_node(uid, "js")
→ 检查代码语法
→ 常见问题:
   - ctx.record 在表格上下文中可能为 undefined → 用 ctx.record || {}
   - (async () => { ... })() 中忘记 catch → 页面白屏
   - createElement 拼写错误 → const h = ctx.React.createElement
```

---

## §4 事件流问题

### 事件不触发

检查 flowRegistry 结构：
```
nb_read_node(form_uid, "flow")
→ flowRegistry 应有:
   {
     "随机key": {
       "on": { "eventName": "formValuesChange" },
       "steps": {
         "随机key": {
           "use": "RunScript",
           "defaultParams": { "code": "..." }
         }
       }
     }
   }
```

关键点：
- eventName 必须精确：`formValuesChange` / `beforeRender` / `afterSuccess`
- 事件挂在 **CreateFormModel / EditFormModel** 上，不是 ActionModel
- XML 中 `<event>` 必须放在 `<addnew>` 或 `<edit>` 内部

### 常见 eventName

| 事件 | 触发时机 | 典型用途 |
|------|---------|---------|
| `formValuesChange` | 表单字段值变化 | 自动计算、级联选择、概率映射 |
| `beforeRender` | 表单渲染前 | 自动填充默认值（日期、编号） |
| `afterSuccess` | 表单提交成功后 | 刷新列表、显示提示 |

---

## §5 字段不显示

### 排查

```
nb_list_fields("nb_crm_customers")
→ 确认字段名拼写 (Python snake_case)
→ NocoBase 用驼峰: customer_id → customerId
   但 DDL 中的 snake_case 字段 sync 后保持原名
```

### 常见原因

- DDL 中写了 `customer_name` 但 XML 中用了 `customerName`
- 字段在 DDL 中但没有 `nb_sync_fields()` 同步
- relation 字段（m2o）显示为空 → 检查 foreignKey 对应的 DB 列是否有数据
- 系统字段（createdAt）始终可用，不需要在 DDL 中声明

---

## 源码导航索引

### 层级架构

```
XML Markup (agent 写)
    ↓ parse()
markup_parser.py          解析 XML → TreeNode 树
    ↓ 调用
tree_builder.py           构建 TreeNode（FlowModel 内存对象）
    ↓ save_nested()
client.py                 序列化 → API 调用
    ↓ POST
NocoBase flowModels:save  持久化到数据库
```

### 关键源码文件

| 文件 | 行号 | 方法 | 职责 |
|------|------|------|------|
| `markup_parser.py` | 50 | `parse()` | XML 解析入口 |
| `markup_parser.py` | 60 | `_sanitize_markup()` 之后 | 转义 `<` `&` 等特殊字符 |
| `markup_parser.py` | 193 | `_parse_element()` → table | 处理 `<table>` 及子元素 |
| `markup_parser.py` | 217 | `_parse_element()` → detail | 处理 `<detail>` |
| `markup_parser.py` | 298 | `_parse_detail()` | 解析详情弹窗标签页 |
| `markup_parser.py` | 327 | `_parse_detail()` → js-item | 标签页内 JS 项 |
| `markup_parser.py` | 366 | `_parse_events()` | 解析 `<event>` 并挂到表单 |
| | | | |
| `tree_builder.py` | 785 | `placeholder_js_item()` | JS 项占位符 |
| `tree_builder.py` | 770 | `placeholder_js_block()` | JS 块占位符 |
| `tree_builder.py` | 755 | `placeholder_js_col()` | JS 列占位符 |
| `tree_builder.py` | 800 | `placeholder_event()` | 事件流占位符 |
| `tree_builder.py` | 824 | `addnew_form()` | 新增表单子树 |
| `tree_builder.py` | 852 | `edit_action()` | 编辑表单子树 |
| `tree_builder.py` | 885 | `_build_tab_blocks()` | 详情标签页内容构建 |
| `tree_builder.py` | 965 | `_sub_table_node()` | 关联子表（含 association） |
| `tree_builder.py` | 1034 | `detail_popup()` | 详情弹窗入口 |
| | | | |
| `client.py` | 648 | `save_nested()` | 整棵树一次保存 |
| `client.py` | 1608 | `find_placeholders()` | 发现占位符 |
| `client.py` | 1741 | `inject_js()` | 注入 JS 代码 |
| `client.py` | 1757 | `inject_event()` | 注入事件代码 |
| | | | |
| `models.py` | 13 | `DISPLAY_MAP` | 详情字段类型映射 |
| `models.py` | 50 | `EDIT_MAP` | 编辑字段类型映射 |
| `models.py` | 188 | JSItemModel | JS 表单/详情项 |

### 详情弹窗数据流

```
XML:  <detail>
        <tab title="信息" fields="name|code">
          <js-item title="时间线">描述</js-item>
        </tab>
        <tab title="联系人">
          <subtable collection="nb_crm_contacts" assoc="contacts" fields="name,phone" />
        </tab>
      </detail>

      ↓ markup_parser._parse_detail()        [L298]

tabs = [
  {"title":"信息", "blocks": [
    {"type":"details", "fields":"name|code"},
    {"type":"js", "title":"时间线", "code":"<placeholder>"}
  ]},
  {"title":"联系人", "blocks": [
    {"type":"sub_table", "assoc":"contacts", "coll":"nb_crm_contacts", "fields":["name","phone"]}
  ]}
]

      ↓ tree_builder.detail_popup(coll, tabs)  [L1034]

ChildPageModel
  ├─ ChildPageTabModel("信息")
  │    └─ BlockGridModel
  │         ├─ DetailsBlockModel       ← _build_tab_blocks L900
  │         │    └─ detail_grid()
  │         └─ JSBlockModel            ← _build_tab_blocks L911
  └─ ChildPageTabModel("联系人")
       └─ BlockGridModel
            └─ TableBlockModel         ← _build_tab_blocks L919 → _sub_table_node L965
                 resourceSettings.init:
                   collectionName: "nb_crm_contacts"
                   association: "nb_crm_customers.contacts"    ← 关键！
                   sourceId: "{{ctx.view.inputArgs.filterByTk}}"
```

---

## 详情页 JS 增强指南

### 可用的 JS 节点类型

| 类型 | Model | 位置 | 上下文 | 用途示例 |
|------|-------|------|--------|---------|
| JS Column | JSColumnModel | 表格列 | `ctx.record` = 当前行 | 复合列、金额格式、倒计时 |
| JS Block | JSBlockModel | 页面区块 / 详情 Tab 内 | `ctx.model` = 当前块 | 图表、统计卡片、漏斗 |
| JS Item | JSItemModel | 表单内 / 详情内 | `ctx.model` = 当前表单 | 时间线、进度指示器、提示信息 |
| Event | flowRegistry | CreateForm / EditForm | `ctx.form` = 表单实例 | 自动计算、级联、校验 |

### JS Item 特点（detail/form 上下文）

JS Item 天然拥有表单对象上下文：
```js
// 在详情页中，可以访问当前记录
const record = ctx.model?.record || {};
const h = ctx.React.createElement;

// 示例：显示状态变化时间线
const steps = [
  { label: '创建', time: record.createdAt, done: true },
  { label: '跟进中', time: record.follow_date, done: record.status !== '新客户' },
  { label: '已签约', time: record.sign_date, done: record.status === '已签约' },
];
ctx.render(h('div', { style: { padding: 8 } },
  steps.map((s, i) => h('div', { key: i, style: { display: 'flex', gap: 8, opacity: s.done ? 1 : 0.4 } },
    h('span', { style: { color: s.done ? '#52c41a' : '#d9d9d9' } }, s.done ? '●' : '○'),
    h('span', null, s.label),
    s.time && h('span', { style: { color: '#8c8c8c', fontSize: 12 } }, new Date(s.time).toLocaleDateString())
  ))
));
```

### 详情页丰富内容建议

#### 客户详情
```xml
<detail>
  <tab title="基本信息" fields="name|code\nstatus|grade\nindustry|city">
    <js-item title="客户画像">
      显示等级标签(A/B/C/D彩色)、行业标签、创建天数、最近跟进距今天数
    </js-item>
  </tab>
  <tab title="联系人">
    <subtable collection="nb_crm_contacts" assoc="contacts" fields="name,phone,position,is_primary" />
  </tab>
  <tab title="商机">
    <subtable collection="nb_crm_opportunities" assoc="opportunities" fields="title,stage,amount,probability" />
    <js-block title="商机漏斗">按 stage 分组统计金额，水平条形图</js-block>
  </tab>
  <tab title="跟进记录">
    <subtable collection="nb_crm_activities" assoc="activities" fields="follow_type,content,follow_date" />
    <js-item title="最近动态">
      时间线样式展示最近5条跟进记录，显示类型图标+内容摘要+相对时间
    </js-item>
  </tab>
</detail>
```

#### 合同详情
```xml
<detail>
  <tab title="合同信息" fields="title|contract_code\nstatus|amount\nstart_date|end_date">
    <js-item title="回款进度">
      进度条显示 已回款/合同总额 比例，下方列出每笔回款时间和金额
    </js-item>
    <js-item title="到期提醒">
      大字显示剩余天数，30天内橙色，已到期红色闪烁
    </js-item>
  </tab>
  <tab title="合同明细">
    <subtable collection="nb_crm_contract_items" assoc="contract_items" fields="product_name,quantity,unit_price,subtotal" />
  </tab>
  <tab title="回款记录">
    <subtable collection="nb_crm_payments" assoc="payments" fields="payment_code,amount,payment_date,status" />
  </tab>
</detail>
```

---

## 关系验证清单

在构建含子表的详情页之前，逐项确认：

- [ ] 子表 collection 的 m2o 关系已建立（如 `contacts.customer` → `nb_crm_customers`）
- [ ] 父表 collection 的 o2m 关系已建立（如 `customers.contacts` → `nb_crm_contacts`）
- [ ] `nb_list_fields(parent_collection)` 中能看到 o2m 字段
- [ ] XML 中 `<subtable>` 的 `assoc` 属性 = 父表上的 o2m 字段名
- [ ] `assoc` 字段名用关系名（如 `contacts`），不是外键名（不是 `customer_id`）
