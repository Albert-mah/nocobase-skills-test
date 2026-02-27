#!/usr/bin/env python3
"""nb-am-js-blocks.py — 为 AM 系统补充 JS 区块

在已创建的页面上追加缺失的 JS 列（状态标记、金额格式化、到期提醒等）
以及填充 TODO 占位的 JS 区块（资产卡片、车辆卡片）。

用法：
    python3 nb-am-js-blocks.py              # 全部
    python3 nb-am-js-blocks.py columns      # 只加 JS 列
    python3 nb-am-js-blocks.py cards        # 只填充详情卡片
    python3 nb-am-js-blocks.py audit        # 只审计（不写入）

前置：nb-am-pages.py 已执行（页面已创建）
"""

import sys
from nb_page_builder import NB

# ═══════════════════════════════════════════════════════════════
# 表格 UID 动态查找（collection name → 页面 title 映射）
# ═══════════════════════════════════════════════════════════════

# collection → 期望匹配的页面 key
TABLE_COLL_MAP = {
    "资产台账":         "nb_am_assets",
    "采购申请":         "nb_am_purchase_requests",
    "领用借用":         "nb_am_asset_transfers",
    "报修管理":         "nb_am_repairs",
    "报废管理":         "nb_am_disposals",
    "物品目录":         "nb_am_consumables",
    "领用申请":         "nb_am_consumable_requests",
    "库存管理":         "nb_am_stock_records",
    "车辆档案":         "nb_am_vehicles",
    "用车申请":         "nb_am_vehicle_requests",
    "行程记录":         "nb_am_trips",
    "保养维修":         "nb_am_vehicle_maintenance",
    "费用统计":         "nb_am_vehicle_costs",
}

# 子表：assoc collection → parent collection（用于查找详情弹窗内的子表）
SUB_TABLE_MAP = {
    "领用记录(资产详情)": ("nb_am_asset_transfers", "nb_am_assets"),
    "报修记录(资产详情)": ("nb_am_repairs", "nb_am_assets"),
    "报废记录(资产详情)": ("nb_am_disposals", "nb_am_assets"),
}

# TODO 卡片：title keyword → 对应代码变量名
TODO_CARD_MAP = {
    "资产卡片": "ASSET_CARD_CODE",
    "车辆卡片": "VEHICLE_CARD_CODE",
}

TABLES = {}  # 动态填充


def discover_tables(nb):
    """从 flowModels API 动态发现所有 TableBlockModel 的 UID。"""
    global TABLES
    r = nb.s.get(f"{nb.base}/api/flowModels:list?paginate=false")
    all_models = r.json().get("data", [])

    # 主表：找 TableBlockModel 匹配 collection
    coll_to_keys = {}
    for key, coll in TABLE_COLL_MAP.items():
        coll_to_keys.setdefault(coll, []).append(key)

    for m in all_models:
        if m.get("use") != "TableBlockModel":
            continue
        coll = (m.get("stepParams") or {}).get("resourceSettings", {}).get("init", {}).get("collectionName", "")
        assoc = (m.get("stepParams") or {}).get("resourceSettings", {}).get("init", {}).get("associationName", "")
        if assoc:
            # 子表（在详情弹窗内）
            for key, (sub_coll, parent_coll) in SUB_TABLE_MAP.items():
                if coll == sub_coll and parent_coll in assoc:
                    TABLES[key] = m["uid"]
                    break
        elif coll in coll_to_keys:
            # 主表：可能多个同 collection 的 TableBlockModel，取第一个（页面级的）
            for key in coll_to_keys[coll]:
                if key not in TABLES:
                    TABLES[key] = m["uid"]
                    break

    print(f"\n  Discovered {len(TABLES)} tables:")
    for name, uid in TABLES.items():
        print(f"    {name:24s} [{uid}]")


# ═══════════════════════════════════════════════════════════════
# JS 列代码模板（全部支持暗色模式）
# ═══════════════════════════════════════════════════════════════

