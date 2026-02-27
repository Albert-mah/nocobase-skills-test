#!/usr/bin/env python3
"""nb-am-setup.py — 资产行政管理系统数据建模脚本（23 张表）

一个脚本完成：SQL DDL → 注册 collection → 系统字段 → 同步 → 接口升级 → 关系 → 种子数据

Usage:
    python nb-am-setup.py                      # 全量执行
    python nb-am-setup.py --dry-run             # 预览模式
    python nb-am-setup.py --module M1           # 只执行 M1 基础数据
    python nb-am-setup.py --skip-data           # 跳过种子数据
    python nb-am-setup.py --sql-only            # 只打印 SQL 不执行 API
    python nb-am-setup.py --drop                # 先 DROP 再 CREATE（危险）

Environment:
    NB_URL       http://localhost:14000
    NB_USER      admin@nocobase.com
    NB_PASSWORD  admin123
    NB_DB_URL    postgresql://nocobase:nocobase@localhost:5435/nocobase
"""

import argparse
import json
import os
import subprocess
import sys

# Import from nb-setup.py (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
nb_setup = import_module("nb-setup")
NocoBaseClient = nb_setup.NocoBaseClient
process_collection = nb_setup.process_collection

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sel(*values, colors=None):
    """Shorthand for select enum."""
    c = colors or {}
    return [{"value": v, "label": v, "color": c.get(v, "default")} for v in values]


def status_enum(*values, **kw):
    """Status select field."""
    return {"interface": "select", "title": kw.get("title", "状态"), "enum": sel(*values, colors=kw.get("colors"))}


STATUS_COLORS = {
    "启用": "green", "停用": "red", "合作中": "green", "已终止": "red",
    "在库": "default", "在用": "green", "借用中": "blue", "报修中": "orange", "已报废": "red",
    "草稿": "default", "待部门审批": "blue", "待行政审批": "blue", "待领导审批": "blue",
    "已通过": "green", "已驳回": "red", "采购中": "orange", "已完成": "grey",
    "待审批": "blue", "待发放": "orange", "已发放": "green", "已归还": "grey",
    "待受理": "blue", "维修中": "orange", "待确认": "cyan",
    "已修复": "green", "无法修复": "red", "建议报废": "orange",
    "待行政鉴定": "blue", "待财务审核": "blue", "待处置": "orange",
    "进行中": "blue", "可用": "green", "使用中": "blue",
    "待派车": "orange", "已派车": "cyan", "已确认": "green", "已取消": "red",
}


def st(*values, **kw):
    """Status field with auto-color lookup."""
    return status_enum(*values, colors=STATUS_COLORS, **kw)


def m2o(target, fk, title, label="name"):
    return {"type": "m2o", "target": f"nb_am_{target}", "foreignKey": fk, "title": title, "label": label}


def o2m(target, fk, title, label="id"):
    return {"type": "o2m", "target": f"nb_am_{target}", "foreignKey": fk, "title": title, "label": label}


# ---------------------------------------------------------------------------
# SQL DDL (no createdAt/updatedAt/createdById/updatedById — API creates those)
# ---------------------------------------------------------------------------

SQL_M1 = """
-- M1 基础数据
CREATE TABLE IF NOT EXISTS nb_am_companies (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    short_code VARCHAR(10),
    company_type VARCHAR(50),
    parent_id BIGINT REFERENCES nb_am_companies(id),
    address TEXT,
    contact_person VARCHAR(100),
    contact_phone VARCHAR(50),
    status VARCHAR(50) DEFAULT '启用',
    sort INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nb_am_departments (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    company_id BIGINT REFERENCES nb_am_companies(id),
    parent_id BIGINT REFERENCES nb_am_departments(id),
    manager VARCHAR(100),
    sort INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nb_am_locations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location_type VARCHAR(255),
    resident_count INT,
    address TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    status VARCHAR(50) DEFAULT '启用',
    company_id BIGINT REFERENCES nb_am_companies(id),
    sort INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nb_am_suppliers (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    supply_type VARCHAR(255),
    contact_person VARCHAR(100),
    contact_phone VARCHAR(50),
    address TEXT,
    bank_name VARCHAR(255),
    bank_account VARCHAR(100),
    cooperation_status VARCHAR(50) DEFAULT '合作中',
    remark TEXT
);
"""

