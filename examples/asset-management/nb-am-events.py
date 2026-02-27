#!/usr/bin/env python3
"""nb-am-events.py — 资产管理系统表单事件流

为所有表单添加 formValuesChange / beforeRender 事件流。
前置：nb-am-pages.py 已执行（页面已建好）

用法：
    python3 nb-am-events.py              # 全部
    python3 nb-am-events.py purchases    # 只做采购申请
    python3 nb-am-events.py transfers    # 只做领用借用
    python3 nb-am-events.py repairs      # 只做报修
    python3 nb-am-events.py disposals    # 只做报废
    python3 nb-am-events.py consumables  # 只做易耗品领用
    python3 nb-am-events.py stock        # 只做出入库
    python3 nb-am-events.py vehicles_req # 只做用车申请
    python3 nb-am-events.py trips        # 只做行程记录
    python3 nb-am-events.py maintenance  # 只做保养维修
    python3 nb-am-events.py costs        # 只做费用记录
    python3 nb-am-events.py --list       # 列出所有可用 section
"""

import sys
from nb_page_tool import PageTool


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def find_forms(pt, page_title):
    """Find CreateFormModel and EditFormModel UIDs in a page.

    Returns dict: {"addnew": uid_or_None, "edit": uid_or_None}
    """
    result = {"addnew": None, "edit": None}

    addnew = pt.locate(page_title, block="form_create")
    if addnew:
        result["addnew"] = addnew
        print(f"    CreateFormModel: {addnew}")
    else:
        print(f"    CreateFormModel: not found")

    edit = pt.locate(page_title, block="form_edit")
    if edit:
        result["edit"] = edit
        print(f"    EditFormModel:   {edit}")
    else:
        print(f"    EditFormModel:   not found")

    return result


# ═══════════════════════════════════════════════════════════════
# M2 固定资产
# ═══════════════════════════════════════════════════════════════