def _tag(field, mapping, default_color="default"):
    """生成通用状态 Tag 列代码。"""
    # mapping: {'值': 'color', ...}
    pairs = ", ".join(f"'{k}':'{v}'" for k, v in mapping.items())
    return f"""const r = ctx.record || {{}};
const s = r.{field} || '';
const m = {{{pairs}}};
ctx.render(ctx.React.createElement(ctx.antd.Tag, {{color: m[s]||'{default_color}'}}, s||'-'));"""


def _badge(field, mapping, default_status="default"):
    """生成通用状态 Badge 列代码。"""
    pairs = ", ".join(f"'{k}':'{v}'" for k, v in mapping.items())
    return f"""const r = ctx.record || {{}};
const s = r.{field} || '';
const m = {{{pairs}}};
ctx.render(ctx.React.createElement(ctx.antd.Badge, {{status: m[s]||'{default_status}', text: s||'-'}}));"""


def _money(field):
    """生成金额格式化列代码。"""
    return f"""const r = ctx.record || {{}};
const v = r.{field};
const text = v != null ? '\\u00A5' + Number(v).toLocaleString('zh-CN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) : '-';
const color = v > 10000 ? ctx.themeToken?.colorWarning || '#faad14' : ctx.themeToken?.colorText || '#000';
ctx.render(ctx.React.createElement('span', {{style: {{fontWeight: 500, color}}}}, text));"""


def _date_countdown(field, label="到期"):
    """生成日期倒计时列代码（到期提醒）。"""
    return f"""const r = ctx.record || {{}};
const d = r.{field};
if (!d) {{ ctx.render(ctx.React.createElement('span', {{style: {{color: '#999'}}}}, '-')); return; }}
const diff = Math.ceil((new Date(d) - new Date()) / 86400000);
let color = '#52c41a', text = diff + '天';
if (diff < 0) {{ color = '#ff4d4f'; text = '已过期' + Math.abs(diff) + '天'; }}
else if (diff <= 30) {{ color = '#faad14'; text = diff + '天'; }}
ctx.render(ctx.React.createElement(ctx.antd.Tag, {{color}}, '{label}: ' + text));"""


# ═══════════════════════════════════════════════════════════════
# Step 1: 补充缺失的 JS 列
# ═══════════════════════════════════════════════════════════════