SQL_M2 = """
-- M2 固定资产
CREATE TABLE IF NOT EXISTS nb_am_asset_categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    parent_id BIGINT REFERENCES nb_am_asset_categories(id),
    default_years INT,
    sort INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nb_am_assets (
    id BIGSERIAL PRIMARY KEY,
    asset_code VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    category_id BIGINT REFERENCES nb_am_asset_categories(id),
    brand VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    purchase_date DATE,
    purchase_price DECIMAL(12,2),
    supplier_id BIGINT REFERENCES nb_am_suppliers(id),
    useful_years INT,
    salvage_value DECIMAL(12,2),
    status VARCHAR(50) DEFAULT '在库',
    company_id BIGINT REFERENCES nb_am_companies(id),
    department_id BIGINT REFERENCES nb_am_departments(id),
    custodian VARCHAR(100),
    location VARCHAR(255),
    remark TEXT
);

CREATE TABLE IF NOT EXISTS nb_am_purchase_requests (
    id BIGSERIAL PRIMARY KEY,
    request_no VARCHAR(50),
    category_id BIGINT REFERENCES nb_am_asset_categories(id),
    asset_name VARCHAR(255),
    brand_model VARCHAR(255),
    quantity INT,
    estimated_price DECIMAL(12,2),
    total_price DECIMAL(12,2),
    reason TEXT,
    expected_date DATE,
    status VARCHAR(50) DEFAULT '草稿',
    company_id BIGINT REFERENCES nb_am_companies(id),
    department_id BIGINT REFERENCES nb_am_departments(id),
    applicant VARCHAR(100),
    supplier_id BIGINT REFERENCES nb_am_suppliers(id),
    actual_price DECIMAL(12,2),
    actual_quantity INT,
    actual_total DECIMAL(12,2),
    purchase_date DATE,
    invoice_no VARCHAR(100),
    approval_remark TEXT
);

CREATE TABLE IF NOT EXISTS nb_am_asset_transfers (
    id BIGSERIAL PRIMARY KEY,
    transfer_type VARCHAR(50),
    asset_id BIGINT REFERENCES nb_am_assets(id),
    applicant VARCHAR(100),
    reason TEXT,
    expected_return_date DATE,
    actual_return_date DATE,
    status VARCHAR(50) DEFAULT '待审批',
    company_id BIGINT REFERENCES nb_am_companies(id),
    department_id BIGINT REFERENCES nb_am_departments(id)
);

CREATE TABLE IF NOT EXISTS nb_am_repairs (
    id BIGSERIAL PRIMARY KEY,
    repair_no VARCHAR(50),
    asset_id BIGINT REFERENCES nb_am_assets(id),
    fault_desc TEXT,
    repair_method VARCHAR(50),
    supplier_id BIGINT REFERENCES nb_am_suppliers(id),
    repair_content TEXT,
    repair_cost DECIMAL(12,2),
    repair_result VARCHAR(50),
    status VARCHAR(50) DEFAULT '待受理',
    applicant VARCHAR(100),
    company_id BIGINT REFERENCES nb_am_companies(id)
);

CREATE TABLE IF NOT EXISTS nb_am_disposals (
    id BIGSERIAL PRIMARY KEY,
    asset_id BIGINT REFERENCES nb_am_assets(id),
    reason TEXT,
    estimated_salvage DECIMAL(12,2),
    disposal_method VARCHAR(50),
    status VARCHAR(50) DEFAULT '待部门审批',
    appraisal_remark TEXT,
    book_value DECIMAL(12,2),
    disposal_detail TEXT,
    applicant VARCHAR(100),
    company_id BIGINT REFERENCES nb_am_companies(id)
);

CREATE TABLE IF NOT EXISTS nb_am_inventories (
    id BIGSERIAL PRIMARY KEY,
    task_name VARCHAR(255) NOT NULL,
    scope VARCHAR(50),
    department_id BIGINT REFERENCES nb_am_departments(id),
    deadline DATE,
    status VARCHAR(50) DEFAULT '进行中',
    normal_count INT DEFAULT 0,
    abnormal_count INT DEFAULT 0,
    company_id BIGINT REFERENCES nb_am_companies(id)
);
"""

SQL_M3 = """
-- M3 低值易耗品
CREATE TABLE IF NOT EXISTS nb_am_consumable_categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    need_approval BOOLEAN DEFAULT FALSE,
    remark TEXT,
    sort INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nb_am_consumables (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    category_id BIGINT REFERENCES nb_am_consumable_categories(id),
    spec VARCHAR(255),
    unit VARCHAR(50),
    ref_price DECIMAL(10,2),
    status VARCHAR(50) DEFAULT '启用',
    current_stock INT DEFAULT 0,
    safe_stock INT DEFAULT 0,
    storage_location VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS nb_am_consumable_requests (
    id BIGSERIAL PRIMARY KEY,
    applicant VARCHAR(100),
    total_amount DECIMAL(10,2),
    status VARCHAR(50) DEFAULT '待审批',
    remark TEXT,
    company_id BIGINT REFERENCES nb_am_companies(id),
    department_id BIGINT REFERENCES nb_am_departments(id)
);

CREATE TABLE IF NOT EXISTS nb_am_stock_records (
    id BIGSERIAL PRIMARY KEY,
    consumable_id BIGINT REFERENCES nb_am_consumables(id),
    record_type VARCHAR(50),
    quantity INT,
    unit_price DECIMAL(10,2),
    request_id BIGINT REFERENCES nb_am_consumable_requests(id),
    operator VARCHAR(100),
    company_id BIGINT REFERENCES nb_am_companies(id)
);
"""

SQL_M4 = """
-- M4 车辆管理
CREATE TABLE IF NOT EXISTS nb_am_vehicles (
    id BIGSERIAL PRIMARY KEY,
    plate_number VARCHAR(20),
    brand VARCHAR(100),
    model VARCHAR(100),
    color VARCHAR(50),
    vehicle_type VARCHAR(50),
    seats INT,
    purchase_date DATE,
    purchase_price DECIMAL(12,2),
    engine_no VARCHAR(100),
    vin VARCHAR(100),
    fuel_type VARCHAR(50),
    current_mileage INT DEFAULT 0,
    status VARCHAR(50) DEFAULT '可用',
    company_id BIGINT REFERENCES nb_am_companies(id)
);

CREATE TABLE IF NOT EXISTS nb_am_vehicle_insurance (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT REFERENCES nb_am_vehicles(id),
    insurance_company VARCHAR(255),
    policy_no VARCHAR(100),
    insurance_type VARCHAR(255),
    start_date DATE,
    end_date DATE,
    premium DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS nb_am_vehicle_inspections (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT REFERENCES nb_am_vehicles(id),
    inspection_date DATE,
    valid_until DATE,
    station VARCHAR(255),
    cost DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS nb_am_drivers (
    id BIGSERIAL PRIMARY KEY,
    employee_name VARCHAR(100) NOT NULL,
    driver_type VARCHAR(50),
    license_no VARCHAR(50),
    license_class VARCHAR(10),
    license_expiry DATE,
    first_license_date DATE,
    avg_rating DECIMAL(3,2),
    total_trips INT DEFAULT 0,
    total_mileage INT DEFAULT 0,
    company_id BIGINT REFERENCES nb_am_companies(id)
);

CREATE TABLE IF NOT EXISTS nb_am_vehicle_requests (
    id BIGSERIAL PRIMARY KEY,
    request_no VARCHAR(50),
    use_date DATE,
    depart_time TIME,
    return_time TIME,
    destination VARCHAR(255),
    purpose TEXT,
    passenger_count INT,
    passengers TEXT,
    need_driver BOOLEAN DEFAULT FALSE,
    vehicle_id BIGINT REFERENCES nb_am_vehicles(id),
    driver_id BIGINT REFERENCES nb_am_drivers(id),
    status VARCHAR(50) DEFAULT '待审批',
    applicant VARCHAR(100),
    company_id BIGINT REFERENCES nb_am_companies(id),
    department_id BIGINT REFERENCES nb_am_departments(id),
    dispatch_remark TEXT
);

CREATE TABLE IF NOT EXISTS nb_am_trips (
    id BIGSERIAL PRIMARY KEY,
    request_id BIGINT REFERENCES nb_am_vehicle_requests(id),
    vehicle_id BIGINT REFERENCES nb_am_vehicles(id),
    driver_id BIGINT REFERENCES nb_am_drivers(id),
    start_mileage INT,
    end_mileage INT,
    distance INT,
    start_fuel VARCHAR(50),
    end_fuel VARCHAR(50),
    status VARCHAR(50) DEFAULT '进行中',
    checkin_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nb_am_vehicle_maintenance (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT REFERENCES nb_am_vehicles(id),
    maint_type VARCHAR(50),
    current_mileage INT,
    plan_date DATE,
    supplier_id BIGINT REFERENCES nb_am_suppliers(id),
    parts_cost DECIMAL(10,2),
    labor_cost DECIMAL(10,2),
    total_cost DECIMAL(10,2),
    next_maint_mileage INT,
    next_maint_date DATE,
    use_insurance BOOLEAN DEFAULT FALSE,
    insurance_amount DECIMAL(10,2),
    status VARCHAR(50) DEFAULT '待审批',
    detail TEXT,
    company_id BIGINT REFERENCES nb_am_companies(id)
);

CREATE TABLE IF NOT EXISTS nb_am_vehicle_costs (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT REFERENCES nb_am_vehicles(id),
    cost_type VARCHAR(50),
    amount DECIMAL(10,2),
    cost_date DATE,
    remark TEXT,
    operator VARCHAR(100),
    company_id BIGINT REFERENCES nb_am_companies(id)
);
"""

