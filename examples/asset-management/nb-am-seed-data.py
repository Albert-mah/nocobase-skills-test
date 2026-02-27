#!/usr/bin/env python3
"""AM 资产管理系统 — 测试数据生成

按依赖顺序插入全部 23 张表的模拟数据，覆盖各种状态。
用法：
    python3 scripts/nocobase/nb-am-seed-data.py          # 生成全部
    python3 scripts/nocobase/nb-am-seed-data.py clean     # 清空全部数据
"""

import sys, json, random
from datetime import date, timedelta

sys.path.insert(0, "scripts/nocobase")
from nb_page_builder import NB

nb = NB()
BASE = nb.base
S = nb.s

# ── helpers ──────────────────────────────────────────────────────

created_ids = {}  # table -> [id, ...]

def create(table, records):
    """批量创建记录，返回 id 列表"""
    ids = []
    for r in records:
        resp = S.post(f"{BASE}/api/{table}:create", json=r)
        if resp.ok and resp.json().get("data"):
            rid = resp.json()["data"].get("id")
            ids.append(rid)
        else:
            print(f"  ✗ {table}: {resp.status_code} — {resp.text[:200]}")
            ids.append(None)
    created_ids[table] = ids
    ok = sum(1 for i in ids if i)
    print(f"  ✓ {table}: {ok}/{len(records)}")
    return ids


def pick(table, idx=None):
    """从已创建的记录中取 id"""
    ids = created_ids.get(table, [])
    if not ids:
        return None
    if idx is not None:
        return ids[idx] if idx < len(ids) else ids[0]
    return random.choice([i for i in ids if i])


def d(offset_days=0):
    """生成日期字符串"""
    return (date.today() + timedelta(days=offset_days)).isoformat()


def clean_all():
    """按反向依赖顺序清空所有 AM 表"""
    tables = [
        # 先清子表
        "nb_am_vehicle_insurance", "nb_am_vehicle_inspections",
        "nb_am_vehicle_costs", "nb_am_vehicle_maintenance",
        "nb_am_trips", "nb_am_vehicle_requests", "nb_am_drivers",
        "nb_am_stock_records", "nb_am_inventories",
        "nb_am_consumable_requests", "nb_am_disposals", "nb_am_repairs",
        "nb_am_asset_transfers", "nb_am_purchase_requests",
        # 再清主表
        "nb_am_vehicles", "nb_am_consumables", "nb_am_assets",
        "nb_am_suppliers", "nb_am_locations", "nb_am_departments",
        "nb_am_consumable_categories", "nb_am_asset_categories",
        "nb_am_companies",
    ]
    for t in tables:
        r = S.get(f"{BASE}/api/{t}:list?paginate=false&fields[]=id")
        if not r.ok:
            continue
        ids = [rec["id"] for rec in r.json().get("data", [])]
        if not ids:
            print(f"  · {t}: empty")
            continue
        for rid in ids:
            S.post(f"{BASE}/api/{t}:destroy?filterByTk={rid}")
        print(f"  ✓ {t}: deleted {len(ids)}")


# ── Layer 0: 基础数据 ──────────────────────────────────────────

def seed_companies():
    return create("nb_am_companies", [
        {"name": "梧州总部", "code": "HQ", "short_code": "WZ",
         "company_type": "总公司", "status": "正常",
         "contact_person": "张三", "contact_phone": "13800138001",
         "address": "广西梧州市万秀区"},
        {"name": "南宁分公司", "code": "NN", "short_code": "NN",
         "company_type": "分公司", "status": "正常",
         "contact_person": "李四", "contact_phone": "13800138002",
         "address": "广西南宁市青秀区"},
        {"name": "桂林分公司", "code": "GL", "short_code": "GL",
         "company_type": "分公司", "status": "正常",
         "contact_person": "王五", "contact_phone": "13800138003",
         "address": "广西桂林市七星区"},
    ])


def seed_departments():
    c1, c2, c3 = created_ids["nb_am_companies"][:3]
    return create("nb_am_departments", [
        {"name": "行政部", "code": "ADMIN", "manager": "赵一", "companyId": c1},
        {"name": "技术部", "code": "TECH", "manager": "钱二", "companyId": c1},
        {"name": "财务部", "code": "FIN", "manager": "孙三", "companyId": c1},
        {"name": "销售部", "code": "SALES", "manager": "周四", "companyId": c2},
        {"name": "仓储部", "code": "WH", "manager": "吴五", "companyId": c2},
        {"name": "运营部", "code": "OPS", "manager": "郑六", "companyId": c3},
    ])


