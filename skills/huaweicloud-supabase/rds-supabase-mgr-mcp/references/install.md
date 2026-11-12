# 安装手册：管理面 MCP 的来源、安装与使能

SKILL.md 第二步的展开。安装方式的权威定义是本仓 `server/mcp_server_rds_supabase_mgr/README.md`；本手册把结论固化下来，并给出宿主注册模板。

## 一、来源锁定（先立规矩，再动手）

- **唯一来源**：GitHub 仓库 `https://github.com/huaweicloud/rds-supabase-fullstack` 的 `server/mcp_server_rds_supabase_mgr/` 子目录（源码、README、examples、docs 都在里面）。
- 服务端**没有发布到 PyPI，也没有 npm 包**。`mcp-huaweicloud-rds-supabase-mgr` 是 uv 安装后的入口脚本名，不是 PyPI 包名。
- **禁止**：
  - `uvx mcp-huaweicloud-rds-supabase-mgr`（不带 `--from` 的裸入口名会去 PyPI 解析，命中同名第三方包）
  - `pip install` / `npm install` 任何同名或近名包
  - 从搜索引擎、第三方镜像找"华为云 Supabase MCP"安装
- PyPI 存在同名第三方包——装上就是错误的服务器：工具列表对不上，凭据还发给了不受信代码。**找不到官方包不是去别处搜的理由，是回本仓的理由。**

## 二、前置条件

Python 3.10+ 和 uv：

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 三、安装方式（二选一）

### 方式 A：uvx 直接从 GitHub 运行（推荐，免克隆）

```bash
uvx --from "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr" \
  mcp-huaweicloud-rds-supabase-mgr
```

生产建议在 URL 后加 `@<commit>` 锁定版本（默认跟随分支，分支变更会引入未验证行为）：

```
git+https://github.com/huaweicloud/rds-supabase-fullstack@<commit>#subdirectory=server/mcp_server_rds_supabase_mgr
```

