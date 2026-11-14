# rds-supabase-mgr-mcp 安装（AI Agent 一键安装）

安装范围**仅本技能**——不安装、不配置任何 MCP 服务器、凭据与云资源。管理面 MCP 服务器在技能触发后的环境检查环节由 Agent 动态安装使能（会话内免重启），规程见 [SKILL.md](SKILL.md) 与 [references/install.md](references/install.md)。

将下面这句话发送给你的 AI Agent：

> 按照 https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-mgr-mcp/INSTALL.md 安装 rds-supabase-mgr-mcp 技能；装完报告安装路径。

## 一、安装范围

| 项 | 何时 | 来源 |
|---|---|---|
| **本技能（安装阶段的全部内容）** | 现在，一次性 | 本仓 `skills/huaweicloud-supabase/rds-supabase-mgr-mcp/` |
| 管理面 MCP 服务器（29 工具） | 技能触发后环境检查通过时动态安装 | 本仓 `server/mcp_server_rds_supabase_mgr/`（不在技能包内，uvx 从 GitHub 直装） |
| 凭据（AK/SK 或 Token）、Region、PROJECT_ID | 首次使用时 | 项目内受保护文件/用户提供 |

前置：Agent 支持 Agent Skills 标准；网络可达 GitHub（不可达见方式 B）。

## 二、安装目录（各宿主差异）

**强约束：只装项目级技能目录**——技能版本随项目走，不污染其他项目与本机全局。

| 宿主 | 项目级技能目录（唯一允许） | 禁止的个人级目录 |
|---|---|---|
| Claude Code | `<项目根>/.claude/skills/` | `~/.claude/skills` |
| opencode | `<项目根>/.opencode/skills/` | `~/.config/opencode/skills` |
| CodeArts | `<项目根>/.codeartsdoer/skills/` | `~/.codeartsdoer/skills` |
| 其余宿主 | 该宿主的项目级技能机制（Agent 自知位置，以项目根为界） | 一切系统级与个人级目录 |

## 三、安装方式（A/B 择一）

### 方式 A：git 克隆复制（主路径）

```bash
TMP=$(mktemp -d)   # 克隆落唯一临时目录，不污染项目目录与家目录
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-mgr-mcp" <项目技能目录>/
rm -rf "$TMP"     # 复制完成即清理
```

### 方式 B：ZIP 归档（网络逃生通道——git 连续失败 2 次或 30 秒无进展即切，不反复重试）

```bash
TMP=$(mktemp -d)
curl -L --fail --max-time 120 -o "$TMP/rds.zip" \
  https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
unzip -q "$TMP/rds.zip" -d "$TMP"
cp -r "$TMP/rds-supabase-fullstack-main/skills/huaweicloud-supabase/rds-supabase-mgr-mcp" <项目技能目录>/
rm -rf "$TMP"
```

浏览器直接下载该 ZIP URL 亦可（下载物同样落临时目录）。ZIP 归档属本仓官方源；**任何情况下禁止去 PyPI/npm/第三方镜像找同名包**——服务端未发布至此类渠道，同名第三方包是错误的服务器。

## 四、校验与完成报告

- 校验：技能目录内含 `SKILL.md`、`README.md`、`INSTALL.md`、`references/` 五个参考文档、`scripts/skill-lint.py`
- 向用户报告：安装路径；一句话触发语（如"帮我从零创建一个 RDS Supabase 应用"）；约定说明——MCP 与凭据不在安装阶段出现，首次使用时技能自动引导

## 五、更新与卸载

- **更新**：`git pull` 后重新复制（重复方式 A；版本 pin 等价形式 `.../archive/<commit>.zip`）
- **卸载**：删除项目级技能目录中本技能；技能曾动态安装管理面 MCP 的，另移除项目级 MCP 配置中对应条目
