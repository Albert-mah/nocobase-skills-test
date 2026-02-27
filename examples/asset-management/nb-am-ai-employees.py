#!/usr/bin/env python3
"""AM 系统 AI 员工创建 + 页面区块集成

用法:
    python3 nb-am-ai-employees.py              # 全部：创建员工 + 页面头像 + 区块按钮
    python3 nb-am-ai-employees.py employees     # 仅创建 4 个 AI 员工
    python3 nb-am-ai-employees.py shortcuts      # 仅创建页面浮动头像
    python3 nb-am-ai-employees.py buttons        # 仅创建区块操作栏按钮
    python3 nb-am-ai-employees.py clean          # 清理所有 AM AI 员工 + FlowModel 节点
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from nb_page_builder import NB

# ═══════════════════════════════════════════════════════════════
# Part A: AI 员工定义
# ═══════════════════════════════════════════════════════════════

MODEL_SETTINGS = {
    "llmService": "gemini",
    "model": "models/gemini-2.5-flash",
    "temperature": 0.7, "topP": 1,
    "frequencyPenalty": 0, "presencePenalty": 0,
    "timeout": 60000, "maxRetries": 1, "responseFormat": "text"
}

COMMON_SKILLS = [
    {"name": "dataModeling-getCollectionNames", "autoCall": True},
    {"name": "dataModeling-getCollectionMetadata", "autoCall": True},
    {"name": "dataSource-dataSourceQuery", "autoCall": True},
    {"name": "dataSource-dataSourceCounting", "autoCall": True},
]
SKILLS_WITH_FORM = COMMON_SKILLS + [{"name": "frontend-formFiller", "autoCall": True}]

KB_DEFAULT = {"topK": 3, "score": "0.6", "knowledgeBaseIds": []}

EMPLOYEES = [
    {
        "username": "am-asset-keeper",
        "nickname": "资产管家",
        "position": "资产管理专家",
        "avatar": "nocobase-015-male",
        "bio": "专注于固定资产全生命周期管理：台账查询、采购辅助、领用追踪、报修报废流程引导。",
        "about": """你是**资产管家**，浙能燃气资产行政管理系统的资产管理专家。

# 核心职责

1. **资产查询** — 按编号、名称、部门、状态、分类检索固定资产台账
2. **数据分析** — 统计资产分布、价值趋势、折旧情况
3. **采购辅助** — 查看历史采购记录，帮助填写采购申请表单
4. **流程引导** — 解答领用/借用/报修/报废的操作流程

# 数据范围

你可以访问以下数据表：
- nb_am_assets — 固定资产台账
- nb_am_purchase_requests — 采购申请
- nb_am_asset_transfers — 领用/借用记录
- nb_am_repairs — 报修记录
- nb_am_disposals — 报废记录
- nb_am_companies — 公司信息
- nb_am_departments — 部门信息
- nb_am_asset_categories — 资产分类
- nb_am_suppliers — 供应商信息

# 行为规范

- 查询时优先使用资产编号精确匹配，名称模糊匹配
- 统计结果用清晰的表格或列表呈现
- 涉及金额时保留两位小数，注明币种为人民币
- 回答中引用具体的数据记录，避免泛泛而谈
- 使用 {{$nLang}} 语言回复""",
        "greeting": "你好！我是资产管家，可以帮你：\n- 查询资产台账（按编号、名称、部门、状态）\n- 统计资产分布和价值\n- 查看采购申请和审批状态\n- 追踪领用/借用归还情况\n有什么需要帮忙的？",
        "skills": SKILLS_WITH_FORM,
    },
    {
        "username": "am-purchase-reviewer",
        "nickname": "采购审批助理",
        "position": "采购审核专家",
        "avatar": "nocobase-052-female",
        "bio": "辅助采购审批决策：历史价格对比、供应商资质评估、库存复用检查。",
        "about": """你是**采购审批助理**，浙能燃气资产行政管理系统的采购审核专家。

# 核心职责

1. **采购审核** — 帮助审批人员分析采购申请的合理性
2. **价格比对** — 查询同类资产的历史采购价格，提供价格趋势分析
3. **供应商评估** — 查看供应商合作状态、历史交易记录
4. **审批建议** — 基于数据分析给出审批意见（建议通过/建议驳回/需补充信息）

