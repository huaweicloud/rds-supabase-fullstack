# rds-supabase-mcp（华为云 RDS Supabase 数据面管理技能）

华为云 RDS Supabase 的**数据面管理技能**：实例就绪后的平台操作全部经本技能完成——init.sql 迁移脚本（建表、授权、RLS 策略、函数）的编写与五步部署、数据库结构与数据查询、登录用户管理、存储配置、行级安全（RLS）与安全建议检查、连接与执行计划排查。

技能的运行载体为配套的数据面 MCP 服务器 `mcp-server-huaweicloud-rds-supabase`（38 个工具，Apache-2.0，基于 HenkDz/selfhosted-supabase-mcp 的 Python 改进实现）。相对原版本的核心整改：`execute_sql` 采用数据库内加固函数（仅 service_role 可调用、只读白名单）；移除数据库直连通道，SQL 经 PostgREST RPC 执行、用户管理经 GoTrue 管理 API 完成；工具按风险分级并支持只读模式、操作拦截与二次确认规则、调用审计、敏感信息脱敏。

在后端开发模式中，后端代码以 init.sql 迁移脚本形式组织，经 `execute_sql` 部署为数据库层定义（表结构、授权、RLS 策略、函数），前端经 REST API 直接消费，应用端无需自建后端服务。

执行逻辑见 [SKILL.md](SKILL.md)。

## 能力概览

### 核心工作流

| 工作流 | 内容 |
|---|---|
| 实例接入 | 实例创建或选定后，凭三项配置信息动态安装 MCP 服务器（见下文"第二步"），`get_project_url` / `list_tables` 验证 |
| 部署后端定义（五步） | init.sql → ① 预检（核对现状）→ ② 审查（可重复执行、破坏性语句、RLS 覆盖、最小授权四项强制检查）→ ③ 部署（整批单一事务，失败自动回滚）→ ④ 授权暴露（GRANT + `NOTIFY pgrst, 'reload schema'`）→ ⑤ 查询确认（以查询到的实际状态为准） |
| SQL 排查 | `execute_sql` 传 `read_only=true`（数据库层仅允许 SELECT、WITH、VALUES、TABLE、EXPLAIN） |
| 安全检查 | `get_advisors`（security/performance）逐条处置，`get_rls_status` / `list_rls_policies` 复核 |
| 用户管理 | `list/get/create/update/delete_auth_user`（官方管理 API，密码哈希与邮箱确认由 GoTrue 处理） |

### 工具分组（38 个）

| 分类 | 代表工具 |
|---|---|
| SQL 执行 | execute_sql（整批单事务、失败自动回滚、read_only 白名单） |
| 结构查询 | list_tables、list_table_columns、list_indexes、list_constraints、get_function_definition 等 |
| 安全检查 | get_rls_status、list_rls_policies、get_advisors |
| 运行排查 | get_database_connections、get_database_stats、get_logs、explain_query |
| 扩展 | list_extensions、list_available_extensions |
| 用户管理 | list/get/create/update/delete_auth_user |
| 存储与平台 | get/update_storage_config、verify_jwt_secret、get_project_url、list_cron_jobs、get_cron_job_history、向量索引与统计 |

不可用工具（4 个）：`list_storage_buckets`、`list_storage_objects`、`list_realtime_publications`、`generate_typescript_types`——此部署形态已移除数据库直连通道，调用时返回明确的错误说明。完整清单见 [references/related-tools.md](references/related-tools.md)。

### 安全护栏

- 两层只读：`execute_sql` 的 `read_only` 参数限制单次语句类型；`HUAWEICLOUD_MCP_READ_ONLY=true` 在服务器层拦截全部写工具
- 风险分级（READ / WRITE / DANGEROUS 通道）与保护名单、拦截与二次确认规则（`HUAWEICLOUD_MCP_GUARDRAILS_CONFIG` 等）
- 每次调用记录审计日志（stderr，可经 `HUAWEICLOUD_MCP_AUDIT_FILE` 持久留存）；输出中符合密钥特征的值自动脱敏
- 环境变量全表见 [references/mcp-installation-guide.md](references/mcp-installation-guide.md)

## 快速安装

安装分两步：**先装技能**（纯内容，无凭据），**实例就绪后再接入 MCP 服务器**（凭网关地址与 API Key）。两项均在实例可用前即可完成第一步。

### 第一步：安装技能

#### 方式一：自然语言安装（推荐）

