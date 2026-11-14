# rds-supabase-function-graph 安装（AI Agent 一键安装）

安装范围**仅本技能**——技能文档、样板与验证门脚本；不安装、不配置 MCP 服务器、凭据与云资源。云操作全部经 KooCLI（前置条件见 README"前置条件"，在技能触发后的步骤一核对，缺失则提醒安装并停止）。

将下面这句话发送给你的 AI Agent：

> 按照 https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-function-graph/INSTALL.md 安装 rds-supabase-function-graph 技能；装完报告安装路径。

## 一、安装目录（各宿主差异）

**强约束：只装项目级技能目录**——技能版本随项目走，不污染其他项目与本机全局。

| 宿主 | 项目级技能目录（唯一允许） | 禁止的个人级目录 |
|---|---|---|
| Claude Code | `<项目根>/.claude/skills/` | `~/.claude/skills` |
| opencode | `<项目根>/.opencode/skills/` | `~/.config/opencode/skills` |
| CodeArts | `<项目根>/.codeartsdoer/skills/` | `~/.codeartsdoer/skills` |
| 其余宿主 | 该宿主的项目级技能机制（Agent 自知位置，以项目根为界） | 一切系统级与个人级目录 |

前置：Agent 支持 Agent Skills 标准；网络可达 GitHub（不可达见方式 B）。

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
- 向用户报告：安装路径；触发语示例（如"给博客加一个交易通知云函数，需要幂等防重放"）；前置提示——首次使用前需 KooCLI 已安装认证、有可用 RDS Supabase 应用与 OBS 桶

## 四、更新与卸载

- **更新**：`git pull` 后重新复制（重复方式 A；版本 pin 等价形式 `.../archive/<commit>.zip`）
- **卸载**：删除项目级技能目录中本技能；已部署的云函数属云端资源，卸载技能不影响，按 SKILL.md 下线规程另行处理