def seed_locations():
    c1, c2, c3 = created_ids["nb_am_companies"][:3]
    return create("nb_am_locations", [
        {"name": "梧州总部大楼", "location_type": "办公楼", "status": "在用",
         "address": "梧州市万秀区西江路88号", "resident_count": 120, "companyId": c1},
        {"name": "梧州仓库A", "location_type": "仓库", "status": "在用",
         "address": "梧州市龙圩区工业园", "resident_count": 8, "companyId": c1},
        {"name": "南宁办公室", "location_type": "办公楼", "status": "在用",
         "address": "南宁市青秀区东盟商务区", "resident_count": 45, "companyId": c2},
        {"name": "桂林办事处", "location_type": "办公室", "status": "在用",
         "address": "桂林市七星区高新区", "resident_count": 20, "companyId": c3},
    ])


def seed_suppliers():
    return create("nb_am_suppliers", [
        {"name": "联想供应商", "supply_type": "IT设备", "cooperation_status": "合作中",
         "contact_person": "刘经理", "contact_phone": "13900139001",
         "address": "深圳市南山区", "bank_name": "工商银行", "bank_account": "622202001001"},
        {"name": "格力空调", "supply_type": "办公设备", "cooperation_status": "合作中",
         "contact_person": "陈经理", "contact_phone": "13900139002",
         "address": "珠海市香洲区"},
        {"name": "中石化油品", "supply_type": "车辆油料", "cooperation_status": "合作中",
         "contact_person": "王主管", "contact_phone": "13900139003",
         "address": "梧州市长洲区"},
        {"name": "广西汽贸", "supply_type": "车辆维修", "cooperation_status": "合作中",
         "contact_person": "黄师傅", "contact_phone": "13900139004",
         "address": "梧州市万秀区"},
        {"name": "齐心办公", "supply_type": "办公耗材", "cooperation_status": "合作中",
         "contact_person": "何经理", "contact_phone": "13900139005",
         "address": "广州市天河区"},
    ])


def seed_asset_categories():
    return create("nb_am_asset_categories", [
        {"name": "电子设备", "code": "IT", "default_years": 5},
        {"name": "办公家具", "code": "FURN", "default_years": 10},
        {"name": "交通工具", "code": "VEH", "default_years": 8},
        {"name": "空调暖通", "code": "HVAC", "default_years": 10},
        {"name": "安防设备", "code": "SEC", "default_years": 8},
    ])


def seed_consumable_categories():
    return create("nb_am_consumable_categories", [
        {"name": "办公用纸", "need_approval": False},
        {"name": "打印耗材", "need_approval": False},
        {"name": "清洁用品", "need_approval": False},
        {"name": "电子配件", "need_approval": True},
        {"name": "劳保用品", "need_approval": False},
    ])


# ── Layer 1: 业务主表 ─────────────────────────────────────────

