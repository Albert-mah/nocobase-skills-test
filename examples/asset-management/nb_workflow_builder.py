"""nb_workflow_builder.py -- NocoBase 工作流构建通用库

极简 API：只需业务参数，自动处理 API 调用、节点链接、变量引用。

用法示例：
    from nb_page_builder import NB
    from nb_workflow_builder import WorkflowBuilder

    nb = NB()
    wb = WorkflowBuilder(nb)

    # 1. 简单状态联动（3行）
    wf = wb.on_create("AM 采购状态自动更新", "nb_am_purchase_requests")
    n1 = wf.condition_equal("status", None, title="状态是否为空")
    n1.on_true().update("nb_am_purchase_requests", {"status": "草稿"})
    wf.enable()

    # 2. 条件分支（领用/借用 -> 不同状态）
    wf = wb.on_create("AM 资产领用借用联动", "nb_am_asset_transfers")
    n1 = wf.condition_equal("transfer_type", "领用")
    n1.on_true().update("nb_am_assets", {"status": "在用"},
                         filter={"id": "{{$context.data.asset_id}}"})
    n1.on_false().update("nb_am_assets", {"status": "借用中"},
                          filter={"id": "{{$context.data.asset_id}}"})
    wf.enable()

    # 3. 状态变更触发
    wf = wb.on_update("AM 报废完成", "nb_am_disposals",
                       changed=["status"], condition={"status": {"$eq": "已报废"}})
    wf.update("nb_am_assets", {"status": "已报废"},
              filter={"id": "{{$context.data.asset_id}}"})
    wf.enable()

    # 4. SQL 节点
    wf = wb.on_create("AM 采购编号", "nb_am_purchase_requests")
    wf.sql(\"\"\"
        UPDATE nb_am_purchase_requests
        SET request_no = 'PR-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
            LPAD((SELECT COALESCE(MAX(CAST(SUBSTRING(request_no FROM '[0-9]+$') AS INT)),0)+1
                  FROM nb_am_purchase_requests
                  WHERE request_no LIKE 'PR-' || TO_CHAR(NOW(), 'YYYY') || '-%')::TEXT, 3, '0')
        WHERE id = {{$context.data.id}}
    \"\"\")
    wf.enable()

    # 5. 定时触发（DateField 模式）
    wf = wb.on_date_field("AM 保险到期提醒", "nb_am_vehicle_insurance",
                           field="end_date", offset_days=-30)
    wf.sql("UPDATE nb_am_vehicle_insurance SET remark = '即将到期' WHERE id = {{$context.data.id}}")
    wf.enable()

    # 6. 容错：重名检查
    wf = wb.on_create("AM 采购状态自动更新", "nb_am_purchase_requests")
    # -> 返回 None，打印警告，不会重复创建

    # 7. 查看创建结果
    wb.summary()
"""

import json


# ══════════════════════════════════════════════════════════════
# NodeRef / BranchBuilder / ChainBuilder — 链式节点构建
# ══════════════════════════════════════════════════════════════

class NodeRef:
    """节点引用 -- 从条件/循环等分支节点返回，用于链式添加子节点。

    用法：
        n = wf.condition_equal("status", "草稿")
        n.on_true().update(...)   # 真分支
        n.on_false().update(...)  # 假分支
        n.then().sql(...)         # 条件节点之后的主线下游
    """

    def __init__(self, wf, node_id, node_key):
        self.wf = wf
        self.id = node_id
        self.key = node_key

    def on_true(self):
        """真分支 (branchIndex=1)。"""
        return BranchBuilder(self.wf, self.id, branch_index=1)

    def on_false(self):
        """假分支 (branchIndex=0)。"""
        return BranchBuilder(self.wf, self.id, branch_index=0)

    def on_branch(self, index):
        """指定分支索引（用于 loop 节点: index=1 是循环体）。"""
        return BranchBuilder(self.wf, self.id, branch_index=index)

    def then(self):
        """主线下游 -- 在当前节点之后追加节点。"""
        return ChainBuilder(self.wf, self.id)


