# rds-supabase-usage（华为云 RDS Supabase 应用开发技能）

面向运行在华为云 RDS PostgreSQL 上的自建 Supabase 栈（Kong 网关、PostgREST 数据 API、GoTrue 认证、Storage、Realtime、pgvector）的应用开发技能。覆盖六类任务：supabase-js / @supabase/ssr 客户端库与 Next.js、React、SvelteKit、Astro、Remix 框架集成；认证与会话排查（登录登出、JWT、Cookie、getSession/getUser、RLS 相关报错）；schema 变更与 init.sql 部署纪律；REST/Data API 行为异常（permission denied、schema cache、42501、超时、表不可见）；Storage 与 Realtime 故障；向量检索与服务端计算选型。

技能同时约束 Agent 的开发纪律：组件版本以部署内实测为准、修改后必验证、错误恢复不循环、按层定位故障（数据库 → 服务容器 → 控制台日志）。

执行逻辑见 [SKILL.md](SKILL.md)。

## 能力概览

| 领域 | 内容 |
|---|---|
| 客户端集成 | supabase-js / @supabase/ssr 的接入模式、服务端/客户端组件会话管理、环境变量与密钥边界 |
| 认证与会话 | 登录登出流程、JWT claims 时效、`user_metadata` 与 `app_metadata` 的权限边界、令牌吊销与用户删除的会话失效处置 |
| 数据 API | 表暴露的两层机制（GRANT 决定可见、RLS 决定行集）、PostgREST 报错语义、Kong 网关超时特征 |
| schema 部署 | 变更脚本经 Git 目录管理、MCP `execute_sql` 整批单事务部署、五步流程要点（预检/审查/部署/授权暴露/查询确认） |
| 故障排查 | 症状到层的定位表（42501、空结果、prepared statement 报错、慢查询、服务级错误） |
| 向量检索 | pgvector 索引查看工具与索引类型选型（HNSW/IVF/GIN） |
| 服务端计算 | FunctionGraph / Postgres RPC / pg_cron / pg_net 的选型与边界 |

## 安装

见 [INSTALL.md](INSTALL.md)。

## 使用

安装后正常开展开发对话即可，命中场景（客户端集成、认证问题、Data API 异常、平台调试）时 Agent 自动加载。触发语句示例：

> 我的 Next.js 应用用 supabase-js 登录后 getSession 拿不到用户，帮我排查。

> REST API 查询返回 42501 permission denied，数据确实存在，怎么处理？

> 帮我把现有的表加上 RLS 策略，前端用户只能看到自己的数据。

## 许可

MIT。衍生自 [supabase/agent-skills](https://github.com/supabase/agent-skills)（commit `c9be0e9`，MIT），针对华为云 RDS Supabase 自建部署适配。
