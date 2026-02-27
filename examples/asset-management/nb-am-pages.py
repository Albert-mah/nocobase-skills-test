#!/usr/bin/env python3
"""nb-am-pages.py — 资产行政管理系统页面构建脚本

依赖：nb_page_builder.py（通用库）
用法：
    python3 nb-am-pages.py              # 全部页面
    python3 nb-am-pages.py assets       # 只建 M2 固定资产
    python3 nb-am-pages.py consumables  # 只建 M3 易耗品
    python3 nb-am-pages.py vehicles     # 只建 M4 车辆
    python3 nb-am-pages.py base         # 只建 M1 基础数据 + 系统设置
    python3 nb-am-pages.py routes       # 只创建路由（菜单）

前置：nb-am-setup.py 已执行（23 张表已建好）
"""

import sys, json
from nb_page_builder import NB

# ═══════════════════════════════════════════════════════════════
# Step 1: 创建路由（菜单结构）
# ═══════════════════════════════════════════════════════════════

def create_routes(nb):
    """创建菜单组和页面路由，返回所有 Tab UID。"""
    print("═" * 60)
    print("  Creating routes...")
    print("═" * 60)

    tabs = {}

    # 顶级菜单组
    am_gid = nb.group("资产行政管理", None, icon="homeoutlined")

    # M2 固定资产
    tabs.update(nb.menu("资产管理", am_gid, [
        ("资产台账", "databaseoutlined"),
        ("采购申请", "shoppingcartoutlined"),
        ("领用借用", "swapoutlined"),
        ("报修管理", "tooloutlined"),
        ("报废管理", "deleteoutlined"),
    ], group_icon="bankoutlined"))

    # M3 易耗品
    tabs.update(nb.menu("易耗品管理", am_gid, [
        ("物品目录", "appstoreoutlined"),
        ("领用申请", "formoutlined"),
        ("库存管理", "containeroutlined"),
        ("领用统计", "barchartoutlined"),
    ], group_icon="inboxoutlined"))

    # M4 车辆
    tabs.update(nb.menu("车辆管理", am_gid, [
        ("车辆档案", "idcardoutlined"),
        ("用车申请", "sendoutlined"),
        ("行程记录", "environmentoutlined"),
        ("保养维修", "tooloutlined"),
        ("费用统计", "piechartoutlined"),
    ], group_icon="caroutlined"))

    # M1 基础数据
    tabs.update(nb.menu("基础数据", am_gid, [
        ("公司管理", "clusteroutlined"),
        ("部门管理", "apartmentoutlined"),
        ("场所管理", "environmentoutlined"),
        ("供应商管理", "shopoutlined"),
    ], group_icon="settingoutlined"))

    # 系统设置（多 Tab 页，直接挂在顶级组下）
    _, _, settings_tabs = nb.route("系统设置", am_gid, icon="controloutlined",
                                   tabs=["资产分类", "易耗品分类"])
    for name, tu in settings_tabs.items():
        tabs[f"设置_{name}"] = tu

    # 保存路由映射
    with open("nb-am-routes.json", "w") as f:
        json.dump(tabs, f, ensure_ascii=False, indent=2)
    print(f"\n  Saved {len(tabs)} tab UIDs to nb-am-routes.json")
    return tabs