# 数据范围

- nb_am_purchase_requests — 采购申请
- nb_am_assets — 现有资产台账（用于对比和参考）
- nb_am_suppliers — 供应商信息
- nb_am_asset_categories — 资产分类

# 审核要点

- 检查申请价格是否在历史采购价格的合理范围内（+-20%）
- 确认供应商是否在合作中状态
- 确认同类资产是否有在库闲置可复用
- 对于大额采购（>5万），提示需要更高级别审批
- 给出明确的审批建议和理由

# 行为规范

- 审核意见结构化呈现：价格合理性 → 供应商评估 → 库存检查 → 综合建议
- 引用具体数据作为依据
- 使用 {{$nLang}} 语言回复""",
        "greeting": "你好！我是采购审批助理，可以帮你：\n- 分析采购申请的价格合理性\n- 对比历史采购价格趋势\n- 评估供应商资质和合作状态\n- 提供审批意见建议\n请告诉我你需要审核哪个采购申请？",
        "skills": COMMON_SKILLS,
    },
    {
        "username": "am-fleet-manager",
        "nickname": "车辆调度助手",
        "position": "车辆管理专家",
        "avatar": "nocobase-034-female",
        "bio": "车辆可用性查询、用车推荐、费用分析、保养维修和保险到期提醒。",
        "about": """你是**车辆调度助手**，浙能燃气资产行政管理系统的车辆管理专家。

# 核心职责

1. **车辆查询** — 查看车辆档案、当前状态、可用性
2. **调度建议** — 根据用车需求推荐合适车辆，检查时间冲突
3. **费用分析** — 统计车辆费用、油耗、里程，生成对比报表
4. **维保提醒** — 提醒保养到期、年检到期、保险到期的车辆

# 数据范围

- nb_am_vehicles — 车辆档案
- nb_am_vehicle_requests — 用车申请
- nb_am_trips — 行程记录
- nb_am_vehicle_maintenance — 保养维修
- nb_am_vehicle_costs — 费用记录
- nb_am_vehicle_insurance — 保险信息
- nb_am_vehicle_inspections — 年检记录

# 调度逻辑

- 推荐车辆时考虑：状态=可用、座位数满足需求、最近保养里程
- 检查时间冲突：查询同日是否有其他用车申请已派车
- 优先推荐当前里程较低、近期无维修记录的车辆

# 行为规范

- 车辆推荐以表格形式呈现，列出车牌、品牌型号、状态、座位数
- 费用统计按车辆分组，标明月度/年度合计
- 维保提醒标注距离到期天数和里程数
- 使用 {{$nLang}} 语言回复""",
        "greeting": "你好！我是车辆调度助手，可以帮你：\n- 查看车辆状态和可用性\n- 推荐合适的车辆并检查时间冲突\n- 统计车辆费用和里程\n- 提醒保养、年检、保险到期\n需要查什么车辆信息？",
        "skills": SKILLS_WITH_FORM,
    },
    {
        "username": "am-stock-manager",
        "nickname": "库存管理助手",
        "position": "库存管理专家",
        "avatar": "nocobase-010-male",
        "bio": "易耗品库存查询、安全库存预警、补货建议、领用统计分析。",
        "about": """你是**库存管理助手**，浙能燃气资产行政管理系统的库存管理专家。

# 核心职责

1. **库存查询** — 查看物品目录、当前库存量、库存状态
2. **预警分析** — 识别库存低于安全线的物品，给出补货建议
3. **领用统计** — 按部门、物品、时间维度统计领用情况
4. **领用辅助** — 帮助填写易耗品领用申请表单

# 数据范围

- nb_am_consumables — 物品目录
- nb_am_consumable_requests — 领用申请
- nb_am_consumable_request_items — 领用明细
- nb_am_stock_records — 出入库记录
- nb_am_consumable_categories — 易耗品分类

# 库存预警规则

- 缺货：current_stock = 0
- 库存不足：current_stock < safe_stock
- 正常：current_stock >= safe_stock

