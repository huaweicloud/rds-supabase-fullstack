# rds-supabase-web-build 安装（AI Agent 一键安装）

面向 AI Agent 的安装指导。用户对 Agent 说：

> 按照 https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-web-build/INSTALL.md ，安装 rds-supabase-web-build 技能；装完告诉我如何触发建站。

Agent 按本文四节执行。安装范围**仅本技能**——不安装、不配置任何 MCP、凭据与云资源；MCP 与凭据在九步工作流内按需动态安装（见下表）。

## 一、安装范围

| 项 | 何时 | 来源 |
|---|---|---|
| **本技能（安装阶段的全部内容）** | 现在，一次性 | 本 GitHub 源码仓 `skills/huaweicloud-supabase/rds-supabase-web-build/` |
| 管理面 MCP（29 工具） | 工作流步骤三动态启动 | 本仓 `server/`（不在技能包内） |
| 数据面 MCP（38 工具） | 工作流步骤四动态安装 | 同上；依赖步骤三交付的实例凭据 |
| 凭据 / Region / 接入点 / PROJECT_ID | 工作流步骤一 | 项目内 `.hwsupabase/`（项目级隔离） |

**编排依赖说明**：本技能是编排者，步骤路由指向六个专项技能（mgr-mcp / mcp / usage / frontend / postgres-best-practices / function-graph，均在 `skills/huaweicloud-supabase/` 下）。路由目标缺失时对应环节如实降级：提示用户安装该专项技能后继续，或按能力边界自行执行可直接完成的部分。完整编排体验建议连带安装全部技能。

前置：Agent 支持 Agent Skills 标准；网络可达 GitHub（不可达见方式 B）。

## 二、安装目录（各宿主差异）

**强约束：只装项目级技能目录**——技能版本随项目走，不污染其他项目与本机全局。

| 宿主 | 项目级技能目录（唯一允许） | 禁止的个人级目录（同名不同根） |
|---|---|---|
| CodeArts | `<项目根>/.codeartsdoer/skills/` | `~/.codeartsdoer/skills` |
| opencode | `<项目根>/.opencode/skills/` | `~/.config/opencode/skills` |
| Claude Code | `<项目根>/.claude/skills/` | `~/.claude/skills` |
| 其余宿主 | 该宿主的项目级技能机制（Agent 自知位置，以项目根为界） | 一切系统级与个人级目录 |

- 系统内置/系统级目录一律禁止；CodeArts 两级目录同名不同根，家目录下属个人级、严禁使用
- 安装路径仅本文两条（git 克隆 / ZIP 归档）；**禁用 `npx skills add` 等一切 CLI/包管理器自动安装**——技能包未发布至此类来源渠道，命令不可用；Agent 不得自行尝试

## 三、三步安装

### 第 1 步 · 安装技能文件（方式 A/B 择一）

**方式 A**（git 克隆复制，主路径）：

```bash
TMP=$(mktemp -d)   # 克隆落唯一临时目录，不污染项目目录与家目录
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-web-build" <项目技能目录>/
rm -rf "$TMP"     # 复制完成即清理
```

（连带安装全部技能时，把复制源换成 `"$TMP/repo/skills/huaweicloud-supabase/"*`。）

**方式 B**（网络逃生通道——git 失败即切，不反复重试）：连续失败 2 次或 30 秒无进展即判失败 → 下载 ZIP 归档解压：

```bash
TMP=$(mktemp -d)
curl -L --fail --max-time 120 -o "$TMP/rds.zip" \
  https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
unzip -q "$TMP/rds.zip" -d "$TMP"
cp -r "$TMP/rds-supabase-fullstack-main/skills/huaweicloud-supabase/rds-supabase-web-build" <项目技能目录>/
rm -rf "$TMP"
```

浏览器直接下载该 ZIP URL 亦可（下载物同样落临时目录）。ZIP 归档属本仓官方源；版本 pin 等价形式 `.../archive/<commit>.zip`。

### 第 2 步 · 校验

技能目录内含 `SKILL.md`、`README.md`、`INSTALL.md`、`USER_GUIDE_REPORT.md`、`assets/framework.svg`、`references/`、`scripts/`、`tests/`。

### 第 3 步 · 完成报告

向用户汇报三项：安装路径；触发语句示例（如"帮我建一个博客网站"）；约定说明——MCP 与凭据不在安装阶段出现，首次建站时技能从步骤一环境检查开始逐项处理。

## 四、更新与卸载

- **更新**：`git pull` 后重新复制（重复第 1 步）
- **卸载**：删除项目级技能目录中本技能；工作流曾配置 MCP 的，另移除项目级 MCP 配置中对应条目
