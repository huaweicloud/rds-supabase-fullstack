# 端到端上线清单（步骤七）

上线门槛 = 三层组合验证。任何必需项 failed → 不标记 `launched`（处置见 workflow-stages.md 步骤七）。验收事件沿用 frontend 契约的 checks 语义：新的 check_id、独立文件、不覆写历史。加载时机：步骤七 上线验证前。

## 第一层：后端项（数据面 MCP）

| 检查 | 方法 | 通过标准 |
|---|---|---|
| 结构确认 | `list_tables` / `list_constraints` / `list_table_columns` | 与 init.sql 对象清单一致 |
| RLS 生效 | `get_rls_status` / `list_rls_policies` | 对外表全部启用且至少一条策略 |
| 安全建议 | `get_advisors(type=security)` | 无新增问题项 |
| REST 可达 | `GET /rest/v1/<对外表>`（anon key） | 200 且 anon 可见性符合设计（公开表返回数据；受保护表返回空集——RLS 拒绝表现为受限结果，不是 4xx） |

## 第二层：前端项（frontend 技能 checks 契约）

| 检查 | 通过标准 |
|---|---|
| entry | stable_url GET 2xx + 浏览器访问通过 + 非附件响应 |
| assets | 静态资源 2xx |
| routes | 路由可达（SPA fallback 正确） |
| negative_paths | 预期 4xx |
| cache | 缓存头符合 frontend 契约 |

## 第三层：连通项（web-build 特有）

| 检查 | 方法 | 通过标准 |
|---|---|---|
| 站点访问 | 浏览器打开 stable_url | 页面正常渲染 |
| 前端 → Supabase API | 站点内执行一次数据查询或登录流 | 返回数据可见性正确（匿名/登录态按 RLS 预期受限；空集/子集即正确表现） |
| 多用户隔离抽检 | 两个测试账号（经数据面 MCP 用户管理创建）在站点内互访对方数据行 | 均不可见（RLS 行级隔离实证；空集即通过） |
| auth 回调 | 走一次登录/登出 | 回调跳转正确（步骤六↻ 已配置 site_url / redirect_uris） |

## 上线报告格式

```text
【上线报告】
项目：<name>（.hwsupabase/webapp.json）
实例：<supabase_application_id> @ <gateway_url>
后端：批次 <current_batch>（对象 N 项 · advisors 无新增 · REST 200 · anon 可见性符合设计）
前端：<version>（checks 全必需项 passed · stable_url HTTPS）
连通：站点渲染 ✓ · API 可见性 ✓ · 多用户隔离抽检 ✓ · 回调 ✓
结论：线上验收通过（launched）
三级交付语义：本地已验证 / 环境已准备 / 线上验收通过
```

任一层失败：报告区分失败层与处置路径，webapp.json history 记录 `failed`，不标记 `launched`。HTTP 页面可达不等于 HTTPS/Auth 通过；本地检查不能代替真实入口验证。**RLS 拒绝的正确表现是受限结果（空集/子集），不是 4xx/5xx——不得以状态码代替数据可见性断言。**