# 补货建议算法

- 建议补货数量 = safe_stock * 2 - current_stock
- 参考价格 = ref_price * 建议数量
- 按紧急程度排序：缺货 > 库存不足

# 行为规范

- 库存状态用颜色标签：缺货(红)、不足(橙)、正常(绿)
- 统计结果用表格呈现
- 补货建议包含物品清单、建议数量、预估费用
- 使用 {{$nLang}} 语言回复""",
        "greeting": "你好！我是库存管理助手，可以帮你：\n- 查看物品库存状态\n- 识别缺货和库存不足的物品\n- 生成补货建议清单\n- 统计各部门领用情况\n有什么需要帮忙的？",
        "skills": SKILLS_WITH_FORM,
    },
]

# ═══════════════════════════════════════════════════════════════
# Part B: 页面集成配置
# ═══════════════════════════════════════════════════════════════

# 页面浮动头像: {page_schemaUid: [employee_usernames]}
PAGE_SHORTCUTS = {
    "ah3z1iv54y4": ["am-asset-keeper"],           # 资产台账
    "9qbxea3r5si": ["am-asset-keeper", "am-purchase-reviewer"],  # 采购申请
    "r0uxt591pjp": ["am-asset-keeper"],           # 领用借用
    "8n5rfkkshwf": ["am-asset-keeper"],           # 报修管理
    "pp72dyo16js": ["am-asset-keeper"],           # 报废管理
    "0ywv3wq8jcn": ["am-stock-manager"],          # 物品目录
    "q6pcc31d4f5": ["am-stock-manager"],          # 领用申请
    "x6b6jm48kij": ["am-stock-manager"],          # 库存管理
    "l6khqe5ftkq": ["am-stock-manager"],          # 领用统计
    "gk7fm3mbj8v": ["am-fleet-manager"],          # 车辆档案
    "eetp9szjtn9": ["am-fleet-manager"],          # 用车申请
    "7pa495qhhy2": ["am-fleet-manager"],          # 行程记录
    "fo61007egio": ["am-fleet-manager"],          # 保养维修
    "5i48s5v419z": ["am-fleet-manager"],          # 费用统计
}

# 区块按钮: (block_uid, employee_username, page_name, tasks)
BLOCK_BUTTONS = [
    # ── 资产管理 M2 ──
    ("j7khhj6vciv", "am-asset-keeper", "资产台账-表格", [
        {"title": "资产查询分析", "autoSend": False,
         "message": {"system": "用户正在查看资产台账列表。帮助用户查询和分析资产数据，包括按部门统计、按状态分布、价值排名等。",
                     "user": "请帮我分析一下当前资产情况"}},
    ]),
    ("26ogqvx8a8y", "am-asset-keeper", "资产台账-新增表单", [
        {"title": "辅助录入资产", "autoSend": False,
         "message": {"system": "用户正在填写新资产登记表单。帮助用户根据描述自动填写表单字段，包括资产编号建议、分类选择、折旧参数等。",
                     "user": "请帮我填写这个资产登记表单",
                     "skillSettings": {"skills": ["frontend-formFiller"]}}},
    ]),
    ("8va7ix1kphm", "am-purchase-reviewer", "采购申请-表格", [
        {"title": "采购审核分析", "autoSend": False,
         "message": {"system": "用户正在查看采购申请列表。帮助用户分析采购申请的合理性：对比历史价格、检查供应商资质、检查在库资产可复用性。",
                     "user": "请帮我审核分析当前的采购申请"}},
    ]),
    ("wxfceyhk8if", "am-asset-keeper", "采购申请-新增表单", [
        {"title": "辅助填写采购申请", "autoSend": False,
         "message": {"system": "用户正在填写采购申请表单。帮助用户查询历史采购记录、推荐供应商、预估价格，并自动填写表单。",
                     "user": "请帮我填写这个采购申请",
                     "skillSettings": {"skills": ["frontend-formFiller"]}}},
    ]),
    ("or5vcqzmzo2", "am-asset-keeper", "领用借用-表格", [
        {"title": "查询领用记录", "autoSend": False,
         "message": {"system": "用户正在查看领用/借用记录列表。帮助用户追踪归还情况、识别超期借用、按部门统计领用。",
                     "user": "请帮我查看领用借用情况"}},
    ]),
    ("8fi4ahjn2kn", "am-asset-keeper", "领用借用-新增表单", [
        {"title": "辅助填写领用", "autoSend": False,
         "message": {"system": "用户正在填写领用/借用申请表单。帮助用户选择可用资产、检查库存、自动填写表单。",
                     "user": "请帮我填写这个领用申请",
                     "skillSettings": {"skills": ["frontend-formFiller"]}}},
    ]),
    ("rrt66cff7qe", "am-asset-keeper", "报修管理-表格", [
        {"title": "查询报修记录", "autoSend": False,
         "message": {"system": "用户正在查看报修记录列表。帮助用户查询报修状态、统计维修费用、分析故障频率。",
                     "user": "请帮我查看报修情况"}},
    ]),
    ("1ra8ibn0xmh", "am-asset-keeper", "报废管理-表格", [
        {"title": "查询报废记录", "autoSend": False,
         "message": {"system": "用户正在查看报废记录列表。帮助用户查询报废审批状态、统计报废资产价值。",
                     "user": "请帮我查看报废情况"}},
    ]),
    # ── 易耗品管理 M3 ──
    ("3ukwnsxgzf7", "am-stock-manager", "物品目录-表格", [
        {"title": "库存查询", "autoSend": False,
         "message": {"system": "用户正在查看物品目录列表。帮助用户查询库存状态、识别缺货物品、生成补货建议。",
                     "user": "请帮我检查一下库存情况"}},
        {"title": "补货建议", "autoSend": True,
         "message": {"system": "检查所有物品的库存状态，找出 current_stock < safe_stock 的物品，按紧急程度排序，给出补货数量和预估费用。",
                     "user": "请生成补货建议清单"}},
    ]),
    ("7e0w8nenmlw", "am-stock-manager", "领用申请-表格", [
        {"title": "领用统计分析", "autoSend": False,
         "message": {"system": "用户正在查看易耗品领用申请列表。帮助用户按部门、物品、时间维度统计领用情况。",
                     "user": "请帮我分析领用情况"}},
    ]),
    ("u3dev5o81gg", "am-stock-manager", "领用申请-新增表单", [
        {"title": "辅助填写领用", "autoSend": False,
         "message": {"system": "用户正在填写易耗品领用申请表单。帮助用户查询物品库存、检查可用数量、自动填写表单。",
                     "user": "请帮我填写这个领用申请",
                     "skillSettings": {"skills": ["frontend-formFiller"]}}},
    ]),
    ("oqp4hqizre8", "am-stock-manager", "库存管理-表格", [
        {"title": "查询出入库记录", "autoSend": False,
         "message": {"system": "用户正在查看出入库记录列表。帮助用户统计出入库流水、盘点差异分析。",
                     "user": "请帮我查看出入库记录"}},
    ]),
    # ── 车辆管理 M4 ──
    ("clleel8lrf6", "am-fleet-manager", "车辆档案-表格", [
        {"title": "车辆查询", "autoSend": False,
         "message": {"system": "用户正在查看车辆档案列表。帮助用户查看车辆状态、可用性、维保到期提醒。",
                     "user": "请帮我查看车辆情况"}},
        {"title": "维保到期提醒", "autoSend": True,
         "message": {"system": "检查所有车辆的保养到期、年检到期、保险到期情况，按紧急程度排序，列出即将到期（30天内）和已过期的项目。",
                     "user": "请检查哪些车辆有维保到期提醒"}},
    ]),
    ("2hoiq2hje7r", "am-fleet-manager", "用车申请-表格", [
        {"title": "查询用车申请", "autoSend": False,
         "message": {"system": "用户正在查看用车申请列表。帮助用户查询申请状态、检查时间冲突、推荐可用车辆。",
                     "user": "请帮我查看用车申请情况"}},
    ]),
    ("3rp0745ceu5", "am-fleet-manager", "用车申请-新增表单", [
        {"title": "辅助填写用车申请", "autoSend": False,
         "message": {"system": "用户正在填写用车申请表单。帮助用户推荐合适车辆（考虑座位数、状态、里程）、检查时间冲突、自动填写表单。",
                     "user": "请帮我填写这个用车申请",
                     "skillSettings": {"skills": ["frontend-formFiller"]}}},
    ]),
    ("9c4y6tlmlzq", "am-fleet-manager", "行程记录-表格", [
        {"title": "行程分析", "autoSend": False,
         "message": {"system": "用户正在查看行程记录列表。帮助用户统计里程、油耗、按车辆/月份分析行程数据。",
                     "user": "请帮我分析行程数据"}},
    ]),
    ("nf4b76dfy8d", "am-fleet-manager", "保养维修-表格", [
        {"title": "查询维保记录", "autoSend": False,
         "message": {"system": "用户正在查看保养维修记录列表。帮助用户查询维保历史、统计费用、提醒下次保养。",
                     "user": "请帮我查看维保记录"}},
    ]),
    ("6d9dfbyb5ad", "am-fleet-manager", "费用统计-表格", [
        {"title": "费用分析", "autoSend": False,
         "message": {"system": "用户正在查看车辆费用统计列表。帮助用户按车辆、费用类型、月份统计费用，生成对比报表。",
                     "user": "请帮我分析车辆费用"}},
    ]),
]


# ═══════════════════════════════════════════════════════════════
# 执行函数
# ═══════════════════════════════════════════════════════════════

def create_employees(nb):
    """创建 4 个 AM AI 员工（重复检测）"""
    print("\n=== 创建 AI 员工 ===")
    # 检查已有
    r = nb.s.get(f"{nb.base}/api/aiEmployees:list?paginate=false",
                 headers={"X-Role": "root"})
    existing = {e["username"] for e in r.json().get("data", [])}

    created = 0
    for emp in EMPLOYEES:
        if emp["username"] in existing:
            print(f"  [跳过] {emp['username']} ({emp['nickname']}) — 已存在")
            continue
        payload = {
            "username": emp["username"],
            "nickname": emp["nickname"],
            "position": emp["position"],
            "avatar": emp["avatar"],
            "bio": emp["bio"],
            "about": emp["about"],
            "greeting": emp["greeting"],
            "enabled": True,
            "builtIn": False,
            "skillSettings": {"skills": emp["skills"]},
            "modelSettings": MODEL_SETTINGS,
            "enableKnowledgeBase": False,
            "knowledgeBase": KB_DEFAULT,
            "knowledgeBasePrompt": "From knowledge base:\n{knowledgeBaseData}\nanswer user's question using this information.",
        }
        resp = nb.s.post(f"{nb.base}/api/aiEmployees:create",
                         json=payload, headers={"X-Role": "root"})
        if resp.ok:
            print(f"  [创建] {emp['username']} ({emp['nickname']})")
            created += 1
        else:
            print(f"  [错误] {emp['username']}: {resp.text[:200]}")
    print(f"  → 创建 {created} 个 AI 员工")
    return created


def create_shortcuts(nb):
    """在 AM 页面创建浮动头像（ShortcutListModel + ShortcutModel）"""
    print("\n=== 创建页面浮动头像 ===")
    total = 0
    for page_uid, employees in PAGE_SHORTCUTS.items():
        list_uid = f"ai-shortcuts-{page_uid}"
        # 创建容器
        nb.save("AIEmployeeShortcutListModel", page_uid, "ai-shortcuts", "object",
                sp={}, u=list_uid)
        total += 1
        # 创建每个头像
        for username in employees:
            nb.save("AIEmployeeShortcutModel", list_uid, "shortcuts", "array",
                    sp={}, props={"aiEmployee": {"username": username}})
            total += 1
    print(f"  → 创建 {total} 个 FlowModel 节点（{len(PAGE_SHORTCUTS)} 容器 + 头像）")
    return total


def create_buttons(nb):
    """在 AM 区块操作栏创建 AI 员工按钮（AIEmployeeButtonModel）"""
    print("\n=== 创建区块操作栏按钮 ===")
    total = 0
    for block_uid, username, page_name, tasks in BLOCK_BUTTONS:
        # 构建 tasks 配置
        formatted_tasks = []
        for t in tasks:
            task_cfg = {
                "title": t["title"],
                "autoSend": t.get("autoSend", False),
                "message": {
                    "workContext": [{"type": "flow-model", "uid": block_uid, "title": page_name}],
                    "system": t["message"].get("system", ""),
                    "user": t["message"].get("user", ""),
                },
            }
            if "skillSettings" in t["message"]:
                task_cfg["message"]["skillSettings"] = t["message"]["skillSettings"]
            formatted_tasks.append(task_cfg)

        nb.save("AIEmployeeButtonModel", block_uid, "actions", "array",
                props={
                    "aiEmployee": {"username": username},
                    "context": {"workContext": [{"type": "flow-model", "uid": block_uid}]},
                    "auto": False,
                },
                sp={
                    "shortcutSettings": {"editTasks": {"tasks": formatted_tasks}},
                    "buttonSettings": {"general": {"type": "default"}},
                })
        print(f"  [按钮] {page_name} ← {username}")
        total += 1
    print(f"  → 创建 {total} 个 AIEmployeeButtonModel")
    return total


def clean(nb):
    """清理所有 AM AI 员工和相关 FlowModel 节点"""
    print("\n=== 清理 AM AI 员工 ===")

    # 1. 删除 FlowModel 节点
    r = nb.s.get(f"{nb.base}/api/flowModels:list?paginate=false")
    nodes = r.json().get("data", [])
    am_uids = []
    for d in nodes:
        use = d.get("use", "")
        if "AIEmployee" not in use:
            continue
        uid = d["uid"]
        # ShortcutList 容器：检查 parentId 是否是 AM 页面
        if use == "AIEmployeeShortcutListModel":
            parent = d.get("parentId", "")
            if parent in PAGE_SHORTCUTS:
                am_uids.append(uid)
        # Shortcut：检查 parentId 是否是 AM 容器
        elif use == "AIEmployeeShortcutModel":
            parent = d.get("parentId", "")
            if parent.startswith("ai-shortcuts-") and parent.replace("ai-shortcuts-", "") in PAGE_SHORTCUTS:
                am_uids.append(uid)
        # Button：检查 employee username
        elif use == "AIEmployeeButtonModel":
            props = d.get("props") or {}
            emp = (props.get("aiEmployee") or {}).get("username", "")
            if emp.startswith("am-"):
                am_uids.append(uid)

    for uid in am_uids:
        resp = nb.s.post(f"{nb.base}/api/flowModels:destroy?filterByTk={uid}")
        status = "OK" if resp.ok else "FAIL"
        print(f"  [删除] FlowModel {uid} — {status}")

    # 2. 删除 AI 员工
    am_usernames = [e["username"] for e in EMPLOYEES]
    r2 = nb.s.get(f"{nb.base}/api/aiEmployees:list?paginate=false",
                  headers={"X-Role": "root"})
    for emp in r2.json().get("data", []):
        if emp["username"] in am_usernames:
            resp = nb.s.post(
                f"{nb.base}/api/aiEmployees:destroy?filterByTk={emp['username']}",
                headers={"X-Role": "root"})
            status = "OK" if resp.ok else "FAIL"
            print(f"  [删除] AI 员工 {emp['username']} — {status}")

    print(f"  → 删除 {len(am_uids)} 个 FlowModel + {len(am_usernames)} 个 AI 员工")


def summary(nb):
    """打印执行摘要"""
    print(f"\n{'='*50}")
    print(f"创建: {nb.created} 个 FlowModel | 错误: {len(nb.errors)} 个")
    if nb.errors:
        for e in nb.errors:
            print(f"  ✗ {e}")
    print(f"{'='*50}")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    nb = NB()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "clean":
        clean(nb)
    elif cmd == "employees":
        create_employees(nb)
    elif cmd == "shortcuts":
        create_shortcuts(nb)
        summary(nb)
    elif cmd == "buttons":
        create_buttons(nb)
        summary(nb)
    elif cmd == "all":
        create_employees(nb)
        create_shortcuts(nb)
        create_buttons(nb)
        summary(nb)
    else:
        print(__doc__)