def load_routes():
    """从文件加载已保存的路由映射。"""
    try:
        with open("nb-am-routes.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


# ═══════════════════════════════════════════════════════════════
# M2 固定资产模块
# ═══════════════════════════════════════════════════════════════

def page_assets(nb, tabs):
    """资产台账页面"""
    print("\n── 资产台账 ──")
    C = "nb_am_assets"
    grid = nb.page_layout(tabs["资产台账"])

    # KPIs
    kpis = nb.kpi_row(grid, C,
        ("总资产",),
        ("在用",   {"status": "在用"},   "#52c41a"),
        ("在库",   {"status": "在库"},   "#1890ff"),
        ("报修中", {"status": "报修中"}, "#faad14"))

    # 图表占位
    ch1 = nb.chart_placeholder(grid, "资产分类分布", "按分类统计资产数量饼图")
    ch2 = nb.chart_placeholder(grid, "资产价值趋势", "按月新增资产价值柱状图", icon="💰")

    # 表格
    tbl, addnew, actcol = nb.table_block(grid, C,
        ["asset_code", "name", "category", "brand", "model",
         "status", "company", "department", "custodian",
         "purchase_date", "purchase_price"],
        first_click=True, title="资产台账")

    # 筛选
    fb, _ = nb.filter_form(grid, C, "name", target_uid=tbl, label="搜索",
        search_fields=["name", "asset_code", "serial_number", "custodian"])

    # JS 列：状态着色
    nb.js_column(tbl, "状态", """
const r = ctx.record || {};
const colors = {'在用':'green','借用中':'blue','报修中':'orange','已报废':'red','在库':'default'};
ctx.render(ctx.React.createElement(ctx.antd.Tag, {color: colors[r.status]||'default'}, r.status||'-'));
""", sort=90, width=90)

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        [(ch1, 12), (ch2, 12)],
        (fb,),
        (tbl,),
    ])

    # 新增表单
    nb.addnew_form(addnew, C, """
        --- 基本信息
        name* | category*
        brand | model
        serial_number
        --- 采购信息
        purchase_date* | purchase_price
        supplier | useful_years
        salvage_value
        --- 使用信息
        status | company*
        department | custodian
        location
        --- 备注
        remark
    """)

    # 编辑
    nb.edit_action(actcol, C, """
        --- 基本信息
        asset_code | name*
        category* | brand
        model | serial_number
        --- 采购信息
        purchase_date | purchase_price
        supplier | useful_years
        salvage_value
        --- 使用信息
        status | company
        department | custodian
        location
        --- 备注
        remark
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl)
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "资产概览", "blocks": [
                {"type": "details", "title": "资产信息", "fields": """
                    --- 基本信息
                    asset_code | name
                    category | status
                    brand | model
                    serial_number
                    --- 采购与财务
                    purchase_date | purchase_price
                    supplier | useful_years
                    salvage_value
                    --- 使用信息
                    company | department
                    custodian | location
                    --- 备注
                    remark
                """},
                {"type": "js", "title": "资产卡片",
                 "code": "// TODO: 折旧进度环 + 使用年限倒计时 + 状态时间线"},
            ], "sizes": [14, 10]},
            {"title": "领用记录", "assoc": "transfers", "coll": "nb_am_asset_transfers",
             "fields": ["transfer_type", "applicant", "status",
                        "expected_return_date", "actual_return_date", "createdAt"]},
            {"title": "报修记录", "assoc": "repairs", "coll": "nb_am_repairs",
             "fields": ["repair_no", "fault_desc", "repair_method",
                        "repair_cost", "repair_result", "status", "createdAt"]},
            {"title": "报废记录", "assoc": "disposals", "coll": "nb_am_disposals",
             "fields": ["reason", "disposal_method", "status",
                        "estimated_salvage", "book_value", "createdAt"]},
        ], mode="drawer", size="large")


def page_purchase(nb, tabs):
    """采购申请页面"""
    print("\n── 采购申请 ──")
    C = "nb_am_purchase_requests"
    grid = nb.page_layout(tabs["采购申请"])

    kpis = nb.kpi_row(grid, C,
        ("总申请",),
        ("待审批", {"status.$in": ["待部门审批", "待行政审批", "待领导审批"]}, "#faad14"),
        ("采购中", {"status": "采购中"}, "#1890ff"),
        ("已完成", {"status": "已完成"}, "#52c41a"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["request_no", "asset_name", "category", "quantity",
         "estimated_price", "total_price", "status", "applicant",
         "company", "createdAt"],
        first_click=True, title="采购申请列表")

    fb, _ = nb.filter_form(grid, C, "asset_name", target_uid=tbl, label="搜索",
        search_fields=["request_no", "asset_name", "applicant"])

    # JS 列：审批状态
    nb.js_column(tbl, "审批", """
const s = (ctx.record||{}).status || '';
const m = {'草稿':'default','待部门审批':'processing','待行政审批':'processing',
           '待领导审批':'warning','已通过':'success','已驳回':'error',
           '采购中':'processing','已完成':'success'};
ctx.render(ctx.React.createElement(ctx.antd.Badge, {status:m[s]||'default', text:s}));
""", sort=90, width=120)

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 资产信息
        category* | asset_name*
        brand_model | quantity*
        estimated_price | total_price
        --- 申请信息
        reason | expected_date
        --- 组织
        company* | department
        applicant
    """)

    nb.edit_action(actcol, C, """
        --- 资产信息
        category | asset_name
        brand_model | quantity
        estimated_price | total_price
        --- 申请信息
        reason | expected_date
        status
        --- 采购执行
        supplier | actual_price
        actual_quantity | actual_total
        purchase_date | invoice_no
        --- 审批
        approval_remark
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "request_no")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "申请详情", "blocks": [
                {"type": "details", "fields": """
                    --- 资产信息
                    request_no | category
                    asset_name | brand_model
                    quantity | estimated_price
                    total_price
                    --- 申请信息
                    reason | expected_date
                    applicant | status
                    --- 组织
                    company | department
                    --- 采购执行
                    supplier | actual_price
                    actual_quantity | actual_total
                    purchase_date | invoice_no
                    --- 审批
                    approval_remark
                """},
            ]},
        ], mode="drawer", size="large")


def page_transfer(nb, tabs):
    """领用/借用页面"""
    print("\n── 领用借用 ──")
    C = "nb_am_asset_transfers"
    grid = nb.page_layout(tabs["领用借用"])

    kpis = nb.kpi_row(grid, C,
        ("总记录",),
        ("待审批", {"status": "待审批"}, "#faad14"),
        ("已发放", {"status": "已发放"}, "#1890ff"),
        ("已归还", {"status": "已归还"}, "#52c41a"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["transfer_type", "asset", "applicant", "reason",
         "expected_return_date", "actual_return_date", "status",
         "company", "department", "createdAt"],
        first_click=True, title="领用/借用记录")

    fb, _ = nb.filter_form(grid, C, "applicant", target_uid=tbl, label="搜索",
        search_fields=["applicant"])

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 申请信息
        transfer_type* | asset*
        applicant* | reason
        --- 借用信息
        expected_return_date
        --- 组织
        company | department
    """)

    nb.edit_action(actcol, C, """
        --- 申请信息
        transfer_type | asset
        applicant | reason
        --- 借用信息
        expected_return_date | actual_return_date
        status
        --- 组织
        company | department
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "transfer_type")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "申请详情", "blocks": [
                {"type": "details", "fields": """
                    --- 申请信息
                    transfer_type | asset
                    applicant | reason
                    status
                    --- 借用信息
                    expected_return_date | actual_return_date
                    --- 组织
                    company | department
                    --- 时间
                    createdAt | updatedAt
                """},
            ]},
        ], mode="drawer", size="large")


def page_repair(nb, tabs):
    """报修管理页面"""
    print("\n── 报修管理 ──")
    C = "nb_am_repairs"
    grid = nb.page_layout(tabs["报修管理"])

    kpis = nb.kpi_row(grid, C,
        ("总报修",),
        ("待受理", {"status": "待受理"}, "#faad14"),
        ("维修中", {"status": "维修中"}, "#1890ff"),
        ("已完成", {"status": "已完成"}, "#52c41a"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["repair_no", "asset", "fault_desc", "repair_method",
         "supplier", "repair_cost", "repair_result", "status",
         "applicant", "createdAt"],
        first_click=True, title="报修列表")

    fb, _ = nb.filter_form(grid, C, "repair_no", target_uid=tbl, label="搜索",
        search_fields=["repair_no", "applicant"])

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 报修信息
        asset* | fault_desc*
        applicant*
        --- 组织
        company
    """)

    nb.edit_action(actcol, C, """
        --- 报修信息
        repair_no | asset
        fault_desc | applicant
        --- 维修处理
        repair_method | supplier
        repair_content
        repair_cost | repair_result
        status
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "repair_no")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "报修详情", "blocks": [
                {"type": "details", "fields": """
                    --- 报修信息
                    repair_no | asset
                    fault_desc | applicant
                    --- 维修处理
                    repair_method | supplier
                    repair_content
                    repair_cost | repair_result
                    status
                    --- 组织
                    company
                    --- 时间
                    createdAt | updatedAt
                """},
            ]},
        ], mode="drawer", size="large")


def page_disposal(nb, tabs):
    """报废管理页面"""
    print("\n── 报废管理 ──")
    C = "nb_am_disposals"
    grid = nb.page_layout(tabs["报废管理"])

    kpis = nb.kpi_row(grid, C,
        ("总申请",),
        ("待审批", {"status.$in": ["待部门审批", "待行政鉴定", "待财务审核", "待领导审批"]}, "#faad14"),
        ("待处置", {"status": "待处置"}, "#1890ff"),
        ("已报废", {"status": "已报废"}, "#52c41a"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["asset", "reason", "disposal_method", "estimated_salvage",
         "book_value", "status", "applicant", "createdAt"],
        first_click=True, title="报废申请列表")

    fb, _ = nb.filter_form(grid, C, "applicant", target_uid=tbl, label="搜索",
        search_fields=["applicant"])

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 报废信息
        asset* | reason*
        estimated_salvage | disposal_method
        --- 申请人
        applicant* | company
    """)

    nb.edit_action(actcol, C, """
        --- 报废信息
        asset | reason
        estimated_salvage | disposal_method
        status
        --- 鉴定与审核
        appraisal_remark | book_value
        --- 处置
        disposal_detail
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "asset")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "报废详情", "blocks": [
                {"type": "details", "fields": """
                    --- 报废信息
                    asset | reason
                    estimated_salvage | disposal_method
                    status | applicant
                    --- 鉴定与审核
                    appraisal_remark | book_value
                    --- 处置
                    disposal_detail
                    --- 组织
                    company
                    --- 时间
                    createdAt | updatedAt
                """},
            ]},
        ], mode="drawer", size="large")


# ═══════════════════════════════════════════════════════════════
# M3 易耗品模块
# ═══════════════════════════════════════════════════════════════

def page_consumables(nb, tabs):
    """物品目录页面"""
    print("\n── 物品目录 ──")
    C = "nb_am_consumables"
    grid = nb.page_layout(tabs["物品目录"])

    kpis = nb.kpi_row(grid, C,
        ("物品总数",),
        ("启用中", {"status": "启用"}, "#52c41a"),
        ("已停用", {"status": "停用"}, "#ff4d4f"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["code", "name", "category", "spec", "unit",
         "ref_price", "current_stock", "safe_stock",
         "storage_location", "status"],
        first_click=True, title="物品目录")

    fb, _ = nb.filter_form(grid, C, "name", target_uid=tbl, label="搜索",
        search_fields=["name", "code"])

    # JS 列：库存状态着色
    nb.js_column(tbl, "库存状态", """
const r = ctx.record || {};
const cur = r.current_stock || 0, safe = r.safe_stock || 0;
let color = 'green', text = '正常';
if (cur === 0) { color = 'red'; text = '缺货'; }
else if (cur < safe) { color = 'orange'; text = '不足'; }
ctx.render(ctx.React.createElement(ctx.antd.Tag, {color}, text));
""", sort=90, width=80)

    nb.set_layout(grid, [
        [(k, 8) for k in kpis],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 基本信息
        name* | code
        category* | spec
        unit | ref_price
        --- 库存
        current_stock | safe_stock
        storage_location
        --- 状态
        status
    """)

    nb.edit_action(actcol, C, """
        --- 基本信息
        name* | code
        category | spec
        unit | ref_price
        --- 库存
        current_stock | safe_stock
        storage_location
        --- 状态
        status
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "code")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "物品详情", "blocks": [
                {"type": "details", "fields": """
                    --- 基本信息
                    code | name
                    category | spec
                    unit | ref_price
                    --- 库存
                    current_stock | safe_stock
                    storage_location
                    --- 状态
                    status
                """},
            ]},
        ], mode="drawer", size="medium")


def page_cons_requests(nb, tabs):
    """易耗品领用申请页面"""
    print("\n── 易耗品领用申请 ──")
    C = "nb_am_consumable_requests"
    grid = nb.page_layout(tabs["领用申请"])

    kpis = nb.kpi_row(grid, C,
        ("总申请",),
        ("待审批", {"status": "待审批"}, "#faad14"),
        ("待发放", {"status": "待发放"}, "#1890ff"),
        ("已发放", {"status": "已发放"}, "#52c41a"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["applicant", "total_amount", "status",
         "company", "department", "remark", "createdAt"],
        first_click=True, title="领用申请列表")

    fb, _ = nb.filter_form(grid, C, "applicant", target_uid=tbl, label="搜索",
        search_fields=["applicant"])

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 申请信息
        applicant*
        --- 组织
        company | department
        --- 备注
        remark
    """)

    nb.edit_action(actcol, C, """
        --- 申请信息
        applicant | status
        total_amount
        --- 组织
        company | department
        --- 备注
        remark
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "applicant")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "申请详情", "blocks": [
                {"type": "details", "fields": """
                    --- 申请信息
                    applicant | status
                    total_amount
                    --- 组织
                    company | department
                    --- 备注
                    remark
                    --- 时间
                    createdAt | updatedAt
                """},
            ]},
        ], mode="drawer", size="large")


def page_stock(nb, tabs):
    """库存管理页面"""
    print("\n── 库存管理 ──")
    C = "nb_am_stock_records"
    grid = nb.page_layout(tabs["库存管理"])

    kpi1 = nb.kpi(grid, "物品种类", "nb_am_consumables")
    kpi2 = nb.kpi(grid, "本月入库", C, filter_={"record_type": "入库"}, color="#52c41a")
    kpi3 = nb.kpi(grid, "本月出库", C, filter_={"record_type": "出库"}, color="#1890ff")

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["consumable", "record_type", "quantity", "unit_price",
         "request", "operator", "company", "createdAt"],
        title="出入库记录")

    fb, _ = nb.filter_form(grid, C, "operator", target_uid=tbl, label="搜索",
        search_fields=["operator"])

    nb.set_layout(grid, [
        [(kpi1, 8), (kpi2, 8), (kpi3, 8)],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 入库信息
        consumable* | record_type*
        quantity* | unit_price
        --- 操作
        operator | company
    """)