def seed_assets():
    c1, c2, _ = created_ids["nb_am_companies"][:3]
    cats = created_ids["nb_am_asset_categories"]
    deps = created_ids["nb_am_departments"]
    sups = created_ids["nb_am_suppliers"][:2]
    return create("nb_am_assets", [
        {"name": "ThinkPad X1 Carbon", "asset_code": "IT-2024-001", "brand": "联想",
         "model": "X1C Gen11", "serial_number": "SN10001", "status": "在用",
         "purchase_price": 12999, "salvage_value": 1000, "useful_years": 5,
         "purchase_date": "2024-03-15", "custodian": "钱二", "location": "梧州总部大楼3F",
         "companyId": c1, "categoryId": cats[0], "departmentId": deps[1], "supplierId": sups[0]},
        {"name": "MacBook Pro 16", "asset_code": "IT-2024-002", "brand": "Apple",
         "model": "M3 Pro", "serial_number": "SN10002", "status": "在用",
         "purchase_price": 19999, "salvage_value": 2000, "useful_years": 5,
         "purchase_date": "2024-06-01", "custodian": "张三", "location": "梧州总部大楼5F",
         "companyId": c1, "categoryId": cats[0], "departmentId": deps[0], "supplierId": sups[0]},
        {"name": "Dell 27寸显示器", "asset_code": "IT-2024-003", "brand": "Dell",
         "model": "U2723QE", "serial_number": "SN10003", "status": "在用",
         "purchase_price": 3599, "salvage_value": 300, "useful_years": 5,
         "purchase_date": "2024-03-15", "custodian": "钱二", "location": "梧州总部大楼3F",
         "companyId": c1, "categoryId": cats[0], "departmentId": deps[1], "supplierId": sups[0]},
        {"name": "格力柜机空调 5P", "asset_code": "HVAC-2023-001", "brand": "格力",
         "model": "KFR-120LW", "serial_number": "SN20001", "status": "在用",
         "purchase_price": 8999, "salvage_value": 500, "useful_years": 10,
         "purchase_date": "2023-06-01", "custodian": "赵一", "location": "梧州总部大楼1F大厅",
         "companyId": c1, "categoryId": cats[3], "departmentId": deps[0], "supplierId": sups[1]},
        {"name": "办公桌椅套装", "asset_code": "FURN-2024-001", "brand": "震旦",
         "model": "L1800", "serial_number": "SN30001", "status": "在用",
         "purchase_price": 2999, "salvage_value": 200, "useful_years": 10,
         "purchase_date": "2024-01-10", "custodian": "周四", "location": "南宁办公室",
         "companyId": c2, "categoryId": cats[1], "departmentId": deps[3], "supplierId": sups[0]},
        {"name": "海康威视监控套装", "asset_code": "SEC-2024-001", "brand": "海康威视",
         "model": "DS-7608NI", "serial_number": "SN40001", "status": "在用",
         "purchase_price": 15000, "salvage_value": 1000, "useful_years": 8,
         "purchase_date": "2024-02-20", "custodian": "赵一", "location": "梧州仓库A",
         "companyId": c1, "categoryId": cats[4], "departmentId": deps[0], "supplierId": sups[0]},
        {"name": "ThinkPad E16", "asset_code": "IT-2025-001", "brand": "联想",
         "model": "E16 Gen2", "serial_number": "SN10004", "status": "闲置",
         "purchase_price": 5999, "salvage_value": 500, "useful_years": 5,
         "purchase_date": "2025-01-05", "custodian": "", "location": "梧州仓库A",
         "companyId": c1, "categoryId": cats[0], "departmentId": deps[0], "supplierId": sups[0]},
        {"name": "佳能打印机", "asset_code": "IT-2023-005", "brand": "佳能",
         "model": "iR-ADV C5560", "serial_number": "SN50001", "status": "维修中",
         "purchase_price": 35000, "salvage_value": 3000, "useful_years": 8,
         "purchase_date": "2023-09-01", "custodian": "赵一", "location": "梧州总部大楼2F",
         "companyId": c1, "categoryId": cats[0], "departmentId": deps[0], "supplierId": sups[0]},
        {"name": "会议室投影仪", "asset_code": "IT-2024-010", "brand": "爱普生",
         "model": "CB-FH52", "serial_number": "SN60001", "status": "报废中",
         "purchase_price": 6500, "salvage_value": 200, "useful_years": 5,
         "purchase_date": "2020-03-01", "custodian": "赵一", "location": "梧州总部大楼5F会议室",
         "companyId": c1, "categoryId": cats[0], "departmentId": deps[0], "supplierId": sups[0]},
        {"name": "站立办公桌", "asset_code": "FURN-2025-001", "brand": "乐歌",
         "model": "E5", "serial_number": "SN30002", "status": "在用",
         "purchase_price": 3999, "salvage_value": 300, "useful_years": 10,
         "purchase_date": "2025-02-01", "custodian": "钱二", "location": "梧州总部大楼3F",
         "companyId": c1, "categoryId": cats[1], "departmentId": deps[1], "supplierId": sups[0]},
    ])


