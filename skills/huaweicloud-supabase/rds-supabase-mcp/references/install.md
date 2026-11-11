# 一句话动态安装（AI Agent 执行路径）

面向 AI Agent 的最短安装流程：收集三项连接信息，写入客户端 MCP 配置，验证即完成。本 MCP 服务器在 Web 全栈开发流程中随实例动态接入：RDS Supabase 实例完成创建或选定后，配置信息（网关 URL 与 API Key）方可获得，随即按本文一次执行到位。完整安装说明（Docker 部署、环境变量全表、护栏规则、execute_sql 函数部署）见 mcp-installation-guide.md。

## 需向用户收集的三项信息

| 环境变量 | 含义 | 形态 |
|---|---|---|
| SUPABASE_URL | 实例网关基础 URL（Kong 统一入口） | 协议 + 地址 + 端口 |
| SUPABASE_ANON_KEY | 匿名 API Key（anon 角色 JWT） | eyJ 开头的 JWT 字符串 |
| SUPABASE_SERVICE_ROLE_KEY | service_role API Key | eyJ 开头的 JWT 字符串；SQL 执行与用户管理必需 |

要点：

- 三项信息由 Web 全栈开发流程注入或由用户提供，逐字核对，不做推断
- SUPABASE_URL 是网关地址，不是数据库直连地址
- service_role key 绕过 RLS：仅安装到可信环境；首次接入可在 env 中叠加 `"HUAWEICLOUD_MCP_READ_ONLY": "true"` 先行只读验证
- 密钥只写入**项目级**客户端配置（该文件必须列入项目 `.gitignore`，见「注册位置强约束」），不得提交到仓库或出现在日志中

## 前置条件

- 客户端环境已安装 uv（含 uvx）：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 数据库侧已部署 `sql/mcp-execute-sql.sql` 加固函数；未部署时仅 execute_sql 不可用，不影响其余工具（见 mcp-installation-guide.md）

## 配置模板（stdio，本地推荐）

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

## 配置样例（stdio，已填充，值为演示用）

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
        "SUPABASE_URL": "http://supabase.example.com:8443",
        "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<anon 载荷>.<anon 签名>",
        "SUPABASE_SERVICE_ROLE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<service_role 载荷>.<service_role 签名>"
      }
    }
  }
}
```

## 注册位置强约束（项目级隔离，红线）

本 MCP 随项目动态接入，**只允许注册进当前项目的项目级 MCP 配置**——当前项目之外不可见。**禁止一切用户级与系统级注册**：用户级注册会使本机所有项目都能看到并使用本项目实例的 MCP 与凭据，属边界溢出，严格禁止。常见宿主（Claude Code、CodeArts、OfficeAce 及 opencode 等）逐一适配如下：

| 宿主 | 项目级 MCP 配置（唯一允许） | 条目结构 | 禁止的用户级/系统级位置 |
|---|---|---|---|
| Claude Code | `<项目根>/.mcp.json`（project scope） | `mcpServers` 键 | `~/.claude.json`（user scope）、Claude Desktop 的 `claude_desktop_config.json`（用户级）、系统 managed 配置 |
| CodeArts | `<项目根>/.codeartsdoer/` 下项目级 MCP 配置（与项目级技能目录同根） | 按宿主项目级结构 | `~/.codeartsdoer/` 个人级目录（两级目录同名不同根） |
| OfficeAce | 项目根下该宿主的项目级 MCP 配置（Agent 自知位置，以项目根为界） | 按宿主项目级结构 | `~` 家目录下与系统目录下的一切该宿主配置 |
| opencode | `<项目根>/opencode.json` 或 `.opencode/` 目录内配置 | `mcp` 键 | `~/.config/opencode/opencode.json` 等全局配置 |
| 其余宿主 | 该宿主的项目级 MCP 配置机制（Agent 自知位置，以项目根为界） | 按宿主项目级结构 | 同上 |

硬性规则：

- **落位判定**：注册条目所在配置文件必须位于当前项目根之内；任何指向 `~` 家目录或系统目录的位置一律禁止
- **宿主仅有用户级配置机制 → 停止并报告，不注册**（宁可本流程不可用，不可边界溢出）；严禁以"图方便"为由降级写入用户级/系统级配置
- **注册后核验**：确认条目已写入项目级配置文件、且未触碰任何用户级/系统级位置，再重载客户端
- 含实例凭据的项目级配置文件**必须列入项目 `.gitignore`**（权限 0600）；凭据值由用户从项目内受保护文件复制填入，Agent 不经手明文
- **安装方式边界**：`uvx` 为一次性缓存运行（uv 共享构建缓存**不是安装**——不落任何注册与命令行入口，其他项目不可见）；**严禁 `uv tool install`、`pip install` 装入用户级/系统级环境**（入口脚本与包将落入 `~/.local/bin`、用户 site-packages 等，跨项目可见）；本地克隆模板的 `.venv` 只生成于仓内目录（项目级或唯一临时目录），随项目或临时目录销毁

## 远程部署接入（streamable-http）

服务器经 Docker 部署（Dockerfile 见 `server/mcp_server_rds_supabase/`）后，客户端仅需（远程接入的注册位置约束与上文相同：仅项目级配置，禁止用户级/系统级）：

```json
{
  "mcpServers": {
    "rds-supabase": {
      "type": "streamable_http",
      "url": "http://<部署主机>:8000/mcp"
    }
  }
}
```

## 执行步骤

1. 向用户收集三项信息（上表），逐字核对
2. 将模板中的 `<...>` 占位符替换为实际值，写入**当前项目的项目级 MCP 配置**（唯一允许位置与条目结构见「注册位置强约束」——Claude Code `.mcp.json`、CodeArts `.codeartsdoer/`、OfficeAce 项目级配置、opencode `opencode.json`；**禁止** `~/.claude.json`、Claude Desktop `claude_desktop_config.json`、`~/.config/opencode/` 等一切用户级/系统级位置）
3. 注册后核验落位（条目在项目级配置内、未触碰任何用户级/系统级位置）→ 重启客户端或重载 MCP 配置（注册于项目级配置，重载后仅本项目生效；其他项目不受影响、不可见）；首次启动 uvx 需拉取依赖，稍候
4. 验证：
   - `get_project_url` 返回值应与 SUPABASE_URL 一致
   - `list_tables` 返回表清单（或明确的错误说明）
   - 完整验证清单见 verification-method.md
5. 安装完成后向用户报告：接入方式（stdio / streamable-http）、只读模式状态、execute_sql 可用性

## 失败排查

- 依赖拉取失败：检查网络；私有仓库需配置 Git 凭证
- 401 / 403：核对密钥与 URL（应为网关地址，非数据库地址）
- execute_sql 报函数缺失：部署 `sql/mcp-execute-sql.sql`（见 mcp-installation-guide.md）
- 其余错误码与含义见 related-tools.md