def page_cons_stats(nb, tabs):
    """领用统计页面"""
    print("\n── 领用统计 ──")
    grid = nb.page_layout(tabs["领用统计"])

    kpi1 = nb.kpi(grid, "年度领用总额", "nb_am_consumable_requests",
                  filter_={"status": "已发放"}, color="#1890ff")
    kpi2 = nb.kpi(grid, "领用人次", "nb_am_consumable_requests",
                  filter_={"status": "已发放"})

    ch1 = nb.chart_placeholder(grid, "部门领用排名", "各部门领用金额 TOP10 横向柱状图")
    ch2 = nb.chart_placeholder(grid, "物品领用排名", "各物品领用数量 TOP10 横向柱状图")
    ch3 = nb.chart_placeholder(grid, "月度领用趋势", "按月领用金额折线图", icon="📈")

    nb.set_layout(grid, [
        [(kpi1, 12), (kpi2, 12)],
        [(ch1, 12), (ch2, 12)],
        (ch3,),
    ])


# ═══════════════════════════════════════════════════════════════
# M4 车辆管理模块
# ═══════════════════════════════════════════════════════════════

def page_vehicles(nb, tabs):
    """车辆档案页面"""
    print("\n── 车辆档案 ──")
    C = "nb_am_vehicles"
    grid = nb.page_layout(tabs["车辆档案"])

    kpis = nb.kpi_row(grid, C,
        ("车辆总数",),
        ("可用",   {"status": "可用"},   "#52c41a"),
        ("使用中", {"status": "使用中"}, "#1890ff"),
        ("维修中", {"status": "维修中"}, "#faad14"))

    ch = nb.chart_placeholder(grid, "车辆类型分布", "按车辆类型统计饼图")

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["plate_number", "brand", "model", "vehicle_type",
         "fuel_type", "current_mileage", "status", "company",
         "purchase_date"],
        first_click=True, title="车辆档案")

    fb, _ = nb.filter_form(grid, C, "plate_number", target_uid=tbl, label="搜索",
        search_fields=["plate_number", "brand", "model", "vin"])

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        (ch,),
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 基本信息
        plate_number* | brand
        model | color
        vehicle_type | seats
        --- 购入信息
        purchase_date | purchase_price
        --- 技术参数
        engine_no | vin
        fuel_type | current_mileage
        --- 组织
        company* | status
    """)

    nb.edit_action(actcol, C, """
        --- 基本信息
        plate_number | brand
        model | color
        vehicle_type | seats
        --- 购入信息
        purchase_date | purchase_price
        --- 技术参数
        engine_no | vin
        fuel_type | current_mileage
        --- 组织
        company | status
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl)
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "车辆概览", "blocks": [
                {"type": "details", "title": "车辆信息", "fields": """
                    --- 基本信息
                    plate_number | brand
                    model | color
                    vehicle_type | seats
                    fuel_type | current_mileage
                    --- 购入信息
                    purchase_date | purchase_price
                    engine_no | vin
                    --- 归属
                    company | status
                """},
                {"type": "js", "title": "车辆卡片",
                 "code": "// TODO: 里程统计+费用汇总+保险/年检到期倒计时"},
            ], "sizes": [14, 10]},
            {"title": "保险", "assoc": "insurance", "coll": "nb_am_vehicle_insurance",
             "fields": ["insurance_company", "policy_no", "insurance_type",
                        "start_date", "end_date", "premium"]},
            {"title": "年检", "assoc": "inspections", "coll": "nb_am_vehicle_inspections",
             "fields": ["inspection_date", "valid_until", "station", "cost"]},
            {"title": "费用", "assoc": "costs", "coll": "nb_am_vehicle_costs",
             "fields": ["cost_type", "amount", "cost_date", "remark", "operator"]},
            {"title": "行程", "assoc": "trips", "coll": "nb_am_trips",
             "fields": ["start_mileage", "end_mileage", "distance",
                        "status", "checkin_time", "createdAt"]},
            {"title": "保养维修", "assoc": "maintenance", "coll": "nb_am_vehicle_maintenance",
             "fields": ["maint_type", "total_cost", "status", "plan_date",
                        "supplier", "next_maint_date"]},
        ], mode="drawer", size="large")


