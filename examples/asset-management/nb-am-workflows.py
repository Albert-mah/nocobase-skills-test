#!/usr/bin/env python3
"""nb-am-workflows.py -- AM 系统工作流批量创建脚本

依赖：nb_page_builder.py + nb_workflow_builder.py
用法：
    python3 nb-am-workflows.py              # 全部（跳过 WF-02/06/10 审批流程）
    python3 nb-am-workflows.py purchases    # 采购相关 (WF-01, WF-15)
    python3 nb-am-workflows.py assets       # 资产相关 (WF-03, WF-04, WF-05a/b, WF-07)
    python3 nb-am-workflows.py consumables  # 易耗品 (WF-08, WF-09)
    python3 nb-am-workflows.py vehicles     # 车辆 (WF-11, WF-12, WF-13, WF-14)
    python3 nb-am-workflows.py clean        # 清理所有 AM 工作流（重建前用）

跳过项：
    WF-02 采购审批流程      -- 需要 manual 节点 + 用户 ID，暂不自动化
    WF-06 报废审批流程      -- 同上
    WF-10 用车审批流程      -- 同上

设计文档：am-workflows.md
"""

import sys
from nb_page_builder import NB
from nb_workflow_builder import WorkflowBuilder

# ── 命名前缀（用于 clean 和重名检查）──────────────────
PREFIX = "AM-"


# ═══════════════════════════════════════════════════════════════
# 采购相关 (WF-01, WF-15)
# ═══════════════════════════════════════════════════════════════

def wf01_purchase_status(wb):
    """WF-01：采购申请状态自动更新

    触发：nb_am_purchase_requests 新增
    逻辑：status 为空时自动设为"草稿"
    """
    print("\n-- WF-01 采购申请状态自动更新")
    wf = wb.on_create(f"{PREFIX}WF01 采购申请状态自动更新",
                      "nb_am_purchase_requests")
    if not wf:
        return
    n = wf.condition_equal("status", None, title="检查状态是否为空")
    n.on_true().update("nb_am_purchase_requests",
                       {"status": "草稿"}, title="设置状态为草稿")
    wf.enable()


def wf15_purchase_number(wb):
    """WF-15：采购申请编号自动生成

    触发：nb_am_purchase_requests 新增
    逻辑：生成 PR-YYYY-NNN 格式编号
    """
    print("\n-- WF-15 采购申请编号自动生成")
    wf = wb.on_create(f"{PREFIX}WF15 采购申请编号自动生成",
                      "nb_am_purchase_requests")
    if not wf:
        return
    wf.sql("""
        UPDATE nb_am_purchase_requests
        SET request_no = 'PR-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
            LPAD(CAST((SELECT COALESCE(MAX(CAST(SUBSTRING(request_no FROM '[0-9]+$') AS INT)), 0) + 1
                  FROM nb_am_purchase_requests
                  WHERE request_no LIKE 'PR-' || TO_CHAR(NOW(), 'YYYY') || '-%') AS TEXT), 3, '0')
        WHERE id = {{$context.data.id}}
    """, title="生成采购编号")
    wf.enable()


# ═══════════════════════════════════════════════════════════════
# 资产相关 (WF-03, WF-04, WF-05a/b, WF-07)
# ═══════════════════════════════════════════════════════════════

def wf03_transfer_status(wb):
    """WF-03：资产领用/借用状态联动

    触发：nb_am_asset_transfers 新增
    逻辑：领用 -> 资产"在用"，借用 -> 资产"借用中"
    """
    print("\n-- WF-03 资产领用借用状态联动")
    wf = wb.on_create(f"{PREFIX}WF03 资产领用借用状态联动",
                      "nb_am_asset_transfers",
                      appends=["asset"])
    if not wf:
        return
    n = wf.condition_equal("transfer_type", "领用", title="是否为领用")
    n.on_true().update("nb_am_assets", {"status": "在用"},
                       filter={"id": "{{$context.data.asset_id}}"},
                       title="资产状态->在用")
    n.on_false().update("nb_am_assets", {"status": "借用中"},
                        filter={"id": "{{$context.data.asset_id}}"},
                        title="资产状态->借用中")
    wf.enable()


def wf04_asset_return(wb):
    """WF-04：资产归还处理

    触发：nb_am_asset_transfers status 变更
    条件：status == "已归还"
    逻辑：资产状态恢复为"在库"
    """
    print("\n-- WF-04 资产归还处理")
    wf = wb.on_update(f"{PREFIX}WF04 资产归还处理",
                      "nb_am_asset_transfers",
                      changed=["status"],
                      condition={"status": {"$eq": "已归还"}},
                      appends=["asset"])
    if not wf:
        return
    wf.update("nb_am_assets", {"status": "在库"},
              filter={"id": "{{$context.data.asset_id}}"},
              title="资产状态->在库")
    wf.enable()