ALL_SQL = {"M1": SQL_M1, "M2": SQL_M2, "M3": SQL_M3, "M4": SQL_M4}

# ---------------------------------------------------------------------------
# Collection definitions (compact Python dicts)
# ---------------------------------------------------------------------------

# ── M1 基础数据 ─────────────────────────────────────────────────

COMPANIES = {
    "name": "nb_am_companies", "title": "公司", "module": "M1",
    "tree": "adjacency-list",
    "fields": {
        "name":           {"interface": "input", "title": "公司名称"},
        "code":           {"interface": "input", "title": "公司编码"},
        "short_code":     {"interface": "input", "title": "公司代码"},
        "company_type":   {"interface": "select", "title": "公司类型",
                           "enum": sel("总部", "子公司", colors={"总部": "blue", "子公司": "green"})},
        "address":        {"interface": "textarea", "title": "地址"},
        "contact_person": {"interface": "input", "title": "联系人"},
        "contact_phone":  {"interface": "input", "title": "联系电话"},
        "status":         st("启用", "停用"),
        "sort":           "sort",
    },
    "relations": {
        "parent":      m2o("companies", "parent_id", "上级公司"),
        "children":    o2m("companies", "parent_id", "下级公司", "name"),
        "departments": o2m("departments", "company_id", "部门", "name"),
        "locations":   o2m("locations", "company_id", "场所", "name"),
    },
    "data": [
        {"name": "浙能燃气集团",                           "code": "4000", "short_code": "ZNRQ", "company_type": "总部",  "status": "启用", "sort": 1},
        {"name": "浙能天然气运行有限公司",                 "code": "4020", "short_code": "TYRX", "company_type": "子公司", "status": "启用", "sort": 2,  "parent_id": 1},
        {"name": "浙能燃气投资有限公司",                   "code": "4021", "short_code": "RQTZ", "company_type": "子公司", "status": "启用", "sort": 3,  "parent_id": 1},
        {"name": "浙江浙能液化天然气有限公司",             "code": "4030", "short_code": "YHTG", "company_type": "子公司", "status": "启用", "sort": 4,  "parent_id": 1},
        {"name": "浙能天然气运行台州分公司",               "code": "4031", "short_code": "TZFG", "company_type": "子公司", "status": "启用", "sort": 5,  "parent_id": 2},
        {"name": "浙能天然气运行宁波分公司",               "code": "4032", "short_code": "NBFG", "company_type": "子公司", "status": "启用", "sort": 6,  "parent_id": 2},
        {"name": "浙能天然气运行温州分公司",               "code": "4033", "short_code": "WZFG", "company_type": "子公司", "status": "启用", "sort": 7,  "parent_id": 2},
        {"name": "浙能天然气运行嘉兴分公司",               "code": "4034", "short_code": "JXFG", "company_type": "子公司", "status": "启用", "sort": 8,  "parent_id": 2},
        {"name": "浙能天然气运行绍兴分公司",               "code": "4035", "short_code": "SXFG", "company_type": "子公司", "status": "启用", "sort": 9,  "parent_id": 2},
        {"name": "浙能天然气运行金华分公司",               "code": "4036", "short_code": "JHFG", "company_type": "子公司", "status": "启用", "sort": 10, "parent_id": 2},
        {"name": "浙能天然气运行衢州分公司",               "code": "4037", "short_code": "QZFG", "company_type": "子公司", "status": "启用", "sort": 11, "parent_id": 2},
        {"name": "浙能天然气运行丽水分公司",               "code": "4038", "short_code": "LSFG", "company_type": "子公司", "status": "启用", "sort": 12, "parent_id": 2},
        {"name": "浙能天然气运行舟山分公司",               "code": "4039", "short_code": "ZSFG", "company_type": "子公司", "status": "启用", "sort": 13, "parent_id": 2},
    ],
}

DEPARTMENTS = {
    "name": "nb_am_departments", "title": "部门", "module": "M1",
    "tree": "adjacency-list",
    "fields": {
        "name":    {"interface": "input", "title": "部门名称"},
        "code":    {"interface": "input", "title": "部门编码"},
        "manager": {"interface": "input", "title": "部门负责人"},
        "sort":    "sort",
    },
    "relations": {
        "company":  m2o("companies", "company_id", "所属公司"),
        "parent":   m2o("departments", "parent_id", "上级部门"),
        "children": o2m("departments", "parent_id", "下级部门", "name"),
    },
}