def seed_consumables():
    cats = created_ids["nb_am_consumable_categories"]
    return create("nb_am_consumables", [
        {"name": "A4 复印纸", "code": "CON-001", "unit": "包", "spec": "80g 500张/包",
         "current_stock": 200, "safe_stock": 50, "ref_price": 28, "status": "正常",
         "storage_location": "梧州仓库A-A1", "categoryId": cats[0]},
        {"name": "HP 黑色碳粉盒", "code": "CON-002", "unit": "个", "spec": "CF258A",
         "current_stock": 15, "safe_stock": 5, "ref_price": 380, "status": "正常",
         "storage_location": "梧州仓库A-A2", "categoryId": cats[1]},
        {"name": "中性笔 0.5mm", "code": "CON-003", "unit": "支", "spec": "黑色 0.5mm",
         "current_stock": 500, "safe_stock": 100, "ref_price": 2.5, "status": "正常",
         "storage_location": "梧州仓库A-A1", "categoryId": cats[0]},
        {"name": "洗手液", "code": "CON-004", "unit": "瓶", "spec": "500ml",
         "current_stock": 30, "safe_stock": 10, "ref_price": 18, "status": "正常",
         "storage_location": "梧州仓库A-B1", "categoryId": cats[2]},
        {"name": "USB-C 数据线", "code": "CON-005", "unit": "根", "spec": "1.5m 快充",
         "current_stock": 3, "safe_stock": 10, "ref_price": 35, "status": "库存不足",
         "storage_location": "梧州仓库A-A2", "categoryId": cats[3]},
        {"name": "垃圾袋", "code": "CON-006", "unit": "卷", "spec": "45×50cm 30只/卷",
         "current_stock": 80, "safe_stock": 20, "ref_price": 8, "status": "正常",
         "storage_location": "梧州仓库A-B1", "categoryId": cats[2]},
        {"name": "安全帽", "code": "CON-007", "unit": "顶", "spec": "ABS V型",
         "current_stock": 25, "safe_stock": 10, "ref_price": 45, "status": "正常",
         "storage_location": "梧州仓库A-C1", "categoryId": cats[4]},
        {"name": "HP 彩色碳粉套装", "code": "CON-008", "unit": "套", "spec": "CF400A四色",
         "current_stock": 2, "safe_stock": 3, "ref_price": 1200, "status": "库存不足",
         "storage_location": "梧州仓库A-A2", "categoryId": cats[1]},
    ])


def seed_vehicles():
    c1, c2, c3 = created_ids["nb_am_companies"][:3]
    return create("nb_am_vehicles", [
        {"plate_number": "桂D·A8888", "brand": "丰田", "model": "凯美瑞 2.5G",
         "vehicle_type": "轿车", "color": "白色", "seats": 5,
         "vin": "LVGB4A5E2PG001001", "engine_no": "ENG001",
         "fuel_type": "汽油", "purchase_date": "2023-05-15",
         "purchase_price": 189800, "current_mileage": 45600, "status": "在用",
         "companyId": c1},
        {"plate_number": "桂D·B6666", "brand": "别克", "model": "GL8 ES",
         "vehicle_type": "商务车", "color": "黑色", "seats": 7,
         "vin": "LVGB4A5E2PG001002", "engine_no": "ENG002",
         "fuel_type": "汽油", "purchase_date": "2023-08-20",
         "purchase_price": 289900, "current_mileage": 38200, "status": "在用",
         "companyId": c1},
        {"plate_number": "桂A·C3333", "brand": "比亚迪", "model": "汉EV",
         "vehicle_type": "轿车", "color": "灰色", "seats": 5,
         "vin": "LVGB4A5E2PG001003", "engine_no": "MOTOR003",
         "fuel_type": "纯电", "purchase_date": "2024-01-10",
         "purchase_price": 219800, "current_mileage": 22800, "status": "在用",
         "companyId": c2},
        {"plate_number": "桂D·D1111", "brand": "五菱", "model": "星光150Pro",
         "vehicle_type": "轿车", "color": "银色", "seats": 5,
         "vin": "LVGB4A5E2PG001004", "engine_no": "MOTOR004",
         "fuel_type": "插混", "purchase_date": "2025-01-20",
         "purchase_price": 98800, "current_mileage": 3200, "status": "在用",
         "companyId": c1},
        {"plate_number": "桂C·E9999", "brand": "丰田", "model": "海狮 9座",
         "vehicle_type": "客车", "color": "白色", "seats": 9,
         "vin": "LVGB4A5E2PG001005", "engine_no": "ENG005",
         "fuel_type": "柴油", "purchase_date": "2022-03-01",
         "purchase_price": 265000, "current_mileage": 86500, "status": "维修中",
         "companyId": c3},
    ])


def seed_drivers():
    c1, c2, c3 = created_ids["nb_am_companies"][:3]
    return create("nb_am_drivers", [
        {"employee_name": "刘师傅", "license_no": "450403199001011234",
         "license_class": "A2", "driver_type": "专职",
         "first_license_date": "2012-06-15", "license_expiry": "2028-06-15",
         "total_trips": 320, "total_mileage": 128000, "avg_rating": 4.8,
         "companyId": c1},
        {"employee_name": "陈师傅", "license_no": "450403198805022345",
         "license_class": "B1", "driver_type": "专职",
         "first_license_date": "2010-03-20", "license_expiry": "2026-03-20",
         "total_trips": 450, "total_mileage": 195000, "avg_rating": 4.6,
         "companyId": c1},
        {"employee_name": "黄师傅", "license_no": "450103199205033456",
         "license_class": "C1", "driver_type": "兼职",
         "first_license_date": "2015-09-01", "license_expiry": "2027-09-01",
         "total_trips": 80, "total_mileage": 32000, "avg_rating": 4.5,
         "companyId": c2},
    ])