def wf05a_repair_create(wb):
    """WF-05a：报修创建 -> 资产状态更新

    触发：nb_am_repairs 新增
    逻辑：关联资产状态设为"报修中"
    """
    print("\n-- WF-05a 报修创建→资产状态更新")
    wf = wb.on_create(f"{PREFIX}WF05a 报修创建→资产状态更新",
                      "nb_am_repairs")
    if not wf:
        return
    wf.update("nb_am_assets", {"status": "报修中"},
              filter={"id": "{{$context.data.asset_id}}"},
              title="资产状态->报修中")
    wf.enable()


def wf05b_repair_complete(wb):
    """WF-05b：报修完成 -> 资产状态联动

    触发：nb_am_repairs status 变更为"已完成"
    逻辑：已修复 -> 资产"在用"，其他 -> 不处理
    """
    print("\n-- WF-05b 报修完成→资产状态联动")
    wf = wb.on_update(f"{PREFIX}WF05b 报修完成→资产状态联动",
                      "nb_am_repairs",
                      changed=["status"],
                      condition={"$and": [{"status": {"$eq": "已完成"}}]})
    if not wf:
        return
    n = wf.condition_equal("result", "已修复", title="是否已修复")
    n.on_true().update("nb_am_assets", {"status": "在用"},
                       filter={"id": "{{$context.data.asset_id}}"},
                       title="资产状态->在用")
    wf.enable()


def wf07_disposal_complete(wb):
    """WF-07：报废完成 -> 资产状态更新

    触发：nb_am_disposals status 变更为"已报废"
    逻辑：关联资产状态设为"已报废"
    """
    print("\n-- WF-07 报废完成→资产状态更新")
    wf = wb.on_update(f"{PREFIX}WF07 报废完成→资产状态更新",
                      "nb_am_disposals",
                      changed=["status"],
                      condition={"status": {"$eq": "已报废"}})
    if not wf:
        return
    wf.update("nb_am_assets", {"status": "已报废"},
              filter={"id": "{{$context.data.asset_id}}"},
              title="资产状态->已报废")
    wf.enable()


# ═══════════════════════════════════════════════════════════════
# 易耗品 (WF-08, WF-09)
# ═══════════════════════════════════════════════════════════════

def wf08_consumable_deduct(wb):
    """WF-08：易耗品领用 -> 库存扣减

    触发：nb_am_consumable_requests status 变更为"已发放"
    逻辑：SQL 批量扣减对应物品库存
    """
    print("\n-- WF-08 易耗品领用→库存扣减")
    wf = wb.on_update(f"{PREFIX}WF08 易耗品领用→库存扣减",
                      "nb_am_consumable_requests",
                      changed=["status"],
                      condition={"status": {"$eq": "已发放"}})
    if not wf:
        return
    wf.sql("""
        UPDATE nb_am_consumables c
        SET current_stock = current_stock - sr.quantity
        FROM nb_am_stock_records sr
        WHERE sr.consumable_id = c.id
          AND sr.request_id = {{$context.data.id}}
          AND sr.record_type = '出库'
    """, title="批量扣减库存")
    wf.enable()


def wf09_stock_alert(wb):
    """WF-09：库存变动 -> 预警检查

    触发：nb_am_stock_records 新增
    逻辑：查询物品当前库存，低于安全库存时标记预警
    """
    print("\n-- WF-09 库存变动→预警检查")
    wf = wb.on_create(f"{PREFIX}WF09 库存变动→预警检查",
                      "nb_am_stock_records",
                      appends=["consumable"])
    if not wf:
        return
    # SQL 方式：直接查询并标记
    wf.sql("""
        UPDATE nb_am_consumables
        SET remark = CASE
            WHEN current_stock < safe_stock THEN '库存不足'
            ELSE remark
        END
        WHERE id = {{$context.data.consumable_id}}
          AND status = '启用'
          AND current_stock < safe_stock
    """, title="检查并标记库存预警")
    wf.enable()


# ═══════════════════════════════════════════════════════════════
# 车辆 (WF-11, WF-12, WF-13, WF-14)
# ═══════════════════════════════════════════════════════════════