LOCATIONS = {
    "name": "nb_am_locations", "title": "场所", "module": "M1",
    "fields": {
        "name":           {"interface": "input", "title": "场所名称"},
        "location_type":  {"interface": "multipleSelect", "title": "场所类型",
                           "enum": sel("办公楼", "营业厅", "门站", "LNG站", "仓库", "停车场",
                                       colors={"办公楼": "blue", "营业厅": "green", "门站": "orange",
                                                "LNG站": "purple", "仓库": "cyan", "停车场": "grey"})},
        "resident_count": {"interface": "integer", "title": "常驻人员数量"},
        "address":        {"interface": "textarea", "title": "详细地址"},
        "longitude":      {"interface": "number", "title": "经度", "precision": 6},
        "latitude":       {"interface": "number", "title": "纬度", "precision": 6},
        "status":         st("启用", "停用"),
        "sort":           "sort",
    },
    "relations": {
        "company": m2o("companies", "company_id", "所属公司"),
    },
}

SUPPLIERS = {
    "name": "nb_am_suppliers", "title": "供应商", "module": "M1",
    "fields": {
        "name":               {"interface": "input", "title": "供应商名称"},
        "supply_type":        {"interface": "multipleSelect", "title": "供应类型",
                               "enum": sel("固定资产", "易耗品", "维修", "车辆服务",
                                           colors={"固定资产": "blue", "易耗品": "green",
                                                    "维修": "orange", "车辆服务": "purple"})},
        "contact_person":     {"interface": "input", "title": "联系人"},
        "contact_phone":      {"interface": "input", "title": "联系电话"},
        "address":            {"interface": "textarea", "title": "地址"},
        "bank_name":          {"interface": "input", "title": "开户行"},
        "bank_account":       {"interface": "input", "title": "银行账号"},
        "cooperation_status": st("合作中", "已终止", title="合作状态"),
        "remark":             {"interface": "textarea", "title": "备注"},
    },
}

# ── M2 固定资产 ─────────────────────────────────────────────────

ASSET_CATEGORIES = {
    "name": "nb_am_asset_categories", "title": "资产分类", "module": "M2",
    "tree": "adjacency-list",
    "fields": {
        "name":          {"interface": "input", "title": "分类名称"},
        "code":          {"interface": "input", "title": "分类编码"},
        "default_years": {"interface": "integer", "title": "默认使用年限"},
        "sort":          "sort",
    },
    "relations": {
        "parent":   m2o("asset_categories", "parent_id", "上级分类"),
        "children": o2m("asset_categories", "parent_id", "下级分类", "name"),
    },
    "data": [
        # 一级分类
        {"name": "办公家具",   "code": "AC01", "default_years": 10, "sort": 1},
        {"name": "电脑设备",   "code": "AC02", "default_years": 5,  "sort": 2},
        {"name": "打印设备",   "code": "AC03", "default_years": 5,  "sort": 3},
        {"name": "网络设备",   "code": "AC04", "default_years": 6,  "sort": 4},
        {"name": "监控设备",   "code": "AC05", "default_years": 6,  "sort": 5},
        {"name": "服务器设备", "code": "AC06", "default_years": 5,  "sort": 6},
        # 二级：办公家具
        {"name": "办公桌",   "code": "AC0101", "default_years": 10, "sort": 1, "parent_id": 1},
        {"name": "办公椅",   "code": "AC0102", "default_years": 8,  "sort": 2, "parent_id": 1},
        {"name": "文件柜",   "code": "AC0103", "default_years": 10, "sort": 3, "parent_id": 1},
        {"name": "会议桌",   "code": "AC0104", "default_years": 10, "sort": 4, "parent_id": 1},
        # 二级：电脑设备
        {"name": "台式电脑",   "code": "AC0201", "default_years": 5, "sort": 1, "parent_id": 2},
        {"name": "笔记本电脑", "code": "AC0202", "default_years": 4, "sort": 2, "parent_id": 2},
        {"name": "显示器",     "code": "AC0203", "default_years": 5, "sort": 3, "parent_id": 2},
        # 二级：打印设备
        {"name": "激光打印机", "code": "AC0301", "default_years": 5, "sort": 1, "parent_id": 3},
        {"name": "复印机",     "code": "AC0302", "default_years": 6, "sort": 2, "parent_id": 3},
        # 二级：网络设备
        {"name": "路由器", "code": "AC0401", "default_years": 6, "sort": 1, "parent_id": 4},
        {"name": "交换机", "code": "AC0402", "default_years": 6, "sort": 2, "parent_id": 4},
        {"name": "防火墙", "code": "AC0403", "default_years": 5, "sort": 3, "parent_id": 4},
        # 二级：监控设备
        {"name": "摄像头",      "code": "AC0501", "default_years": 5, "sort": 1, "parent_id": 5},
        {"name": "录像机(NVR)", "code": "AC0502", "default_years": 6, "sort": 2, "parent_id": 5},
        # 二级：服务器设备
        {"name": "机架式服务器", "code": "AC0601", "default_years": 5, "sort": 1, "parent_id": 6},
        {"name": "塔式服务器",   "code": "AC0602", "default_years": 5, "sort": 2, "parent_id": 6},
        {"name": "UPS电源",      "code": "AC0603", "default_years": 6, "sort": 3, "parent_id": 6},
    ],
}

ASSETS = {
    "name": "nb_am_assets", "title": "资产台账", "module": "M2",
    "fields": {
        "asset_code":     {"interface": "input", "title": "资产编号"},
        "name":           {"interface": "input", "title": "资产名称"},
        "brand":          {"interface": "input", "title": "品牌"},
        "model":          {"interface": "input", "title": "规格型号"},
        "serial_number":  {"interface": "input", "title": "序列号/SN码"},
        "purchase_date":  {"interface": "date", "title": "购入日期"},
        "purchase_price": {"interface": "number", "title": "购入价格", "precision": 2},
        "useful_years":   {"interface": "integer", "title": "使用年限"},
        "salvage_value":  {"interface": "number", "title": "残值", "precision": 2},
        "status":         st("在库", "在用", "借用中", "报修中", "已报废"),
        "custodian":      {"interface": "input", "title": "保管人"},
        "location":       {"interface": "input", "title": "存放位置"},
        "remark":         {"interface": "textarea", "title": "备注"},
    },
    "relations": {
        "category":   m2o("asset_categories", "category_id", "资产分类"),
        "supplier":   m2o("suppliers", "supplier_id", "供应商"),
        "company":    m2o("companies", "company_id", "所属公司"),
        "department": m2o("departments", "department_id", "使用部门"),
        "transfers":  o2m("asset_transfers", "asset_id", "领用记录"),
        "repairs":    o2m("repairs", "asset_id", "报修记录", "repair_no"),
        "disposals":  o2m("disposals", "asset_id", "报废记录"),
    },
}