### 方式 B：克隆本仓本地运行（内网/离线/调试）

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack.git
cd rds-supabase-fullstack/server/mcp_server_rds_supabase_mgr
uv sync
uv run mcp-huaweicloud-rds-supabase-mgr          # stdio（默认）
```

两种方式等价；克隆后还可以跑 `uv run python -m mcp_server_supabase.diagnostics check` 做不碰云的自检。

## 四、注册到当前项目（禁止全局）

注册到**当前项目**的 MCP 配置：opencode 用项目 `opencode.json`；Claude Code / Cursor / Trae 用项目 `.mcp.json`（或各自 MCP 配置处，结构相同）。禁止注册到用户级/全局配置——凭据与项目绑定，全局注册等于跨项目泄漏。

**模板一：AK/SK（sdk_core 模式）**——用访问密钥（含临时密钥）必须走这个模式：

```json
{
  "mcpServers": {
    "rds-supabase-mgr-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr",
        "mcp-huaweicloud-rds-supabase-mgr"
      ],
      "env": {
        "SUPABASE_TRANSPORT": "sdk_core",
        "SUPABASE_RDS_ENDPOINT": "<原生 RDS HTTPS 端点>",
        "HUAWEICLOUD_PROJECT_ID": "<项目 ID>",
        "HUAWEICLOUD_ACCESS_KEY": "<AK>",
        "HUAWEICLOUD_SECRET_KEY": "<SK>",
        "HUAWEICLOUD_SECURITY_TOKEN": "<临时密钥才有，永久密钥删掉此行>",
        "HUAWEICLOUD_MCP_READ_ONLY": "true",
        "SUPABASE_ENABLE_WRITES": "false"
      }
    }
  }
}
```

opencode 项目 `opencode.json` 等价写法（键名与嵌套不同）：

```json
{
  "mcp": {
    "rds-supabase-mgr-mcp": {
      "type": "local",
      "command": ["uvx", "--from", "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr", "mcp-huaweicloud-rds-supabase-mgr"],
      "environment": {
        "SUPABASE_TRANSPORT": "sdk_core",
        "SUPABASE_RDS_ENDPOINT": "<原生 RDS HTTPS 端点>",
        "HUAWEICLOUD_PROJECT_ID": "<项目 ID>",
        "HUAWEICLOUD_ACCESS_KEY": "<AK>",
        "HUAWEICLOUD_SECRET_KEY": "<SK>"
      }
    }
  }
}
```

**模板二：服务 Token（REST 模式，默认）**——把 env 换成：

```json
{
  "SUPABASE_RDS_ENDPOINT": "<原生 RDS HTTPS 端点>",
  "HUAWEICLOUD_PROJECT_ID": "<项目 ID>",
  "HUAWEICLOUD_AUTH_TOKEN": "<外部预置的服务 Token>"
}
```

**模式选错的症状（记住这个坑）**：只填 AK/SK 不设 `SUPABASE_TRANSPORT=sdk_core`，服务端按 REST 模式启动并**完全忽略 AK/SK**，每次调用报 `MCP_PERMISSION_DENIED`。反过来，REST 模式没配 `HUAWEICLOUD_AUTH_TOKEN` 也是这个错。

**首次接入保持只读**：`HUAWEICLOUD_MCP_READ_ONLY=true`、`SUPABASE_ENABLE_WRITES=false`，验证通过后再按需放开。凭据值从项目配置/秘密存储注入进程，不进对话、不进代码仓。

## 五、环境变量清单（注册时注入的完整集合）

| 变量 | 何时必填 | 说明 |
|---|---|---|
| `SUPABASE_RDS_ENDPOINT` | 恒必填 | 原生 RDS HTTPS 端点（非 Console、非 /rest 代理）；可由 `diagnostics discover` 推导 |
| `HUAWEICLOUD_PROJECT_ID` | 恒必填 | 目标项目 ID |
| `SUPABASE_TRANSPORT` | AK/SK 模式必填（=sdk_core） | 默认 rest；rest 只认 Token |
| `HUAWEICLOUD_ACCESS_KEY` / `HUAWEICLOUD_SECRET_KEY` | sdk_core 模式必填 | 访问密钥 |
| `HUAWEICLOUD_SECURITY_TOKEN` | 临时密钥必填 | STS Token |
| `HUAWEICLOUD_AUTH_TOKEN` | REST 模式必填 | 外部预置服务 Token |
| `SUPABASE_ENABLE_WRITES` | 需写操作时 =true | 默认 false，云写总开关 |
| `HUAWEICLOUD_MCP_READ_ONLY` | 建议首接 =true | 默认 false；true 拦截所有写工具 |
| `SUPABASE_REQUESTS_FILE` | 走请求别名机制时 | 本地请求文件绝对路径（操作员预置） |
| `SUPABASE_STATE_FILE` | 可选 | 本地执行记录库路径；跨重启保持同一路径 |

护栏类（`HUAWEICLOUD_MCP_PROTECTED_IDS/NAMES/TAGS`、`HUAWEICLOUD_MCP_GUARDRAILS_CONFIG`）与审计类（`HUAWEICLOUD_MCP_AUDIT_FILE`）变量见服务端 README。

## 六、网络逃生通道

uvx 从 GitHub 拉取失败或停滞（连续失败 2 次，或 30 秒无进展，含挂代理后仍不通）→ **立即切换** ZIP 归档 + 本地运行，不要反复重试：

```bash
TMP=$(mktemp -d)
curl -L --fail --max-time 120 -o "$TMP/rds.zip" https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
unzip -q "$TMP/rds.zip" -d "$TMP"
uv run --directory "$TMP/rds-supabase-fullstack-main/server/mcp_server_rds_supabase_mgr" mcp-huaweicloud-rds-supabase-mgr
```

规则：下载物一律落唯一临时目录（`mktemp -d`），不污染项目目录和家目录；MCP 运行期间保留、停止后清理。ZIP 归档属本仓官方源，**不违反来源锁定，但 PyPI/第三方源仍然禁止**。浏览器手动下载同一 URL 也落临时目录。

## 七、装完怎么验证（三层）

1. **进程层**（不碰云）：克隆方式 `uv run python -m mcp_server_supabase.diagnostics check`（配置格式与依赖）；`offline` 做 stdio 自检
2. **注册层**：宿主里调 `get_supabase_capabilities`，能返回=进程活着；**核对返回的 mode 与预期传输一致**（不一致=模式配错，回第四节）
3. **云端层**：`list_supabase_applications`（limit=1）返回真实数据=凭据、端点、项目全对

三层全过才算"装好使能"，才进场景。