def page_veh_requests(nb, tabs):
    """用车申请页面"""
    print("\n── 用车申请 ──")
    C = "nb_am_vehicle_requests"
    grid = nb.page_layout(tabs["用车申请"])

    kpis = nb.kpi_row(grid, C,
        ("总申请",),
        ("待审批", {"status": "待审批"}, "#faad14"),
        ("待派车", {"status": "待派车"}, "#1890ff"),
        ("已派车", {"status": "已派车"}, "#52c41a"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["request_no", "use_date", "depart_time", "return_time",
         "destination", "passenger_count", "need_driver",
         "vehicle", "driver", "status", "applicant", "company"],
        first_click=True, title="用车申请列表")

    fb, _ = nb.filter_form(grid, C, "destination", target_uid=tbl, label="搜索",
        search_fields=["request_no", "destination", "applicant"])

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 用车信息
        use_date* | destination*
        depart_time | return_time
        purpose
        --- 乘车信息
        passenger_count | passengers
        need_driver
        --- 组织
        company | department
        applicant*
    """)

    nb.edit_action(actcol, C, """
        --- 用车信息
        request_no | use_date
        destination | purpose
        depart_time | return_time
        passenger_count | passengers
        need_driver | applicant
        --- 派车
        vehicle | driver
        status | dispatch_remark
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "request_no")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "申请详情", "blocks": [
                {"type": "details", "fields": """
                    --- 用车信息
                    request_no | use_date
                    destination | purpose
                    depart_time | return_time
                    passenger_count | passengers
                    need_driver | applicant
                    --- 派车
                    vehicle | driver
                    status | dispatch_remark
                    --- 组织
                    company | department
                    --- 时间
                    createdAt | updatedAt
                """},
            ]},
        ], mode="drawer", size="large")