PURCHASE_REQUESTS = {
    "name": "nb_am_purchase_requests", "title": "采购申请", "module": "M2",
    "fields": {
        "request_no":      {"interface": "input", "title": "申请单号"},
        "asset_name":      {"interface": "input", "title": "资产名称"},
        "brand_model":     {"interface": "input", "title": "品牌型号要求"},
        "quantity":        {"interface": "integer", "title": "申请数量"},
        "estimated_price": {"interface": "number", "title": "预估单价", "precision": 2},
        "total_price":     {"interface": "number", "title": "预估总价", "precision": 2},
        "reason":          {"interface": "textarea", "title": "申请理由"},
        "expected_date":   {"interface": "date", "title": "期望到货日期"},
        "status":          st("草稿", "待部门审批", "待行政审批", "待领导审批", "已通过", "已驳回", "采购中", "已完成"),
        "applicant":       {"interface": "input", "title": "申请人"},
        "actual_price":    {"interface": "number", "title": "实际采购单价", "precision": 2},
        "actual_quantity": {"interface": "integer", "title": "实际数量"},
        "actual_total":    {"interface": "number", "title": "实际总价", "precision": 2},
        "purchase_date":   {"interface": "date", "title": "采购日期"},
        "invoice_no":      {"interface": "input", "title": "发票号"},
        "approval_remark": {"interface": "textarea", "title": "审批意见"},
    },
    "relations": {
        "category":   m2o("asset_categories", "category_id", "资产分类"),
        "company":    m2o("companies", "company_id", "所属公司"),
        "department": m2o("departments", "department_id", "申请部门"),
        "supplier":   m2o("suppliers", "supplier_id", "供应商"),
    },
}

ASSET_TRANSFERS = {
    "name": "nb_am_asset_transfers", "title": "领用/借用/归还", "module": "M2",
    "fields": {
        "transfer_type":        {"interface": "select", "title": "类型",
                                 "enum": sel("领用", "借用", "归还",
                                             colors={"领用": "green", "借用": "blue", "归还": "grey"})},
        "applicant":            {"interface": "input", "title": "申请人"},
        "reason":               {"interface": "textarea", "title": "申请理由"},
        "expected_return_date": {"interface": "date", "title": "预计归还日期"},
        "actual_return_date":   {"interface": "date", "title": "实际归还日期"},
        "status":               st("待审批", "已通过", "待发放", "已发放", "已归还", "已驳回"),
    },
    "relations": {
        "asset":      m2o("assets", "asset_id", "资产"),
        "company":    m2o("companies", "company_id", "所属公司"),
        "department": m2o("departments", "department_id", "部门"),
    },
}

REPAIRS = {
    "name": "nb_am_repairs", "title": "报修", "module": "M2",
    "fields": {
        "repair_no":      {"interface": "input", "title": "报修单号"},
        "fault_desc":     {"interface": "textarea", "title": "故障描述"},
        "repair_method":  {"interface": "select", "title": "维修方式",
                           "enum": sel("内部维修", "外部维修", colors={"内部维修": "blue", "外部维修": "orange"})},
        "repair_content": {"interface": "textarea", "title": "维修内容"},
        "repair_cost":    {"interface": "number", "title": "维修费用", "precision": 2},
        "repair_result":  {"interface": "select", "title": "维修结果",
                           "enum": sel("已修复", "无法修复", "建议报废", colors=STATUS_COLORS)},
        "status":         st("待受理", "维修中", "待确认", "已完成"),
        "applicant":      {"interface": "input", "title": "报修人"},
    },
    "relations": {
        "asset":    m2o("assets", "asset_id", "资产"),
        "supplier": m2o("suppliers", "supplier_id", "维修供应商"),
        "company":  m2o("companies", "company_id", "所属公司"),
    },
}

DISPOSALS = {
    "name": "nb_am_disposals", "title": "报废", "module": "M2",
    "fields": {
        "reason":            {"interface": "textarea", "title": "报废原因"},
        "estimated_salvage": {"interface": "number", "title": "预估残值", "precision": 2},
        "disposal_method":   {"interface": "select", "title": "处置方式",
                              "enum": sel("变卖", "捐赠", "销毁", "其他",
                                          colors={"变卖": "blue", "捐赠": "green", "销毁": "red", "其他": "grey"})},
        "status":            st("待部门审批", "待行政鉴定", "待财务审核", "待领导审批", "待处置", "已报废", "已驳回"),
        "appraisal_remark":  {"interface": "textarea", "title": "鉴定意见"},
        "book_value":        {"interface": "number", "title": "账面价值", "precision": 2},
        "disposal_detail":   {"interface": "textarea", "title": "处置详情"},
        "applicant":         {"interface": "input", "title": "申请人"},
    },
    "relations": {
        "asset":   m2o("assets", "asset_id", "资产"),
        "company": m2o("companies", "company_id", "所属公司"),
    },
}

INVENTORIES = {
    "name": "nb_am_inventories", "title": "盘点", "module": "M2",
    "fields": {
        "task_name":      {"interface": "input", "title": "盘点任务名称"},
        "scope":          {"interface": "select", "title": "盘点范围",
                           "enum": sel("全公司", "指定部门", colors={"全公司": "blue", "指定部门": "green"})},
        "deadline":       {"interface": "date", "title": "盘点截止日期"},
        "status":         st("进行中", "已完成"),
        "normal_count":   {"interface": "integer", "title": "正常数"},
        "abnormal_count": {"interface": "integer", "title": "异常数"},
    },
    "relations": {
        "department": m2o("departments", "department_id", "指定部门"),
        "company":    m2o("companies", "company_id", "所属公司"),
    },
}

# ── M3 低值易耗品 ───────────────────────────────────────────────

