# Detail Popup & Form Patterns

Read this when refining forms/details in Phase 3B. Do NOT read upfront.

## DETAIL = A FULL PAGE

A detail popup is NOT a field viewer. It is the user's workspace for this record.

### What makes a good detail page

| Component | Purpose | Example |
|-----------|---------|---------|
| **Summary card** (js_item) | Instant understanding | 客户: A级·已签约·科技行业·建档180天 |
| **Key metrics** (js_item) | Numbers that matter | 商机: ¥50万·概率50%·剩余30天 |
| **Field sections** | Organized data | --- 基本信息, --- 联系方式 |
| **Subtables** (tabs) | Related records | 联系人, 商机, 合同 |

**Every core entity: 3+ tabs, 2+ js_items on first tab.**

### js_item desc rules

GOOD (specific): "4个Statistic并排: 商机数+商机总额+合同数+合同总额"
BAD (vague): "客户画像" or "进度显示"

## Example: Customer Detail (richest)

```json
[
  {"title": "概况",
   "fields": "--- 基本信息\nname|code\nindustry|source\ngrade|status\n--- 联系方式\nphone|email\ncity|address",
   "js_items": [
     {"title": "客户画像", "desc": "大字等级(A/B/C/D)+彩色状态标签+行业标签+来源标签+建档N天"},
     {"title": "业务概览", "desc": "4个Statistic并排: 商机数+商机总额+合同数+合同总额"}
   ]},
  {"title": "联系人", "assoc": "contacts", "coll": "nb_crm_contacts",
   "fields": ["name","phone","email","position"]},
  {"title": "商机", "assoc": "opportunities", "coll": "nb_crm_opportunities",
   "fields": ["title","amount","stage","probability"]},
  {"title": "合同", "assoc": "contracts", "coll": "nb_crm_contracts",
   "fields": ["code","title","amount","status","end_date"]}
]
```

## Example: Opportunity Detail

```json
[
  {"title": "概况",
   "fields": "--- 基本信息\ntitle|customer\namount|probability\nstage\nexpected_date",
   "js_items": [
     {"title": "商机进度", "desc": "阶段进度条(6段)+预计金额+概率+倒计时"},
     {"title": "金额分析", "desc": "加权金额(amount×probability)"}
   ]},
  {"title": "报价", "assoc": "quotes", "coll": "nb_crm_quotes",
   "fields": ["title","amount","status","valid_until"]},
  {"title": "跟进记录", "assoc": "activities", "coll": "nb_crm_activities",
   "fields": ["subject","type","follow_date","content"]}
]
```

## Example: Contract Detail

```json
[
  {"title": "概况",
   "fields": "--- 合同信息\ncode|title\ncustomer\nstart_date|end_date\nstatus|amount",
   "js_items": [
     {"title": "回款进度", "desc": "Progress条: 已回款/合同总额+待回款金额+到期倒计时"},
     {"title": "合同状态", "desc": "大字金额+彩色状态标签+剩余天数"}
   ]},
  {"title": "合同明细", "assoc": "items", "coll": "nb_crm_contract_items",
   "fields": ["product_name","quantity","unit_price","subtotal"]},
  {"title": "回款记录", "assoc": "payments", "coll": "nb_crm_payments",
   "fields": ["code","amount","payment_date","status"]}
]
```

## Secondary entities (1-2 tabs, 1 js_item)

报价, 回款, 审批: 概况(fields + 1 js_item) — no subtables.

## Reference entities — skip (auto-generated default is fine)

产品, 知识库, 竞争对手, 公海池, 合同明细.