def page_trips(nb, tabs):
    """行程记录页面"""
    print("\n── 行程记录 ──")
    C = "nb_am_trips"
    grid = nb.page_layout(tabs["行程记录"])

    kpis = nb.kpi_row(grid, C,
        ("总行程",),
        ("进行中", {"status": "进行中"}, "#1890ff"),
        ("已完成", {"status": "已完成"}, "#52c41a"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["request", "vehicle", "driver",
         "start_mileage", "end_mileage", "distance",
         "status", "checkin_time", "createdAt"],
        first_click=True, title="行程记录")

    nb.set_layout(grid, [
        [(k, 8) for k in kpis],
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 行程信息
        request* | vehicle*
        driver
        --- 出车登记
        start_mileage | start_fuel
    """)

    nb.edit_action(actcol, C, """
        --- 行程信息
        request | vehicle | driver
        --- 出车
        start_mileage | start_fuel
        --- 收车
        end_mileage | end_fuel
        status
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "request")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "行程详情", "blocks": [
                {"type": "details", "fields": """
                    --- 行程信息
                    request | vehicle
                    driver | status
                    --- 出车
                    start_mileage | start_fuel
                    --- 收车
                    end_mileage | end_fuel
                    distance
                    --- 打卡
                    checkin_time
                    --- 时间
                    createdAt | updatedAt
                """},
            ]},
        ], mode="drawer", size="medium")