CONSUMABLE_CATEGORIES = {
    "name": "nb_am_consumable_categories", "title": "易耗品分类", "module": "M3",
    "fields": {
        "name":          {"interface": "input", "title": "分类名称"},
        "need_approval": {"interface": "checkbox", "title": "是否需要审批"},
        "remark":        {"interface": "textarea", "title": "说明"},
        "sort":          "sort",
    },
    "data": [
        {"name": "办公用纸",   "need_approval": False, "remark": "A4纸、A3纸、信封等",             "sort": 1},
        {"name": "饮用水",     "need_approval": False, "remark": "桶装水、矿泉水",               "sort": 2},
        {"name": "文具",       "need_approval": False, "remark": "笔、本子、便签、文件袋等",       "sort": 3},
        {"name": "打印耗材",   "need_approval": True,  "remark": "硒鼓、墨盒、碳粉",             "sort": 4},
        {"name": "清洁用品",   "need_approval": False, "remark": "垃圾袋、洗手液、纸巾等",         "sort": 5},
        {"name": "小电器",     "need_approval": True,  "remark": "计算器、插排、鼠标、键盘、U盘等", "sort": 6},
        {"name": "服务类",     "need_approval": True,  "remark": "快递费、维修工具等",             "sort": 7},
    ],
}

CONSUMABLES = {
    "name": "nb_am_consumables", "title": "物品目录", "module": "M3",
    "fields": {
        "code":             {"interface": "input", "title": "物品编码"},
        "name":             {"interface": "input", "title": "物品名称"},
        "spec":             {"interface": "input", "title": "规格"},
        "unit":             {"interface": "select", "title": "单位",
                             "enum": sel("个", "包", "箱", "瓶", "盒", "支")},
        "ref_price":        {"interface": "number", "title": "参考单价", "precision": 2},
        "status":           st("启用", "停用"),
        "current_stock":    {"interface": "integer", "title": "当前库存"},
        "safe_stock":       {"interface": "integer", "title": "安全库存"},
        "storage_location": {"interface": "input", "title": "存放位置"},
    },
    "relations": {
        "category": m2o("consumable_categories", "category_id", "分类"),
    },
}

CONSUMABLE_REQUESTS = {
    "name": "nb_am_consumable_requests", "title": "易耗品领用申请", "module": "M3",
    "fields": {
        "applicant":    {"interface": "input", "title": "申请人"},
        "total_amount": {"interface": "number", "title": "申请总金额", "precision": 2},
        "status":       st("待审批", "待发放", "已发放", "已驳回"),
        "remark":       {"interface": "textarea", "title": "备注"},
    },
    "relations": {
        "company":    m2o("companies", "company_id", "所属公司"),
        "department": m2o("departments", "department_id", "部门"),
    },
}

STOCK_RECORDS = {
    "name": "nb_am_stock_records", "title": "出入库记录", "module": "M3",
    "fields": {
        "record_type": {"interface": "select", "title": "类型",
                        "enum": sel("入库", "出库", colors={"入库": "green", "出库": "orange"})},
        "quantity":    {"interface": "integer", "title": "数量"},
        "unit_price":  {"interface": "number", "title": "单价", "precision": 2},
        "operator":    {"interface": "input", "title": "操作人"},
    },
    "relations": {
        "consumable": m2o("consumables", "consumable_id", "物品"),
        "request":    m2o("consumable_requests", "request_id", "关联申请", "id"),
        "company":    m2o("companies", "company_id", "所属公司"),
    },
}

# ── M4 车辆管理 ─────────────────────────────────────────────────

VEHICLES = {
    "name": "nb_am_vehicles", "title": "车辆档案", "module": "M4",
    "fields": {
        "plate_number":   {"interface": "input", "title": "车牌号"},
        "brand":          {"interface": "input", "title": "品牌"},
        "model":          {"interface": "input", "title": "型号"},
        "color":          {"interface": "input", "title": "颜色"},
        "vehicle_type":   {"interface": "select", "title": "车辆类型",
                           "enum": sel("轿车", "SUV", "商务车", "货车",
                                       colors={"轿车": "blue", "SUV": "green", "商务车": "purple", "货车": "orange"})},
        "seats":          {"interface": "integer", "title": "座位数"},
        "purchase_date":  {"interface": "date", "title": "购入日期"},
        "purchase_price": {"interface": "number", "title": "购入价格", "precision": 2},
        "engine_no":      {"interface": "input", "title": "发动机号"},
        "vin":            {"interface": "input", "title": "车架号"},
        "fuel_type":      {"interface": "select", "title": "燃料类型",
                           "enum": sel("汽油", "柴油", "电动", "混动",
                                       colors={"汽油": "orange", "柴油": "grey", "电动": "green", "混动": "blue"})},
        "current_mileage": {"interface": "integer", "title": "当前里程"},
        "status":          st("可用", "使用中", "维修中", "已报废"),
    },
    "relations": {
        "company":             m2o("companies", "company_id", "所属公司"),
        "insurance_records":   o2m("vehicle_insurance", "vehicle_id", "保险记录", "policy_no"),
        "inspections":         o2m("vehicle_inspections", "vehicle_id", "年检记录"),
        "requests":            o2m("vehicle_requests", "vehicle_id", "用车记录", "request_no"),
        "trips":               o2m("trips", "vehicle_id", "行程记录"),
        "maintenance_records": o2m("vehicle_maintenance", "vehicle_id", "保养维修记录"),
        "costs":               o2m("vehicle_costs", "vehicle_id", "费用记录"),
    },
}

VEHICLE_INSURANCE = {
    "name": "nb_am_vehicle_insurance", "title": "保险", "module": "M4",
    "fields": {
        "insurance_company": {"interface": "input", "title": "保险公司"},
        "policy_no":         {"interface": "input", "title": "保单号"},
        "insurance_type":    {"interface": "multipleSelect", "title": "保险类型",
                              "enum": sel("交强险", "商业险", "车损险", "三者险",
                                          colors={"交强险": "red", "商业险": "blue", "车损险": "orange", "三者险": "green"})},
        "start_date":        {"interface": "date", "title": "生效日期"},
        "end_date":          {"interface": "date", "title": "到期日期"},
        "premium":           {"interface": "number", "title": "保费金额", "precision": 2},
    },
    "relations": {
        "vehicle": m2o("vehicles", "vehicle_id", "车辆", "plate_number"),
    },
}

