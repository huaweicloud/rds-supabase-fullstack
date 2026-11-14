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
| schema 部署 | 变更脚本经 Git 目录管理、MCP `execute_sql` 整批单事务部署、破坏性语句确认纪律 |
| 故障排查 | 症状到层的定位表（42501、空结果、prepared statement 报错、慢查询、服务级错误） |
| 向量检索 | pgvector 索引查看工具与索引类型选型（HNSW/IVF/GIN） |
| 服务端计算 | FunctionGraph / Postgres RPC / pg_cron / pg_net 的选型与边界 |

## 快速安装（独立安装）

本技能为纯内容技能（SKILL.md 与 references 文档），独立安装即可完整使用；安装不引入 MCP 服务器、凭据或云资源。

### 方式一：自然语言安装（推荐）

将下面这句话发送给你的 AI Agent（适用于 Claude Code、CodeArts、opencode 等支持 Agent Skills 标准的宿主）：

> 从 https://github.com/huaweicloud/rds-supabase-fullstack 克隆仓库，把 `skills/huaweicloud-supabase/rds-supabase-usage/` 复制到本项目的项目级技能目录（禁止装入个人级或系统级目录），安装完成后报告安装路径。

各宿主的项目级技能目录：Claude Code 为 `<项目根>/.claude/skills/`，opencode 为 `<项目根>/.opencode/skills/`，CodeArts 为 `<项目根>/.codeartsdoer/skills/`；其余宿主使用其项目级技能机制。

### 方式二：手动安装

```bash
TMP=$(mktemp -d)
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-usage" <项目技能目录>/
rm -rf "$TMP"
```

网络不可达时改用 ZIP 归档下载：把上述 git clone 替换为下载 `https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip` 并解压，复制解压目录下 `skills/huaweicloud-supabase/rds-supabase-usage`。禁止使用 `npx skills add` 等包管理器安装——技能包未发布至此类渠道。

### 运行期依赖（按需，不属于安装阶段）

涉及平台查询与 SQL 执行的操作需要数据面 MCP 服务器 `mcp-server-huaweicloud-rds-supabase`（38 个工具）：实例就绪后凭网关地址与 API Key 写入**项目级** MCP 配置接入（环境变量 `SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY`，首接建议加 `HUAWEICLOUD_MCP_READ_ONLY=true` 只读验证）。服务器文档与完整安装规程：https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase/README.md 。MCP 未接入时，本技能的客户端集成、认证排查、文档查询等开发指导仍然可用。

## 使用

安装后正常开展开发对话即可，命中技能描述的场景（客户端集成、认证问题、Data API 异常、平台调试）时 Agent 自动加载。触发语句示例：

> 我的 Next.js 应用用 supabase-js 登录后 getSession 拿不到用户，帮我排查。

> REST API 查询返回 42501 permission denied，数据确实存在，怎么处理？

> 帮我把现有的表加上 RLS 策略，前端用户只能看到自己的数据。

## 许可

MIT。衍生自 [supabase/agent-skills](https://github.com/supabase/agent-skills)（commit `c9be0e9`，MIT），针对华为云 RDS Supabase 自建部署适配。
