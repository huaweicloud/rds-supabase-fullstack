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

注册到**当前项目**的 MCP 配置：opencode 用项目 `opencode.json`（V2 结构 `mcp.servers.*`）；Claude Code / Cursor / Trae 用项目 `.mcp.json`；CodeArts用 `mcp_settings.json`（设置页「MCP工具 → 配置MCP」打开，项目级落位 `<项目根>/.codeartsdoer/`；`mcpServers` 条目结构同 `.mcp.json`，下述模板直接可用）。禁止注册到用户级/全局配置——凭据与项目绑定，全局注册等于跨项目泄漏。写入前确认目标配置文件已被 `.gitignore` 覆盖（凭据不随仓库提交）；宿主支持 `${ENV}` 引用时，优先用环境变量引用而不是内联明文。

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
        "HUAWEICLOUD_REGION": "<区域，如 cn-east-3；安全组工具的 KooCLI 通道用>",
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

opencode 项目 `opencode.json` 等价写法（V2 结构：服务器条目位于 `mcp.servers` 之下，不直接挂在 `mcp` 下；凭据可用 `{env:NAME}` 引用环境变量，避免明文入文件）：

```json
{
  "mcp": {
    "servers": {
      "rds-supabase-mgr": {
        "type": "local",
        "command": ["uvx", "--from", "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr", "mcp-huaweicloud-rds-supabase-mgr"],
        "environment": {
          "SUPABASE_TRANSPORT": "sdk_core",
          "SUPABASE_RDS_ENDPOINT": "<原生 RDS HTTPS 端点>",
          "HUAWEICLOUD_PROJECT_ID": "<项目 ID>",
          "HUAWEICLOUD_ACCESS_KEY": "<AK>",
          "HUAWEICLOUD_SECRET_KEY": "<SK>",
          "HUAWEICLOUD_MCP_READ_ONLY": "true",
          "SUPABASE_ENABLE_WRITES": "false"
        }
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

**Token 模式的安全组限制**：安全组五工具走 KooCLI 通道、只认 AK/SK（或本机 hcloud profile）。Token 模式下这五个工具会报凭据缺失——要用安全组工具，要么本机执行一次 `hcloud configure init` 配好 profile，要么改用模板一的 AK/SK 模式。

**模式选错的症状（记住这个坑）**：只填 AK/SK 不设 `SUPABASE_TRANSPORT=sdk_core`，服务端按 REST 模式启动并**完全忽略 AK/SK**，每次调用报 `MCP_PERMISSION_DENIED`。反过来，REST 模式没配 `HUAWEICLOUD_AUTH_TOKEN` 也是这个错。

**首次接入保持只读**：`HUAWEICLOUD_MCP_READ_ONLY=true`、`SUPABASE_ENABLE_WRITES=false`，验证通过后再按需放开——放开是**两个变量一起改**：`SUPABASE_ENABLE_WRITES=true` 且 `HUAWEICLOUD_MCP_READ_ONLY=false`，改完重启 MCP（只改一个会继续被拦）。凭据值从项目配置/秘密存储注入进程，不进对话、不进代码仓。

### 会话内使能（动态安装后免重启）

配置写入项目级文件后，**当前会话**即可使能，不需要退出重进：

| 宿主 | 使能方式 | 核对 |
|---|---|---|
| opencode | 保存 `opencode.json` 后新服务器**自动连接**；未自动连上时在 `/mcps` 面板选中该服务器连接。等价 CLI：`opencode mcp add rds-supabase-mgr --env K=V -- uvx --from "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr" mcp-huaweicloud-rds-supabase-mgr`（注意 `--env` 的值会留在命令行历史里，写凭据建议直接编辑配置文件） | `opencode mcp list` 或 `/mcps` 显示 connected |
| Claude Code | 保存 `.mcp.json` 后会话内弹出项目服务器**批准提示**（安全机制，每个项目服务器一次），用户批准即连接；提示未弹出时在 `/mcp` 面板找到该服务器批准/连接 | `/mcp` 面板显示 connected 与工具数量 |
| CodeArts | MCP 配置在设置页「MCP工具 → 配置MCP」打开的 `mcp_settings.json` 中编辑（`mcpServers` 结构与 `.mcp.json` 相同，uvx 条目直接复用模板一；服务器名称 ≤64 字符），**保存即启动**（等待"工具启动完成"）；「MCP工具 → 已安装」页签可启用/停用/重启。官方明示：**编辑既有条目后 IDE 缓存可能不自动刷新，须在该页签点一次重启该 MCP** | 「MCP工具 → 已安装」页签显示该服务器且已启用 |
| OfficeAce | 写入项目级 MCP 配置后，在宿主自身的 MCP 管理入口启用/刷新（无公开文档，Agent 在该宿主内按其设置界面操作）；确无会话内机制时按一次性 reload 兜底，如实告知用户——配置已就位，不算安装失败 | 宿主 MCP 管理界面显示已启用 |
| Cursor / Trae / 其他 | 按宿主自身的 MCP 配置刷新机制使能；宿主确实只认重启时，如实告知用户执行一次宿主 reload——配置已就位，属一次性动作，不算安装失败 | 宿主 MCP 面板 |

使能问题的判定顺序：工具列表里没有这个服务器 → 先按上表使能；服务器在但调用报错 → 回下节环境变量核对；进程起不来 → 看宿主 MCP 日志里 uvx 的 stderr（首次启动要拉依赖，稍候属正常）。

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

先确认工具已在本会话可见——列表里调不到这个服务器的工具，是**会话没使能**（回第四节"会话内使能"处理），不是安装失败。然后过三层：

1. **进程层**（不碰云）：克隆方式 `uv run python -m mcp_server_supabase.diagnostics check`（配置格式与依赖）；`offline` 做 stdio 自检
2. **注册层**：宿主里调 `get_supabase_capabilities`，能返回=进程活着；**核对返回的 mode 与预期传输一致**（不一致=模式配错，回第四节）
3. **云端层**：`list_supabase_applications`（limit=1）返回真实数据=凭据、端点、项目全对

三层全过才算"装好使能"，才进场景。