VEHICLE_INSPECTIONS = {
    "name": "nb_am_vehicle_inspections", "title": "年检", "module": "M4",
    "fields": {
        "inspection_date": {"interface": "date", "title": "年检日期"},
        "valid_until":     {"interface": "date", "title": "有效期至"},
        "station":         {"interface": "input", "title": "检测站"},
        "cost":            {"interface": "number", "title": "费用", "precision": 2},
    },
    "relations": {
        "vehicle": m2o("vehicles", "vehicle_id", "车辆", "plate_number"),
    },
}

DRIVERS = {
    "name": "nb_am_drivers", "title": "司机", "module": "M4",
    "fields": {
        "employee_name":      {"interface": "input", "title": "姓名"},
        "driver_type":        {"interface": "select", "title": "司机类型",
                               "enum": sel("专职", "兼职", colors={"专职": "blue", "兼职": "green"})},
        "license_no":         {"interface": "input", "title": "驾驶证号"},
        "license_class":      {"interface": "select", "title": "驾照等级",
                               "enum": sel("C1", "C2", "B1", "B2", "A1", "A2")},
        "license_expiry":     {"interface": "date", "title": "驾驶证有效期"},
        "first_license_date": {"interface": "date", "title": "初次领证日期"},
        "avg_rating":         {"interface": "number", "title": "平均评分", "precision": 2},
        "total_trips":        {"interface": "integer", "title": "累计出车次数"},
        "total_mileage":      {"interface": "integer", "title": "累计行驶里程"},
    },
    "relations": {
        "company": m2o("companies", "company_id", "所属公司"),
    },
}

VEHICLE_REQUESTS = {
    "name": "nb_am_vehicle_requests", "title": "用车申请", "module": "M4",
    "fields": {
        "request_no":      {"interface": "input", "title": "用车申请单号"},
        "use_date":        {"interface": "date", "title": "用车日期"},
        "depart_time":     {"interface": "time", "title": "预计出发时间"},
        "return_time":     {"interface": "time", "title": "预计返回时间"},
        "destination":     {"interface": "input", "title": "目的地"},
        "purpose":         {"interface": "textarea", "title": "用车事由"},
        "passenger_count": {"interface": "integer", "title": "乘车人数"},
        "passengers":      {"interface": "textarea", "title": "乘车人员名单"},
        "need_driver":     {"interface": "checkbox", "title": "是否需要司机"},
        "status":          st("待审批", "待派车", "已派车", "已确认", "已完成", "已取消"),
        "applicant":       {"interface": "input", "title": "申请人"},
        "dispatch_remark": {"interface": "textarea", "title": "调度备注"},
    },
    "relations": {
        "vehicle":    m2o("vehicles", "vehicle_id", "派车车辆", "plate_number"),
        "driver":     m2o("drivers", "driver_id", "派车司机", "employee_name"),
        "company":    m2o("companies", "company_id", "所属公司"),
        "department": m2o("departments", "department_id", "部门"),
    },
}

TRIPS = {
    "name": "nb_am_trips", "title": "行程记录", "module": "M4",
    "fields": {
        "start_mileage": {"interface": "integer", "title": "起始里程"},
        "end_mileage":   {"interface": "integer", "title": "结束里程"},
        "distance":      {"interface": "integer", "title": "行驶里程"},
        "start_fuel":    {"interface": "input", "title": "起始油量"},
        "end_fuel":      {"interface": "input", "title": "结束油量"},
        "status":        st("进行中", "已完成"),
        "checkin_time":  {"interface": "datetime", "title": "目的地打卡时间"},
    },
    "relations": {
        "request": m2o("vehicle_requests", "request_id", "用车申请", "request_no"),
        "vehicle": m2o("vehicles", "vehicle_id", "车辆", "plate_number"),
        "driver":  m2o("drivers", "driver_id", "司机", "employee_name"),
    },
}

VEHICLE_MAINTENANCE = {
    "name": "nb_am_vehicle_maintenance", "title": "保养/维修", "module": "M4",
    "fields": {
        "maint_type":          {"interface": "select", "title": "类型",
                                "enum": sel("常规保养", "大保养", "故障维修", "事故维修",
                                            colors={"常规保养": "green", "大保养": "blue",
                                                     "故障维修": "orange", "事故维修": "red"})},
        "current_mileage":     {"interface": "integer", "title": "当前里程"},
        "plan_date":           {"interface": "date", "title": "计划日期"},
        "parts_cost":          {"interface": "number", "title": "配件费用", "precision": 2},
        "labor_cost":          {"interface": "number", "title": "工时费用", "precision": 2},
        "total_cost":          {"interface": "number", "title": "总费用", "precision": 2},
        "next_maint_mileage":  {"interface": "integer", "title": "下次保养里程"},
        "next_maint_date":     {"interface": "date", "title": "下次保养日期"},
        "use_insurance":       {"interface": "checkbox", "title": "是否走保险"},
        "insurance_amount":    {"interface": "number", "title": "理赔金额", "precision": 2},
        "status":              st("待审批", "已通过", "维修中", "已完成"),
        "detail":              {"interface": "textarea", "title": "维修/保养明细"},
    },
    "relations": {
        "vehicle":  m2o("vehicles", "vehicle_id", "车辆", "plate_number"),
        "supplier": m2o("suppliers", "supplier_id", "维修供应商"),
        "company":  m2o("companies", "company_id", "所属公司"),
    },
}

VEHICLE_COSTS = {
    "name": "nb_am_vehicle_costs", "title": "车辆费用", "module": "M4",
    "fields": {
        "cost_type": {"interface": "select", "title": "费用类型",
                      "enum": sel("油费", "电费", "路桥费", "停车费", "保养费", "维修费", "其他",
                                  colors={"油费": "orange", "电费": "green", "路桥费": "blue",
                                           "停车费": "cyan", "保养费": "purple", "维修费": "red", "其他": "grey"})},
        "amount":    {"interface": "number", "title": "金额", "precision": 2},
        "cost_date": {"interface": "date", "title": "费用日期"},
        "remark":    {"interface": "textarea", "title": "备注"},
        "operator":  {"interface": "input", "title": "录入人"},
    },
    "relations": {
        "vehicle": m2o("vehicles", "vehicle_id", "车辆", "plate_number"),
        "company": m2o("companies", "company_id", "所属公司"),
    },
}