class _NodeMixin:
    """所有 Builder 共享的节点创建方法。

    子类需提供 _make_node(type, title, config) -> NodeRef。
    """

    def update(self, collection, values, filter=None, title=None):
        """创建 update 节点。

        collection: 目标数据表
        values:     要更新的字段值 dict
        filter:     匹配记录的条件（默认 {"id": "{{$context.data.id}}"}）
        """
        if filter is None:
            filter = {"id": "{{$context.data.id}}"}
        title = title or f"更新 {collection}"
        return self._make_node("update", title, {
            "collection": collection,
            "params": {"filter": filter, "values": values}
        })

    def create_record(self, collection, values, title=None):
        """创建 create 节点（新增记录）。"""
        title = title or f"创建 {collection}"
        return self._make_node("create", title, {
            "collection": collection,
            "params": {"values": values}
        })

    def sql(self, sql, title=None):
        """创建 SQL 节点。

        sql: 原生 SQL，可用 {{$context.data.xxx}} 等变量。
        """
        title = title or "SQL"
        return self._make_node("sql", title, {
            "dataSource": "main", "sql": sql.strip()
        })

    def query(self, collection, filter, multiple=False, appends=None, title=None):
        """创建 query 节点（查询记录）。

        返回 NodeRef，可用 .key 在后续节点中引用查询结果。
        """
        title = title or f"查询 {collection}"
        config = {
            "collection": collection,
            "multiple": multiple,
            "params": {"filter": filter}
        }
        if appends:
            config["params"]["appends"] = appends
        return self._make_node("query", title, config)

    def condition_equal(self, field, value, title=None):
        """创建条件节点：$context.data.field == value。

        field: 字段名（自动加 $context.data. 前缀）
        value: 期望值，None 表示检查为空（null 或 ""）
        """
        if value is None:
            calc = {
                "group": {
                    "type": "or",
                    "calculations": [
                        {"calculator": "equal",
                         "operands": [f"{{{{$context.data.{field}}}}}", None]},
                        {"calculator": "equal",
                         "operands": [f"{{{{$context.data.{field}}}}}", ""]},
                    ]
                }
            }
        else:
            calc = {
                "group": {
                    "type": "and",
                    "calculations": [
                        {"calculator": "equal",
                         "operands": [f"{{{{$context.data.{field}}}}}", value]}
                    ]
                }
            }
        title = title or f"{field} == {value!r}"
        return self._make_node("condition", title, {
            "rejectOnFalse": False,
            "engine": "basic",
            "calculation": calc
        })

    def condition_in(self, field, values, title=None):
        """创建条件节点：$context.data.field in [values...]。

        多个值用 OR 连接。
        """
        calcs = [
            {"calculator": "equal",
             "operands": [f"{{{{$context.data.{field}}}}}", v]}
            for v in values
        ]
        title = title or f"{field} in {values!r}"
        return self._make_node("condition", title, {
            "rejectOnFalse": False,
            "engine": "basic",
            "calculation": {"group": {"type": "or", "calculations": calcs}}
        })

    def condition_expr(self, expression, title=None):
        """创建条件节点：自定义 math.js 表达式。

        expression 中可用 {{$context.data.xxx}} 等变量。
        """
        title = title or "条件判断"
        return self._make_node("condition", title, {
            "engine": "math.js",
            "expression": expression,
            "rejectOnFalse": False
        })

    def request(self, url, method="POST", data=None, headers=None, title=None):
        """创建 HTTP 请求节点。"""
        title = title or f"HTTP {method}"
        config = {
            "url": url, "method": method,
            "contentType": "application/json",
            "timeout": 5000, "ignoreFail": False, "onlyData": True
        }
        if data:
            config["data"] = data
        if headers:
            config["headers"] = [{"name": k, "value": v} for k, v in headers.items()]
        return self._make_node("request", title, config)

    def end(self, status=1, title=None):
        """创建 end 节点（终止流程）。

        status: 1=成功, 0=失败
        """
        return self._make_node("end", title or "结束", {"endStatus": status})

    def loop(self, target, title=None):
        """创建循环节点。

        target: 循环目标表达式，如 "{{$context.data.items}}"
        返回 NodeRef -- 用 .on_branch(1) 获取循环体 builder。
        """
        title = title or "循环"
        return self._make_node("loop", title, {"target": target})