def page_maintenance(nb, tabs):
    """保养维修页面"""
    print("\n── 保养维修 ──")
    C = "nb_am_vehicle_maintenance"
    grid = nb.page_layout(tabs["保养维修"])

    kpis = nb.kpi_row(grid, C,
        ("总记录",),
        ("待审批", {"status": "待审批"}, "#faad14"),
        ("维修中", {"status": "维修中"}, "#1890ff"),
        ("已完成", {"status": "已完成"}, "#52c41a"))

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["vehicle", "maint_type", "current_mileage",
         "plan_date", "supplier", "total_cost",
         "use_insurance", "status", "company"],
        first_click=True, title="保养维修记录")

    fb, _ = nb.filter_form(grid, C, "maint_type", target_uid=tbl, label="搜索",
        search_fields=[])

    nb.set_layout(grid, [
        [(k, 6) for k in kpis],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 基本信息
        vehicle* | maint_type*
        current_mileage | plan_date
        supplier
        --- 费用
        parts_cost | labor_cost
        total_cost
        --- 保险
        use_insurance | insurance_amount
        --- 下次保养
        next_maint_mileage | next_maint_date
        --- 详情
        detail | status
        --- 组织
        company
    """)

    nb.edit_action(actcol, C, """
        --- 基本信息
        vehicle | maint_type
        current_mileage | plan_date
        supplier
        --- 费用
        parts_cost | labor_cost
        total_cost
        --- 保险
        use_insurance | insurance_amount
        --- 下次保养
        next_maint_mileage | next_maint_date
        --- 详情
        detail | status
        --- 组织
        company
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl, "vehicle")
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "维修详情", "blocks": [
                {"type": "details", "fields": """
                    --- 基本信息
                    vehicle | maint_type
                    current_mileage | plan_date
                    supplier | status
                    --- 费用
                    parts_cost | labor_cost
                    total_cost
                    --- 保险
                    use_insurance | insurance_amount
                    --- 下次保养
                    next_maint_mileage | next_maint_date
                    --- 详情
                    detail
                    --- 组织
                    company
                    --- 时间
                    createdAt | updatedAt
                """},
            ]},
        ], mode="drawer", size="large")


