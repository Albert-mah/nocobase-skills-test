# Page Layout Patterns

Each pattern shows an XML markup template for `nb_page_markup`. Replace `{PLACEHOLDER}` with real values.

## Pattern → Template → JS Placeholder Mapping

This is the critical link: requirements pattern → which layout → which JS placeholders to include.

| Pattern | Layout | When to Use | JS Placeholders |
|---------|--------|-------------|-----------------|
| **A: KPI Strip** | KPI row → Chart row → Filter → Table | Core business pages with "打开页面关注 XX 总数/数量" | `<kpi>` row, `<js-block>` for charts |
| **B: Sidebar** | Filter → Table(16)+Stack(8) | Alert/monitor pages: "到期提醒", "待处理", "分布统计" in sidebar | `<js-block>` in `<stack>` sidebar |
| **C: Financial** | Banner → 3×Metric → Filter → Table | Financial pages: "金额汇总", "各状态金额" | `<js-block>` banner + 3 metric blocks |
| **D: Pipeline** | Pipeline → Dist+Stats → Filter → Table | Stage-driven: "漏斗", "阶段", "转化率" | `<js-block>` pipeline + distribution |
| **E: Simple** | Filter → Table | Reference/config data with no KPIs | none |
| **F: Dashboard** | Progress+Ranking → Filter → Table | Target tracking: "达成率", "进度", "排行" | `<js-block>` progress + ranking |

## How to Use (Step by Step)

1. **Determine pattern** from requirements "用户关注" section (use mapping rules in checklist Step 3.1)
2. **Copy the XML template** for that pattern from below
3. **Replace placeholders**: collection names, field names, filter values
4. **Write JS placeholder descriptions** — describe what each `<js-block>`, `<js-col>` should render
5. **Add `<js-col>` to table** — match HTML prototype column patterns (see below)
6. Call `nb_page_markup(tab_uid, markup)` or write to batch file

## Pattern A: KPI Strip + Charts + Table

```xml
<page collection="{COLLECTION}">
  <row>
    <kpi title="{KPI_1_TITLE}" />
    <kpi title="{KPI_2_TITLE}" filter="{FIELD}={VALUE}" color="blue" />
    <kpi title="{KPI_3_TITLE}" filter="{FIELD}={VALUE}" color="green" />
  </row>
  <row>
    <js-block title="{CHART_A_TITLE}" span="10">{CHART_A_DESC}</js-block>
    <js-block title="{CHART_B_TITLE}" span="14">{CHART_B_DESC}</js-block>
  </row>
  <filter fields="{FILTER_FIELDS}" target="tbl" />
  <table id="tbl" fields="{TABLE_FIELDS}">
    <js-col type="composite" field="{PRIMARY_FIELD}" subs="{SUBS}" title="{COL_TITLE}">
      {COL_DESC}
    </js-col>
    <addnew fields="{FORM_FIELDS}" />
    <edit fields="{FORM_FIELDS}" />
    <detail>
      <tab title="详情" fields="{DETAIL_FIELDS}" />
    </detail>
  </table>
</page>
```

## Pattern B: Sidebar + Main

```xml
<page collection="{COLLECTION}">
  <filter fields="{FILTER_FIELDS}" target="tbl" />
  <row>
    <table id="tbl" span="16" fields="{TABLE_FIELDS}">
      <js-col type="composite" field="{PRIMARY_FIELD}" subs="{SUBS}" title="{COL_TITLE}">
        {COL_DESC}
      </js-col>
      <addnew fields="{FORM_FIELDS}" />
      <edit fields="{FORM_FIELDS}" />
    </table>
    <stack span="8">
      <js-block title="{SIDEBAR_A_TITLE}">{SIDEBAR_A_DESC}</js-block>
      <js-block title="{SIDEBAR_B_TITLE}">{SIDEBAR_B_DESC}</js-block>
    </stack>
  </row>
</page>
```

## Pattern C: Financial (Banner + Metrics + Table)

```xml
<page collection="{COLLECTION}">
  <js-block title="{BANNER_TITLE}">{BANNER_DESC: 总金额/已收/待收}</js-block>
  <row>
    <js-block title="{METRIC_A}" span="8">{METRIC_A_DESC}</js-block>
    <js-block title="{METRIC_B}" span="8">{METRIC_B_DESC}</js-block>
    <js-block title="{METRIC_C}" span="8">{METRIC_C_DESC}</js-block>
  </row>
  <filter fields="{FILTER_FIELDS}" target="tbl" />
  <table id="tbl" fields="{TABLE_FIELDS}">
    <js-col type="currency" field="{AMOUNT_FIELD}" title="金额" threshold="{THRESHOLD}">
      ¥格式显示，超过阈值红色高亮
    </js-col>
    <addnew fields="{FORM_FIELDS}" />
    <edit fields="{FORM_FIELDS}" />
  </table>
</page>
```