# ── Layer 2: 业务流水 ─────────────────────────────────────────

def seed_purchase_requests():
    c1 = pick("nb_am_companies", 0)
    cats = created_ids["nb_am_asset_categories"]
    deps = created_ids["nb_am_departments"]
    sups = created_ids["nb_am_suppliers"]
    return create("nb_am_purchase_requests", [
        {"request_no": "PR-2026-001", "asset_name": "ThinkPad T16 笔记本",
         "applicant": "钱二", "quantity": 5, "estimated_price": 6999,
         "total_price": 34995, "brand_model": "联想 T16 Gen2",
         "reason": "技术部新入职员工配置", "status": "待审批",
         "expected_date": d(14), "purchase_date": None,
         "companyId": c1, "categoryId": cats[0], "departmentId": deps[1], "supplierId": sups[0]},
        {"request_no": "PR-2026-002", "asset_name": "办公椅",
         "applicant": "周四", "quantity": 10, "estimated_price": 1299,
         "total_price": 12990, "brand_model": "震旦 CH-180",
         "reason": "南宁办公室扩建", "status": "已审批",
         "expected_date": d(7), "purchase_date": d(-3),
         "actual_price": 1199, "actual_quantity": 10, "actual_total": 11990,
         "companyId": pick("nb_am_companies", 1), "categoryId": cats[1],
         "departmentId": deps[3], "supplierId": sups[0]},
        {"request_no": "PR-2026-003", "asset_name": "格力挂机空调 1.5P",
         "applicant": "赵一", "quantity": 3, "estimated_price": 3200,
         "total_price": 9600, "brand_model": "格力 KFR-35GW",
         "reason": "会议室空调老化更换", "status": "已完成",
         "expected_date": d(-20), "purchase_date": d(-25),
         "actual_price": 3100, "actual_quantity": 3, "actual_total": 9300,
         "invoice_no": "INV-2026-0088",
         "companyId": c1, "categoryId": cats[3], "departmentId": deps[0], "supplierId": sups[1]},
        {"request_no": "PR-2026-004", "asset_name": "会议室投影仪",
         "applicant": "赵一", "quantity": 1, "estimated_price": 8500,
         "total_price": 8500, "brand_model": "爱普生 CB-FH06",
         "reason": "替换报废投影仪", "status": "已驳回",
         "approval_remark": "请重新比价，预算超标",
         "companyId": c1, "categoryId": cats[0], "departmentId": deps[0], "supplierId": sups[0]},
    ])


def seed_asset_transfers():
    c1 = pick("nb_am_companies", 0)
    assets = created_ids["nb_am_assets"]
    deps = created_ids["nb_am_departments"]
    return create("nb_am_asset_transfers", [
        {"transfer_type": "领用", "applicant": "新员工小王",
         "reason": "入职配置笔记本电脑", "status": "已完成",
         "companyId": c1, "assetId": assets[0], "departmentId": deps[1]},
        {"transfer_type": "借用", "applicant": "周四",
         "reason": "南宁出差借用显示器", "status": "待归还",
         "expected_return_date": d(7),
         "companyId": c1, "assetId": assets[2], "departmentId": deps[3]},
        {"transfer_type": "调拨", "applicant": "赵一",
         "reason": "闲置笔记本调拨至南宁", "status": "已完成",
         "companyId": c1, "assetId": assets[6], "departmentId": deps[3]},
        {"transfer_type": "领用", "applicant": "钱二",
         "reason": "站立办公桌领用", "status": "已完成",
         "companyId": c1, "assetId": assets[9], "departmentId": deps[1]},
    ])