def add_js_columns(nb):
    """为各表格添加 JS 状态标记列。"""
    print("\n" + "=" * 60)
    print("  Adding JS Columns...")
    print("=" * 60)

    # ── 领用借用：状态标记 + 类型标记
    tbl = TABLES["领用借用"]
    print(f"\n  领用借用 [{tbl}]")

    nb.js_column(tbl, "状态", _tag("status", {
        "待审批": "orange", "待发放": "processing",
        "已发放": "blue", "已归还": "green",
        "已驳回": "red", "已取消": "default",
    }), sort=90, width=90)

    nb.js_column(tbl, "类型", _tag("transfer_type", {
        "领用": "blue", "借用": "orange", "归还": "green",
    }), sort=5, width=70)

    # ── 报修管理：状态标记 + 费用
    tbl = TABLES["报修管理"]
    print(f"\n  报修管理 [{tbl}]")

    nb.js_column(tbl, "状态", _badge("status", {
        "待受理": "warning", "维修中": "processing",
        "已完成": "success", "已取消": "default",
    }), sort=90, width=100)

    nb.js_column(tbl, "维修费", _money("repair_cost"), sort=85, width=110)

    # ── 报废管理：状态标记 + 残值
    tbl = TABLES["报废管理"]
    print(f"\n  报废管理 [{tbl}]")

    nb.js_column(tbl, "审批状态", _badge("status", {
        "草稿": "default",
        "待部门审批": "processing", "待行政鉴定": "processing",
        "待财务审核": "warning", "待领导审批": "warning",
        "已通过": "success", "已驳回": "error",
        "待处置": "processing", "已报废": "success",
    }), sort=90, width=110)

    nb.js_column(tbl, "账面价值", _money("book_value"), sort=85, width=110)

    # ── 领用申请：审批状态
    tbl = TABLES["领用申请"]
    print(f"\n  领用申请 [{tbl}]")

    nb.js_column(tbl, "审批状态", _badge("status", {
        "草稿": "default", "待审批": "warning",
        "待发放": "processing", "已发放": "success",
        "已驳回": "error",
    }), sort=90, width=100)

    nb.js_column(tbl, "金额", _money("total_amount"), sort=85, width=100)

    # ── 库存管理：出入库类型标记
    tbl = TABLES["库存管理"]
    print(f"\n  库存管理 [{tbl}]")

    nb.js_column(tbl, "类型标记", _tag("record_type", {
        "入库": "green", "出库": "blue",
        "盘盈": "cyan", "盘亏": "red",
    }), sort=5, width=80)

    nb.js_column(tbl, "单价", _money("unit_price"), sort=85, width=100)

    # ── 车辆档案：状态标记
    tbl = TABLES["车辆档案"]
    print(f"\n  车辆档案 [{tbl}]")

    nb.js_column(tbl, "状态标记", _tag("status", {
        "可用": "green", "使用中": "blue",
        "维修中": "orange", "已报废": "red",
        "已处置": "default",
    }), sort=90, width=90)

    # ── 用车申请：审批状态
    tbl = TABLES["用车申请"]
    print(f"\n  用车申请 [{tbl}]")

    nb.js_column(tbl, "审批状态", _badge("status", {
        "草稿": "default", "待审批": "warning",
        "待派车": "processing", "已派车": "success",
        "已完成": "success", "已取消": "default",
        "已驳回": "error",
    }), sort=90, width=100)

    # ── 行程记录：状态标记
    tbl = TABLES["行程记录"]
    print(f"\n  行程记录 [{tbl}]")

    nb.js_column(tbl, "行程状态", _tag("status", {
        "进行中": "blue", "已完成": "green",
    }), sort=90, width=90)

    # ── 保养维修：状态标记 + 费用
    tbl = TABLES["保养维修"]
    print(f"\n  保养维修 [{tbl}]")

    nb.js_column(tbl, "状态", _badge("status", {
        "待审批": "warning", "已批准": "processing",
        "维修中": "processing", "已完成": "success",
        "已驳回": "error",
    }), sort=90, width=100)

    nb.js_column(tbl, "总费用", _money("total_cost"), sort=85, width=110)

    nb.js_column(tbl, "下次保养", _date_countdown("next_maint_date", "保养"), sort=92, width=130)

    # ── 费用统计：金额 + 费用类型
    tbl = TABLES["费用统计"]
    print(f"\n  费用统计 [{tbl}]")

    nb.js_column(tbl, "金额", _money("amount"), sort=85, width=110)

    nb.js_column(tbl, "费用类型", _tag("cost_type", {
        "油费": "blue", "电费": "cyan",
        "保养费": "green", "维修费": "orange",
        "保险费": "purple", "年检费": "geekblue",
        "路桥费": "default", "停车费": "default",
        "违章罚款": "red", "其他": "default",
    }), sort=5, width=90)

    # ── 详情弹窗子表的 JS 列
    # 领用记录（资产详情）
    tbl = TABLES["领用记录(资产详情)"]
    print(f"\n  领用记录子表 [{tbl}]")

    nb.js_column(tbl, "状态", _tag("status", {
        "待审批": "orange", "待发放": "processing",
        "已发放": "blue", "已归还": "green",
        "已驳回": "red",
    }), sort=90, width=80)

    # 报修记录（资产详情）
    tbl = TABLES["报修记录(资产详情)"]
    print(f"\n  报修记录子表 [{tbl}]")

    nb.js_column(tbl, "状态", _badge("status", {
        "待受理": "warning", "维修中": "processing",
        "已完成": "success",
    }), sort=90, width=80)

    # 报废记录（资产详情）
    tbl = TABLES["报废记录(资产详情)"]
    print(f"\n  报废记录子表 [{tbl}]")

    nb.js_column(tbl, "状态", _badge("status", {
        "草稿": "default", "待部门审批": "processing",
        "待处置": "warning", "已报废": "success",
    }), sort=90, width=80)


# ═══════════════════════════════════════════════════════════════
# Step 2: 填充详情弹窗 JS 卡片
# ═══════════════════════════════════════════════════════════════