# ---------------------------------------------------------------------------
# Ordered table list (dependency order: referenced tables first)
# ---------------------------------------------------------------------------

ALL_COLLECTIONS = {
    "M1": [COMPANIES, DEPARTMENTS, LOCATIONS, SUPPLIERS],
    "M2": [ASSET_CATEGORIES, ASSETS, PURCHASE_REQUESTS, ASSET_TRANSFERS, REPAIRS, DISPOSALS, INVENTORIES],
    "M3": [CONSUMABLE_CATEGORIES, CONSUMABLES, CONSUMABLE_REQUESTS, STOCK_RECORDS],
    "M4": [VEHICLES, VEHICLE_INSURANCE, VEHICLE_INSPECTIONS, DRIVERS, VEHICLE_REQUESTS, TRIPS, VEHICLE_MAINTENANCE, VEHICLE_COSTS],
}

# ---------------------------------------------------------------------------
# SQL execution
# ---------------------------------------------------------------------------

def run_sql(sql_text, db_url, drop=False):
    """Execute SQL via psycopg2 (falls back to psql if unavailable)."""
    if drop:
        # Generate DROP statements for all nb_am_ tables (reverse order)
        all_tables = []
        for module in ["M4", "M3", "M2", "M1"]:
            for coll in reversed(ALL_COLLECTIONS[module]):
                all_tables.append(coll["name"])
        drop_sql = "\n".join(f"DROP TABLE IF EXISTS {t} CASCADE;" for t in all_tables)
        sql_text = drop_sql + "\n\n" + sql_text

    # Try psycopg2 first (no external dependency on psql binary)
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(sql_text)
        cur.close()
        conn.close()
        print(f"  ✅ SQL executed successfully (psycopg2)")
        return True
    except ImportError:
        pass  # Fall through to psql
    except Exception as e:
        print(f"  ❌ SQL error (psycopg2): {e}")
        return False

    # Fallback: psql CLI
    cmd = ["psql", db_url, "-c", sql_text]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  ❌ SQL error:\n{result.stderr}")
            return False
        print(f"  ✅ SQL executed successfully (psql)")
        return True
    except FileNotFoundError:
        print(f"  ❌ Neither psycopg2 nor psql available.")
        print(f"     Install: pip install psycopg2-binary")
        return False
    except subprocess.TimeoutExpired:
        print(f"  ❌ SQL timed out")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="资产行政管理系统 — 数据建模脚本 (23 tables)")
    parser.add_argument("--url", default=os.environ.get("NB_URL", "http://localhost:14000"))
    parser.add_argument("--user", default=os.environ.get("NB_USER", "admin@nocobase.com"))
    parser.add_argument("--password", default=os.environ.get("NB_PASSWORD", "admin123"))
    parser.add_argument("--db-url", default=os.environ.get("NB_DB_URL", "postgresql://nocobase:nocobase@localhost:5435/nocobase"))
    parser.add_argument("--module", "-m", choices=["M1", "M2", "M3", "M4"], help="Only process one module")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Preview mode")
    parser.add_argument("--skip-data", action="store_true", help="Skip seed data insertion")
    parser.add_argument("--sql-only", action="store_true", help="Only print/execute SQL, no API calls")
    parser.add_argument("--drop", action="store_true", help="DROP tables before CREATE (dangerous!)")
    parser.add_argument("--no-sql", action="store_true", help="Skip SQL, only do API registration")

    args = parser.parse_args()

    # Determine which modules to process
    modules = [args.module] if args.module else ["M1", "M2", "M3", "M4"]

    # ── Step 1: SQL DDL ──
    combined_sql = "\n".join(ALL_SQL[m] for m in modules)

    if args.sql_only:
        print(combined_sql)
        return

    if not args.no_sql:
        print(f"\n{'='*60}")
        print(f"  Step 1: Execute SQL DDL ({', '.join(modules)})")
        print(f"{'='*60}")
        if args.dry_run:
            print(f"  🔵 DRY-RUN: Would execute SQL for {', '.join(modules)}")
            print(combined_sql[:200] + "...")
        else:
            if not run_sql(combined_sql, args.db_url, drop=args.drop):
                print("\n  ⚠️  SQL failed — you may need to run it manually.")
                print("  Tip: python nb-am-setup.py --sql-only | psql $NB_DB_URL")
                # Continue anyway — tables might already exist
    else:
        print(f"\n  ⏭️  Skipping SQL (--no-sql)")

    # ── Step 2: NocoBase API ──
    print(f"\n{'='*60}")
    print(f"  Step 2: NocoBase API Registration")
    print(f"{'='*60}")

    client = NocoBaseClient(args.url, args.user, args.password)
    print(f"  🔑 Logging in to {args.url}...")
    try:
        client.login()
        print(f"  ✅ Authenticated")
    except Exception as e:
        print(f"  ❌ Login failed: {e}")
        sys.exit(1)

    # If --drop and data will be inserted, truncate tables first to prevent duplicates
    if args.drop and not args.skip_data and not args.dry_run:
        print(f"\n  Truncating data in tables (--drop mode)...")
        truncate_sql = ""
        for m in ["M4", "M3", "M2", "M1"]:
            if m in modules:
                for coll in reversed(ALL_COLLECTIONS[m]):
                    truncate_sql += f"TRUNCATE TABLE {coll['name']} CASCADE;\n"
        if truncate_sql:
            try:
                import psycopg2
                conn = psycopg2.connect(args.db_url)
                conn.autocommit = True
                cur = conn.cursor()
                cur.execute(truncate_sql)
                cur.close()
                conn.close()
                print(f"  ✅ Tables truncated")
            except Exception as e:
                print(f"  ⚠️  Truncate failed (data may duplicate): {e}")

    total = 0
    for m in modules:
        for coll in ALL_COLLECTIONS[m]:
            process_collection(client, coll, args.dry_run, args.skip_data)
            total += 1

    print(f"\n{'='*60}")
    print(f"  Done! Processed {total} collection(s)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