def seed_repairs():
    assets = created_ids["nb_am_assets"]
    sups = created_ids["nb_am_suppliers"]
    return create("nb_am_repairs", [
        {"repair_no": "RP-2026-001", "fault_desc": "打印机卡纸频繁，进纸轮磨损",
         "repair_method": "外修", "repair_content": "更换进纸轮组件+清洁光路",
         "repair_cost": 1200, "status": "维修中", "repair_result": "",
         "assetId": assets[7], "supplierId": sups[0]},
        {"repair_no": "RP-2026-002", "fault_desc": "投影仪灯泡烧毁，画面偏色",
         "repair_method": "外修", "repair_content": "检测后判断主板故障，维修不经济",
         "repair_cost": 0, "status": "已完成", "repair_result": "建议报废",
         "assetId": assets[8], "supplierId": sups[0]},
        {"repair_no": "RP-2025-018", "fault_desc": "空调制冷效果差",
         "repair_method": "上门维修", "repair_content": "清洗滤网+补充冷媒",
         "repair_cost": 350, "status": "已完成", "repair_result": "已恢复正常",
         "assetId": assets[3], "supplierId": sups[1]},
    ])


def seed_disposals():
    assets = created_ids["nb_am_assets"]
    c1 = pick("nb_am_companies", 0)
    return create("nb_am_disposals", [
        {"applicant": "赵一", "disposal_method": "报废回收",
         "reason": "主板故障维修不经济，已超使用年限",
         "book_value": 1200, "estimated_salvage": 200,
         "status": "待审批", "disposal_detail": "投影仪已使用6年，超过5年使用年限",
         "assetId": assets[8], "companyId": c1},
        {"applicant": "赵一", "disposal_method": "捐赠",
         "reason": "办公家具更新换代，旧家具捐赠社区",
         "book_value": 500, "estimated_salvage": 0,
         "status": "已完成", "disposal_detail": "已捐赠至梧州市万秀区社区服务中心",
         "companyId": c1},
    ])


def seed_consumable_requests():
    c1 = pick("nb_am_companies", 0)
    deps = created_ids["nb_am_departments"]
    return create("nb_am_consumable_requests", [
        {"applicant": "赵一", "status": "已完成", "total_amount": 560,
         "remark": "行政部月度办公用品领用",
         "companyId": c1, "departmentId": deps[0]},
        {"applicant": "钱二", "status": "已完成", "total_amount": 1520,
         "remark": "技术部碳粉+数据线补充",
         "companyId": c1, "departmentId": deps[1]},
        {"applicant": "周四", "status": "待审批", "total_amount": 2400,
         "remark": "南宁办公室开业物资采购（电子配件需审批）",
         "companyId": pick("nb_am_companies", 1), "departmentId": deps[3]},
        {"applicant": "吴五", "status": "已完成", "total_amount": 224,
         "remark": "仓库日常清洁用品补充",
         "companyId": pick("nb_am_companies", 1), "departmentId": deps[4]},
    ])


def seed_stock_records():
    cons = created_ids["nb_am_consumables"]
    reqs = created_ids["nb_am_consumable_requests"]
    c1 = pick("nb_am_companies", 0)
    return create("nb_am_stock_records", [
        # 入库记录
        {"record_type": "入库", "quantity": 100, "unit_price": 28,
         "operator": "吴五", "consumableId": cons[0], "companyId": c1},
        {"record_type": "入库", "quantity": 10, "unit_price": 380,
         "operator": "吴五", "consumableId": cons[1], "companyId": c1},
        {"record_type": "入库", "quantity": 200, "unit_price": 2.5,
         "operator": "吴五", "consumableId": cons[2], "companyId": c1},
        # 出库记录（领用）
        {"record_type": "出库", "quantity": 20, "unit_price": 28,
         "operator": "赵一", "consumableId": cons[0], "requestId": reqs[0], "companyId": c1},
        {"record_type": "出库", "quantity": 4, "unit_price": 380,
         "operator": "钱二", "consumableId": cons[1], "requestId": reqs[1], "companyId": c1},
        {"record_type": "出库", "quantity": 50, "unit_price": 2.5,
         "operator": "赵一", "consumableId": cons[2], "requestId": reqs[0], "companyId": c1},
    ])


def seed_inventories():
    c1 = pick("nb_am_companies", 0)
    deps = created_ids["nb_am_departments"]
    return create("nb_am_inventories", [
        {"task_name": "2026年Q1固定资产盘点", "scope": "全公司",
         "status": "已完成", "deadline": d(-10),
         "normal_count": 8, "abnormal_count": 1,
         "companyId": c1, "departmentId": deps[0]},
        {"task_name": "2026年Q1耗材盘点", "scope": "仓库",
         "status": "进行中", "deadline": d(5),
         "normal_count": 6, "abnormal_count": 2,
         "companyId": c1, "departmentId": deps[4] if len(deps) > 4 else deps[0]},
    ])