## Pattern D: Pipeline

```xml
<page collection="{COLLECTION}">
  <js-block title="{PIPELINE_TITLE}">{PIPELINE_DESC: 各阶段数量漏斗}</js-block>
  <row>
    <js-block title="{DIST_TITLE}" span="10">{DIST_DESC}</js-block>
    <js-block title="{STATS_TITLE}" span="14">{STATS_DESC}</js-block>
  </row>
  <filter fields="{FILTER_FIELDS}" target="tbl" />
  <table id="tbl" fields="{TABLE_FIELDS}">
    <js-col type="composite" field="{PRIMARY_FIELD}" subs="{SUBS}" title="{COL_TITLE}">
      {COL_DESC}
    </js-col>
    <addnew fields="{FORM_FIELDS}" />
    <edit fields="{FORM_FIELDS}" />
  </table>
</page>
```

## Pattern E: Simple (Reference/Config)

```xml
<page collection="{COLLECTION}">
  <filter fields="{FILTER_FIELDS}" target="tbl" />
  <table id="tbl" fields="{TABLE_FIELDS}">
    <addnew fields="{FORM_FIELDS}" />
    <edit fields="{FORM_FIELDS}" />
  </table>
</page>
```

No JS blocks needed. For Pattern E, you can also use `nb_crud_page` shortcut.

## Pattern F: Dashboard + Progress

```xml
<page collection="{COLLECTION}">
  <row>
    <js-block title="{PROGRESS_TITLE}" span="10">{PROGRESS_DESC: 整体达成率圆形进度条}</js-block>
    <js-block title="{RANKING_TITLE}" span="14">{RANKING_DESC: Top N 排行列表}</js-block>
  </row>
  <filter fields="{FILTER_FIELDS}" target="tbl" />
  <table id="tbl" fields="{TABLE_FIELDS}">
    <js-col type="progress" field="{PROGRESS_FIELD}" title="达成率">
      彩色进度条+百分比
    </js-col>
    <addnew fields="{FORM_FIELDS}" />
    <edit fields="{FORM_FIELDS}" />
  </table>
</page>
```

## Table Block — JS Column Placeholders (Business-Driven)

Add `<js-col>` in Phase 1 when the table has fields that **NocoBase cannot render natively**. Do NOT force JS columns on every table.

### ★ MOST IMPORTANT: Every entity's primary column = composite

Look at the HTML prototypes — every entity's first column shows **bold title + gray subtitle**:
- 客户: "华为技术有限公司" + "深圳 · 转介绍"
- 商机: "企业云服务采购项目" + "创建于 2024-01-15"
- 合同: "云服务年度合同" + "2024-01-01 ~ 2024-12-31"

**Every non-reference table SHOULD have a composite primary column.**

### HTML `<td>` → JS column type mapping

| HTML prototype pattern | `<js-col>` type | Skip? |
|----------------------|----------|-------|
| Two nested `<div>` (bold name + gray info) | `composite` | |
| ¥ + monospace number | `currency` | |
| "还剩X天" / "已逾期X天" countdown | `countdown` | |
| Progress bar + percentage | `progress` | |
| "N小时前" / "N天前" relative time | `relative_time` | |
| Stars / rating | `stars` | |
| Target vs actual bar | `comparison` | |
| Colored tag/badge (等级/状态/类型) | **SKIP** — NocoBase native | ✓ |
| Plain text | **SKIP** — NocoBase native | ✓ |
| Relation name | **SKIP** — NocoBase native | ✓ |

### Example — CRM 合同 table:

```xml
<table id="tbl" fields="title,customer_id,status,amount,end_date,createdAt">
  <js-col type="composite" field="title" subs="start_date,end_date" title="合同">
    蓝色粗体合同名，下方灰色显示起止日期
  </js-col>
  <js-col type="currency" field="amount" title="金额" threshold="500000">
    ¥格式，超过50万红色高亮
  </js-col>
  <js-col type="countdown" field="end_date" title="到期">
    还剩N天/已逾期N天
  </js-col>
  <addnew fields="title*|customer_id\namount|status\nstart_date|end_date" />
  <edit fields="title*|customer_id\namount|status\nstart_date|end_date" />
</table>
```
Note: `status` → select field → SKIP. `customer_id` → relation → SKIP.

## Placeholders Reference

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{COLLECTION}` | Collection name | `nb_crm_customers` |
| `{TABLE_FIELDS}` | Comma-separated column names | `name,status,createdAt` |
| `{FILTER_FIELDS}` | Comma-separated searchable fields | `name,status` |
| `{FORM_FIELDS}` | DSL string for add/edit forms | `name*\nstatus\nremark` |
| `{DETAIL_FIELDS}` | DSL string for detail tab | `name\|status\namount` |
| `{PRIMARY_FIELD}` | Main name/title field | `name` |
| `{SUBS}` | Sub-fields for composite | `city,source` |