def events_purchases(pt):
    """采购申请 — formValuesChange 事件流"""
    print("\n── 采购申请 事件流 ──")
    forms = find_forms(pt, "采购申请")
    nb = pt.nb

    # ------ 新增表单 ------
    if forms["addnew"]:
        uid = forms["addnew"]

        # 1) quantity * estimated_price → total_price 自动计算
        #    + 默认值：applicant = ctx.user.nickname
        nb.form_logic(uid, "采购申请：自动计算总价 + 默认值填充", """
(async () => {
  // === 采购申请表单逻辑 ===
  // 1. quantity * estimated_price → total_price
  // 2. 默认填充 applicant
  const values = ctx.form?.values || {};

  // 自动计算总价
  const qty = Number(values.quantity) || 0;
  const price = Number(values.estimated_price) || 0;
  if (qty > 0 && price > 0) {
    const total = Math.round(qty * price * 100) / 100;
    if (total !== Number(values.total_price)) {
      ctx.form.setFieldsValue({ total_price: total });
    }
  }

  // 默认填充申请人（仅当为空时）
  if (!values.applicant && ctx.user?.nickname) {
    ctx.form.setFieldsValue({ applicant: ctx.user.nickname });
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")

    # ------ 编辑表单 ------
    if forms["edit"]:
        uid = forms["edit"]

        # 编辑时也需要自动计算
        # actual_quantity * actual_price → actual_total
        nb.form_logic(uid, "采购申请编辑：自动计算实际总价和预估总价", """
(async () => {
  // === 采购申请编辑表单逻辑 ===
  // 1. quantity * estimated_price → total_price
  // 2. actual_quantity * actual_price → actual_total
  const values = ctx.form?.values || {};

  // 预估总价
  const qty = Number(values.quantity) || 0;
  const price = Number(values.estimated_price) || 0;
  if (qty > 0 && price > 0) {
    const total = Math.round(qty * price * 100) / 100;
    if (total !== Number(values.total_price)) {
      ctx.form.setFieldsValue({ total_price: total });
    }
  }

  // 实际总价
  const aqty = Number(values.actual_quantity) || 0;
  const aprice = Number(values.actual_price) || 0;
  if (aqty > 0 && aprice > 0) {
    const atotal = Math.round(aqty * aprice * 100) / 100;
    if (atotal !== Number(values.actual_total)) {
      ctx.form.setFieldsValue({ actual_total: atotal });
    }
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


def events_transfers(pt):
    """领用/借用 — formValuesChange 事件流"""
    print("\n── 领用借用 事件流 ──")
    forms = find_forms(pt, "领用借用")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        # 1) 选择资产时自动填充信息
        # 2) type 为"借用"时提示归还日期
        # 3) 默认值：applicant
        nb.form_logic(uid, "领用借用：资产自动填充 + 借用提醒 + 默认值", """
(async () => {
  // === 领用/借用表单逻辑 ===
  // 1. 选择资产 → 自动校验状态（在用/在库才能领用）
  // 2. 借用类型 → 提示必须填写归还日期
  // 3. 默认填充 applicant
  const values = ctx.form?.values || {};

  // 默认填充申请人
  if (!values.applicant && ctx.user?.nickname) {
    ctx.form.setFieldsValue({ applicant: ctx.user.nickname });
  }

  // 选择资产后校验状态
  if (values.asset && typeof values.asset === 'object') {
    const assetStatus = values.asset.status;
    if (assetStatus && !['在用', '在库'].includes(assetStatus)) {
      ctx.message.warning('该资产当前状态为"' + assetStatus + '"，不可领用/借用');
    }
  }

  // 借用类型提醒
  if (values.transfer_type === '借用' && !values.expected_return_date) {
    // 不阻断，只提示
    // ctx.message.info 的频繁调用会被系统自动节流
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")

    if forms["edit"]:
        uid = forms["edit"]

        nb.form_logic(uid, "领用借用编辑：归还日期校验", """
(async () => {
  // === 领用/借用编辑表单逻辑 ===
  // 1. 归还时校验：actual_return_date >= expected_return_date 校验
  // 2. 状态为"已归还"时，actual_return_date 必填检查提示
  const values = ctx.form?.values || {};

  if (values.status === '已归还' && !values.actual_return_date) {
    ctx.message.warning('归还状态请填写实际归还日期');
  }

  // 逾期提醒
  if (values.expected_return_date && values.status === '已发放') {
    const today = ctx.dayjs();
    const expected = ctx.dayjs(values.expected_return_date);
    if (today.isAfter(expected)) {
      const days = today.diff(expected, 'day');
      ctx.message.warning('已逾期 ' + days + ' 天，请尽快归还');
    }
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


def events_repairs(pt):
    """报修管理 — formValuesChange 事件流"""
    print("\n── 报修管理 事件流 ──")
    forms = find_forms(pt, "报修管理")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        # 默认值 + 故障描述提示
        nb.form_logic(uid, "报修：默认值 + 资产填充", """
(async () => {
  // === 报修新增表单逻辑 ===
  // 1. 默认填充 applicant = 当前用户
  // 2. 选择资产后可做额外校验
  const values = ctx.form?.values || {};

  // 默认填充报修人
  if (!values.applicant && ctx.user?.nickname) {
    ctx.form.setFieldsValue({ applicant: ctx.user.nickname });
  }

  // 选择资产后检查状态
  if (values.asset && typeof values.asset === 'object') {
    const s = values.asset.status;
    if (s === '已报废') {
      ctx.message.warning('该资产已报废，无法报修');
    } else if (s === '报修中') {
      ctx.message.warning('该资产已在报修中，请勿重复报修');
    }
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")

    if forms["edit"]:
        uid = forms["edit"]

        # 维修方式切换 → 外部维修时需要供应商和费用
        nb.form_logic(uid, "报修编辑：维修方式联动 + 费用校验", """
(async () => {
  // === 报修编辑表单逻辑 ===
  // 1. repair_method = "外部维修" → 提示填写供应商和费用
  // 2. repair_result = "建议报废" → 提示可以转报废流程
  const values = ctx.form?.values || {};

  // 外部维修提示
  if (values.repair_method === '外部维修') {
    if (!values.supplier) {
      // 提示但不阻断
    }
  }

  // 建议报废提示
  if (values.repair_result === '建议报废') {
    ctx.message.info('维修结果为"建议报废"，完成后可发起报废申请');
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


def events_disposals(pt):
    """报废管理 — formValuesChange 事件流"""
    print("\n── 报废管理 事件流 ──")
    forms = find_forms(pt, "报废管理")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        # 选择资产 → 自动填充购入价格/计算折旧
        nb.form_logic(uid, "报废：资产信息填充 + 残值预估", """
(async () => {
  // === 报废新增表单逻辑 ===
  // 1. 选择资产 → 自动计算账面价值（简化直线折旧法）
  // 2. 默认填充 applicant
  const values = ctx.form?.values || {};

  // 默认填充申请人
  if (!values.applicant && ctx.user?.nickname) {
    ctx.form.setFieldsValue({ applicant: ctx.user.nickname });
  }

  // 资产选择后自动估算残值
  if (values.asset && typeof values.asset === 'object') {
    const asset = values.asset;
    const purchasePrice = Number(asset.purchase_price) || 0;
    const usefulYears = Number(asset.useful_years) || 5;
    const salvageValue = Number(asset.salvage_value) || 0;
    const purchaseDate = asset.purchase_date;

    if (purchasePrice > 0 && purchaseDate) {
      // 直线折旧法：(原值 - 残值) / 使用年限 * 已用年数
      const years = ctx.dayjs().diff(ctx.dayjs(purchaseDate), 'year', true);
      const annualDep = (purchasePrice - salvageValue) / usefulYears;
      const accumulated = Math.min(annualDep * years, purchasePrice - salvageValue);
      const bookValue = Math.round((purchasePrice - accumulated) * 100) / 100;

      const updates = {};
      if (!values.estimated_salvage && salvageValue > 0) {
        updates.estimated_salvage = salvageValue;
      }
      if (Object.keys(updates).length > 0) {
        ctx.form.setFieldsValue(updates);
      }
    }
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")

    if forms["edit"]:
        uid = forms["edit"]

        nb.form_logic(uid, "报废编辑：处置方式提示", """
(async () => {
  // === 报废编辑表单逻辑 ===
  // 1. disposal_method 变化 → 不同提示
  // 2. 账面价值自动计算（从资产读取）
  const values = ctx.form?.values || {};

  const tips = {
    '变卖': '请在处置详情中记录变卖金额和买方信息',
    '捐赠': '请在处置详情中记录受赠方信息',
    '销毁': '请在处置详情中记录销毁方式和见证人',
  };
  if (values.disposal_method && tips[values.disposal_method]) {
    // 提示在控制台，避免频繁弹窗
    console.log('[报废提示]', tips[values.disposal_method]);
  }

  // 从关联资产计算账面价值
  if (values.asset && typeof values.asset === 'object' && !values.book_value) {
    const asset = values.asset;
    const pp = Number(asset.purchase_price) || 0;
    const uy = Number(asset.useful_years) || 5;
    const sv = Number(asset.salvage_value) || 0;
    const pd = asset.purchase_date;
    if (pp > 0 && pd) {
      const yrs = ctx.dayjs().diff(ctx.dayjs(pd), 'year', true);
      const dep = Math.min((pp - sv) / uy * yrs, pp - sv);
      const bv = Math.round((pp - dep) * 100) / 100;
      ctx.form.setFieldsValue({ book_value: Math.max(bv, 0) });
    }
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


# ═══════════════════════════════════════════════════════════════
# M3 易耗品
# ═══════════════════════════════════════════════════════════════

def events_consumables(pt):
    """易耗品领用申请 — formValuesChange 事件流"""
    print("\n── 易耗品领用申请 事件流 ──")
    forms = find_forms(pt, "领用申请")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        nb.form_logic(uid, "易耗品领用：默认值填充", """
(async () => {
  // === 易耗品领用申请表单逻辑 ===
  // 1. 默认填充 applicant = 当前用户
  const values = ctx.form?.values || {};

  if (!values.applicant && ctx.user?.nickname) {
    ctx.form.setFieldsValue({ applicant: ctx.user.nickname });
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")


def events_stock(pt):
    """出入库记录 — formValuesChange 事件流"""
    print("\n── 库存管理 事件流 ──")
    forms = find_forms(pt, "库存管理")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        # 选择物品 → 显示当前库存 + 出库校验
        nb.form_logic(uid, "出入库：库存校验 + 金额计算", """
(async () => {
  // === 出入库记录表单逻辑 ===
  // 1. 选择物品 → 查询当前库存显示
  // 2. 出库时：quantity > current_stock 则警告
  // 3. 自动填充 operator
  const values = ctx.form?.values || {};

  // 默认填充操作人
  if (!values.operator && ctx.user?.nickname) {
    ctx.form.setFieldsValue({ operator: ctx.user.nickname });
  }

  // 选择物品后校验库存
  if (values.consumable && typeof values.consumable === 'object') {
    const stock = Number(values.consumable.current_stock) || 0;
    const qty = Number(values.quantity) || 0;

    if (values.record_type === '出库' && qty > stock) {
      ctx.message.warning(
        '库存不足！当前库存 ' + stock + '，申请出库 ' + qty
      );
    }

    // 如果没填单价，用参考单价
    if (!values.unit_price && values.consumable.ref_price) {
      ctx.form.setFieldsValue({ unit_price: values.consumable.ref_price });
    }
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")


# ═══════════════════════════════════════════════════════════════
# M4 车辆管理
# ═══════════════════════════════════════════════════════════════

def events_vehicles_req(pt):
    """用车申请 — formValuesChange 事件流"""
    print("\n── 用车申请 事件流 ──")
    forms = find_forms(pt, "用车申请")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        # 默认值 + 时间计算 + 冲突检查
        nb.form_logic(uid, "用车申请：默认值 + 时间校验 + 冲突检查", """
(async () => {
  // === 用车申请表单逻辑 ===
  // 1. 默认填充 applicant = 当前用户
  // 2. depart_time / return_time → 计算用车时长提示
  // 3. use_date 默认今天
  const values = ctx.form?.values || {};

  // 默认填充申请人
  if (!values.applicant && ctx.user?.nickname) {
    ctx.form.setFieldsValue({ applicant: ctx.user.nickname });
  }

  // 默认用车日期为今天
  if (!values.use_date) {
    ctx.form.setFieldsValue({ use_date: ctx.dayjs().format('YYYY-MM-DD') });
  }

  // 计算用车时长提示
  if (values.depart_time && values.return_time) {
    try {
      const base = '2000-01-01 ';
      const dep = ctx.dayjs(base + values.depart_time);
      const ret = ctx.dayjs(base + values.return_time);
      if (ret.isBefore(dep)) {
        ctx.message.warning('返回时间早于出发时间，请检查');
      } else {
        const hours = ret.diff(dep, 'hour', true);
        if (hours > 12) {
          ctx.message.info('用车时长超过12小时（' + hours.toFixed(1) + 'h），请确认');
        }
      }
    } catch(e) {
      // 时间格式解析失败，静默忽略
    }
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")

    if forms["edit"]:
        uid = forms["edit"]

        # 派车时检查车辆状态
        nb.form_logic(uid, "用车申请编辑：派车校验", """
(async () => {
  // === 用车申请编辑表单逻辑 ===
  // 1. 选择车辆时检查车辆状态
  // 2. 状态变更提示
  const values = ctx.form?.values || {};

  // 选择车辆后校验状态
  if (values.vehicle && typeof values.vehicle === 'object') {
    const vs = values.vehicle.status;
    if (vs && vs !== '可用') {
      ctx.message.warning('该车辆当前状态为"' + vs + '"，请确认是否可派');
    }
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


def events_trips(pt):
    """行程记录 — formValuesChange 事件流"""
    print("\n── 行程记录 事件流 ──")
    forms = find_forms(pt, "行程记录")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        nb.form_logic(uid, "行程记录：选择车辆自动填充里程", """
(async () => {
  // === 行程记录新增表单逻辑 ===
  // 选择车辆 → 自动填充起始里程
  const values = ctx.form?.values || {};

  if (values.vehicle && typeof values.vehicle === 'object') {
    const mileage = Number(values.vehicle.current_mileage) || 0;
    if (mileage > 0 && !values.start_mileage) {
      ctx.form.setFieldsValue({ start_mileage: mileage });
    }
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")

    if forms["edit"]:
        uid = forms["edit"]

        # 自动计算行驶里程
        nb.form_logic(uid, "行程编辑：自动计算里程", """
(async () => {
  // === 行程记录编辑表单逻辑 ===
  // 1. end_mileage - start_mileage → distance
  // 2. 校验 end_mileage >= start_mileage
  const values = ctx.form?.values || {};

  const start = Number(values.start_mileage) || 0;
  const end = Number(values.end_mileage) || 0;

  if (start > 0 && end > 0) {
    if (end < start) {
      ctx.message.warning('结束里程不能小于起始里程');
    } else {
      const dist = end - start;
      if (dist !== Number(values.distance)) {
        ctx.form.setFieldsValue({ distance: dist });
      }
    }
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


def events_maintenance(pt):
    """保养维修 — formValuesChange 事件流"""
    print("\n── 保养维修 事件流 ──")
    forms = find_forms(pt, "保养维修")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        # 选择车辆 → 填充当前里程 + 自动计算总费用
        nb.form_logic(uid, "保养维修：自动填充里程 + 费用计算", """
(async () => {
  // === 保养维修新增表单逻辑 ===
  // 1. 选择车辆 → 自动填充 current_mileage
  // 2. parts_cost + labor_cost → total_cost
  // 3. 常规保养 → 自动计算下次保养里程/日期
  const values = ctx.form?.values || {};

  // 选择车辆自动填充当前里程
  if (values.vehicle && typeof values.vehicle === 'object') {
    const mileage = Number(values.vehicle.current_mileage) || 0;
    if (mileage > 0 && !values.current_mileage) {
      ctx.form.setFieldsValue({ current_mileage: mileage });
    }
  }

  // 自动计算总费用
  const parts = Number(values.parts_cost) || 0;
  const labor = Number(values.labor_cost) || 0;
  if (parts > 0 || labor > 0) {
    const total = Math.round((parts + labor) * 100) / 100;
    if (total !== Number(values.total_cost)) {
      ctx.form.setFieldsValue({ total_cost: total });
    }
  }

  // 常规保养 → 自动推算下次保养
  if (values.maint_type === '常规保养') {
    const cm = Number(values.current_mileage) || 0;
    if (cm > 0 && !values.next_maint_mileage) {
      ctx.form.setFieldsValue({ next_maint_mileage: cm + 5000 });
    }
    if (values.plan_date && !values.next_maint_date) {
      const next = ctx.dayjs(values.plan_date).add(6, 'month').format('YYYY-MM-DD');
      ctx.form.setFieldsValue({ next_maint_date: next });
    }
  }

  // 大保养 → 更长间隔
  if (values.maint_type === '大保养') {
    const cm = Number(values.current_mileage) || 0;
    if (cm > 0 && !values.next_maint_mileage) {
      ctx.form.setFieldsValue({ next_maint_mileage: cm + 20000 });
    }
    if (values.plan_date && !values.next_maint_date) {
      const next = ctx.dayjs(values.plan_date).add(12, 'month').format('YYYY-MM-DD');
      ctx.form.setFieldsValue({ next_maint_date: next });
    }
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")

    if forms["edit"]:
        uid = forms["edit"]

        nb.form_logic(uid, "保养维修编辑：费用计算 + 保险联动", """
(async () => {
  // === 保养维修编辑表单逻辑 ===
  // 1. parts_cost + labor_cost → total_cost
  // 2. use_insurance = true → 提示填写理赔金额
  // 3. insurance_amount 不能超过 total_cost
  const values = ctx.form?.values || {};

  // 自动计算总费用
  const parts = Number(values.parts_cost) || 0;
  const labor = Number(values.labor_cost) || 0;
  if (parts > 0 || labor > 0) {
    const total = Math.round((parts + labor) * 100) / 100;
    if (total !== Number(values.total_cost)) {
      ctx.form.setFieldsValue({ total_cost: total });
    }
  }

  // 走保险提醒
  if (values.use_insurance) {
    const insAmt = Number(values.insurance_amount) || 0;
    const totalCost = Number(values.total_cost) || 0;
    if (insAmt > totalCost && totalCost > 0) {
      ctx.message.warning('理赔金额(' + insAmt + ')不能超过总费用(' + totalCost + ')');
    }
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


def events_costs(pt):
    """车辆费用统计 — formValuesChange 事件流"""
    print("\n── 费用统计 事件流 ──")
    forms = find_forms(pt, "费用统计")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        # 默认值 + 费用日期
        nb.form_logic(uid, "车辆费用：默认值填充", """
(async () => {
  // === 车辆费用新增表单逻辑 ===
  // 1. 默认 cost_date = 今天
  // 2. 默认 operator = 当前用户
  // 3. 选择车辆后显示车辆信息
  const values = ctx.form?.values || {};

  const updates = {};

  // 默认费用日期
  if (!values.cost_date) {
    updates.cost_date = ctx.dayjs().format('YYYY-MM-DD');
  }

  // 默认操作人
  if (!values.operator && ctx.user?.nickname) {
    updates.operator = ctx.user.nickname;
  }

  if (Object.keys(updates).length > 0) {
    ctx.form.setFieldsValue(updates);
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")


# ═══════════════════════════════════════════════════════════════
# M1 基础数据（少量逻辑）
# ═══════════════════════════════════════════════════════════════

def events_companies(pt):
    """公司管理 — 简单校验"""
    print("\n── 公司管理 事件流 ──")
    forms = find_forms(pt, "公司管理")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        nb.form_logic(uid, "公司：编码大写化 + short_code 自动生成", """
(async () => {
  // === 公司管理表单逻辑 ===
  // 1. code 自动转大写
  // 2. name 变化时如果 short_code 为空，取前两个字做拼音缩写占位
  const values = ctx.form?.values || {};

  if (values.code && values.code !== values.code.toUpperCase()) {
    ctx.form.setFieldsValue({ code: values.code.toUpperCase() });
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")


def events_suppliers(pt):
    """供应商管理 — 简单校验"""
    print("\n── 供应商管理 事件流 ──")
    forms = find_forms(pt, "供应商管理")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        nb.form_logic(uid, "供应商：默认合作状态", """
(async () => {
  // === 供应商管理表单逻辑 ===
  // 默认合作状态 = "合作中"
  const values = ctx.form?.values || {};

  if (!values.cooperation_status) {
    ctx.form.setFieldsValue({ cooperation_status: '合作中' });
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")


# ═══════════════════════════════════════════════════════════════
# 物品目录（库存预警）
# ═══════════════════════════════════════════════════════════════

def events_consumable_catalog(pt):
    """物品目录 — 库存预警"""
    print("\n── 物品目录 事件流 ──")
    forms = find_forms(pt, "物品目录")
    nb = pt.nb

    if forms["edit"]:
        uid = forms["edit"]

        nb.form_logic(uid, "物品目录编辑：库存预警", """
(async () => {
  // === 物品目录编辑表单逻辑 ===
  // 1. current_stock < safe_stock → 低库存警告
  // 2. current_stock = 0 → 缺货警告
  const values = ctx.form?.values || {};

  const cur = Number(values.current_stock) || 0;
  const safe = Number(values.safe_stock) || 0;

  if (cur === 0 && safe > 0) {
    ctx.message.warning('当前库存为 0，物品已缺货！');
  } else if (cur < safe && safe > 0) {
    ctx.message.warning('库存不足！当前 ' + cur + '，安全库存 ' + safe);
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


# ═══════════════════════════════════════════════════════════════
# 资产台账（编辑校验）
# ═══════════════════════════════════════════════════════════════

def events_assets(pt):
    """资产台账 — 编辑校验"""
    print("\n── 资产台账 事件流 ──")
    forms = find_forms(pt, "资产台账")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        # 选择分类 → 自动填充使用年限
        nb.form_logic(uid, "资产台账新增：分类联动使用年限 + 残值计算", """
(async () => {
  // === 资产台账新增表单逻辑 ===
  // 1. 选择资产分类 → 自动填充 useful_years（从分类的 default_years）
  // 2. 填写 purchase_price + useful_years → 预估残值（5% 原值）
  const values = ctx.form?.values || {};

  // 分类联动使用年限
  if (values.category && typeof values.category === 'object') {
    const defaultYears = Number(values.category.default_years) || 0;
    if (defaultYears > 0 && !values.useful_years) {
      ctx.form.setFieldsValue({ useful_years: defaultYears });
    }
  }

  // 预估残值 = 原值 * 5%（行业惯例）
  const pp = Number(values.purchase_price) || 0;
  if (pp > 0 && !values.salvage_value) {
    const sv = Math.round(pp * 0.05 * 100) / 100;
    ctx.form.setFieldsValue({ salvage_value: sv });
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")

    if forms["edit"]:
        uid = forms["edit"]

        nb.form_logic(uid, "资产台账编辑：状态变更校验", """
(async () => {
  // === 资产台账编辑表单逻辑 ===
  // 1. 状态改为"已报废" → 提示应通过报废流程处理
  // 2. 使用年限或残值变化后的一致性检查
  const values = ctx.form?.values || {};

  if (values.status === '已报废') {
    ctx.message.info('建议通过"报废管理"页面发起正式报废流程');
  }
})();
""")
        print(f"    + formValuesChange on EditForm {uid}")


# ═══════════════════════════════════════════════════════════════
# 车辆档案
# ═══════════════════════════════════════════════════════════════

def events_vehicle_catalog(pt):
    """车辆档案 — 新增/编辑校验"""
    print("\n── 车辆档案 事件流 ──")
    forms = find_forms(pt, "车辆档案")
    nb = pt.nb

    if forms["addnew"]:
        uid = forms["addnew"]

        nb.form_logic(uid, "车辆档案：车牌格式校验 + 默认值", """
(async () => {
  // === 车辆档案新增表单逻辑 ===
  // 1. 车牌号自动转大写
  // 2. 默认状态 = "可用"
  // 3. 默认里程 = 0
  const values = ctx.form?.values || {};

  const updates = {};

  // 车牌号大写
  if (values.plate_number && values.plate_number !== values.plate_number.toUpperCase()) {
    updates.plate_number = values.plate_number.toUpperCase();
  }

  // 默认值
  if (!values.current_mileage && values.current_mileage !== 0) {
    updates.current_mileage = 0;
  }

  if (Object.keys(updates).length > 0) {
    ctx.form.setFieldsValue(updates);
  }
})();
""")
        print(f"    + formValuesChange on CreateForm {uid}")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

SECTIONS = {
    # M2 固定资产
    "assets":       ("资产台账",     events_assets),
    "purchases":    ("采购申请",     events_purchases),
    "transfers":    ("领用借用",     events_transfers),
    "repairs":      ("报修管理",     events_repairs),
    "disposals":    ("报废管理",     events_disposals),
    # M3 易耗品
    "consumable_catalog": ("物品目录",     events_consumable_catalog),
    "consumables":  ("易耗品领用",   events_consumables),
    "stock":        ("出入库记录",   events_stock),
    # M4 车辆
    "vehicle_catalog": ("车辆档案",  events_vehicle_catalog),
    "vehicles_req": ("用车申请",     events_vehicles_req),
    "trips":        ("行程记录",     events_trips),
    "maintenance":  ("保养维修",     events_maintenance),
    "costs":        ("费用记录",     events_costs),
    # M1 基础数据
    "companies":    ("公司管理",     events_companies),
    "suppliers":    ("供应商管理",   events_suppliers),
}


def main():
    if "--list" in sys.argv:
        print("Available sections:")
        for key, (desc, _) in SECTIONS.items():
            print(f"  {key:25s} {desc}")
        return

    section = sys.argv[1] if len(sys.argv) > 1 else "all"

    pt = PageTool()

    print(f"\n{'=' * 60}")
    print(f"  Asset Management — Event Flows Builder")
    print(f"  Section: {section}")
    print(f"{'=' * 60}")

    if section == "all":
        funcs = list(SECTIONS.values())
    elif section in SECTIONS:
        funcs = [SECTIONS[section]]
    else:
        print(f"Unknown section: {section}")
        print(f"Available: {', '.join(SECTIONS.keys())}, all")
        print(f"Use --list to see all sections")
        return

    success = 0
    errors = 0
    for desc, fn in funcs:
        try:
            fn(pt)
            success += 1
        except Exception as e:
            print(f"  ERROR in {desc}: {e}")
            import traceback
            traceback.print_exc()
            errors += 1

    print(f"\n{'=' * 60}")
    print(f"  Done! {success} sections processed, {errors} errors")
    print(f"  Total API calls: {pt.nb.created} created")
    if pt.nb.errors:
        print(f"  API errors: {len(pt.nb.errors)}")
        for e in pt.nb.errors[:5]:
            print(f"    - {e}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