def wf11_vehicle_status(wb):
    """WF-11：用车派车 -> 车辆状态联动

    触发：nb_am_vehicle_requests status 变更
    条件：status in [已派车, 已完成, 已取消]
    逻辑：已派车 -> 车辆"使用中"，已完成/已取消 -> 车辆"可用"
    """
    print("\n-- WF-11 用车派车→车辆状态联动")
    wf = wb.on_update(f"{PREFIX}WF11 用车派车→车辆状态联动",
                      "nb_am_vehicle_requests",
                      changed=["status"],
                      condition={"status": {"$in": ["已派车", "已完成", "已取消"]}})
    if not wf:
        return
    n = wf.condition_equal("status", "已派车", title="是否已派车")
    n.on_true().update("nb_am_vehicles", {"status": "使用中"},
                       filter={"id": "{{$context.data.vehicle_id}}"},
                       title="车辆状态->使用中")
    n.on_false().update("nb_am_vehicles", {"status": "可用"},
                        filter={"id": "{{$context.data.vehicle_id}}"},
                        title="车辆状态->可用")
    wf.enable()


def wf12_trip_mileage(wb):
    """WF-12：行程完成 -> 里程更新

    触发：nb_am_trips status 变更为"已完成"
    逻辑：计算行驶距离，更新车辆当前里程
    """
    print("\n-- WF-12 行程完成→里程更新")
    wf = wb.on_update(f"{PREFIX}WF12 行程完成→里程更新",
                      "nb_am_trips",
                      changed=["status"],
                      condition={"status": {"$eq": "已完成"}})
    if not wf:
        return
    wf.sql("""
        UPDATE nb_am_trips
        SET distance = end_mileage - start_mileage
        WHERE id = {{$context.data.id}};

        UPDATE nb_am_vehicles
        SET current_mileage = {{$context.data.end_mileage}}
        WHERE id = {{$context.data.vehicle_id}};
    """, title="计算里程并更新车辆")
    wf.enable()


def wf13_insurance_reminder(wb):
    """WF-13：保险到期提醒

    触发：nb_am_vehicle_insurance.end_date 到期前 30 天
    逻辑：标记即将到期（后续接通知渠道后可改为发送通知）
    """
    print("\n-- WF-13 保险到期提醒")
    wf = wb.on_date_field(f"{PREFIX}WF13 保险到期提醒",
                          "nb_am_vehicle_insurance",
                          field="end_date", offset_days=-30,
                          appends=["vehicle"])
    if not wf:
        return
    wf.sql("""
        UPDATE nb_am_vehicle_insurance
        SET remark = '即将到期'
        WHERE id = {{$context.data.id}}
    """, title="标记到期提醒")
    wf.enable()


def wf14_inspection_reminder(wb):
    """WF-14：年检到期提醒

    触发：nb_am_vehicle_inspections.valid_until 到期前 30 天
    逻辑：标记即将到期
    """
    print("\n-- WF-14 年检到期提醒")
    wf = wb.on_date_field(f"{PREFIX}WF14 年检到期提醒",
                          "nb_am_vehicle_inspections",
                          field="valid_until", offset_days=-30,
                          appends=["vehicle"])
    if not wf:
        return
    wf.sql("""
        UPDATE nb_am_vehicle_inspections
        SET remark = '即将到期'
        WHERE id = {{$context.data.id}}
    """, title="标记到期提醒")
    wf.enable()


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

SECTIONS = {
    "purchases":   [wf01_purchase_status, wf15_purchase_number],
    "assets":      [wf03_transfer_status, wf04_asset_return,
                    wf05a_repair_create, wf05b_repair_complete,
                    wf07_disposal_complete],
    "consumables": [wf08_consumable_deduct, wf09_stock_alert],
    "vehicles":    [wf11_vehicle_status, wf12_trip_mileage,
                    wf13_insurance_reminder, wf14_inspection_reminder],
}


def main():
    section = sys.argv[1] if len(sys.argv) > 1 else "all"

    nb = NB()
    wb = WorkflowBuilder(nb)

    print(f"\n{'=' * 60}")
    print(f"  AM Workflow Builder")
    print(f"  Section: {section}")
    print(f"{'=' * 60}")

    # clean 模式：删除所有 AM 工作流
    if section == "clean":
        count = wb.clean_by_prefix(PREFIX)
        print(f"\n  Deleted {count} workflows with prefix '{PREFIX}'")
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
        print(f"Available: {', '.join(SECTIONS.keys())}, clean, all")
        return

    for fn in funcs:
        try:
            fn(wb)
        except Exception as e:
            print(f"  [ERR] {fn.__name__}: {e}")
            import traceback
            traceback.print_exc()

    wb.summary()


if __name__ == "__main__":
    main()