def page_veh_costs(nb, tabs):
    """车辆费用统计页面"""
    print("\n── 费用统计 ──")
    C = "nb_am_vehicle_costs"
    grid = nb.page_layout(tabs["费用统计"])

    kpi1 = nb.kpi(grid, "年度总费用", C, color="#ff4d4f")
    kpi2 = nb.kpi(grid, "油费/电费", C,
                  filter_={"cost_type.$in": ["油费", "电费"]}, color="#1890ff")
    kpi3 = nb.kpi(grid, "保养维修费", C,
                  filter_={"cost_type.$in": ["保养费", "维修费"]}, color="#faad14")
    kpi4 = nb.kpi(grid, "其他费用", C,
                  filter_={"cost_type.$in": ["路桥费", "停车费", "其他"]})

    ch1 = nb.chart_placeholder(grid, "车辆总费用趋势", "按月/季度费用折线图", icon="📈")
    ch2 = nb.chart_placeholder(grid, "费用类型分布", "各费用类型占比饼图")
    ch3 = nb.chart_placeholder(grid, "单车费用排名", "各车辆费用 TOP10 横向柱状图")
    ch4 = nb.chart_placeholder(grid, "公里平均费用", "各车辆公里均费对比柱状图")

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["vehicle", "cost_type", "amount", "cost_date",
         "remark", "operator", "company"],
        title="费用明细")

    fb, _ = nb.filter_form(grid, C, "remark", target_uid=tbl, label="搜索",
        search_fields=["remark"])

    nb.set_layout(grid, [
        [(kpi1, 6), (kpi2, 6), (kpi3, 6), (kpi4, 6)],
        [(ch1, 12), (ch2, 12)],
        [(ch3, 12), (ch4, 12)],
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 费用信息
        vehicle* | cost_type*
        amount* | cost_date*
        --- 备注
        remark | operator
        company
    """)


# ═══════════════════════════════════════════════════════════════
# M1 基础数据 + 系统设置
# ═══════════════════════════════════════════════════════════════

def page_companies(nb, tabs):
    """公司管理页面"""
    print("\n── 公司管理 ──")
    C = "nb_am_companies"
    grid = nb.page_layout(tabs["公司管理"])

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["name", "code", "short_code", "company_type",
         "contact_person", "contact_phone", "status", "sort"],
        title="公司列表")

    nb.set_layout(grid, [(tbl,)])

    nb.addnew_form(addnew, C, """
        --- 基本信息
        name* | code*
        short_code | company_type
        parent
        --- 联系信息
        address
        contact_person | contact_phone
        --- 状态
        status | sort
    """)

    nb.edit_action(actcol, C, """
        --- 基本信息
        name* | code*
        short_code | company_type
        parent
        --- 联系信息
        address
        contact_person | contact_phone
        --- 状态
        status | sort
    """)


def page_departments(nb, tabs):
    """部门管理页面"""
    print("\n── 部门管理 ──")
    C = "nb_am_departments"
    grid = nb.page_layout(tabs["部门管理"])

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["name", "code", "company", "manager", "sort"],
        title="部门列表")

    nb.set_layout(grid, [(tbl,)])

    nb.addnew_form(addnew, C, """
        --- 部门信息
        name* | code
        company* | parent
        manager | sort
    """)

    nb.edit_action(actcol, C, """
        --- 部门信息
        name* | code
        company | parent
        manager | sort
    """)


def page_locations(nb, tabs):
    """场所管理页面"""
    print("\n── 场所管理 ──")
    C = "nb_am_locations"
    grid = nb.page_layout(tabs["场所管理"])

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["name", "location_type", "resident_count", "address",
         "status", "company", "sort"],
        title="场所列表")

    fb, _ = nb.filter_form(grid, C, "name", target_uid=tbl, label="搜索",
        search_fields=["name", "address"])

    nb.set_layout(grid, [
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 场所信息
        name* | location_type*
        address
        --- 位置
        longitude | latitude
        resident_count
        --- 归属
        company* | status
        sort
    """)

    nb.edit_action(actcol, C, """
        --- 场所信息
        name | location_type
        address
        --- 位置
        longitude | latitude
        resident_count
        --- 归属
        company | status
        sort
    """)


def page_suppliers(nb, tabs):
    """供应商管理页面"""
    print("\n── 供应商管理 ──")
    C = "nb_am_suppliers"
    grid = nb.page_layout(tabs["供应商管理"])

    tbl, addnew, actcol = nb.table_block(grid, C,
        ["name", "supply_type", "contact_person", "contact_phone",
         "cooperation_status"],
        first_click=True, title="供应商列表")

    fb, _ = nb.filter_form(grid, C, "name", target_uid=tbl, label="搜索",
        search_fields=["name", "contact_person"])

    nb.set_layout(grid, [
        (fb,),
        (tbl,),
    ])

    nb.addnew_form(addnew, C, """
        --- 基本信息
        name* | supply_type*
        contact_person | contact_phone
        address
        --- 银行信息
        bank_name | bank_account
        --- 状态
        cooperation_status
        --- 备注
        remark
    """)

    nb.edit_action(actcol, C, """
        --- 基本信息
        name | supply_type
        contact_person | contact_phone
        address
        --- 银行信息
        bank_name | bank_account
        --- 状态
        cooperation_status
        --- 备注
        remark
    """)

    # 详情弹窗
    click_uid = nb.find_click_field(tbl)
    if click_uid:
        nb.detail_popup(click_uid, C, [
            {"title": "供应商信息", "blocks": [
                {"type": "details", "fields": """
                    name | supply_type
                    contact_person | contact_phone
                    address
                    bank_name | bank_account
                    cooperation_status
                    remark
                """},
            ]},
        ], mode="drawer", size="medium")


def page_settings(nb, tabs):
    """系统设置 — 配置表"""
    print("\n── 系统设置 ──")

    if "设置_资产分类" in tabs:
        nb.config_table(tabs["设置_资产分类"], "nb_am_asset_categories",
            ["name", "code", "default_years", "sort"],
            "资产分类")

    if "设置_易耗品分类" in tabs:
        nb.config_table(tabs["设置_易耗品分类"], "nb_am_consumable_categories",
            ["name", "need_approval", "remark", "sort"],
            "易耗品分类")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

SECTIONS = {
    "assets": [page_assets, page_purchase, page_transfer, page_repair, page_disposal],
    "consumables": [page_consumables, page_cons_requests, page_stock, page_cons_stats],
    "vehicles": [page_vehicles, page_veh_requests, page_trips, page_maintenance, page_veh_costs],
    "base": [page_companies, page_departments, page_locations, page_suppliers, page_settings],
}

def main():
    section = sys.argv[1] if len(sys.argv) > 1 else "all"

    nb = NB()
    print(f"\n{'═' * 60}")
    print(f"  Asset Management Pages Builder")
    print(f"  Section: {section}")
    print(f"{'═' * 60}")

    # 加载或创建路由
    tabs = load_routes()
    if not tabs or section == "routes":
        tabs = create_routes(nb)
        if section == "routes":
            nb.summary()
            return

    # 运行指定模块
    if section == "all":
        funcs = []
        for fns in SECTIONS.values():
            funcs.extend(fns)
    elif section in SECTIONS:
        funcs = SECTIONS[section]
    else:
        print(f"Unknown section: {section}")
        print(f"Available: {', '.join(SECTIONS.keys())}, routes, all")
        return

    for fn in funcs:
        try:
            fn(nb, tabs)
        except Exception as e:
            print(f"  ❌ {fn.__name__}: {e}")
            import traceback
            traceback.print_exc()

    nb.summary()

if __name__ == "__main__":
    main()