将下面这句话发送给你的 AI Agent（适用于 Claude Code、CodeArts、opencode 等支持 Agent Skills 标准的宿主）：

> 从 https://github.com/huaweicloud/rds-supabase-fullstack 克隆仓库，把 `skills/huaweicloud-supabase/rds-supabase-mcp/` 复制到本项目的项目级技能目录（禁止装入个人级或系统级目录），安装完成后报告安装路径。

各宿主的项目级技能目录：Claude Code 为 `<项目根>/.claude/skills/`，opencode 为 `<项目根>/.opencode/skills/`，CodeArts 为 `<项目根>/.codeartsdoer/skills/`；其余宿主使用其项目级技能机制。

#### 方式二：手动安装

```bash
TMP=$(mktemp -d)
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-mcp" <项目技能目录>/
rm -rf "$TMP"
```

网络不可达时改用 ZIP 归档下载：把上述 git clone 替换为下载 `https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip` 并解压，复制解压目录下 `skills/huaweicloud-supabase/rds-supabase-mcp`。禁止使用 `npx skills add` 等包管理器安装——技能包未发布至此类渠道。

安装校验：技能目录内含 `SKILL.md` 与 `references/` 五个参考文档。

### 第二步：接入 MCP 服务器（实例创建或选定后执行一次）

#### 自然语言接入

将下面这句话发送给你的 AI Agent（需实例已就绪，由你提供三项连接信息）：

> 我的 RDS Supabase 实例已就绪。按照 https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-mcp/references/install.md 把数据面 MCP 服务器接入本项目：我会提供网关 URL、anon key 与 service_role key，写入项目级 MCP 配置，接入后用 get_project_url 和 list_tables 验证。

Agent 按 [references/install.md](references/install.md) 执行：收集三项信息（`SUPABASE_URL` 为网关地址，非数据库直连地址）、写入项目级 MCP 配置、重载、验证。

#### 配置信息（三项）

| 环境变量 | 含义 | 备注 |
|---|---|---|
| `SUPABASE_URL` | 实例网关基础 URL（Kong 统一入口） | 协议 + 地址 + 端口 |
| `SUPABASE_ANON_KEY` | 匿名 API Key（anon 角色 JWT） | eyJ 开头 |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role API Key | SQL 执行与用户管理必需；绕过 RLS，仅安装到可信环境 |

#### stdio 配置模板（本地推荐）

```json
{
  "mcpServers": {
    "rds-supabase": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/huaweicloud/rds-supabase-fullstack",
        "--subdirectory", "server/mcp_server_rds_supabase",
        "mcp-server-huaweicloud-rds-supabase"
      ],
      "env": {
        "SUPABASE_URL": "<SUPABASE_URL>",
        "SUPABASE_ANON_KEY": "<SUPABASE_ANON_KEY>",
        "SUPABASE_SERVICE_ROLE_KEY": "<SUPABASE_SERVICE_ROLE_KEY>"
      }
    }
  }
}
```

注册位置强约束：**只允许写入当前项目的项目级 MCP 配置**（Claude Code `.mcp.json`、opencode `opencode.json`、CodeArts `mcp_settings.json`），禁止一切用户级与系统级注册；含凭据的配置文件必须列入项目 `.gitignore`。前置条件：客户端环境已安装 uv；数据库侧部署一次[加固函数](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase/sql/mcp-execute-sql.sql)（未部署仅影响 execute_sql）。首次接入建议在 env 中叠加 `"HUAWEICLOUD_MCP_READ_ONLY": "true"` 先行只读验证；远程部署（Docker + streamable-http）与环境变量全表见 [references/mcp-installation-guide.md](references/mcp-installation-guide.md)。服务器文档见 https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase/README.md 。

## 使用

安装后正常开展开发对话即可，命中技能描述的场景（init.sql 编写与部署、结构与数据查询、用户管理、RLS 检查、连接排查）时 Agent 自动加载。触发语句示例：

> 实例已接入，帮我把博客的后端建出来：文章表、分类表、RLS 策略和授权，写进 init.sql 部署。

> 检查一下当前数据库的安全建议，对外表 RLS 覆盖是否完整。

> 帮我创建一个测试登录用户，邮箱 test@example.com。

## 许可

技能：MIT。配套服务器 `mcp-server-huaweicloud-rds-supabase`：Apache-2.0，衍生自 HenkDz/selfhosted-supabase-mcp（TypeScript，MIT 衍生链见仓库 NOTICE）。