ASSET_CARD_CODE = """(async () => {
  const h = ctx.React.createElement;
  const { Card, Progress, Tag, Descriptions, Statistic, Space, Divider, Typography } = ctx.antd;
  const token = ctx.themeToken || {};
  const r = ctx.record || {};

  // 折旧计算
  const purchaseDate = r.purchase_date ? new Date(r.purchase_date) : null;
  const usefulYears = r.useful_years || 5;
  const purchasePrice = r.purchase_price || 0;
  const salvageValue = r.salvage_value || 0;
  const now = new Date();

  let yearsUsed = 0, depreciation = 0, netValue = purchasePrice, progress = 0;
  if (purchaseDate) {
    yearsUsed = Math.max(0, (now - purchaseDate) / (365.25 * 86400000));
    const annualDep = usefulYears > 0 ? (purchasePrice - salvageValue) / usefulYears : 0;
    depreciation = Math.min(annualDep * yearsUsed, purchasePrice - salvageValue);
    netValue = Math.max(purchasePrice - depreciation, salvageValue);
    progress = usefulYears > 0 ? Math.min(100, (yearsUsed / usefulYears) * 100) : 0;
  }

  // 状态颜色
  const statusColors = {'在用':'green','借用中':'blue','报修中':'orange','已报废':'red','在库':'default'};
  const statusColor = statusColors[r.status] || 'default';

  // 剩余使用年限
  const remainYears = Math.max(0, usefulYears - yearsUsed);

  const fmt = (v) => v != null ? '\\u00A5' + Number(v).toLocaleString('zh-CN', {minimumFractionDigits: 2}) : '-';

  ctx.render(
    h('div', {style: {padding: 0}},
      // 状态 + 资产编码
      h(Space, {style: {marginBottom: 12}},
        h(Tag, {color: statusColor, style: {fontSize: 14, padding: '2px 12px'}}, r.status || '-'),
        h(Typography.Text, {type: 'secondary'}, r.asset_code || '')
      ),

      // 折旧进度
      h(Card, {size: 'small', title: '折旧进度', style: {marginBottom: 12}},
        h(Progress, {
          percent: Math.round(progress),
          strokeColor: progress > 80 ? '#ff4d4f' : progress > 50 ? '#faad14' : '#52c41a',
          format: (p) => p + '%'
        }),
        h('div', {style: {display: 'flex', justifyContent: 'space-between', marginTop: 8}},
          h(Statistic, {title: '原值', value: fmt(purchasePrice), valueStyle: {fontSize: 16}}),
          h(Statistic, {title: '累计折旧', value: fmt(depreciation), valueStyle: {fontSize: 16, color: '#ff4d4f'}}),
          h(Statistic, {title: '净值', value: fmt(netValue), valueStyle: {fontSize: 16, color: '#52c41a'}})
        )
      ),

      // 使用年限
      h(Card, {size: 'small', title: '使用年限'},
        h('div', {style: {display: 'flex', justifyContent: 'space-between'}},
          h(Statistic, {title: '使用寿命', value: usefulYears, suffix: '年', valueStyle: {fontSize: 16}}),
          h(Statistic, {title: '已使用', value: yearsUsed.toFixed(1), suffix: '年', valueStyle: {fontSize: 16}}),
          h(Statistic, {title: '剩余', value: remainYears.toFixed(1), suffix: '年',
            valueStyle: {fontSize: 16, color: remainYears < 1 ? '#ff4d4f' : remainYears < 2 ? '#faad14' : '#52c41a'}
          })
        )
      )
    )
  );
})();"""