def seed_vehicle_requests():
    c1 = pick("nb_am_companies", 0)
    vehs = created_ids["nb_am_vehicles"]
    drvs = created_ids["nb_am_drivers"]
    deps = created_ids["nb_am_departments"]
    return create("nb_am_vehicle_requests", [
        {"request_no": "VR-2026-001", "applicant": "张三", "use_date": d(1),
         "depart_time": "08:30:00", "return_time": "17:30:00",
         "destination": "南宁市青秀区客户现场", "purpose": "客户拜访+项目交付",
         "passenger_count": 3, "passengers": "张三、钱二、客户经理",
         "need_driver": True, "status": "已派车",
         "companyId": c1, "departmentId": deps[0],
         "vehicleId": vehs[1], "driverId": drvs[0]},
        {"request_no": "VR-2026-002", "applicant": "钱二", "use_date": d(3),
         "depart_time": "09:00:00", "return_time": "12:00:00",
         "destination": "梧州市龙圩区仓库", "purpose": "仓库盘点",
         "passenger_count": 2, "need_driver": False, "status": "待审批",
         "companyId": c1, "departmentId": deps[1]},
        {"request_no": "VR-2026-003", "applicant": "郑六", "use_date": d(-5),
         "depart_time": "07:00:00", "return_time": "19:00:00",
         "destination": "桂林市区多个客户点", "purpose": "区域巡检",
         "passenger_count": 4, "passengers": "郑六、巡检员×3",
         "need_driver": True, "status": "已完成",
         "companyId": pick("nb_am_companies", 2), "departmentId": deps[5],
         "vehicleId": vehs[4], "driverId": drvs[1]},
    ])


def seed_trips():
    vehs = created_ids["nb_am_vehicles"]
    drvs = created_ids["nb_am_drivers"]
    reqs = created_ids["nb_am_vehicle_requests"]
    return create("nb_am_trips", [
        {"start_mileage": 86500, "end_mileage": 86780, "distance": 280,
         "start_fuel": "满", "end_fuel": "3/4", "status": "已完成",
         "checkin_time": (date.today() + timedelta(days=-5)).isoformat() + "T19:15:00+08:00",
         "vehicleId": vehs[4], "driverId": drvs[1], "requestId": reqs[2]},
        {"start_mileage": 38200, "end_mileage": 0, "distance": 0,
         "start_fuel": "满", "status": "出车中",
         "vehicleId": vehs[1], "driverId": drvs[0], "requestId": reqs[0]},
    ])


def seed_vehicle_maintenance():
    vehs = created_ids["nb_am_vehicles"]
    c1 = pick("nb_am_companies", 0)
    sups = created_ids["nb_am_suppliers"]
    return create("nb_am_vehicle_maintenance", [
        {"maint_type": "保养", "plan_date": d(-30), "current_mileage": 45000,
         "detail": "更换机油+机滤+空气滤+空调滤", "status": "已完成",
         "parts_cost": 680, "labor_cost": 200, "total_cost": 880,
         "next_maint_date": d(150), "next_maint_mileage": 55000,
         "use_insurance": False, "insurance_amount": 0,
         "vehicleId": vehs[0], "companyId": c1, "supplierId": sups[3]},
        {"maint_type": "维修", "plan_date": d(-10), "current_mileage": 86500,
         "detail": "更换前刹车片+刹车油", "status": "维修中",
         "parts_cost": 1200, "labor_cost": 400, "total_cost": 1600,
         "use_insurance": False, "insurance_amount": 0,
         "vehicleId": vehs[4], "companyId": pick("nb_am_companies", 2), "supplierId": sups[3]},
        {"maint_type": "保养", "plan_date": d(15), "current_mileage": 22800,
         "detail": "首次大保养（电池检测+制动液+轮胎轮换）", "status": "待保养",
         "vehicleId": vehs[2], "companyId": pick("nb_am_companies", 1), "supplierId": sups[3]},
    ])


