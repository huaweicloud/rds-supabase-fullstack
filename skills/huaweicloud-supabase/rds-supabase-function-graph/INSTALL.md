# rds-supabase-function-graph 安装（AI Agent 一键安装）

安装范围**仅本技能**——技能文档、样板与验证门脚本；不安装、不配置 MCP 服务器、凭据与云资源。云操作全部经 KooCLI（前置条件见 README"前置条件"，在技能触发后的步骤一核对，缺失则提醒安装并停止）。

将下面这句话发送给你的 AI Agent：

> 按照 https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-function-graph/INSTALL.md 安装 rds-supabase-function-graph 技能；装完报告安装路径。

## 一、安装位置选择（必须交互，默认项目级）

前置：Agent 支持 Agent Skills 标准；网络可达 GitHub（不可达见方式 B）。

安装前 Agent **必须**把下表展示给用户、等用户明确选择后才落盘——不许静默安装到任何位置。**默认选项是项目级**（回车/说"默认"即选它）。选用户级或系统级时，Agent 必须复述对应的风险提示并获得用户再次确认。

| 选项 | 目录（按宿主解析） | 生效范围与后果 |
|---|---|---|
| **① 项目级（默认，推荐）** | Claude Code：`<项目根>/.claude/skills/`；opencode：`<项目根>/.opencode/skills/`；CodeArts：`<项目根>/.codeartsdoer/skills/`；其余宿主：该宿主的项目级技能机制 | 仅本项目可见。技能版本随项目走，团队成员各自安装后行为一致；不污染其他项目 |
| ② 用户级 | Claude Code：`~/.claude/skills/`；opencode：`~/.config/opencode/skills/`；CodeArts：`~/.codeartsdoer/skills/`；其余宿主：宿主个人级技能目录 | 本机所有项目可见。你本机任何项目的对话都可能触发本技能；技能升级影响全部项目 |
| ③ 系统级 | 宿主的系统级/内置技能目录（若存在） | 本机所有用户、所有项目可见。影响面最大，一般仅管理员统一预装时使用 |

交互示例：

```
请选择技能安装位置（默认 ①）：
① 项目级（推荐）：<项目根>/.claude/skills/     —— 仅本项目生效
② 用户级：        ~/.claude/skills/            —— 本机全部项目生效，升级影响所有项目
③ 系统级：        <宿主系统级技能目录>          —— 全机所有用户生效，影响面最大
```

风险提示（用户选 ②③ 时必须复述）：
- 用户级/系统级会把技能暴露给无关项目与无关用户，本项目后续升级、卸载都会波及它们
- CodeArts 的 `~/.codeartsdoer/skills` 与项目级 `<项目根>/.codeartsdoer/skills` 同名不同根，极易装错——选 ② 时逐字核对完整路径

## 二、安装方式（A/B 择一）

### 方式 A：git 克隆复制（主路径）

```bash
TMP=$(mktemp -d)   # 克隆落唯一临时目录，不污染项目目录与家目录
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-function-graph" <项目技能目录>/
rm -rf "$TMP"     # 复制完成即清理
```

### 方式 B：ZIP 归档（网络逃生通道——git 连续失败 2 次或 30 秒无进展即切，不反复重试）

```bash
TMP=$(mktemp -d)
curl -L --fail --max-time 120 -o "$TMP/rds.zip" \
  https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
unzip -q "$TMP/rds.zip" -d "$TMP"
cp -r "$TMP/rds-supabase-fullstack-main/skills/huaweicloud-supabase/rds-supabase-function-graph" <项目技能目录>/
rm -rf "$TMP"
```

浏览器直接下载该 ZIP URL 亦可（下载物同样落临时目录）。ZIP 归档属本仓官方源；**禁用 `npx skills add` 等一切 CLI/包管理器自动安装**——技能包未发布至此类来源渠道。

## 三、校验与完成报告

- 校验：技能目录内含 `SKILL.md`、`README.md`、`INSTALL.md`、`references/` 五个参考文档、`template/` 样板、`scripts/fgs-gate.py`、`tests/`
- 向用户报告：安装位置（层级 + 完整路径，须与交互选择一致）；触发语示例（如"给博客加一个交易通知云函数，需要幂等防重放"）；前置提示——首次使用前需 KooCLI 已安装认证、有可用 RDS Supabase 应用与 OBS 桶

## 四、更新与卸载

- **更新**：`git pull` 后重新复制（重复方式 A；版本 pin 等价形式 `.../archive/<commit>.zip`）
- **卸载**：删除项目级技能目录中本技能；已部署的云函数属云端资源，卸载技能不影响，按 SKILL.md 下线规程另行处理