class BranchBuilder(_NodeMixin):
    """分支节点构建器 -- 在条件/循环的指定分支上创建节点。

    通过 NodeRef.on_true() / on_false() / on_branch(n) 获得。
    """

    def __init__(self, wf, upstream_id, branch_index):
        self.wf = wf
        self.upstream_id = upstream_id
        self.branch_index = branch_index
        self._last_id = None

    def _make_node(self, node_type, title, config):
        # 分支内第一个节点挂在分支上，后续节点链式追加
        if self._last_id is None:
            ref = self.wf._create_node(node_type, title, config,
                                       upstream_id=self.upstream_id,
                                       branch_index=self.branch_index)
        else:
            ref = self.wf._create_node(node_type, title, config,
                                       upstream_id=self._last_id)
        self._last_id = ref.id
        return ref


class ChainBuilder(_NodeMixin):
    """主线下游节点构建器 -- 在指定节点之后追加节点。

    通过 NodeRef.then() 获得。
    """

    def __init__(self, wf, upstream_id):
        self.wf = wf
        self.upstream_id = upstream_id
        self._last_id = None

    def _make_node(self, node_type, title, config):
        uid = self._last_id or self.upstream_id
        ref = self.wf._create_node(node_type, title, config, upstream_id=uid)
        self._last_id = ref.id
        return ref


# ══════════════════════════════════════════════════════════════
# Workflow — 单个工作流实例
# ══════════════════════════════════════════════════════════════

class Workflow(_NodeMixin):
    """单个工作流实例 -- 提供链式节点创建 API。

    通过 WorkflowBuilder.on_create() 等方法获得，不要直接实例化。
    """

    def __init__(self, builder, wf_id, wf_key, title, collection):
        self.builder = builder
        self.id = wf_id
        self.key = wf_key
        self.title = title
        self.collection = collection
        self.nodes = []
        self._last_node_id = None
        self._enabled = False

    # ── 内部：创建节点 ────────────────────────────────

    def _create_node(self, node_type, title, config,
                     upstream_id=None, branch_index=None):
        """创建节点并自动链接。返回 NodeRef。

        被 _NodeMixin 方法和 BranchBuilder/ChainBuilder 调用。
        """
        s = self.builder.nb.s
        base = self.builder.nb.base

        data = {"type": node_type, "title": title, "config": config}
        if upstream_id is not None:
            data["upstreamId"] = upstream_id
        elif self._last_node_id is not None:
            data["upstreamId"] = self._last_node_id
        if branch_index is not None:
            data["branchIndex"] = branch_index

        try:
            r = s.post(f"{base}/api/workflows/{self.id}/nodes:create", json=data)
        except Exception as e:
            self.builder.errors.append(f"node create [{title}]: network error: {e}")
            return NodeRef(self, None, None)

        if not r.ok:
            self.builder.errors.append(
                f"node create [{title}]: {r.status_code} {r.text[:200]}")
            return NodeRef(self, None, None)

        resp = r.json()
        if "data" not in resp:
            self.builder.errors.append(
                f"node create [{title}]: unexpected response format")
            return NodeRef(self, None, None)

        node = resp["data"]
        nid = node.get("id")
        nkey = node.get("key", "")
        self.nodes.append({
            "id": nid, "key": nkey, "type": node_type, "title": title
        })

        # 只有主线节点（非分支）才更新 _last_node_id
        if branch_index is None and upstream_id is None:
            self._last_node_id = nid

        return NodeRef(self, nid, nkey)

    def _make_node(self, node_type, title, config):
        """_NodeMixin 接口：在主线追加节点。"""
        return self._create_node(node_type, title, config)

    # ── 启用/禁用 ────────────────────────────────────

    def enable(self):
        """启用工作流。"""
        s = self.builder.nb.s
        base = self.builder.nb.base
        try:
            r = s.post(f"{base}/api/workflows:update?filterByTk={self.id}",
                       json={"enabled": True})
        except Exception as e:
            self.builder.errors.append(f"enable [{self.title}]: network error: {e}")
            return
        if r.ok:
            self._enabled = True
            self.builder.created += 1
        else:
            self.builder.errors.append(f"enable [{self.title}]: {r.text[:200]}")

    def disable(self):
        """禁用工作流。"""
        s = self.builder.nb.s
        base = self.builder.nb.base
        try:
            s.post(f"{base}/api/workflows:update?filterByTk={self.id}",
                   json={"enabled": False})
        except Exception:
            pass
        self._enabled = False

    # ── 信息 ─────────────────────────────────────────

    def info(self):
        """返回工作流摘要 dict。"""
        return {
            "id": self.id, "key": self.key, "title": self.title,
            "collection": self.collection,
            "nodes": len(self.nodes), "enabled": self._enabled,
        }