def seed_vehicle_costs():
    vehs = created_ids["nb_am_vehicles"]
    c1 = pick("nb_am_companies", 0)
    return create("nb_am_vehicle_costs", [
        {"cost_type": "加油", "amount": 450, "cost_date": d(-15),
         "operator": "刘师傅", "remark": "95号汽油 60L",
         "vehicleId": vehs[0], "companyId": c1},
        {"cost_type": "加油", "amount": 520, "cost_date": d(-8),
         "operator": "陈师傅", "remark": "95号汽油 70L",
         "vehicleId": vehs[1], "companyId": c1},
        {"cost_type": "充电", "amount": 85, "cost_date": d(-12),
         "operator": "黄师傅", "remark": "快充桩 65kWh",
         "vehicleId": vehs[2], "companyId": pick("nb_am_companies", 1)},
        {"cost_type": "停车", "amount": 120, "cost_date": d(-5),
         "operator": "刘师傅", "remark": "南宁客户现场停车费",
         "vehicleId": vehs[1], "companyId": c1},
        {"cost_type": "违章", "amount": 200, "cost_date": d(-20),
         "operator": "陈师傅", "remark": "超速罚款",
         "vehicleId": vehs[1], "companyId": c1},
        {"cost_type": "过路费", "amount": 180, "cost_date": d(-5),
         "operator": "陈师傅", "remark": "梧州-桂林高速",
         "vehicleId": vehs[4], "companyId": pick("nb_am_companies", 2)},
    ])


def seed_vehicle_inspections():
    vehs = created_ids["nb_am_vehicles"]
    return create("nb_am_vehicle_inspections", [
        {"inspection_date": "2025-05-10", "valid_until": "2027-05-10",
         "station": "梧州市车辆检测站", "cost": 300, "vehicleId": vehs[0]},
        {"inspection_date": "2025-08-15", "valid_until": "2027-08-15",
         "station": "梧州市车辆检测站", "cost": 300, "vehicleId": vehs[1]},
        {"inspection_date": "2025-01-20", "valid_until": "2027-01-20",
         "station": "南宁市第二检测站", "cost": 280, "vehicleId": vehs[2]},
        {"inspection_date": "2024-03-05", "valid_until": "2026-03-05",
         "station": "桂林市综合检测站", "cost": 320, "vehicleId": vehs[4]},
    ])


def seed_vehicle_insurance():
    vehs = created_ids["nb_am_vehicles"]
    return create("nb_am_vehicle_insurance", [
        {"insurance_type": "交强险", "insurance_company": "中国人保",
         "policy_no": "PICC-2025-001", "premium": 950,
         "start_date": "2025-05-15", "end_date": "2026-05-14",
         "vehicleId": vehs[0]},
        {"insurance_type": "商业险", "insurance_company": "中国人保",
         "policy_no": "PICC-2025-002", "premium": 3800,
         "start_date": "2025-05-15", "end_date": "2026-05-14",
         "vehicleId": vehs[0]},
        {"insurance_type": "交强险", "insurance_company": "平安保险",
         "policy_no": "PA-2025-001", "premium": 950,
         "start_date": "2025-08-20", "end_date": "2026-08-19",
         "vehicleId": vehs[1]},
        {"insurance_type": "商业险", "insurance_company": "平安保险",
         "policy_no": "PA-2025-002", "premium": 5200,
         "start_date": "2025-08-20", "end_date": "2026-08-19",
         "vehicleId": vehs[1]},
        {"insurance_type": "交强险", "insurance_company": "太平洋保险",
         "policy_no": "CPIC-2025-001", "premium": 950,
         "start_date": "2025-01-10", "end_date": "2026-01-09",
         "vehicleId": vehs[2]},
    ])


# ── main ─────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        print("🗑️  清空 AM 全部数据...")
        clean_all()
        print("\n✅ 清空完成")
        return

    print("🌱 AM 测试数据生成")
    print("=" * 50)

    print("\n── Layer 0: 基础数据 ──")
    seed_companies()
    seed_departments()
    seed_locations()
    seed_suppliers()
    seed_asset_categories()
    seed_consumable_categories()

    print("\n── Layer 1: 业务主表 ──")
    seed_assets()
    seed_consumables()
    seed_vehicles()
    seed_drivers()

    print("\n── Layer 2: 业务流水 ──")
    seed_purchase_requests()
    seed_asset_transfers()
    seed_repairs()
    seed_disposals()
    seed_consumable_requests()
    seed_stock_records()
    seed_inventories()
    seed_vehicle_requests()
    seed_trips()
    seed_vehicle_maintenance()
    seed_vehicle_costs()
    seed_vehicle_inspections()
    seed_vehicle_insurance()

    # 统计
    print("\n" + "=" * 50)
    total = sum(len([i for i in ids if i]) for ids in created_ids.values())
    print(f"✅ 完成！共创建 {total} 条记录，覆盖 {len(created_ids)} 张表")
    print()
    for table, ids in created_ids.items():
        short = table.replace("nb_am_", "")
        ok = sum(1 for i in ids if i)
        print(f"  {short}: {ok}")


if __name__ == "__main__":
    main()