def fill_detail_cards(nb):
    """填充详情弹窗中的 TODO JS 区块（动态查找）。"""
    print("\n" + "=" * 60)
    print("  Filling Detail Cards...")
    print("=" * 60)

    # 代码映射：title keyword → code string
    code_map = {
        "资产卡片": ASSET_CARD_CODE,
        # "车辆卡片": VEHICLE_CARD_CODE,  # 未定义时跳过
    }

    # 从 API 搜索所有含 "// TODO" 的 JSBlockModel
    r = nb.s.get(f"{nb.base}/api/flowModels:list?paginate=false")
    all_models = r.json().get("data", [])

    found = 0
    for m in all_models:
        if m.get("use") != "JSBlockModel":
            continue
        code = (m.get("stepParams") or {}).get("jsSettings", {}).get("runJs", {}).get("code", "")
        if "// TODO" not in code:
            continue
        title = (m.get("stepParams") or {}).get("cardSettings", {}).get("titleDescription", {}).get("title", "")
        uid = m["uid"]

        # 匹配 title → 代码
        matched_code = None
        for keyword, replacement in code_map.items():
            if keyword in title:
                matched_code = replacement
                break

        if matched_code:
            print(f"\n  {title} [{uid}]")
            ok = nb.update(uid, {
                "stepParams": {
                    "jsSettings": {"runJs": {"version": "v1", "code": matched_code}}
                }
            })
            print(f"    {'Updated successfully' if ok else 'FAILED to update'}")
            found += 1
        else:
            print(f"\n  ⚠️  TODO block [{uid}] title='{title}' — no matching code, skipped")

    if found == 0:
        print("\n  No TODO JS blocks found (all cards may already be filled)")


# ═══════════════════════════════════════════════════════════════
# 审计：列出所有缺失的 JS 区块
# ═══════════════════════════════════════════════════════════════

def audit(nb):
    """审计现有页面，报告 JS 区块完整性。"""
    print("\n" + "=" * 60)
    print("  JS Block Audit Report")
    print("=" * 60)

    # 获取所有模型
    r = nb.s.get(f"{nb.base}/api/flowModels:list?paginate=false")
    all_models = r.json().get("data", [])

    # 分析每个表的 JS 列
    print("\n  === 表格 JS 列统计 ===")
    for name, tbl_uid in TABLES.items():
        cols = [m for m in all_models
                if m.get("parentId") == tbl_uid and m.get("use") == "JSColumnModel"]
        js_titles = [m.get("stepParams", {}).get("tableColumnSettings", {}).get("title", {}).get("title", "?")
                     for m in cols]
        marker = " OK" if cols else " MISSING"
        print(f"  {name:20s} JS列:{len(cols):2d}{marker}  {', '.join(js_titles)}")

    # 检查 TODO 占位
    print("\n  === TODO 占位区块 ===")
    todo_count = 0
    for m in all_models:
        code = m.get("stepParams", {}).get("jsSettings", {}).get("runJs", {}).get("code", "")
        if "// TODO" in code:
            title = m.get("stepParams", {}).get("cardSettings", {}).get("titleDescription", {}).get("title", "?")
            print(f"  [{m['uid']}] {m['use']:20s} title={title}")
            print(f"    code: {code[:80]}")
            todo_count += 1
    if todo_count == 0:
        print("  None found")

    # 检查空代码 JS 区块
    print("\n  === 无代码 JS 区块 ===")
    empty_count = 0
    for m in all_models:
        if m.get("use") in ("JSBlockModel", "JSColumnModel", "JSItemModel"):
            code = m.get("stepParams", {}).get("jsSettings", {}).get("runJs", {}).get("code", "")
            if not code.strip():
                title = (m.get("stepParams", {}).get("cardSettings", {})
                         .get("titleDescription", {}).get("title", ""))
                if not title:
                    title = (m.get("stepParams", {}).get("tableColumnSettings", {})
                             .get("title", {}).get("title", "?"))
                print(f"  [{m['uid']}] {m['use']:20s} parent={m.get('parentId','?')} title={title}")
                empty_count += 1
    if empty_count == 0:
        print("  None found")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    section = sys.argv[1] if len(sys.argv) > 1 else "all"

    nb = NB()
    print(f"\n{'=' * 60}")
    print(f"  AM JS Blocks Builder")
    print(f"  Section: {section}")
    print(f"{'=' * 60}")

    if section == "audit":
        audit(nb)
        return

    # 动态发现表格 UID（替代硬编码）
    if section in ("all", "columns"):
        discover_tables(nb)
        add_js_columns(nb)

    if section in ("all", "cards"):
        fill_detail_cards(nb)

    nb.summary()


if __name__ == "__main__":
    main()