# ══════════════════════════════════════════════════════════════
# WorkflowBuilder — 工作流构建器（入口）
# ══════════════════════════════════════════════════════════════

class WorkflowBuilder:
    """工作流构建器 -- 和 NB 类配合使用。

    用法：
        nb = NB()
        wb = WorkflowBuilder(nb)

        wf = wb.on_create("名称", "collection_name")
        wf.update(...)
        wf.enable()

        wb.summary()

    容错：
        - 创建前自动检查同名工作流，避免重复创建
        - 网络错误和非预期 API 返回格式会记录到 self.errors
        - 调用 wb.summary() 查看完整结果
    """

    def __init__(self, nb):
        self.nb = nb
        self.workflows = []
        self.created = 0
        self.errors = []
        self._existing_titles = None  # lazy loaded

    def _load_existing_titles(self):
        """加载已有工作流标题集合（用于重名检查）。"""
        if self._existing_titles is not None:
            return
        wfs = self.list_workflows()
        self._existing_titles = {w.get("title", "") for w in wfs}

    def _check_duplicate(self, title):
        """检查同名工作流是否已存在。返回 True 表示有重复。"""
        self._load_existing_titles()
        if title in self._existing_titles:
            print(f"  [SKIP] '{title}' already exists")
            return True
        return False

    def _create_workflow(self, title, wf_type, config, sync=False):
        """创建工作流，返回 Workflow 实例。重名时返回 None。

        title:    工作流标题
        wf_type:  触发器类型 (collection/schedule/action/...)
        config:   触发器配置
        sync:     是否同步执行（默认 False）
        """
        if self._check_duplicate(title):
            return None

        data = {
            "title": title,
            "type": wf_type,
            "config": config,
            "enabled": False,
            "sync": sync,
        }

        try:
            r = self.nb.s.post(f"{self.nb.base}/api/workflows:create", json=data)
        except Exception as e:
            self.errors.append(f"workflow create [{title}]: network error: {e}")
            return None

        if not r.ok:
            self.errors.append(
                f"workflow create [{title}]: {r.status_code} {r.text[:200]}")
            return None

        resp = r.json()
        if "data" not in resp:
            self.errors.append(
                f"workflow create [{title}]: unexpected response format")
            return None

        wf_data = resp["data"]
        wf_id = wf_data.get("id")
        wf_key = wf_data.get("key", "")
        coll = config.get("collection", "")
        wf = Workflow(self, wf_id, wf_key, title, coll)
        self.workflows.append(wf)
        self._existing_titles.add(title)
        return wf

    # ── 触发器快捷方式 ─────────────────────────────────

    def on_create(self, title, collection, appends=None, condition=None):
        """创建"数据表新增"触发的工作流。

        collection: 数据表名
        appends:    预加载的关联字段列表
        condition:  触发条件（NocoBase filter 格式）
        """
        config = {
            "mode": 1,
            "collection": collection,
            "appends": appends or [],
            "condition": condition or {"$and": []}
        }
        return self._create_workflow(title, "collection", config)

    def on_update(self, title, collection, changed=None, condition=None,
                  appends=None):
        """创建"数据表更新"触发的工作流。

        changed:   只监听这些字段变化（列表）
        condition: NocoBase filter 格式的触发条件
        appends:   预加载的关联字段列表
        """
        config = {
            "mode": 2,
            "collection": collection,
            "appends": appends or [],
            "condition": condition or {"$and": []}
        }
        if changed:
            config["changed"] = changed
        return self._create_workflow(title, "collection", config)

    def on_create_or_update(self, title, collection, changed=None,
                             condition=None, appends=None):
        """创建"新增或更新"触发的工作流。"""
        config = {
            "mode": 3,
            "collection": collection,
            "appends": appends or [],
            "condition": condition or {"$and": []}
        }
        if changed:
            config["changed"] = changed
        return self._create_workflow(title, "collection", config)

    def on_delete(self, title, collection, condition=None):
        """创建"删除"触发的工作流。"""
        config = {
            "mode": 4,
            "collection": collection,
            "appends": [],
            "condition": condition or {"$and": []}
        }
        return self._create_workflow(title, "collection", config)

    def on_schedule(self, title, cron, starts_on="2026-01-01T00:00:00.000Z"):
        """创建定时触发的工作流（Static 模式）。

        cron: cron 表达式，如 "0 9 * * 1-5"（工作日 9 点）
        """
        config = {
            "mode": 0,
            "startsOn": starts_on,
            "repeat": cron,
        }
        return self._create_workflow(title, "schedule", config)

    def on_date_field(self, title, collection, field, offset_days=-7,
                      appends=None):
        """创建基于日期字段触发的工作流（DateField 模式）。

        field:       日期字段名
        offset_days: 偏移天数（负数=提前，如 -30 表示提前 30 天）
        appends:     预加载的关联字段列表
        """
        config = {
            "mode": 1,
            "collection": collection,
            "startsOn": {
                "field": field,
                "offset": offset_days,
                "unit": 86400000  # 毫秒/天
            },
            "repeat": None,
            "appends": appends or []
        }
        return self._create_workflow(title, "schedule", config)

    # ── 查询/管理 ──────────────────────────────────────

    def list_workflows(self, filter_enabled=None):
        """列出所有工作流（当前版本）。

        filter_enabled: True=只列启用的，False=只列禁用的，None=全部
        返回: workflow dict 列表
        """
        params = {"pageSize": 200}
        if filter_enabled is not None:
            params["filter[enabled]"] = str(filter_enabled).lower()
        try:
            r = self.nb.s.get(f"{self.nb.base}/api/workflows:list",
                              params=params)
        except Exception:
            return []
        if not r.ok:
            return []
        # 只返回 current 版本（过滤旧版本）
        all_wfs = r.json().get("data", [])
        return [w for w in all_wfs if w.get("current", True)]

    def get_workflow(self, wf_id):
        """获取单个工作流详情（含节点列表）。

        返回 (workflow_data, nodes_list) 或 (None, [])。
        """
        try:
            r = self.nb.s.get(
                f"{self.nb.base}/api/workflows:get?filterByTk={wf_id}")
            if not r.ok:
                return None, []
            wf_data = r.json().get("data")

            r2 = self.nb.s.get(
                f"{self.nb.base}/api/workflows/{wf_id}/nodes:list")
            nodes = r2.json().get("data", []) if r2.ok else []

            return wf_data, nodes
        except Exception:
            return None, []

    def find_by_title(self, title):
        """按标题查找工作流。返回 workflow dict 或 None。"""
        for w in self.list_workflows():
            if w.get("title") == title:
                return w
        return None

    def delete_workflow(self, wf_id):
        """删除工作流（自动先禁用）。"""
        try:
            self.nb.s.post(
                f"{self.nb.base}/api/workflows:update?filterByTk={wf_id}",
                json={"enabled": False})
            r = self.nb.s.post(
                f"{self.nb.base}/api/workflows:destroy?filterByTk={wf_id}")
            return r.ok
        except Exception:
            return False

    def delete_by_title(self, title):
        """按标题删除工作流。返回是否找到并删除。"""
        wf = self.find_by_title(title)
        if wf:
            ok = self.delete_workflow(wf["id"])
            if ok and self._existing_titles is not None:
                self._existing_titles.discard(title)
            return ok
        return False

    def clean_by_prefix(self, prefix):
        """删除所有标题以 prefix 开头的工作流。返回删除数量。"""
        count = 0
        for w in self.list_workflows():
            if w.get("title", "").startswith(prefix):
                if self.delete_workflow(w["id"]):
                    count += 1
                    print(f"  [DEL] {w['title']} (id={w['id']})")
        # 重置缓存
        self._existing_titles = None
        return count

    # ── Summary ──────────────────────────────────────

    def summary(self):
        """打印本次构建的工作流汇总。"""
        print(f"\n{'='*60}")
        print(f"  Workflows: {self.created} enabled, {len(self.workflows)} total")
        print(f"  Errors: {len(self.errors)}")
        print(f"{'='*60}")
        for wf in self.workflows:
            info = wf.info()
            status = "[ON]" if info["enabled"] else "[--]"
            print(f"  {status} {info['title']} ({info['nodes']} nodes) id={info['id']}")
        for e in self.errors[:10]:
            print(f"  [ERR] {e}")
