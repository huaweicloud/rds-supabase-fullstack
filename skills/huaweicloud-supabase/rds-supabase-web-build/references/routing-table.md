# 跨技能 / MCP 路由矩阵

web-build 是编排者：只路由不复制。命中左列任务时，加载对应技能/文档执行；负向路由明确不做的事。加载时机：任务归属不明时查。

## 正向路由

| 任务 | 路由目标 | 锚点 |
|---|---|---|
| 管理面 MCP 拉起（devkit 检测 → 动态拉起） | mgr 服务器 uvx 模板 | https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/README.md |
| 实例创建/选定/配置（EIP/安全组/SSL）/密钥交付/删除 | rds-supabase-mgr-mcp 技能 + 管理面 MCP | SKILL.md 六场景工作流；工具两阶段确认 |
| 数据面 MCP 动态安装 | rds-supabase-mcp 技能 | `references/install.md` |
| init.sql 生成质量（步骤四 强制门） | rds-supabase-postgres-best-practices 技能 | SKILL.md 症状/任务索引 → 对应规则文件 |
| init.sql 编写规范与五步部署 | rds-supabase-mcp 技能 | `references/init-sql-guide.md`；SKILL.md 五步部署 |
| 前端 SDK 用法（步骤五 强制门；步骤四 客户端消费视角） | rds-supabase-usage 技能 | SKILL.md（客户端集成/auth/RLS 调试速查） |
| 构建环境/构建/OBS 上传/CDN/版本记录与回退 | rds-supabase-frontend 技能 | `references/build-environment.md`、`references/obs-release.md`、`references/record-contract.md`、`references/deployment.md` |
| OBS 租户桶创建（步骤二） | rds-supabase-frontend 技能 | `references/hosting.md` / `references/obs-release.md` |
| auth 回调配置（步骤六↻：site_url/redirect_uris） | 管理面 MCP | `update_supabase_auth_config`（两阶段确认） |
| 部署验证（步骤四/步骤七 后端项） | rds-supabase-mcp 技能 | `references/verification-method.md` |
| 单工具数据操作（结构查询/用户管理等） | rds-supabase-mcp 技能 | SKILL.md 可用工具表 |

## 负向路由（web-build 不做）

| 任务 | 处置 |
|---|---|
| SQL 质量规则细节 | 不复制 best-practices 内容，只路由 |
| 前端构建/发布/域名细节 | 不复制 frontend 内容，只路由 |
| 复杂业务逻辑（支付/第三方调用/长任务） | v1 边界外：明确告知用户并停止；FunctionGraph 留待 v2 |
| SSR 后端部署 | 不支持：静态导出为边界（继承 frontend 策略） |
| 文件上传（Storage） | v1 默认不含：步骤一 识别并说明（可选扩展：管理面 `update_supabase_storage` 配 OBS 凭据，数据桶与前端托管桶分离） |
| 绕过强制门直接生成代码 | 禁止：步骤四步骤五 生成前必读对应技能 |
| agent 读取密钥交付文件 | 禁止：凭据只经 devkit 注入或用户在可信客户端复制 |
| 从 PyPI/第三方仓库搜索安装 MCP | 禁止：只从本仓安装（uvx git 模板或本地 `uv run --directory`）；PyPI 存在同名第三方包，装上即错误服务器 |
