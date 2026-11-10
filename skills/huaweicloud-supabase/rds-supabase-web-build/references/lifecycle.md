# 生命周期（更新 / 回滚 / 下线 / 密钥轮换）

首次上线（`launched`）之后的循环工作流。所有操作沿用各专项技能的安全约束，并在 webapp.json 的 history 追加事件（不改写历史）。加载时机：launched 之后的生命周期操作前。

## 更新

触发：用户提出功能或数据模型增量。

1. 需求增量澄清（同 ⓪ 的规则，范围限定增量；费用影响一并说明）
2. 数据模型差异 → 生成**增量 init.sql**（可重复执行原则：已存在对象用 `IF NOT EXISTS` / 增量变更，不整库重建）
3. 重走 ③：**强制门同样生效**（best-practices 必读）；五步部署门槛重验；记录新部署批次（webapp.json 追加 deployment）
4. 前端更新 → ⑤ 新版本发布与验收（frontend 契约的 update 语义）→ ⑥ 复验

注意：新增对外表同样需要 RLS 覆盖与最小授权；`get_advisors(security)` 复核无新增问题。

## 回滚

**前端**：路由 rds-supabase-frontend 技能的版本回退流程（`.hwsupabase/frontend/` 记录契约的 rollback 语义：回退切换后须验收，不把切换当成功）。

**后端**：以**向前修复**为主——生成修正批次（新 init.sql）而非回退 DDL。破坏性回滚（DROP 表/列）须：逐条人工确认 + 先备份 + 遵循 best-practices 的破坏性语句规则；不承诺自动回滚。

**原则**：前端回滚不隐含后端回滚，反之亦然；任一侧回滚后在 webapp.json 追加事件并重验 ⑥ 的连通项。

## 下线

按清理清单执行（每项经用户确认后操作）：

1. **前端**：桶对象清理/桶删除（frontend 技能）、CDN 停用、域名解析回收
2. **后端**：数据导出（用户要求时）→ 应用删除经管理面（两阶段确认；仅删应用保留 PG，提示 PG 可能继续计费）
3. **凭据**：Anon/Service Role Key 失效提示——前端产物内嵌的 anon key 一并失效
4. webapp.json 标记 `decommissioned`（保留全部历史供审计，不删除记录）

## 密钥轮换

触发：管理面 `reset_supabase_api_key` 或用户主动轮换。

1. 新 Key 经管理面交付（受保护文件 / devkit）
2. **② 的数据面 MCP env 同步更新** → 客户端重载 → `get_project_url` 复验连通
3. **前端重建**：anon key 内嵌于前端构建产物，须按新 key 重建并走 ⑤ 再发布（版本记录新版本）
4. webapp.json 仅更新 `credential_source` 与注入状态（不记值），history 追加轮换事件；提示下游所有使用旧 Key 的配置同步更新
